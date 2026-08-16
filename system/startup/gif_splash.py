"""动画 GIF 启动闪屏：水滴背景 + logo 淡入 + 圆角透明窗口（pywin32 GDI + 色键透明）

基于 PoCs/gdi_splash_gif.py 移植，移除演示与生成代码，供主程序启动时调用。
核心: 独立线程窗口 + SetTimer 驱动逐帧重绘，WS_EX_LAYERED 色键抠出透明圆角。
启动 GIF 资源固定为程序目录下的 splash.gif，不再动态生成。

用法:
    splash = gif_splash.GifSplash(gif_splash.SPLASH_GIF_PATH, scale=scale)
    splash.start()                          # 独立线程显示，不阻塞主程序加载
    splash.close()                          # 主程序加载完成后关闭
"""

import ctypes
import os
import sys
import threading

import win32api
import win32con
import win32gui
import win32ui
from PIL import Image, ImageWin

TIMER_ID = 1
WND_CLASS_NAME = "HypeBeatGifSplash"

# 透明色键: GIF 中该颜色的像素被 WS_EX_LAYERED 色键抠成透明
KEY_RGB = (255, 0, 255)          # 品红（与白色 logo 无冲突）
KEY_COLORREF = (255 << 16) | (0 << 8) | 255   # COLORREF(0x00BBGGRR)
LWA_COLORKEY = 0x1
LWA_ALPHA = 0x2

# 启动 GIF 定位：依次尝试 源码目录（开发模式）→ exe 所在目录（Nuitka onefile/standalone，
# include-data-files 将 splash.gif 放在 exe 旁）→ 环境变量覆盖。
# 注意：Nuitka onefile 下编译模块的 __file__ 指向解压临时目录，上溯三级 ≠ exe 目录，
# 因此必须回退到 sys.executable 所在目录。
def _locate_splash_gif():
    candidates = []
    env_path = os.environ.get("HYPEBEAT_SPLASH_GIF")
    if env_path:
        candidates.append(env_path)
    # gif_splash.py -> startup -> system -> 项目根目录，共上三级
    candidates.append(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "splash.gif",
        )
    )
    candidates.append(os.path.join(os.path.dirname(sys.executable), "splash.gif"))
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return candidates[-1]


SPLASH_GIF_PATH = _locate_splash_gif()

# pywin32 未封装 SetTimer/KillTimer，用 ctypes 调 user32（显式 argtypes 防 64 位句柄截断）
_user32 = ctypes.windll.user32
_user32.SetTimer.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p]
_user32.SetTimer.restype = ctypes.c_void_p
_user32.KillTimer.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_user32.KillTimer.restype = ctypes.c_int

# 模块级 WndProc: 从 hwnd -> 实例 映射取对象，避免闭包被回收导致回调崩溃
_splash_instances = {}
_class_registered = False


def _wnd_proc(hwnd, msg, wparam, lparam):
    splash = _splash_instances.get(hwnd)
    if splash is None:
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
    return splash._on_message(hwnd, msg, wparam, lparam)


