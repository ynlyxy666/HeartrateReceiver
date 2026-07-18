from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPainterPath
from qfluentwidgets import CardWidget, SubtitleLabel, BodyLabel


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
    def __init__(self, parent=None, signals=None, storage_service=None, system_monitor=None, settings_manager=None):
        super().__init__(parent)
        self.signals = signals
        self.storage_service = storage_service
        self.system_monitor = system_monitor
        self.settings_manager = settings_manager

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

        self.dataLayout.addStretch()

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

    def initial_refresh(self):
        print("[StoragePage] 执行启动时初始刷新")
        if self.storage_service:
            self.storage_service.emit_disk_space_info()
        if self.system_monitor:
            self.system_monitor.start_monitoring()

    def on_disk_space_updated(self, total_gb, used_gb, used_percent):
        self.diskSpaceTotalLabel.setText(f"共 {total_gb} GB")

        if self.storage_service and total_gb > 0:
            app_size_gb, app_percent = self.storage_service.get_app_size_info(total_gb)
        else:
            app_size_gb, app_percent = 0, 0

        orange_percent = app_percent
        cyan_percent = used_percent - app_percent
        if cyan_percent < 0:
            cyan_percent = 0

        self.diskSpaceBar.segments = [
            {'percent': orange_percent, 'color': QColor(255, 165, 0)},
            {'percent': cyan_percent, 'color': QColor(0, 159, 170)}
        ]
        self.diskSpaceBar.update()

        other_data_gb = round(used_gb - app_size_gb, 3)
        free_space = round(total_gb - used_gb, 3)

        self.softwareSizeLabel.setText(f"软件占用 {app_size_gb} GB  ")
        self.otherDataLabel.setText(f"其他数据 {other_data_gb} GB  ")
        self.freeSpaceLabel.setText(f"可用 {free_space} GB")

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.system_monitor:
            self.system_monitor.stop_monitoring()

    def showEvent(self, event):
        super().showEvent(event)
        if self.system_monitor:
            self.system_monitor.start_monitoring()

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
