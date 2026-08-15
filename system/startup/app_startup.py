import ctypes
import win32api

import system.startup.gif_splash as gif_splash

syshwnd = None  # 动画闪屏对象（GifSplash 实例）


def show_system_splash(pre_aware_width=None):
    """创建动画闪屏（水滴背景 + logo 淡入 + 圆角透明窗口，无 QApp 依赖，立即显示）

    Args:
        pre_aware_width: 设置DPI感知前的屏幕虚拟宽度，用于计算缩放倍数

    Returns:
        GifSplash 实例，失败时返回 None
    """
    try:
        # 首次运行生成 GIF 缓存，之后直接复用
        gif_splash.ensure_splash_gif()

        # 通过感知前后的屏幕宽度比值计算DPI缩放倍数
        # 不依赖任何DPI API，纯数学计算，最可靠
        scale = 1.0
        if pre_aware_width:
            physical_width = win32api.GetSystemMetrics(0)
            if physical_width and physical_width > pre_aware_width:
                scale = physical_width / pre_aware_width
        print(f"[Splash] DPI scale: {scale} (pre_aware={pre_aware_width}, "
              f"physical={physical_width if pre_aware_width else 'N/A'})")

        splash = gif_splash.GifSplash(gif_splash.SPLASH_GIF_PATH, scale=scale)
        splash.start()
        print("[Splash] GIF splash show")
        return splash

    except Exception as e:
        print(f"Error creating splash: {e}")
        import traceback
        traceback.print_exc()
        return None


def close_system_splash(splash):
    """关闭动画闪屏"""
    if splash is not None:
        try:
            splash.close()
        except Exception:
            pass


def startup_check():
    import sys

    def is_single_instance():
        """检测是否只有一个实例在运行"""
        if sys.platform == 'win32':
            mutex_name = "Global\\HypeBeatMutex"
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
            last_error = ctypes.windll.kernel32.GetLastError()

            if last_error == 183:
                try:
                    import win32gui
                    import win32con

                    def enum_windows_callback(hwnd, lParam):
                        window_title = win32gui.GetWindowText(hwnd)
                        if "心率监测器" in window_title:
                            if win32gui.IsIconic(hwnd):
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd)
                            return False
                        return True

                    win32gui.EnumWindows(enum_windows_callback, None)
                except Exception as e:
                    print(f"激活现有窗口失败: {e}")
                return False
            return True
        return True

    if not is_single_instance():
        print("程序已经在运行，正在切换到前台...")
        sys.exit(0)


def start():
    global syshwnd
    # 必须在 DPI 感知前抓取虚拟屏幕宽度，用于后续计算缩放倍数
    pre_aware_width = win32api.GetSystemMetrics(0)

    # 主动声明DPI感知，防止Windows虚拟缩放导致闪屏尺寸异常
    # 必须在创建任何窗口前调用，保证与后续PyQt6的DPI行为一致
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    syshwnd = show_system_splash(pre_aware_width)
    startup_check()
