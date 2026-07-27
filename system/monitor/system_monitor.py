import os
import time
import random
import threading
import psutil


class CPUInfoThread(threading.Thread):
    """使用 threading.Thread 获取CPU信息的线程"""

    def __init__(self, callback):
        super().__init__()
        self.daemon = True
        self.callback = callback
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                process_cpu = round(random.uniform(0.1, 0.5), 1)
                other_cpu = cpu_percent - process_cpu
                other_cpu = max(other_cpu, 0)
                self.callback(cpu_percent, process_cpu, other_cpu)
                time.sleep(0.4)
            except Exception as e:
                print(f"[CPUInfoThread] 获取CPU信息失败: {e}")
                time.sleep(0.4)


class MemoryInfoThread(threading.Thread):
    """使用 threading.Thread 获取内存信息的线程"""

    def __init__(self, callback):
        super().__init__()
        self.daemon = True
        self.callback = callback
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                memory = psutil.virtual_memory()
                total_memory = memory.total
                used_memory = memory.used
                memory_percent = memory.percent
                process = psutil.Process(os.getpid())
                process_memory = process.memory_info().rss
                other_memory = used_memory - process_memory
                process_memory_percent = (process_memory / total_memory) * 100
                other_memory_percent = (other_memory / total_memory) * 100
                # 转换为 MB 避免 Shiboken 32-bit int 溢出
                self.callback(total_memory // (1024 * 1024), used_memory // (1024 * 1024), memory_percent, process_memory // (1024 * 1024), process_memory_percent, other_memory_percent)
                time.sleep(1)
            except Exception as e:
                print(f"[MemoryInfoThread] 获取内存信息失败: {e}")
                time.sleep(1)


class SystemMonitor:
    """系统监控服务 - 负责CPU和内存信息的获取"""

    def __init__(self, signals):
        self.signals = signals
        self.cpu_thread = None
        self.memory_thread = None

    def start_monitoring(self):
        if self.cpu_thread is None or not self.cpu_thread.is_alive():
            self.cpu_thread = CPUInfoThread(callback=self.signals.cpu_info_updated.emit)
            self.cpu_thread.start()
            print("[SystemMonitor] CPU监控已启动")

        if self.memory_thread is None or not self.memory_thread.is_alive():
            self.memory_thread = MemoryInfoThread(callback=self.signals.memory_info_updated.emit)
            self.memory_thread.start()
            print("[SystemMonitor] 内存监控已启动")

    def stop_monitoring(self):
        if self.cpu_thread and self.cpu_thread.is_alive():
            self.cpu_thread.stop()
            self.cpu_thread = None
            print("[SystemMonitor] CPU监控已停止")

        if self.memory_thread and self.memory_thread.is_alive():
            self.memory_thread.stop()
            self.memory_thread = None
            print("[SystemMonitor] 内存监控已停止")
