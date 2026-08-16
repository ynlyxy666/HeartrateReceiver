import sys
import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    Theme, setTheme, isDarkTheme, setThemeColor,
    NavigationToolButton, ToolTipFilter, ToolTipPosition,
    SystemThemeListener
)
from qframelesswindow.utils import getSystemAccentColor

from resources.icon import ICON_ICO
from ui.utils.icon_helper import get_icon_from_base64
from ui.tray.tray_manager import TrayManager
from ui.dialogs.close_dialog import CloseConfirmationDialog
from ui.pages.home.home_page import HomePage
from ui.pages.settings.settings_page import SettingsPage
from ui.pages.widget.widget_page import WidgetPage
from ui.pages.data.data_page import DataPage
from ui.pages.storage.storage_page import StoragePage
from ui.pages.storage.device_filter_page import DeviceFilterPage
from ui.services.app_signals import AppSignals
from help.helphtml import show_help_async
from core.device.device_manager import DeviceManager
from persistence.manager.data_manager import DataManager
from system.memory.shared_memory import MemoryShareManager
from system.settings.settings_manager import SettingsManager
from system.monitor.system_monitor import SystemMonitor
from system.monitor.storage_service import StorageService


class HypeBeatWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self._exiting = False
        self.setWindowTitle("听澜 · HypeBeat")
        self.resize(900, 700)
        self.setWindowIcon(get_icon_from_base64(ICON_ICO))

        self.tray_manager = TrayManager(get_icon_from_base64(ICON_ICO), self)
        self.tray_manager.set_show_callback(self.show_main_window)
        self.tray_manager.set_exit_callback(self.exit_application)
        self.tray_manager.show()

        self.settings_manager = SettingsManager()
        print("[SettingsManager] 设置管理器已初始化")

        self.data_manager = DataManager(settings_manager=self.settings_manager)
        print("[DataManager] 数据管理器已初始化")

        self.memory_share = MemoryShareManager()
        self.memory_share.initialize()
        
        self.signals = AppSignals()
        print("[AppSignals] 全局信号已初始化")

        self.device_manager = DeviceManager(
            self.settings_manager, 
            self.data_manager, 
            self.memory_share,
            self.signals
        )
        print("[DeviceManager] 设备管理器已初始化")
        
        self.storage_service = StorageService(self.signals)
        print("[StorageService] 存储服务已初始化")
        
        self.system_monitor = SystemMonitor(self.signals)
        print("[SystemMonitor] 系统监控已初始化")

        if sys.platform in ["win32", "darwin"]:
            try:
                system_color = getSystemAccentColor()
                print(f"[Theme] 获取到的系统主题色: {system_color}")
                setThemeColor(system_color, save=False)
                print(f"[Theme] 已设置主题色为系统色: {system_color}")
            except Exception as e:
                print(f"[Theme] 获取系统主题色失败: {e}")

        setTheme(Theme.LIGHT)
        print("[Theme] 已应用默认主题: 浅色主题")

        self.themeListener = SystemThemeListener(self)
        self.themeListener.start()
        print("[Theme] 系统主题监听器已启动")

        self.initWindow()

        self.homePage = HomePage(self, self.signals, self.device_manager._get_stable_device_name)
        self.addSubInterface(self.homePage, FluentIcon.HOME, "主页")

        self.widgetPage = WidgetPage(self)
        self.addSubInterface(self.widgetPage, FluentIcon.ZOOM, "小组件")

        self.dataPage = DataPage(self, data_manager=self.data_manager)
        self.addSubInterface(self.dataPage, FluentIcon.MARKET, "数据分析与趋势")

        self.storagePage = StoragePage(
            self, 
            self.signals, 
            self.storage_service, 
            self.system_monitor,
            self.settings_manager,
            self.data_manager,
            navigate_to_device_filter=self._show_device_filter_page
        )
        self.addSubInterface(self.storagePage, FluentIcon.SPEED_HIGH, "存储和性能")

        # 设备筛选配置页 - 不显示在导航栏
        self.deviceFilterPage = DeviceFilterPage(
            self,
            back_callback=self._show_storage_page_from_filter
        )
        self.stackedWidget.addWidget(self.deviceFilterPage)

        self.websiteButton = NavigationToolButton(FluentIcon.GLOBE, self)
        self.websiteButton.installEventFilter(ToolTipFilter(self.websiteButton, showDelay=300, position=ToolTipPosition.TOP))
        self.websiteButton.setToolTip("官方网站")
        self.websiteButton.clicked.connect(self.on_custom_button_clicked)
        self.navigationInterface.addWidget(
            routeKey='websiteButton',
            widget=self.websiteButton,
            position=NavigationItemPosition.BOTTOM
        )

        self.navigationInterface.addItem(
            routeKey='helpButton',
            icon=FluentIcon.QUESTION,
            text='帮助',
            onClick=lambda: None,
            position=NavigationItemPosition.BOTTOM
        )

        self.settingsPage = SettingsPage(
            self, 
            self.settings_manager, 
            self.device_manager,
            self.signals,
            self.storage_service
        )
        self.addSubInterface(self.settingsPage, FluentIcon.SETTING, "设置", NavigationItemPosition.BOTTOM)

        # 连接 UI 动作信号 → DeviceManager（HomePage 不再直接引用 DeviceManager）
        self.signals.scan_requested.connect(self.device_manager.start_scan)
        self.signals.connect_requested.connect(self.device_manager.connect_device)
        self.signals.disconnect_requested.connect(self.device_manager.disconnect_device)
        self.signals.navigate_to_storage.connect(lambda: self.switchTo(self.storagePage))

    def initWindow(self):
        window_size = (900, 700)
        self.resize(window_size[0], window_size[1])

        self.setMinimumSize(window_size[0], window_size[1])
        self.setMaximumSize(window_size[0], window_size[1])

        self.setWindowIcon(get_icon_from_base64(ICON_ICO))

        self.setWindowTitle("听澜 · HypeBeat")

        self.titleBar.maxBtn.hide()
        self.titleBar.setDoubleClickEnabled(False)

        self.setMicaEffectEnabled(False)

    def show_main_window(self):
        self.bring_to_front()

    def bring_to_front(self):
        """将主窗口置顶并激活到前台（启动完成或从后台唤醒时调用）

        activateWindow 可能被 Windows 前台锁定机制拒绝，导致窗口虽显示却
        落在其它窗口后面；这里再用 Win32 SetWindowPos 强制提到 Z 序顶部兜底。
        """
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            import ctypes
            # HWND_TOP(0) + SWP_NOSIZE|SWP_NOMOVE|SWP_SHOWWINDOW
            ctypes.windll.user32.SetWindowPos(
                int(self.winId()), 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
        except Exception:
            pass

    def hide_main_window(self):
        self.hide()

    def exit_application(self):
        print("[Cleanup] 开始清理资源")
        self._exiting = True
        # 断开 BLE 设备（会停止 monitor 线程、取消重连定时器）。
        # trigger_auto_rescan=False：避免退出后仍启动幽灵扫描线程
        self.device_manager.disconnect_device(trigger_auto_rescan=False)
        print("[DeviceManager] 设备已断开")
        # 停止系统监控线程
        self.system_monitor.stop_monitoring()
        print("[SystemMonitor] 系统监控已停止")
        try:
            self.themeListener.terminate()
            self.themeListener.deleteLater()
        except RuntimeError:
            pass
        print("[Theme] 系统主题监听器已停止")
        self.data_manager.flush_data()
        print("[DataManager] 数据已保存")
        self.memory_share.close()
        print("[MemoryShare] 共享内存已关闭")
        self.tray_manager.hide()
        QApplication.quit()

    def _onThemeChangedFinish(self):
        super()._onThemeChangedFinish()

        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

        print(f"[Theme] 主题已切换为: {'深色' if isDarkTheme() else '浅色'}")

    def on_custom_button_clicked(self):
        webbrowser.open("https://www.nstechcod.top/")

    def _show_device_filter_page(self):
        """切换到设备筛选配置页（不更新导航高亮）"""
        self.stackedWidget.setCurrentWidget(self.deviceFilterPage)

    def _show_storage_page_from_filter(self):
        """从设备筛选配置页返回到存储和性能页"""
        self.switchTo(self.storagePage)

    def closeEvent(self, event):
        # 正在退出程序中，直接放行
        if self._exiting:
            event.accept()
            return

        show_confirmation = self.settings_manager.get("show_close_confirmation", True)
        close_behavior = self.settings_manager.get("close_behavior", "minimize")

        print(f"[MainWindow] 关闭事件触发: show_confirmation={show_confirmation}, behavior={close_behavior}")

        if show_confirmation:
            dialog = CloseConfirmationDialog(self)
            result = dialog.exec()

            if dialog.get_dont_ask_again():
                self.settings_manager.set("show_close_confirmation", False)
                if result == 1:
                    self.settings_manager.set("close_behavior", "minimize")
                elif result == 2:
                    self.settings_manager.set("close_behavior", "close")

            if result == 0:
                event.ignore()
                return
            elif result == 1:
                self.hide_main_window()
                event.ignore()
                return
            elif result == 2:
                self.exit_application()
                event.accept()
                return
        else:
            if close_behavior == "close":
                self.exit_application()
                event.accept()
                return
            else:
                self.hide_main_window()
                event.ignore()
                return
