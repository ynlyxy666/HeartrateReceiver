"""将 SQLite 心率数据全量导出为 Parquet（供 ML / 全量分析使用）

设计：SQLite 继续担任实时写入存储（App 运行时不变）；
DuckDB 作为全量分析/ML 读取层，直接扫描 SQLite 文件或导出列存 Parquet。

依赖: duckdb（sqlite_scanner 扩展首次使用需联网下载）

用法:
    python -m persistence.export_to_parquet
    python -m persistence.export_to_parquet --output D:\\heart_rate.parquet
    python -m persistence.export_to_parquet --db D:\\x\\hypebeat.db --no-checkpoint

注意（WAL）:
    App 在 WAL 模式下写入，最近的数据可能还在 -wal 文件里未合并到主库。
    DuckDB 的 sqlite_scanner 直接读主库文件，可能读不到这部分数据。
    本脚本默认先执行 PRAGMA wal_checkpoint(TRUNCATE) 尽力合并；
    App 正在运行时 checkpoint 可能返回 busy（此时仅警告，不阻塞导出）。
"""

import argparse
import os
import sqlite3
import sys


def _default_db_path():
    """与 DataManager 保持一致：优先取 SettingsManager 的数据库目录"""
    try:
        from system.settings.settings_manager import SettingsManager
        return os.path.join(SettingsManager().get_db_directory(), "hypebeat.db")
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".heartrate_monitor", "hypebeat.db")


def _quote_sql(s):
    """SQL 字符串字面量转义（Windows 路径可能含单引号/反斜杠）"""
    return s.replace("'", "''")


def _checkpoint_wal(db_path):
    """WAL checkpoint（TRUNCATE），尽量把 -wal 中未合并的数据刷回主库。

    返回 True 表示完全成功；busy/异常时返回 False（仅提示，不阻塞导出）。
    """
    try:
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            # 返回 (busy, log, checkpointed)
            if row is not None and row[0] == 0:
                print(f"[Export] WAL checkpoint 完成: 合并 {row[2]} 页")
                return True
            print(f"[Export] 警告: WAL checkpoint 未完全执行 (busy={row[0] if row else '?'})，"
                  "可能缺失最近未提交到主库的数据")
            return False
        finally:
            conn.close()
    except Exception as e:
        print(f"[Export] 警告: WAL checkpoint 失败: {e}")
        return False


def export_to_parquet(db_path, output_path, checkpoint=True):
    """全量导出 SQLite heart_rate 表为 Parquet，返回是否成功"""
    try:
        import duckdb
    except ImportError:
        print("[Export] 错误: 未安装 duckdb。请先执行: pip install duckdb")
        return False

    if not os.path.exists(db_path):
        print(f"[Export] 错误: 数据库不存在: {db_path}")
        return False

    if checkpoint:
        _checkpoint_wal(db_path)

    # 用 Python sqlite3 读取权威行数（能正确读到 WAL 数据），
    # 用于导出后交叉校验，检测 checkpoint 失败导致的 WAL 数据缺失
    authoritative_total = None
    try:
        src = sqlite3.connect(db_path)
        try:
            authoritative_total = src.execute(
                "SELECT COUNT(*) FROM heart_rate"
            ).fetchone()[0]
        finally:
            src.close()
    except Exception as e:
        print(f"[Export] 警告: 无法读取权威行数（跳过交叉校验）: {e}")

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        con = duckdb.connect()
        # sqlite_scanner 是外部扩展，首次使用需要联网下载
        try:
            con.execute("INSTALL sqlite")
            con.execute("LOAD sqlite")
        except Exception as e:
            print(f"[Export] 错误: 无法加载 sqlite 扩展（首次使用需联网下载）: {e}")
            return False

        q_db = _quote_sql(db_path)
        q_out = _quote_sql(output_path)
        sql = f"SELECT ts, hr FROM sqlite_scan('{q_db}', 'heart_rate')"

        # 全量导出为列存 Parquet（数据量再大也只需一次向量化扫描）
        con.execute(f"COPY ({sql}) TO '{q_out}' (FORMAT PARQUET)")

        # 导出后快速统计（直接读 Parquet，验证产物）
        n = con.execute(f"SELECT COUNT(*) FROM '{q_out}'").fetchone()[0]
        if authoritative_total is not None and n != authoritative_total:
            print(f"[Export] 警告: Parquet 行数 {n:,} 与 SQLite 权威行数 "
                  f"{authoritative_total:,} 不一致，可能有 WAL 数据未被导出")
        span = con.execute(f"SELECT MIN(ts), MAX(ts) FROM '{q_out}'").fetchone()
        size = os.path.getsize(output_path) / 1024 / 1024
        print(f"[Export] 完成: {n:,} 条 -> {output_path} ({size:.1f} MB)")
        if span[0] is not None:
            from datetime import datetime, timezone
            print(f"[Export] 时间范围: "
                  f"{datetime.fromtimestamp(span[0] / 1000, timezone.utc):%Y-%m-%d %H:%M} ~ "
                  f"{datetime.fromtimestamp(span[1] / 1000, timezone.utc):%Y-%m-%d %H:%M} (UTC)")
        con.close()
        return True
    except Exception as e:
        print(f"[Export] 导出失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="导出 SQLite 心率数据为 Parquet（ML/全量分析用）")
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.expanduser("~"), "heart_rate.parquet"),
        help="Parquet 输出路径（默认 ~/heart_rate.parquet）",
    )
    parser.add_argument("--db", default=None, help="SQLite 数据库路径（默认自动定位）")
    parser.add_argument("--no-checkpoint", action="store_true", help="跳过 WAL checkpoint")
    args = parser.parse_args()

    db_path = args.db or _default_db_path()
    print(f"[Export] 数据库: {db_path}")
    ok = export_to_parquet(db_path, args.output, checkpoint=not args.no_checkpoint)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
