from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from qfluentwidgets import SubtitleLabel, TitleLabel, BodyLabel, PushButton, PrimaryPushButton, CardWidget, CheckBox, IndeterminateProgressBar, ProgressBar, ListWidget, ToolTipFilter, ToolTipPosition, InfoBar, InfoBarPosition
from ui.charts.trend_chart.trend_chart_page import TrendChartPage


class HomePage(QFrame):
    """主页页面 - 通过信号与逻辑层通信，不直接引用 DeviceManager"""

    def __init__(self, parent=None, signals=None, resolve_device_name=None):
        super().__init__(parent)
        self.parent = parent
        self.signals = signals
        # 依赖注入：接收设备名称解析回调，避免直接引用 DeviceManager
        self._resolve_name = resolve_device_name or (lambda addr, name: name if name and name.strip() else addr)
        self.setObjectName("homePage")
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.hBoxLayout.setSpacing(20)

        self.leftCard = CardWidget(self)
        self.leftLayout = QVBoxLayout(self.leftCard)
        self.leftLayout.setContentsMargins(20, 20, 20, 20)
        self.leftLayout.setSpacing(12)

        self.leftTitle = TitleLabel("设备连接")
        self.leftSubtitle = SubtitleLabel("扫描并连接您的心率监测设备")
        self.leftLayout.addWidget(self.leftTitle)
        self.leftLayout.addWidget(self.leftSubtitle)

        self.scanText = BodyLabel("设备扫描")
        self.leftLayout.addWidget(self.scanText)

        self.checkBox = CheckBox("自动筛选心率设备（这可能会大幅增加扫描时间）")
        self.checkBox.setToolTip("开启后，仅显示支持心率监测的设备。\n适合不赶时间并对你的设备不太了解的人使用。\n此功能会延长一到两倍的扫描时间。\n默认关闭")
        self.checkBox.installEventFilter(ToolTipFilter(self.checkBox, showDelay=300, position=ToolTipPosition.TOP))
        self.leftLayout.addWidget(self.checkBox)

        self.scanButton = PrimaryPushButton("扫描设备")
        self.scanButton.clicked.connect(lambda: self.signals.scan_requested.emit(self.checkBox.isChecked()))
        self.leftLayout.addWidget(self.scanButton)

        self.indeterminateBar = IndeterminateProgressBar(start=False)
        self.indeterminateBar.hide()

        self.progressBar = ProgressBar()
        self.progressBar.setValue(100)

        self.leftLayout.addWidget(self.indeterminateBar)
        self.leftLayout.addWidget(self.progressBar)

        self.connectionText = BodyLabel("设备连接")
        self.leftLayout.addWidget(self.connectionText)

        self.listWidget = ListWidget()
        self.listWidget.setSelectRightClickedRow(True)

        self.leftLayout.addWidget(self.listWidget)

        self.infoLabel = QLabel("为提升您的使用体验，程序会在本地缓存设备名称。")
        self.infoLabel.setStyleSheet("color: gray; font-size: 12px;")
        self.infoLabel.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.infoLabel.linkActivated.connect(self._on_info_label_link_clicked)
        self.leftLayout.addWidget(self.infoLabel)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(10)

        self.connectButton = PushButton("连接设备")
        self.connectButton.setEnabled(False)
        self.connectButton.clicked.connect(self._on_connect_clicked)

        self.disconnectButton = PushButton("断开连接")
        self.disconnectButton.setEnabled(False)
        self.disconnectButton.clicked.connect(lambda: self.signals.disconnect_requested.emit())

        self.buttonLayout.addWidget(self.connectButton)
        self.buttonLayout.addWidget(self.disconnectButton)

        self.leftLayout.addLayout(self.buttonLayout)

        self.rightContainer = QFrame(self)
        self.rightContainerLayout = QVBoxLayout(self.rightContainer)
        self.rightContainerLayout.setContentsMargins(0, 0, 0, 0)
        self.rightContainerLayout.setSpacing(20)

        self.chartCard = CardWidget(self.rightContainer)
        self.chartLayout = QVBoxLayout(self.chartCard)
        self.chartLayout.setContentsMargins(0, 0, 0, 0)

        self.trendChartPage = TrendChartPage()
        self.chartLayout.addWidget(self.trendChartPage)

        self.emptyCard = CardWidget(self.rightContainer)

        self.rightContainerLayout.addWidget(self.chartCard, 1)
        self.rightContainerLayout.addWidget(self.emptyCard, 2)

        self.hBoxLayout.addWidget(self.leftCard, 1)
        self.hBoxLayout.addWidget(self.rightContainer, 1)

        # 重连进度 InfoBar 引用（用于后续关闭）
        self._reconnect_info_bar = None

        if self.signals:
            self.signals.device_list_cleared.connect(self._clear_device_list)
            self.signals.device_found.connect(self._on_device_found)
            self.signals.device_updated.connect(self._on_device_updated)
            self.signals.ui_scan_state_changed.connect(self._on_scan_state_changed)
            self.signals.ui_progress_state_changed.connect(self._on_progress_state_changed)
            self.signals.ui_connect_state_changed.connect(self._on_connect_state_changed)
            self.signals.ui_list_enabled_changed.connect(self.listWidget.setEnabled)
            self.signals.ui_checkbox_enabled_changed.connect(self.checkBox.setEnabled)
            self.signals.heart_rate_updated.connect(self._on_heart_rate_updated)
            self.signals.connection_status_changed.connect(self._on_connection_status_changed)
            self.signals.info_bar_requested.connect(self._on_info_bar_requested)
            self.signals.reconnect_progress.connect(self._on_reconnect_progress)
            self.signals.reconnect_success.connect(self._on_reconnect_success)
            self.signals.reconnect_failed.connect(self._on_reconnect_failed)
            self.signals.chart_data_clear_requested.connect(self._on_chart_data_clear_requested)

    def _on_connect_clicked(self):
        selected = self._get_selected_text()
        self.signals.connect_requested.emit(selected)

    def _get_selected_text(self):
        if self.listWidget.currentRow() >= 0:
            return self.listWidget.item(self.listWidget.currentRow()).text()
        return ""

    def _clear_device_list(self):
        self.listWidget.clear()
        self._update_info_label()

    def _get_device_display_text(self, address, name):
        return self._resolve_name(address, name)

    def _on_device_found(self, device_info):
        address = device_info.address
        display_text = self._get_device_display_text(address, device_info.name)

        self.listWidget.addItem(display_text)
        self._sort_device_list()
        self.connectButton.setEnabled(True)
        self._update_info_label()

    def _on_device_updated(self, device_info):
        address = device_info.address
        current_display_text = self._get_device_display_text(address, device_info.name)

        for i in range(self.listWidget.count()):
            item_text = self.listWidget.item(i).text()
            if address in item_text or item_text == current_display_text:
                if item_text != current_display_text:
                    self.listWidget.item(i).setText(current_display_text)
                    self._sort_device_list()
                break

    def _sort_device_list(self):
        items = []
        count = self.listWidget.count()

        for i in range(count):
            item = self.listWidget.item(i)
            if item:
                try:
                    text = item.text()
                    items.append((text, item))
                except Exception:
                    pass

        def sort_key(item_tuple):
            try:
                text, item = item_tuple
                is_mac_only = ':' in text and len(text) == 17
                return (is_mac_only, text)
            except Exception:
                return (True, "")

        sorted_items = sorted(items, key=sort_key)

        self.listWidget.clear()

        for text, item in sorted_items:
            try:
                self.listWidget.addItem(text)
            except Exception:
                pass

    def _on_scan_state_changed(self, enabled, text):
        self.scanButton.setEnabled(enabled)
        self.scanButton.setText(text)

    def _on_progress_state_changed(self, indeterminate_visible, progress_visible):
        if indeterminate_visible:
            self.indeterminateBar.show()
            self.indeterminateBar.start()
        else:
            self.indeterminateBar.stop()
            self.indeterminateBar.hide()

        if progress_visible:
            self.progressBar.setCustomBarColor(QColor(0, 159, 170), QColor(0, 130, 140))
            self.progressBar.setValue(100)
            self.progressBar.show()
        else:
            self.progressBar.hide()

    def _on_connect_state_changed(self, connect_enabled, disconnect_enabled):
        self.connectButton.setEnabled(connect_enabled)
        self.disconnectButton.setEnabled(disconnect_enabled)

    def _on_heart_rate_updated(self, heart_rate):
        self.trendChartPage.update_heart_rate(heart_rate)

    def _on_connection_status_changed(self, status):
        if "设备连接成功" in status:
            self.connectionText.setText("设备已连接")
        elif "设备已断开连接" in status or "已断开连接" in status:
            self.connectionText.setText("设备已断开连接")
        elif "请先连接设备" in status:
            self.connectionText.setText("请先连接设备")
        else:
            self.connectionText.setText(status)

    def _on_info_bar_requested(self, info_type, title, content):
        parent = self.window()
        if info_type == "warn":
            InfoBar.warning(title=title, content=content, orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=parent)
        elif info_type == "error":
            InfoBar.error(title=title, content=content, orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=parent)
        elif info_type == "info":
            InfoBar.info(title=title, content=content, orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=parent)
        elif info_type == "success":
            InfoBar.success(title=title, content=content, orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=parent)

    def _update_info_label(self):
        """根据设备列表数量更新 infoLabel 文字"""
        count = self.listWidget.count()
        if count > 3:
            self.infoLabel.setText(
                '设备太多眼花缭乱？'
                '<a href="storage" style="color: #009FAA; text-decoration: none;">设置排除项</a>'
            )
        else:
            self.infoLabel.setText("为提升您的使用体验，程序会在本地缓存设备名称。")

    def _on_info_label_link_clicked(self, link):
        if link == "storage" and self.signals:
            self.signals.navigate_to_storage.emit()

    def _on_reconnect_progress(self, attempt, max_attempts):
        """重连进度更新：第3次起弹出 InfoBar 提示"""
        if attempt >= 3:
            parent = self.window()
            # 关闭之前的重连进度 InfoBar
            if self._reconnect_info_bar is not None:
                try:
                    self._reconnect_info_bar.close()
                except RuntimeError:
                    pass
                self._reconnect_info_bar = None
            # 创建新的进度 InfoBar（永不自动消失）
            self._reconnect_info_bar = InfoBar.info(
                title="正在重连",
                content=f"第 {attempt}/{max_attempts} 次重连...",
                orient=Qt.Orientation.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=parent
            )

    def _on_reconnect_success(self):
        """重连成功：关闭进度 InfoBar，提示成功"""
        if self._reconnect_info_bar is not None:
            try:
                self._reconnect_info_bar.close()
            except RuntimeError:
                pass
            self._reconnect_info_bar = None
        parent = self.window()
        if parent:
            InfoBar.success(
                title="重连成功",
                content="设备已重新连接，继续监测",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=parent
            )

    def _on_reconnect_failed(self):
        """重连失败：关闭进度 InfoBar"""
        if self._reconnect_info_bar is not None:
            try:
                self._reconnect_info_bar.close()
            except RuntimeError:
                pass
            self._reconnect_info_bar = None

    def _on_chart_data_clear_requested(self):
        """彻底断开后重连：清空图表历史数据"""
        self.trendChartPage.clear_data()
