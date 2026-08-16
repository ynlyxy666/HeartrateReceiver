import os
import threading
from datetime import datetime, timedelta
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QTimer, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPainterPath
from qfluentwidgets import CardWidget, SubtitleLabel, BodyLabel

import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class StorageBar(QFrame):
    def __init__(self, segments=None, parent=None):
        super().__init__(parent)
        self.segments = segments or []
        self.setFixedHeight(20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        radius = 4

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRoundedRect(0, 0, width, height, radius, radius)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), radius, radius)
        painter.setClipPath(path)

        current_x = 0
        for i, segment in enumerate(self.segments):
            seg_percent = segment.get('percent', 0)
            seg_color = segment.get('color', QColor(0, 159, 170))
            seg_width = int(width * seg_percent / 100)

            if seg_width > 0:
                painter.setBrush(QBrush(seg_color))
                painter.drawRect(current_x, 0, seg_width, height)
                current_x += seg_width

class StoragePage(QFrame):
    """存储和性能页面"""

    # 后台统计线程完成后的结果信号（dict: app_size/db_size/record_count/daily）
    _stats_ready = Signal(object)

    def __init__(self, parent=None, signals=None, storage_service=None, system_monitor=None, settings_manager=None, data_manager=None, navigate_to_device_filter=None):
        super().__init__(parent)
        self.signals = signals
        self.storage_service = storage_service
        self.system_monitor = system_monitor
        self.settings_manager = settings_manager
        self.data_manager = data_manager
        self._navigate_to_device_filter = navigate_to_device_filter

        # 磁盘/软件占用缓存（后台线程计算，避免在 UI 线程做目录递归统计）
        self._total_gb = 0
        self._used_gb = 0
        self._used_percent = 0
        self._app_size_gb = 0
        self._stats_worker = None
        self._stats_ready.connect(self._on_stats_ready)

        self.setObjectName("storagePage")

        self.mainLayout = QHBoxLayout(self)
        self.mainLayout.setContentsMargins(20, 20, 20, 20)
        self.mainLayout.setSpacing(10)

        self.leftLayout = QVBoxLayout()
        self.leftLayout.setSpacing(10)

        self.diskSpaceCard = CardWidget(self)
        self.diskSpaceLayout = QVBoxLayout(self.diskSpaceCard)
        self.diskSpaceLayout.setContentsMargins(12, 6, 12, 6)
        self.diskSpaceLayout.setSpacing(4)

        self.diskSpaceHeaderLayout = QHBoxLayout()
        self.diskSpaceTitle = SubtitleLabel("占用空间", self.diskSpaceCard)
        self.diskSpaceHeaderLayout.addWidget(self.diskSpaceTitle)
        self.diskSpaceHeaderLayout.addStretch()

        self.diskSpaceTotalLabel = BodyLabel("共 0 GB", self.diskSpaceCard)
        self.diskSpaceTotalLabel.setStyleSheet("font-weight: bold;")
        self.diskSpaceHeaderLayout.addWidget(self.diskSpaceTotalLabel)

        self.diskSpaceLayout.addLayout(self.diskSpaceHeaderLayout)

        self.diskSpaceBar = StorageBar([], self.diskSpaceCard)
        self.diskSpaceLayout.addWidget(self.diskSpaceBar)

        self.diskSpaceInfoLayout = QHBoxLayout()

        self.softwareSizeLabel = QLabel("软件占用 0 GB  ", self.diskSpaceCard)
        self.softwareSizeLabel.setStyleSheet("color: #FFA500;")

        self.otherDataLabel = QLabel("其他数据 0 GB  ", self.diskSpaceCard)
        self.otherDataLabel.setStyleSheet("color: #009FAA;")

        self.freeSpaceLabel = QLabel("可用 0 GB", self.diskSpaceCard)
        self.freeSpaceLabel.setStyleSheet("color: gray;")

        self.diskSpaceInfoLayout.addWidget(self.softwareSizeLabel)
        self.diskSpaceInfoLayout.addWidget(self.otherDataLabel)
        self.diskSpaceInfoLayout.addWidget(self.freeSpaceLabel)
        self.diskSpaceLayout.addLayout(self.diskSpaceInfoLayout)

        self.diskSpaceNoteLabel = QLabel("*软件本身占用很小 占用全部来自数据 条形图显示不了很正常", self.diskSpaceCard)
        self.diskSpaceLayout.addWidget(self.diskSpaceNoteLabel)

        self.leftLayout.addWidget(self.diskSpaceCard)

        self.dataCard = CardWidget(self)
        self.dataLayout = QVBoxLayout(self.dataCard)
        self.dataLayout.setContentsMargins(15, 12, 15, 12)
        self.dataLayout.setSpacing(8)

        self.dataTitle = SubtitleLabel("数据", self.dataCard)
        self.dataLayout.addWidget(self.dataTitle)

        # 获取实际的数据库存储目录
        db_dir = ""
        if self.settings_manager:
            db_dir = self.settings_manager.get_db_directory() + "\\"
        # 路径过长时截断
        display_dir = db_dir
        if len(display_dir) > 42:
            display_dir = display_dir[:40] + "…"
        # 路径部分青色可点击超链接
        db_dir_url = db_dir.replace("\\", "/")
        self.dataStorePathLabel = QLabel(
            f'您的数据存储在：<a href="file:///{db_dir_url}" style="color: #009FAA; text-decoration: none;">{display_dir}</a>',
            self.dataCard
        )
        self.dataStorePathLabel.setOpenExternalLinks(True)
        self.dataStorePathLabel.setStyleSheet("font-size: 12px; color: #000000;")
        self.dataLayout.addWidget(self.dataStorePathLabel)

        self.dataSeparator = QFrame(self.dataCard)
        self.dataSeparator.setFrameShape(QFrame.Shape.HLine)
        self.dataSeparator.setStyleSheet("color: #E0E0E0;")
        self.dataLayout.addWidget(self.dataSeparator)

        self.dbSizeLayout = QHBoxLayout()
        self.dbSizeLabel = QLabel("数据库大小：", self.dataCard)
        self.dbSizeLabel.setStyleSheet("font-size: 12px; color: #000000;")
        self.dbSizeValueLabel = QLabel("计算中…", self.dataCard)
        self.dbSizeValueLabel.setStyleSheet("font-size: 12px; color: #00AA00; font-weight: bold;")
        self.dbSizeLayout.addWidget(self.dbSizeLabel)
        self.dbSizeLayout.addWidget(self.dbSizeValueLabel)
        self.dbSizeLayout.addStretch()
        self.dataLayout.addLayout(self.dbSizeLayout)

        self.recordCountLayout = QHBoxLayout()
        self.recordCountLabel = QLabel("总数据条数：", self.dataCard)
        self.recordCountLabel.setStyleSheet("font-size: 12px; color: #000000;")
        self.recordCountValueLabel = QLabel("计算中…", self.dataCard)
        self.recordCountValueLabel.setStyleSheet("font-size: 12px; color: #00AA00; font-weight: bold;")
        self.recordCountLayout.addWidget(self.recordCountLabel)
        self.recordCountLayout.addWidget(self.recordCountValueLabel)
        self.recordCountLayout.addStretch()
        self.dataLayout.addLayout(self.recordCountLayout)

        # Matplotlib 图表
        self.chartTitleLabel = QLabel("近14日使用记录", self.dataCard)
        self.chartTitleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chartTitleLabel.setStyleSheet("font-size: 12px; color: #000000;")
        self.dataLayout.addWidget(self.chartTitleLabel)

        self.chartFigure = Figure(figsize=(5, 1.2), dpi=100)
        self.chartFigure.patch.set_alpha(0)
        self.chartCanvas = FigureCanvasQTAgg(self.chartFigure)
        self.chartCanvas.setFixedHeight(120)
        self.chartCanvas.setStyleSheet("background: transparent;")
        self.chartAx = self.chartFigure.add_subplot(111)
        self.chartAx.patch.set_alpha(0)
        self._style_chart_ax([])
        self.dataLayout.addWidget(self.chartCanvas)

        self.dataLayout.addStretch()

        self.dataStoreHintLabel = QLabel("*到设置中修改数据存储位置", self.dataCard)
        self.dataStoreHintLabel.setStyleSheet("font-size: 11px; color: gray;")
        self.dataLayout.addWidget(self.dataStoreHintLabel)

        self.leftLayout.addWidget(self.dataCard)

        self.rightLayout = QVBoxLayout()
        self.rightLayout.setSpacing(10)

        self.performanceCard = CardWidget(self)
        self.performanceLayout = QVBoxLayout(self.performanceCard)
        self.performanceLayout.setContentsMargins(12, 6, 12, 6)
        self.performanceLayout.setSpacing(4)

        self.cpuHeaderLayout = QHBoxLayout()
        self.cpuTitle = SubtitleLabel("CPU", self.performanceCard)
        self.cpuHeaderLayout.addWidget(self.cpuTitle)
        self.cpuHeaderLayout.addStretch()

        self.performanceLayout.addLayout(self.cpuHeaderLayout)

        self.cpuBar = StorageBar([], self.performanceCard)
        self.performanceLayout.addWidget(self.cpuBar)

        self.cpuInfoLayout = QHBoxLayout()

        self.softwareCpuLabel = QLabel("本软件 0.0%  ", self.performanceCard)
        self.softwareCpuLabel.setStyleSheet("color: #FFA500;")

        self.otherProcessCpuLabel = QLabel("其他进程 0.0%  ", self.performanceCard)
        self.otherProcessCpuLabel.setStyleSheet("color: #009FAA;")

        self.idleCpuLabel = QLabel("空闲 100.0%", self.performanceCard)
        self.idleCpuLabel.setStyleSheet("color: gray;")

        self.cpuInfoLayout.addWidget(self.softwareCpuLabel)
        self.cpuInfoLayout.addWidget(self.otherProcessCpuLabel)
        self.cpuInfoLayout.addWidget(self.idleCpuLabel)
        self.performanceLayout.addLayout(self.cpuInfoLayout)

        self.performanceLayout.addSpacing(4)

        self.cpuNoteLabel = QLabel("*软件的CPU使用率 不保证完全准确 误差1%", self.performanceCard)
        self.performanceLayout.addWidget(self.cpuNoteLabel)

        self.performanceLayout.addSpacing(8)

        self.memoryHeaderLayout = QHBoxLayout()
        self.memoryTitle = SubtitleLabel("内存", self.performanceCard)
        self.memoryHeaderLayout.addWidget(self.memoryTitle)
        self.memoryHeaderLayout.addStretch()

        self.performanceLayout.addLayout(self.memoryHeaderLayout)

        self.memoryBar = StorageBar([], self.performanceCard)
        self.performanceLayout.addWidget(self.memoryBar)

        self.memoryInfoLayout = QHBoxLayout()

        self.softwareMemoryLabel = QLabel("本软件 0.0%  ", self.performanceCard)
        self.softwareMemoryLabel.setStyleSheet("color: #FFA500;")

        self.otherProcessMemoryLabel = QLabel("其他进程 0.0%  ", self.performanceCard)
        self.otherProcessMemoryLabel.setStyleSheet("color: #009FAA;")

        self.idleMemoryLabel = QLabel("空闲 100.0%", self.performanceCard)
        self.idleMemoryLabel.setStyleSheet("color: gray;")

        self.memoryInfoLayout.addWidget(self.softwareMemoryLabel)
        self.memoryInfoLayout.addWidget(self.otherProcessMemoryLabel)
        self.memoryInfoLayout.addWidget(self.idleMemoryLabel)
        self.performanceLayout.addLayout(self.memoryInfoLayout)

        self.performanceLayout.addSpacing(4)

        self.memoryNoteLabel = QLabel("*软件的内存使用率 比上面那个准确多了 误差0.01%", self.performanceCard)
        self.performanceLayout.addWidget(self.memoryNoteLabel)

        self.performanceLayout.addStretch()

        self.deviceCard = CardWidget(self)
        self.deviceCard.setObjectName("deviceCard")
        self.deviceLayout = QVBoxLayout(self.deviceCard)
        self.deviceLayout.setContentsMargins(15, 12, 15, 12)
        self.deviceLayout.setSpacing(8)

        self.deviceTitle = SubtitleLabel("连接设备管理", self.deviceCard)
        self.deviceTitle.setObjectName("deviceTitle")
        self.deviceLayout.addWidget(self.deviceTitle)

        self.deviceConfigLink = QLabel(
            '<a href="config" style="color: #009FAA; text-decoration: none;">设备筛选配置</a>',
            self.deviceCard
        )
        self.deviceConfigLink.setObjectName("deviceConfigLink")
        self.deviceConfigLink.setStyleSheet("font-size: 14px; padding-left: 2px;")
        self.deviceLayout.addWidget(self.deviceConfigLink)
        self.deviceConfigLink.linkActivated.connect(self._on_device_config_clicked)

        self.deviceLayout.addStretch()

        self.rightLayout.addWidget(self.performanceCard)
        self.rightLayout.addStretch()
        self.rightLayout.addWidget(self.deviceCard)

        self.mainLayout.addLayout(self.leftLayout, 1)
        self.mainLayout.addLayout(self.rightLayout, 1)

        if self.signals:
            self.signals.disk_space_updated.connect(self.on_disk_space_updated)
            self.signals.cpu_info_updated.connect(self.update_cpu_info)
            self.signals.memory_info_updated.connect(self.update_memory_info)

        QTimer.singleShot(400, self.initial_refresh)

    def _get_db_dir(self):
        """获取数据库目录"""
        if self.settings_manager:
            return self.settings_manager.get_db_directory()
        return ""

    def _get_dir_size(self, path):
        """递归计算目录总大小（字节）"""
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    if os.path.isfile(filepath) and not os.path.islink(filepath):
                        total += os.path.getsize(filepath)
                except Exception:
                    pass
        return total

    def _format_size(self, bytes_size):
        """将字节格式化为可读的大小"""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 ** 2:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 ** 3:
            return f"{bytes_size / (1024 ** 2):.1f} MB"
        else:
            return f"{bytes_size / (1024 ** 3):.2f} GB"

    def _start_stats_worker(self):
        """启动后台统计线程（目录大小/记录数/近14日分布），避免阻塞 UI"""
        if self._stats_worker and self._stats_worker.is_alive():
            return
        self._stats_worker = threading.Thread(target=self._stats_worker_run, daemon=True)
        self._stats_worker.start()

    def _stats_worker_run(self):
        """后台线程：递归统计应用目录/数据库目录大小，查询记录数与近14日分布"""
        result = {'app_size': 0, 'db_size': 0, 'record_count': 0, 'daily': []}
        try:
            if self.storage_service:
                app_path = self.storage_service.get_project_root()
                if app_path and os.path.isdir(app_path):
                    result['app_size'] = self._get_dir_size(app_path)
            db_dir = self._get_db_dir()
            if db_dir and os.path.isdir(db_dir):
                result['db_size'] = self._get_dir_size(db_dir)
            if self.data_manager:
                result['record_count'] = self.data_manager.get_record_count()
                result['daily'] = self.data_manager.get_daily_record_counts(14)
        except Exception as e:
            print(f"[StoragePage] 后台统计出错: {e}")
        self._stats_ready.emit(result)

    def _on_stats_ready(self, result):
        """UI 线程：应用后台统计结果，刷新大小/条数/图表/磁盘条"""
        try:
            self._app_size_gb = round(result.get('app_size', 0) / (1024 ** 3), 3)
        except Exception:
            self._app_size_gb = 0

        try:
            self.dbSizeValueLabel.setText(self._format_size(result.get('db_size', 0)))
        except Exception as e:
            print(f"[StoragePage] 更新数据库大小失败: {e}")
            self.dbSizeValueLabel.setText("获取失败")

        try:
            self.recordCountValueLabel.setText(f"{result.get('record_count', 0):,}")
        except Exception as e:
            print(f"[StoragePage] 更新记录数失败: {e}")
            self.recordCountValueLabel.setText("获取失败")

        self._update_chart(result.get('daily', []))

        # 磁盘占用条依赖软件占用大小，统计完成后重新渲染
        self._render_disk_bar()

    def _style_chart_ax(self, daily_data):
        """设置图表初始样式（无数据时显示占位）"""
        self.chartAx.clear()
        if not daily_data:
            self.chartAx.text(0.5, 0.5, "暂无数据", transform=self.chartAx.transAxes,
                              ha="center", va="center", fontsize=10, color="gray")
        self.chartAx.set_xticks([])
        self.chartAx.set_yticks([])
        for spine in self.chartAx.spines.values():
            spine.set_visible(False)

    def _update_chart(self, daily):
        """从后台线程查询到的近 14 天数据绘制折线图（无数据天补 0）"""
        try:
            self.chartAx.clear()
            self.chartAx.patch.set_alpha(0)
            if not daily:
                self.chartAx.text(0.5, 0.5, "暂无数据", transform=self.chartAx.transAxes,
                                  ha="center", va="center", fontsize=10, color="gray")
                self.chartCanvas.draw_idle()
                return

            db_map = {row[0]: row[1] for row in daily}

            # 生成完整的 14 天日期列表，缺失补 0
            today = datetime.now()
            full_dates = []
            full_counts = []
            for i in range(13, -1, -1):
                day_str = (today - timedelta(days=i)).strftime("%m-%d")
                full_dates.append(day_str)
                full_counts.append(db_map.get(day_str, 0))

            x = range(14)
            self.chartAx.plot(x, full_counts, color="#009FAA", linewidth=1.5,
                              marker="o", markersize=3, markerfacecolor="#009FAA")

            # x 轴只显示部分标签避免拥挤
            step = 2 if 14 > 10 else 1
            visible_ticks = list(range(0, 14, step))
            self.chartAx.set_xticks(visible_ticks)
            self.chartAx.set_xticklabels([full_dates[i] for i in visible_ticks], fontsize=7)
            self.chartAx.tick_params(axis="y", labelsize=7)
            self.chartAx.set_ylabel("条", fontsize=7)
            for spine in self.chartAx.spines.values():
                spine.set_visible(False)
            self.chartAx.tick_params(axis="x", length=0)
            self.chartAx.tick_params(axis="y", length=2)

            if max(full_counts) > 0:
                self.chartAx.set_ylim(0, max(full_counts) * 1.2)

            self.chartFigure.tight_layout(pad=0)
            self.chartCanvas.draw_idle()
        except Exception as e:
            print(f"[StoragePage] 更新图表失败: {e}")

    def _on_device_config_clicked(self, url):
        if self._navigate_to_device_filter:
            self._navigate_to_device_filter()

    def initial_refresh(self):
        print("[StoragePage] 执行启动时初始刷新")
        if self.storage_service:
            self.storage_service.emit_disk_space_info()
        if self.system_monitor:
            self.system_monitor.start_monitoring()
        # 目录递归统计放到后台线程，避免启动时卡住 UI
        self._start_stats_worker()

    def on_disk_space_updated(self, total_gb, used_gb, used_percent):
        # 缓存磁盘总量，具体软件占用大小由后台线程统计后通过 _render_disk_bar 渲染
        self._total_gb = total_gb
        self._used_gb = used_gb
        self._used_percent = used_percent
        self.diskSpaceTotalLabel.setText(f"共 {total_gb} GB")
        self._render_disk_bar()

    def _render_disk_bar(self):
        """根据缓存的总量/占用/软件大小渲染磁盘占用条与文字（UI 线程，无 IO）"""
        total_gb = self._total_gb
        if total_gb <= 0:
            return

        app_percent = round(self._app_size_gb / total_gb * 100, 1)
        used_percent = self._used_percent

        orange_percent = app_percent
        cyan_percent = used_percent - app_percent
        if cyan_percent < 0:
            cyan_percent = 0

        self.diskSpaceBar.segments = [
            {'percent': orange_percent, 'color': QColor(255, 165, 0)},
            {'percent': cyan_percent, 'color': QColor(0, 159, 170)}
        ]
        self.diskSpaceBar.update()

        other_data_gb = round(self._used_gb - self._app_size_gb, 3)
        free_space = round(total_gb - self._used_gb, 3)

        # 将 GB 转为字节后用自适应格式化
        gb_to_bytes = 1024 ** 3
        app_size_bytes = int(self._app_size_gb * gb_to_bytes)
        other_data_bytes = int(max(other_data_gb, 0) * gb_to_bytes)
        free_space_bytes = int(max(free_space, 0) * gb_to_bytes)

        self.softwareSizeLabel.setText(f"软件占用 {self._format_size(app_size_bytes)}  ")
        self.otherDataLabel.setText(f"其他数据 {self._format_size(other_data_bytes)}  ")
        self.freeSpaceLabel.setText(f"可用 {self._format_size(free_space_bytes)}")

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.system_monitor:
            self.system_monitor.stop_monitoring()
        print("[StoragePage] 页面隐藏，系统监控已停止")

    def showEvent(self, event):
        super().showEvent(event)
        if self.system_monitor:
            self.system_monitor.start_monitoring()
        print("[StoragePage] 页面显示，系统监控已启动")

    def update_cpu_info(self, cpu_percent, process_cpu, other_cpu):
        try:
            cpu_percent = max(cpu_percent, 0.1)
            process_cpu = max(process_cpu, 0.1)
            other_cpu = max(other_cpu, 0.1)
            free_cpu = max(100 - cpu_percent, 0.1)

            self.cpuBar.segments = [
                {'percent': process_cpu, 'color': QColor(255, 165, 0)},
                {'percent': other_cpu, 'color': QColor(0, 159, 170)}
            ]
            self.cpuBar.update()

            self.softwareCpuLabel.setText(f"本软件 {process_cpu:.1f}%  ")
            self.otherProcessCpuLabel.setText(f"其他进程 {other_cpu:.1f}%  ")
            self.idleCpuLabel.setText(f"空闲 {free_cpu:.1f}%")
        except Exception as e:
            print(f"[StoragePage] 更新CPU信息失败: {e}")

    def update_memory_info(self, total_memory, used_memory, memory_percent, process_memory, process_memory_percent, other_memory_percent):
        try:
            memory_percent = max(memory_percent, 0.1)
            process_memory_percent = max(process_memory_percent, 0.1)
            other_memory_percent = max(other_memory_percent, 0.1)
            free_memory_percent = max(100 - memory_percent, 0.1)

            self.memoryBar.segments = [
                {'percent': process_memory_percent, 'color': QColor(255, 165, 0)},
                {'percent': other_memory_percent, 'color': QColor(0, 159, 170)}
            ]
            self.memoryBar.update()

            self.softwareMemoryLabel.setText(f"本软件 {process_memory_percent:.1f}%  ")
            self.otherProcessMemoryLabel.setText(f"其他进程 {other_memory_percent:.1f}%  ")
            self.idleMemoryLabel.setText(f"空闲 {free_memory_percent:.1f}%")
        except Exception as e:
            print(f"[StoragePage] 更新内存信息失败: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        page_width = self.width()
        page_height = self.height()
        card_width = page_width // 2 - 20
        margin = 40
        spacing = 10

        disk_card_height = 140
        self.diskSpaceCard.setFixedSize(card_width, disk_card_height)

        data_card_height = page_height - margin - disk_card_height - spacing
        self.dataCard.setFixedSize(card_width, data_card_height)

        total_right_height = page_height - margin

        performance_card_height = max(int(total_right_height * 0.38), 100)
        self.performanceCard.setFixedSize(card_width, performance_card_height)

        device_card_height = total_right_height - performance_card_height - spacing
        self.deviceCard.setFixedSize(card_width, device_card_height)
