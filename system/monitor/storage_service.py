import os
import shutil


class StorageService:
    """存储服务 - 负责磁盘空间管理"""

    def __init__(self, signals):
        self.signals = signals

    def get_project_root(self):
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def get_disk_space_info(self):
        try:
            app_path = self.get_project_root()
            total, used, free = shutil.disk_usage(app_path)
            total_gb = round(total / (1024 ** 3), 1)
            used_gb = round(used / (1024 ** 3), 1)
            used_percent = round(used / total * 100, 1) if total > 0 else 0
            print(f"[StorageService] 磁盘空间: 总{total_gb}GB, 已用{used_gb}GB({used_percent}%), 可用{round(free/(1024**3),1)}GB")
            return total_gb, used_gb, used_percent
        except Exception as e:
            print(f"[StorageService] 获取磁盘空间失败: {e}")
            return 0, 0, 0

    def _get_dir_size(self, path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    if os.path.exists(filepath) and not os.path.islink(filepath):
                        total_size += os.path.getsize(filepath)
                except Exception:
                    pass
        return total_size

    def get_app_size_info(self, total_gb):
        try:
            app_path = self.get_project_root()
            app_size = self._get_dir_size(app_path)
            app_size_gb = round(app_size / (1024 ** 3), 3)
            app_percent = round(app_size_gb / total_gb * 100, 1) if total_gb > 0 else 0
            return app_size_gb, app_percent
        except Exception as e:
            print(f"[StorageService] 获取软件大小失败: {e}")
            return 0, 0

    def emit_disk_space_info(self):
        total_gb, used_gb, used_percent = self.get_disk_space_info()
        self.signals.disk_space_updated.emit(total_gb, used_gb, used_percent)
