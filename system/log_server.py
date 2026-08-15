"""基于 mmap 共享内存的日志流

所有 print 输出通过 sys.stdout/stderr 重定向追加写入命名共享内存，
供外部进程流式读取。不再使用 HTTP，也不再输出到标准终端。
"""

import mmap
import struct
import sys
import threading


_NOISE_KEYWORDS = ("QFluentWidgets Pro",)

_redirected = False


class LogShareMemory:
    """命名 mmap 日志缓冲区（顺序追加，头部 4 字节存写偏移）"""

    NAME = "HypeBeatLogMemory"
    SIZE = 1 << 20  # 1MB
    _HDR = 4  # 头部大小

    def __init__(self):
        self._mmap = mmap.mmap(-1, self.SIZE, self.NAME, mmap.ACCESS_WRITE)
        self._lock = threading.Lock()  # 保护 offset 读-改-写与数据写入
        self._offset = struct.unpack('I', self._mmap[0:self._HDR])[0]
        if not (self._HDR <= self._offset < self.SIZE):
            self._offset = self._HDR
            self._commit()

    def _commit(self):
        """持久化写偏移并刷新"""
        self._mmap[0:self._HDR] = struct.pack('I', self._offset)
        self._mmap.flush()

    def write_line(self, text: str):
        """追加一行日志，写满后从头覆盖最旧内容"""
        with self._lock:
            data = (text + '\n').encode('utf-8', errors='replace')
            if len(data) >= self.SIZE - self._HDR:
                data = data[:self.SIZE - self._HDR]
            if self._offset + len(data) > self.SIZE:
                self._offset = self._HDR  # 回绕覆盖
            self._mmap[self._offset:self._offset + len(data)] = data
            self._offset += len(data)
            self._commit()


def redirect_stdio(shared_log: LogShareMemory) -> None:
    """替换 sys.stdout/sys.stderr 为共享内存流，同时并行回显到原控制台

    多次调用安全（幂等）。控制台与共享内存并行输出；
    无控制台环境（如打包后 exe）下回显自动忽略，不阻塞主流程。
    未处理异常 traceback 同样双写。
    """
    global _redirected
    if _redirected:
        return

    # 保存原始流，用于并行回显控制台
    _orig_stdout = sys.stdout
    _orig_stderr = sys.stderr

    class _LogStream:
        def __init__(self, origin):
            self._origin = origin

        def write(self, text):
            if not text:
                return
            if any(k in text for k in _NOISE_KEYWORDS):
                return
            stripped = text.rstrip('\n')
            if stripped:
                shared_log.write_line(stripped)
            # 并行回显到控制台（打包无控制台时忽略失败）
            try:
                self._origin.write(text)
                self._origin.flush()
            except Exception:
                pass

        def flush(self):
            try:
                self._origin.flush()
            except Exception:
                pass

        @property
        def encoding(self):
            return 'utf-8'

        def isatty(self):
            return False

    sys.stdout = _LogStream(_orig_stdout)
    sys.stderr = _LogStream(_orig_stderr)

    def _emit_both(text):
        """异常日志双写: 共享内存 + 原控制台"""
        shared_log.write_line(text)
        try:
            _orig_stderr.write(text + '\n')
            _orig_stderr.flush()
        except Exception:
            pass

    def _sys_hook(exc_type, exc_value, exc_tb):
        import traceback
        text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip('\n')
        _emit_both(f'[UNHANDLED] {text}')

    sys.excepthook = _sys_hook

    def _thread_hook(args):
        import traceback
        text = ''.join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback
        )).rstrip('\n')
        _emit_both(f'[THREAD] {text}')

    threading.excepthook = _thread_hook

    _redirected = True
