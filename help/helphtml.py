import pathlib
import threading
import webview

_lock = threading.Lock()
_window_open = False


def show_help():
    """打开说明书窗口（同步，会阻塞主程序）"""
    html = pathlib.Path(__file__).with_name("help.html").read_text("utf-8")
    window = webview.create_window('说明书', html=html, width=1000, height=750, resizable=False)
    webview.start()


def show_help_async():
    """打开说明书窗口（异步，不阻塞主程序），已打开时忽略重复请求"""
    global _window_open
    with _lock:
        if _window_open:
            print("[帮助] 窗口已打开，忽略重复请求")
            return
        _window_open = True
    thread = threading.Thread(target=_run_help, daemon=True)
    thread.start()


def _run_help():
    try:
        print("[帮助] 说明书窗口已打开")
        show_help()
    finally:
        global _window_open
        with _lock:
            _window_open = False
        print("[帮助] 说明书窗口已关闭")


if __name__ == '__main__':
    show_help()
