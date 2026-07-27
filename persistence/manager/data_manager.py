import os
import sqlite3
import threading
from datetime import datetime


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
        """将缓冲数据批量写入 SQLite"""
        if not self.data_buffer:
            return

        try:
            batch = self.data_buffer[:]
            self.conn.executemany(
                "INSERT INTO heart_rate (ts, hr) VALUES (?, ?)", batch
            )
            self.conn.commit()
            self.data_buffer = []
            print(f"[DataManager] 批量写入完成: {len(batch)} 条")
        except Exception as e:
            print(f"[DataManager] 写入数据库出错: {e}")

    def flush_data(self):
        """确保所有数据写入数据库"""
        if self.data_buffer:
            self.write_data()
        print("[DataManager] 数据已刷新写入")

    def clear_temp_buffer(self):
        """清空临时缓存，不影响 SQLite 已有数据"""
        with self.lock:
            count = len(self.data_buffer)
            self.data_buffer.clear()
            print(f"[DataManager] 临时缓存已清空 ({count} 条)")

    def get_record_count(self):
        """获取数据库中已有的心率记录总数"""
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM heart_rate")
            return cursor.fetchone()[0]
        except Exception as e:
            print(f"[DataManager] 获取记录数失败: {e}")
            return 0

    def get_daily_record_counts(self, days=7):
        """获取最近 N 天每天的记录数

        Returns:
            list[tuple[str, int]]: [(日期字符串, 记录数), ...]，按日期升序
        """
        try:
            now = datetime.now().timestamp() * 1000
            start_ts = int(now - days * 86400 * 1000)
            cursor = self.conn.execute(
                """SELECT strftime('%m-%d', ts / 1000, 'unixepoch') AS day,
                          COUNT(*) AS cnt
                   FROM heart_rate
                   WHERE ts >= ?
                   GROUP BY day
                   ORDER BY day ASC""",
                (start_ts,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"[DataManager] 获取日记录数失败: {e}")
            return []

    def clear_all_data(self):
        """清空所有数据（包括 SQLite 和缓存）"""
        self.clear_temp_buffer()
        self.conn.execute("DELETE FROM heart_rate")
        self.conn.commit()
        print("[DataManager] 所有数据已清空")
