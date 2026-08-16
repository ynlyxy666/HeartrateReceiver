import os
import sqlite3
import threading
from datetime import datetime, timezone


class DataManager:
    def __init__(self, settings_manager=None, batch_size=50):
        """
        初始化数据管理器（SQLite 后端）

        Args:
            settings_manager: 设置管理器实例，用于获取数据库目录
            batch_size: 每多少个数据写一次数据库，默认50
        """
        self.batch_size = batch_size
        self.data_buffer = []
        # 防止数据库持续故障时缓冲无限膨胀（200 万行 ≈ 16MB 内存上限）
        self.MAX_BUFFER_ROWS = 2_000_000
        self.lock = threading.Lock()
        self.settings_manager = settings_manager

        if self.settings_manager:
            db_dir = self.settings_manager.get_db_directory()
        else:
            db_dir = self._get_project_root()
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "hypebeat.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_table()
        print(f"[DataManager] SQLite初始化完成: {db_path}, 批量写入阈值={batch_size}条")

    def _get_project_root(self):
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _init_table(self):
        """初始化 heart_rate 表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS heart_rate (
                id  INTEGER PRIMARY KEY AUTOINCREMENT,
                ts  INTEGER NOT NULL,   -- Unix 毫秒时间戳
                hr  INTEGER NOT NULL    -- 心率值 (BPM)
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_hr_ts ON heart_rate(ts)")
        self.conn.commit()

    def collect_data(self, heart_rate):
        """
        收集心率数据

        Args:
            heart_rate: 心率值
        """
        if heart_rate == 0:
            return

        with self.lock:
            timestamp = int(datetime.now().timestamp() * 1000)
            self.data_buffer.append((timestamp, heart_rate))

            if len(self.data_buffer) >= self.batch_size:
                self.write_data()

    def write_data(self):
        """将缓冲数据批量写入 SQLite

        使用事务上下文（with self.conn）：异常时自动 ROLLBACK，避免悬挂事务
        导致下次写入把半截数据提交；仅在成功后清空缓冲，失败保留数据供重试。
        为防止数据库持续故障时缓冲无限膨胀，超过 MAX_BUFFER_ROWS 直接丢弃。

        Returns:
            bool: 是否写入成功
        """
        if not self.data_buffer:
            return True

        batch = self.data_buffer[:]
        try:
            with self.conn:  # 成功 commit / 异常 rollback
                self.conn.executemany(
                    "INSERT INTO heart_rate (ts, hr) VALUES (?, ?)", batch
                )
            self.data_buffer = []
            print(f"[DataManager] 批量写入完成: {len(batch)} 条")
            return True
        except Exception as e:
            print(f"[DataManager] 写入数据库出错: {e}")
            if len(self.data_buffer) > self.MAX_BUFFER_ROWS:
                print(f"[DataManager] 缓冲超过 {self.MAX_BUFFER_ROWS} 条，丢弃防内存膨胀")
                self.data_buffer = []
            return False

    def flush_data(self):
        """确保所有数据写入数据库（返回是否全部写入成功）"""
        with self.lock:
            if self.data_buffer:
                ok = self.write_data()
                if ok:
                    print("[DataManager] 数据已刷新写入")
                else:
                    print("[DataManager] 警告: 退出时仍有数据未写入数据库")
                return ok
            return True

    def clear_temp_buffer(self):
        """清空临时缓存，不影响 SQLite 已有数据"""
        with self.lock:
            count = len(self.data_buffer)
            self.data_buffer.clear()
            print(f"[DataManager] 临时缓存已清空 ({count} 条)")

    def get_record_count(self):
        """获取数据库中已有的心率记录总数"""
        try:
            with self.lock:
                cursor = self.conn.execute("SELECT COUNT(*) FROM heart_rate")
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"[DataManager] 获取记录数失败: {e}")
            return 0

    def get_daily_record_counts(self, days=7):
        """获取最近 N 天每天的记录数

        用整数日桶 (ts / 86400000) 分组替代逐行 strftime，大数据量下快约 2 倍；
        日键按 UTC 纪元日划分，与旧实现（unixepoch）语义一致。

        Returns:
            list[tuple[str, int]]: [(日期字符串, 记录数), ...]，按日期升序
        """
        try:
            now = datetime.now().timestamp() * 1000
            start_ts = int(now - days * 86400 * 1000)
            with self.lock:
                cursor = self.conn.execute(
                    """SELECT (ts / 86400000) AS day,
                              COUNT(*) AS cnt
                       FROM heart_rate
                       WHERE ts >= ?
                       GROUP BY day
                       ORDER BY day ASC""",
                    (start_ts,)
                )
                return [
                    (
                        datetime.fromtimestamp(row[0] * 86400, timezone.utc).strftime('%m-%d'),
                        row[1]
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            print(f"[DataManager] 获取日记录数失败: {e}")
            return []

    def get_sampled_heart_rate(self, start_ts_ms=None, max_points=800):
        """按时间窗口取均匀步长采样，最多返回 max_points 个点。

        流式游标 + 步长抽样：不把窗口内全部数据装入内存，耗时/内存与数据总量
        基本无关（随窗口行数线性扫描，但只保留采样点）。适合几十万~百万级数据。

        Args:
            start_ts_ms: 起始时间戳（毫秒），None 表示全部历史
            max_points: 返回的最大点数（均匀降采样）

        Returns:
            tuple[list[float], list[int], int]: (时间戳列表(秒), 心率值列表, 窗口总条数)
        """
        try:
            with self.lock:
                if start_ts_ms is not None:
                    where = "WHERE ts >= ?"
                    params = (int(start_ts_ms),)
                else:
                    where = ""
                    params = ()

                total = self.conn.execute(
                    f"SELECT COUNT(*) FROM heart_rate {where}", params
                ).fetchone()[0]

                # 向上取整保证点数不超过 max_points（与 windows 版本算法一致）
                stride = max(1, (total + max_points - 1) // max_points)
                timestamps, values = [], []
                cursor = self.conn.execute(
                    f"SELECT ts, hr FROM heart_rate {where} ORDER BY ts", params
                )
                for i, row in enumerate(cursor):
                    if i % stride == 0:
                        ts_sec = row[0] / 1000  # 毫秒 → 秒
                        hr = row[1]
                        if 30 <= hr <= 250:
                            timestamps.append(ts_sec)
                            values.append(hr)
                return timestamps, values, total
        except Exception as e:
            print(f"[DataManager] 获取采样心率数据失败: {e}")
            return [], [], 0

    def get_sampled_heart_rate_windows(self, windows, max_points=800, max_load=2_000_000):
        """单次有序扫描，为多个时间窗口分别做均匀步长采样。

        相比逐窗口各自查询：只扫一遍表，各窗口用 numpy 掩码 + 等间隔取点，
        避免大数据量下重复全表扫描。内存有界：超过 max_load 条时只取最新 max_load 条。

        Args:
            windows: list[(name, start_ts_ms_or_None)]，None 表示该窗口不限起点
            max_points: 每个窗口最多返回的点数
            max_load: 单次加载的行数上限（峰值内存约 100MB/百万条：列表+numpy 并存）

        Returns:
            dict[name] -> (时间戳列表(秒), 心率值列表, 窗口内总条数)
        """
        empty = {name: ([], [], 0) for name, _ in windows}
        try:
            with self.lock:
                total = self.conn.execute("SELECT COUNT(*) FROM heart_rate").fetchone()[0]
                if total == 0:
                    return empty

                if total <= max_load:
                    cursor = self.conn.execute(
                        "SELECT ts, hr FROM heart_rate ORDER BY ts"
                    )
                else:
                    # 只取最新 max_load 条（倒序 LIMIT 后再升序），保证内存有界
                    cursor = self.conn.execute(
                        "SELECT ts, hr FROM ("
                        "  SELECT ts, hr FROM heart_rate ORDER BY ts DESC LIMIT ?"
                        ") ORDER BY ts",
                        (int(max_load),),
                    )

                ts_list, hr_list = [], []
                for row in cursor:
                    hr = row[1]
                    if 30 <= hr <= 250:
                        ts_list.append(row[0] / 1000)
                        hr_list.append(hr)
                del cursor

                import numpy as np
                ts_arr = np.asarray(ts_list, dtype=np.float64)
                hr_arr = np.asarray(hr_list, dtype=np.int64)
                del ts_list, hr_list

                results = {}
                for name, start_ms in windows:
                    if start_ms is None:
                        idx = np.arange(len(ts_arr))
                        window_total = len(ts_arr)
                    else:
                        idx = np.nonzero(ts_arr >= start_ms / 1000)[0]
                        window_total = int(idx.size)
                    stride = max(1, (window_total + max_points - 1) // max_points)
                    take = idx[::stride]
                    results[name] = (
                        ts_arr[take].tolist(),
                        hr_arr[take].tolist(),
                        window_total,
                    )
                return results
        except Exception as e:
            print(f"[DataManager] 获取窗口采样数据失败: {e}")
            return empty

    def get_all_heart_rate_data(self, limit=None):
        """获取心率数据，按时间升序排列（可选限制条数，取最新的 N 条）

        Args:
            limit: 最多返回多少条（取最新），None 表示全部

        Returns:
            tuple[list[float], list[int]]: (时间戳列表(秒), 心率值列表)
        """
        try:
            with self.lock:
                if limit and limit > 0:
                    # 先取最新的 N 条，再升序返回，保证语义与全量查询一致
                    cursor = self.conn.execute(
                        "SELECT ts, hr FROM ("
                        "  SELECT ts, hr FROM heart_rate ORDER BY ts DESC LIMIT ?"
                        ") ORDER BY ts",
                        (int(limit),)
                    )
                else:
                    cursor = self.conn.execute(
                        "SELECT ts, hr FROM heart_rate ORDER BY ts"
                    )
                timestamps, values = [], []
                for row in cursor:
                    ts_sec = row[0] / 1000  # 毫秒 → 秒
                    hr = row[1]
                    if 30 <= hr <= 250:
                        timestamps.append(ts_sec)
                        values.append(hr)
            return timestamps, values
        except Exception as e:
            print(f"[DataManager] 获取心率数据失败: {e}")
            return [], []

    def clear_all_data(self):
        """清空所有数据（包括 SQLite 和缓存）"""
        with self.lock:
            count = len(self.data_buffer)
            self.data_buffer.clear()
            self.conn.execute("DELETE FROM heart_rate")
            self.conn.commit()
            print(f"[DataManager] 所有数据已清空（丢弃缓存 {count} 条）")
