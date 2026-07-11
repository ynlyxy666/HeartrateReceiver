import os
import sqlite3
import threading
from datetime import datetime


class DataManager:
    def __init__(self, batch_size=50):
        """
        初始化数据管理器（SQLite 后端）

        Args:
            batch_size: 每多少个数据写一次数据库，默认50
        """
        self.batch_size = batch_size
        self.data_buffer = []
        self.lock = threading.Lock()

        db_path = os.path.join(self._get_project_root(), "hypebeat.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_table()

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
            self.conn.executemany(
                "INSERT INTO heart_rate (ts, hr) VALUES (?, ?)", self.data_buffer
            )
            self.conn.commit()
            self.data_buffer = []
        except Exception as e:
            print(f"写入数据库出错: {e}")

    def flush_data(self):
        """确保所有数据写入数据库"""
        if self.data_buffer:
            self.write_data()
