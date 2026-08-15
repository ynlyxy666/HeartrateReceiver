import sys

# === 1. 闪屏（控制台输出） ===
import system.startup.app_startup as app_startup
app_startup.start()

# === 2. 日志共享内存（此后所有 print 并行输出: 控制台 + 共享内存） ===
from system.log_server import LogShareMemory, redirect_stdio
_log_share = LogShareMemory()
redirect_stdio(_log_share)

# === 3. Qt 应用 ===
from PySide6.QtCore import QTimer, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from ui.main_window.main_window import HypeBeatWindow


def _qt_msg_handler(mode, context, message):
    # 屏蔽无实际影响的 Qt 字体警告（第三方库设置无效字号 -1 导致）
    if "QFont::setPointSize" in message:
        return
    print(message)


def run():
    qInstallMessageHandler(_qt_msg_handler)
    app = QApplication(sys.argv)

    window = HypeBeatWindow()
    window.show()
    app_startup.close_system_splash(app_startup.syshwnd)

    # 闪屏（TOPMOST 独立线程窗口）销毁后，事件循环第一帧将主窗口置顶激活，
    # 避免 Windows 前台锁定导致主窗口落在其它窗口后面
    QTimer.singleShot(0, window.bring_to_front)
    sys.exit(app.exec())
