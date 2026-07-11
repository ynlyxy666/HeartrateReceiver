import sys

# DPI 感知由 app_startup.start() 中 SetProcessDpiAwareness(2) 完成
# Qt 使用默认的 PER_MONITOR_AWARE_V2 行为，两者一致，无需额外配置

# 闪屏必须在任何 PyQt 加载前执行，覆盖 PyQt 的初始化耗时
import system.startup.app_startup as app_startup
app_startup.start()

from PyQt6.QtCore import qInstallMessageHandler
from PyQt6.QtWidgets import QApplication

from ui.main_window.main_window import HypeBeatWindow


def _qt_msg_handler(mode, context, message):
    if "QFont::setPointSize" not in message:
        print(message)


def run():
    app = QApplication(sys.argv)
    qInstallMessageHandler(_qt_msg_handler)

    window = HypeBeatWindow()
    window.show()

    app_startup.close_system_splash(app_startup.syshwnd)

    sys.exit(app.exec())
