"""
将 hypebeat.db 中的心率数据备份为 CSV 到 D:\

用法:
    python -m persistence.backup_to_csv
"""

import os
import csv
import sqlite3
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "hypebeat.db")
BACKUP_PATH = r"D:\heart_rate_backup.csv"

BATCH_SIZE = 50000


def backup():
    if not os.path.exists(DB_PATH):
        print(f"[错误] 数据库不存在: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    total = 0

    with open(BACKUP_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "heart_rate_bpm"])

        offset = 0
        while True:
            rows = conn.execute(
                "SELECT ts, hr FROM heart_rate ORDER BY ts LIMIT ? OFFSET ?",
                (BATCH_SIZE, offset)
            ).fetchall()
            if not rows:
                break
            writer.writerows(rows)
            total += len(rows)
            offset += BATCH_SIZE
            print(f"  已备份 {total:,} 条...", end="\r")

    conn.close()

    size_kb = os.path.getsize(BACKUP_PATH) / 1024
    print(f"\n✅ 备份完成！")
    print(f"   文件: {BACKUP_PATH}")
    print(f"   记录: {total:,} 条")
    print(f"   大小: {size_kb:.1f} KB")
    return True


if __name__ == "__main__":
    backup()
