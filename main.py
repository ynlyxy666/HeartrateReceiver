# 导入系统级闪屏模块
from func.splash_screen import show_system_splash, close_system_splash

system_splash_hwnd = show_system_splash()

# 导入其他模块
import sys
import base64
from io import BytesIO
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QSystemTrayIcon, QMenu, QAction, QSplashScreen
from PyQt5.QtGui import QIcon, QPixmap
from qfluentwidgets import (InfoBar, InfoBarPosition,FluentWindow, NavigationItemPosition,FluentIcon)

# 导入base64编码的图标
from func.icon import ICON_ICO

# 从base64数据创建QIcon
def get_icon_from_base64(base64_data):
    """从base64编码数据创建QIcon"""
    try:
        # 解码base64字符串
        icon_data = base64.b64decode(base64_data)
        # 创建BytesIO对象
        icon_stream = BytesIO(icon_data)
        # 创建QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(icon_stream.getvalue())
        # 创建QIcon
        return QIcon(pixmap)
    except Exception as e:
        print(f"Error creating icon from base64: {e}")
        return QIcon()

from func.core import HeartRateMonitorCore, DeviceScanThread, HeartRateMonitorThread
from func.interfaces import HomeInterface, HeartRateInterface, WidgetsInterface, SettingsInterface
from func.interfaces.heart_rate_window import HeartRateWindow
from func.interfaces.close_confirmation_dialog import CloseConfirmationDialog
from func.http_server import HeartRateHTTPServer
from func.settings_manager import SettingsManager
from func.memory_share import MemoryShareManager

