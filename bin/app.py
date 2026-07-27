import sys

# === 1. 闪屏（控制台输出） ===
import system.startup.app_startup as app_startup
app_startup.start()

# === 2. HTTP 日志流（此后所有 print 仅走 HTTP） ===
from system.log_server import LogServer, redirect_stdio
_log_server = LogServer()
_log_server.start()
redirect_stdio(_log_server)

# === 3. Qt 应用 ===
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from ui.main_window.main_window import HypeBeatWindow


def _qt_msg_handler(mode, context, message):
    print(message)


def run():
    qInstallMessageHandler(_qt_msg_handler)
    app = QApplication(sys.argv)

    window = HypeBeatWindow()
    window.show()
    app_startup.close_system_splash(app_startup.syshwnd)
    sys.exit(app.exec())