class GifSplash:
    """基于 pywin32 GDI 的 GIF 动画启动画面（透明圆角窗口）"""

    def __init__(self, gif_path, topmost=True, scale=1.0):
        self._topmost = topmost
        self._scale = scale
        self._frames = []          # [(ImageWin.Dib, duration_ms)]
        self._frame_index = 0
        self._hwnd = None
        self._thread = None
        self._ready = threading.Event()
        self._closed = False

        self._load_frames(gif_path)
        if not self._frames:
            raise ValueError(f"无法解码 GIF: {gif_path}")

        # DPI 缩放后的窗口尺寸（帧本身不重采样，绘制时由 StretchDIBits 拉伸）
        self._win_width = max(1, int(self._width * scale))
        self._win_height = max(1, int(self._height * scale))

    # ---------- 帧数据 ----------

    def _load_frames(self, gif_path):
        """解码 GIF 全部帧；将色键(品红)近似像素替换为精确品红，供 LayeredWindow 色键抠成透明"""
        from PIL import ImageChops

        img = Image.open(gif_path)
        self._width, self._height = img.size
        try:
            while True:
                frame = img.convert("RGBA")
                duration = int(img.info.get("duration", 100))
                if duration <= 0:
                    duration = 100
                # 量化容差: 近似品红像素 -> 精确品红，保证色键精确匹配
                r, g, b, _a = frame.split()
                rm = r.point(lambda v: 255 if v > 200 else 0)
                gm = g.point(lambda v: 255 if v < 80 else 0)
                bm = b.point(lambda v: 255 if v > 200 else 0)
                key_mask = ImageChops.multiply(ImageChops.multiply(rm, gm), bm)
                frame.paste(KEY_RGB, mask=key_mask)
                self._frames.append((ImageWin.Dib(frame.convert("RGB")), duration))
                try:
                    img.seek(img.tell() + 1)
                except EOFError:
                    break
        finally:
            img.close()

    # ---------- 窗口与消息循环 ----------

    def start(self):
        """在独立线程创建窗口并运行消息循环，不阻塞主程序加载"""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run(self):
        self._hwnd = self._create_window()
        self._ready.set()
        win32gui.PumpMessages()

    def _create_window(self):
        global _class_registered
        if not _class_registered:
            wc = win32gui.WNDCLASS()
            wc.hInstance = win32api.GetModuleHandle(None)
            wc.lpszClassName = WND_CLASS_NAME
            wc.lpfnWndProc = _wnd_proc
            win32gui.RegisterClass(wc)
            _class_registered = True

        sw, sh = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        x = (sw - self._win_width) // 2
        y = (sh - self._win_height) // 2

        ex_style = win32con.WS_EX_TOPMOST if self._topmost else 0
        ex_style |= win32con.WS_EX_LAYERED   # 分层窗口: 支持色键透明
        hwnd = win32gui.CreateWindowEx(
            ex_style,
            WND_CLASS_NAME,
            "Splash",
            win32con.WS_POPUP | win32con.WS_VISIBLE,
            x, y, self._win_width, self._win_height,
            0, 0, 0, None,
        )
        _splash_instances[hwnd] = self
        # 色键抠透明（GIF 内已含淡入动画，窗口本身全程不透明）
        # 注: 不使用 Win11 DWM 圆角——它会给窗口加一圈 1px 边框；圆角由 GIF 色键透明实现
        win32gui.SetLayeredWindowAttributes(
            hwnd, KEY_COLORREF, 255, LWA_COLORKEY | LWA_ALPHA)
        # 按首帧时长启动定时器
        _user32.SetTimer(hwnd, TIMER_ID, self._frames[0][1], None)
        return hwnd

    def close(self):
        """主程序加载完成后调用: 销毁窗口并退出消息循环"""
        if self._closed:
            return
        self._closed = True
        if self._hwnd:
            win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
            if self._thread:
                self._thread.join(timeout=3)

    # ---------- 消息处理 ----------

    def _on_message(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_TIMER:
            self._on_timer()
            return 0
        if msg == win32con.WM_PAINT:
            self._on_paint(hwnd)
            return 0
        if msg == win32con.WM_ERASEBKGND:
            return 1  # 禁止擦背景，配合双缓冲防闪烁
        if msg == win32con.WM_DESTROY:
            _user32.KillTimer(hwnd, TIMER_ID)
            _splash_instances.pop(hwnd, None)
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _on_timer(self):
        """定时器回调: 切到下一帧并请求重绘；播放完毕停在最后一帧"""
        n = len(self._frames)
        if n == 0:
            return
        next_index = self._frame_index + 1
        if next_index >= n:
            # 已到最后一帧: 停止定时器，停留在当前画面
            _user32.KillTimer(self._hwnd, TIMER_ID)
            return
        self._frame_index = next_index
        # 按当前帧时长微调定时器，适配 GIF 各帧不同 delay
        _user32.KillTimer(self._hwnd, TIMER_ID)
        _user32.SetTimer(self._hwnd, TIMER_ID, self._frames[self._frame_index][1], None)
        win32gui.InvalidateRect(self._hwnd, None, False)

    def _on_paint(self, hwnd):
        """WM_PAINT: 内存 DC 双缓冲绘制当前帧，再一次性 BitBlt 上屏"""
        hdc, ps = win32gui.BeginPaint(hwnd)
        try:
            w, h = self._win_width, self._win_height
            dib, _ = self._frames[self._frame_index]

            dc = win32ui.CreateDCFromHandle(hdc)
            mem_dc = dc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(dc, w, h)
            old_bmp = mem_dc.SelectObject(bmp)

            # 铺色键底色清屏（该色在 Layered 窗口下被抠成透明，防止拖影）
            mem_dc.FillSolidRect((0, 0, w, h), KEY_COLORREF)
            # StretchDIBits 绘制当前帧（ImageWin.Dib 内部即 StretchDIBits）
            dib.draw(mem_dc.GetHandleOutput(), (0, 0, w, h))
            # 双缓冲整体拷贝到窗口
            dc.BitBlt((0, 0), (w, h), mem_dc, (0, 0), win32con.SRCCOPY)

            mem_dc.SelectObject(old_bmp)
            mem_dc.DeleteDC()
            dc.DeleteDC()
        finally:
            win32gui.EndPaint(hwnd, ps)

    # ---------- 属性 ----------

    @property
    def width(self):
        return self._win_width

    @property
    def height(self):
        return self._win_height

    @property
    def scale(self):
        return self._scale

    @property
    def frame_count(self):
        return len(self._frames)


def ensure_splash_gif():
    """校验启动 GIF 资源存在（固定资源，不再生成）；缺失时仅提示"""
    if not (os.path.exists(SPLASH_GIF_PATH) and os.path.getsize(SPLASH_GIF_PATH) > 0):
        print(f"[Splash] 警告: 未找到启动 GIF 资源: {SPLASH_GIF_PATH}")
