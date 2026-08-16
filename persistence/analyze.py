"""DuckDB 全量分析示例 —— ML 特征工程原型（直接扫描 SQLite 全量数据）

设计：App 运行时继续用 SQLite（实时写入 + 有界采样 UI 读取）；
需要"读全部"的分析/ML 场景走 DuckDB —— 列存 + 向量化，聚合秒级。

依赖: duckdb（sqlite_scanner 扩展首次使用需联网下载）

用法:
    python -m persistence.analyze
    python -m persistence.analyze --db D:\\x\\hypebeat.db
"""

import argparse
import os
import sys


def _default_db_path():
    try:
        from system.settings.settings_manager import SettingsManager
        return os.path.join(SettingsManager().get_db_directory(), "hypebeat.db")
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".heartrate_monitor", "hypebeat.db")


def _quote_sql(s):
    return s.replace("'", "''")


def _open_duckdb(db_path):
    try:
        import duckdb
    except ImportError:
        print("[Analyze] 错误: 未安装 duckdb。请先执行: pip install duckdb")
        return None

    con = duckdb.connect()
    try:
        con.execute("INSTALL sqlite")
        con.execute("LOAD sqlite")
    except Exception as e:
        print(f"[Analyze] 错误: 无法加载 sqlite 扩展（首次使用需联网下载）: {e}")
        return None

    q = f"sqlite_scan('{_quote_sql(db_path)}', 'heart_rate')"
    # 校验表可读
    try:
        con.execute(f"SELECT COUNT(*) FROM {q}").fetchone()
    except Exception as e:
        print(f"[Analyze] 错误: 无法读取 {db_path}: {e}")
        return None
    return con, q


def analyze(db_path):
    opened = _open_duckdb(db_path)
    if opened is None:
        return False
    con, q = opened

    try:
        # 1) 总量与时间跨度
        total, tmin, tmax = con.execute(
            f"SELECT COUNT(*), MIN(ts), MAX(ts) FROM {q}"
        ).fetchone()
        from datetime import datetime, timezone
        print(f"总记录: {total:,} 条")
        if tmin is not None:
            print(f"时间跨度: {datetime.fromtimestamp(tmin/1000, timezone.utc):%Y-%m-%d %H:%M} ~ "
                  f"{datetime.fromtimestamp(tmax/1000, timezone.utc):%Y-%m-%d %H:%M} (UTC)")
        print()

        # 2) 最近 30 天按日聚合（趋势特征）
        print("== 近 30 天按日 ==")
        rows = con.execute(f"""
            SELECT strftime(to_timestamp(ts / 1000), '%Y-%m-%d') AS day,
                   COUNT(*)                        AS n,
                   ROUND(AVG(hr), 1)               AS avg_hr,
                   MAX(hr)                         AS max_hr,
                   MIN(hr)                         AS min_hr
            FROM {q}
            GROUP BY day
            ORDER BY day DESC
            LIMIT 30
        """).fetchall()
        for day, n, avg, mx, mn in rows:
            print(f"  {day}  n={n:>7,}  avg={avg:>6}  max={mx:>3}  min={mn:>3}")
        print()

        # 3) 24 小时均值曲线（节律特征）
        print("== 24h 小时均值 ==")
        rows = con.execute(f"""
            SELECT (ts // 3600000) % 24 AS hour,
                   COUNT(*)            AS n,
                   ROUND(AVG(hr), 1)   AS avg_hr
            FROM {q}
            GROUP BY hour
            ORDER BY hour
        """).fetchall()
        print("  " + "  ".join(f"{h:>2}h:{a}" for h, n, a in rows))
        print()

        # 4) 分钟级窗口聚合（滑动窗口特征原型：每 5 分钟均值/极差/条数）
        print("== 最近 20 个 5 分钟窗口 ==")
        rows = con.execute(f"""
            SELECT ts // 300000 AS bucket,
                   COUNT(*)    AS n,
                   ROUND(AVG(hr), 1) AS avg_hr,
                   MAX(hr) - MIN(hr) AS range_hr
            FROM {q}
            GROUP BY bucket
            ORDER BY bucket DESC
            LIMIT 20
        """).fetchall()
        for bucket, n, avg, rng in rows:
            print(f"  bucket={bucket}  n={n:>4}  avg={avg:>6}  range={rng:>3}")
        print()

        # 5) 5 分钟滑动均值（窗口函数原型，ML 时序特征）
        print("== 每 5 分钟一档的滑动均值（最近 10 档，窗口函数） ==")
        rows = con.execute(f"""
            WITH minute_avg AS (
                SELECT ts // 60000 AS bucket_min,
                       AVG(hr)     AS avg_hr
                FROM {q}
                GROUP BY bucket_min
            )
            SELECT bucket_min,
                   ROUND(avg_hr, 1) AS avg_hr,
                   ROUND(AVG(avg_hr) OVER (ORDER BY bucket_min ROWS BETWEEN 4 PRECEDING AND CURRENT ROW), 1) AS ma5
            FROM minute_avg
            ORDER BY bucket_min DESC
            LIMIT 10
        """).fetchall()
        for bucket, avg, ma5 in rows:
            print(f"  min_bucket={bucket}  avg={avg:>6}  ma5={ma5:>6}")
        print()

        con.close()
        return True
    except Exception as e:
        print(f"[Analyze] 分析失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="DuckDB 全量分析示例（ML 特征原型）")
    parser.add_argument("--db", default=None, help="SQLite 数据库路径（默认自动定位）")
    args = parser.parse_args()

    db_path = args.db or _default_db_path()
    print(f"[Analyze] 数据库: {db_path}")
    sys.exit(0 if analyze(db_path) else 1)


if __name__ == "__main__":
    main()