# 主窗口类
class HeartRateMonitorWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("心率监测器")
        self.resize(500, 400)  # 紧凑窗口大小
        self.setFixedSize(self.size())  # 固定窗口大小，使其不可调整
        # 设置窗口图标（从base64资源）
        self.setWindowIcon(get_icon_from_base64(ICON_ICO))
        
        # 初始化设置管理器
        self.settings_manager = SettingsManager()
        
        # 初始化核心功能类
        self.core = HeartRateMonitorCore()
        self.user_disconnecting = False  # 标记用户是否正在主动断开连接
        self.is_disconnecting = False  # 标记是否正在执行断开连接操作，防止重复调用
        
        # 初始化 HTTP 服务器
        self.http_server = HeartRateHTTPServer(port=3030)
        
        # 初始化内存共享管理器
        self.memory_share_manager = MemoryShareManager()
        self.memory_share_manager.initialize()
        
        # 创建界面实例
        self.home_interface = HomeInterface(self)
        self.heart_rate_interface = HeartRateInterface(self)
        self.widgets_interface = WidgetsInterface(self)
        self.settings_interface = SettingsInterface(self)
        
        # 添加到导航栏
        self.addSubInterface(self.home_interface, FluentIcon.BLUETOOTH, "设备连接", NavigationItemPosition.TOP)
        self.addSubInterface(self.heart_rate_interface, FluentIcon.HEART, "心率显示", NavigationItemPosition.TOP)
        self.addSubInterface(self.widgets_interface, FluentIcon.LINK, "小组件", NavigationItemPosition.TOP)
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, "设置", NavigationItemPosition.TOP)
        
        # 不需要监听导航栏，直接在SettingsInterface的showEvent中更新设置
        
        # 心率窗口（独立窗口）
        self.heart_rate_window = None
        
        # 初始化系统托盘图标
        self.init_tray_icon()
    
    def open_heart_rate_window(self):
        """打开独立的心率显示窗口"""
        if self.heart_rate_window is None:
            self.heart_rate_window = HeartRateWindow(None)
            self.heart_rate_window.parent_window = self
        else:
            # 如果悬浮窗已存在，重新加载设置
            self.heart_rate_window.reload_settings()
        
        self.heart_rate_window.show()
        self.heart_rate_window.raise_()
        self.heart_rate_window.activateWindow()
    
    def close_heart_rate_window(self):
        """关闭独立的心率显示窗口"""
        if self.heart_rate_window:
            self.heart_rate_window.close()
            self.heart_rate_window = None
    
    # 扫描设备
    def start_scan(self):
        self.home_interface.scan_button.setEnabled(False)
        self.home_interface.scan_button.setText("扫描中...")
        self.core.scan_thread = DeviceScanThread()
        self.core.scan_thread.scan_finished.connect(self.on_scan_finished)
        self.core.scan_thread.scan_error.connect(self.on_scan_error)
        self.core.scan_thread.start()
        
    def on_scan_finished(self, devices):        
        self.core.devices = devices
        self.home_interface.combo_box.clear()
        
        if devices:
            for device in devices:
                device_name = device.name if device.name else "未知设备"
                self.home_interface.combo_box.addItem(f"{device_name} ({device.address})")
            self.home_interface.connect_button.setEnabled(True)
            InfoBar.success(
                title="扫描完成",
                content=f"发现 {len(devices)} 个设备",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            self.home_interface.connect_button.setEnabled(False)
            InfoBar.warning(
                title="未发现设备",
                content="没有扫描到任何设备",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        
        self.home_interface.scan_button.setEnabled(True)
        self.home_interface.scan_button.setText("重新扫描")
        
    def on_scan_error(self, error):
        self.home_interface.scan_button.setEnabled(True)
        self.home_interface.scan_button.setText("重新扫描")
        InfoBar.error(
            title="扫描出错：",
            content=f"{error}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    # 连接设备
    def connect_device(self):
        if self.home_interface.combo_box.currentIndex() == -1:
            InfoBar.warning(
                title="请选择设备",
                content="请先选择要连接的设备",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        index = self.home_interface.combo_box.currentIndex()
        self.core.selected_device = self.core.devices[index]
        
        # 检查设备是否支持
        if not self.core.is_device_supported(self.core.selected_device):
            InfoBar.warning(
                title="设备不支持",
                content="请重新选择",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        self.core.monitor_thread = HeartRateMonitorThread(self.core.selected_device)
        self.core.monitor_thread.heart_rate_updated.connect(self.update_heart_rate)
        self.core.monitor_thread.connection_status.connect(self.update_status)
        self.core.monitor_thread.error_occurred.connect(self.on_monitor_error)
        self.core.monitor_thread.start()
        
        self.home_interface.connect_button.setEnabled(False)
        self.home_interface.disconnect_button.setEnabled(True)
        self.home_interface.scan_button.setEnabled(False)
        
        # 自动切换到心率显示界面
        self.stackedWidget.setCurrentWidget(self.heart_rate_interface)

    def on_monitor_error(self, error):
        # 如果是用户主动断开连接，不显示提示
        if not self.user_disconnecting:
            InfoBar.info(
                title="设备已断开",
                content="设备连接已断开，您可以重新扫描或连接其他设备",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
        self.disconnect_device()
    
    # 更新心率数值
    def update_heart_rate(self, heart_rate):
        self.heart_rate_interface.update_heart_rate(heart_rate)
        if self.heart_rate_window:
            self.heart_rate_window.update_heart_rate(heart_rate)
        # 更新 HTTP 服务器的心率数据
        self.http_server.update_heart_rate(heart_rate)
        # 更新共享内存的心率数据
        self.memory_share_manager.update_heart_rate(heart_rate)

    # 更新状态信息
    def update_status(self, status):
        # 同时更新两个界面的状态显示
        self.heart_rate_interface.update_status(status)
        if self.heart_rate_window:
            self.heart_rate_window.update_status(status)
    
    # 断开设备
    def disconnect_device(self):
        print(f"[DEBUG] disconnect_device called, is_disconnecting: {self.is_disconnecting}, user_disconnecting: {self.user_disconnecting}")
        
        # 如果正在执行断开连接操作，直接返回，避免重复调用
        if self.is_disconnecting:
            print("[DEBUG] Already disconnecting, skipping")
            return
        
        # 如果已经断开连接且没有正在断开，直接返回
        if not self.core.monitor_thread and not self.user_disconnecting:
            print("[DEBUG] Already disconnected, skipping")
            return
            
        # 标记为正在断开连接
        self.is_disconnecting = True
        self.user_disconnecting = True
        
        if self.core.monitor_thread:
            self.core.monitor_thread.stop()
            self.core.monitor_thread.wait()
            self.core.monitor_thread = None
        
        self.home_interface.connect_button.setEnabled(True)
        self.home_interface.disconnect_button.setEnabled(False)
        self.home_interface.scan_button.setEnabled(True)
        self.update_status("已断开连接")
        self.update_heart_rate(0)
        
        # 显示友好的断开连接提示
        InfoBar.info(
            title="设备已断开",
            content="设备连接已断开，您可以重新扫描或连接其他设备",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )
        
        # 断开连接后返回设备连接界面
        self.stackedWidget.setCurrentWidget(self.home_interface)
        
        # 重置标志
        self.user_disconnecting = False
        self.is_disconnecting = False
    
    def init_tray_icon(self):
        """初始化系统托盘图标"""
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置托盘图标（从base64资源）
        self.tray_icon.setIcon(get_icon_from_base64(ICON_ICO))
        
        # 创建菜单
        self.tray_menu = QMenu(self)
        
        # 添加显示主窗口动作
        self.show_action = QAction("显示主窗口", self)
        self.show_action.triggered.connect(self.show_main_window)
        self.tray_menu.addAction(self.show_action)
        
        # 添加退出动作
        self.exit_action = QAction("退出", self)
        self.exit_action.triggered.connect(self.exit_application)
        self.tray_menu.addAction(self.exit_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # 连接托盘图标激活信号
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
    
    def show_main_window(self):
        """显示主窗口"""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def hide_main_window(self):
        """隐藏主窗口"""
        self.hide()
    
    def exit_application(self):
        """退出应用程序"""
        # 关闭所有窗口和线程
        if self.heart_rate_window:
            self.close_heart_rate_window()
        
        if self.core.monitor_thread:
            self.core.monitor_thread.stop()
            self.core.monitor_thread.wait()
            self.core.monitor_thread = None
        
        self.http_server.stop()
        
        # 关闭共享内存
        self.memory_share_manager.close()
        
        # 隐藏托盘图标
        self.tray_icon.hide()
        
        # 退出应用
        QApplication.quit()
    
    def on_tray_icon_activated(self, reason):
        """托盘图标激活事件处理"""
        # 左键点击显示主窗口
        if reason == QSystemTrayIcon.Trigger:
            self.show_main_window()
    
    # 关闭窗口时的处理
    def closeEvent(self, event):
        """重写关闭事件，实现最小化到任务栏的逻辑"""
        # 检查设置
        close_behavior = self.settings_manager.get("close_behavior", "ask")
        show_confirmation = self.settings_manager.get("show_close_confirmation", True)
        
        # 如果设置了不显示确认对话框，直接执行对应操作
        if not show_confirmation:
            if close_behavior == "minimize":
                self.hide_main_window()
                event.ignore()
            elif close_behavior == "close":
                self.exit_application()
            return
        
        # 显示确认对话框
        dialog = CloseConfirmationDialog(self)
        if dialog.exec_():
            option = dialog.get_option()
            dont_ask_again = dialog.get_dont_ask_again()
            
            # 如果选择了下次不再提示，保存设置
            if dont_ask_again:
                self.settings_manager.set("show_close_confirmation", False)
                self.settings_manager.set("close_behavior", option)
            
            # 执行对应操作
            if option == "minimize":
                self.hide_main_window()
                event.ignore()
            elif option == "close":
                self.exit_application()
        else:
            # 用户取消关闭
            event.ignore()
    
    # 启动 HTTP 服务器
    def start_http_server(self):
        self.http_server.start()
        InfoBar.success(
            title="HTTP 服务器已启动",
            content=f"服务器运行在 http://127.0.0.1:3030",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    # 停止 HTTP 服务器
    def stop_http_server(self):
        self.http_server.stop()
        InfoBar.info(
            title="HTTP 服务器已停止",
            content="服务器已关闭",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

# 主函数
def main():
    app = QApplication(sys.argv)
    # 创建并显示主窗口
    window = HeartRateMonitorWindow()
    window.show()
    
    # 关闭系统闪屏
    close_system_splash(system_splash_hwnd)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()