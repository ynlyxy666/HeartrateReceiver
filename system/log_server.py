"""HTTP 纯文本日志流服务器

监听 59234 端口，使用 Transfer-Encoding: chunked 将控制台日志以纯文本
流式推送到 HTTP 客户端。打开 http://127.0.0.1:59234 即可查看。
控制台输出保持不变。
"""

import socket
import sys
import threading
from collections import deque


class LogServer:
    """HTTP 纯文本日志流服务器"""

    def __init__(self, host: str = '0.0.0.0', port: int = 59234,
                 max_history: int = 500):
        self.host = host
        self.port = port
        self.max_history = max_history
        self._history: deque[str] = deque(maxlen=max_history)
        self._clients: set[socket.socket] = set()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """在后台线程启动 HTTP 服务器"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(10)
        server.settimeout(1.0)

        while self._running:
            try:
                client, addr = server.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break

        server.close()

    # ---- HTTP 请求处理 ----

    def _handle_client(self, client: socket.socket, addr) -> None:
        """解析 HTTP 请求，所有路径均返回纯文本流"""
        try:
            client.settimeout(5.0)
            data = b''
            while b'\r\n\r\n' not in data:
                chunk = client.recv(4096)
                if not chunk:
                    return
                data += chunk
                if len(data) > 65536:
                    return
        except socket.timeout:
            return
        except OSError:
            return

        self._handle_stream(client)

    def _handle_stream(self, client: socket.socket) -> None:
        """建立 HTTP chunked 纯文本流连接"""
        client.settimeout(30.0)
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        resp = (
            'HTTP/1.1 200 OK\r\n'
            'Content-Type: text/plain; charset=utf-8\r\n'
            'Transfer-Encoding: chunked\r\n'
            'Cache-Control: no-cache\r\n'
            'Connection: keep-alive\r\n'
            'Access-Control-Allow-Origin: *\r\n'
            '\r\n'
        ).encode()
        try:
            client.sendall(resp)
        except OSError:
            return

        # 先发一个 padding 块（~2KB 空格），触发浏览器立即开始渲染
        # 否则 text/plain 会被缓冲到积累 ~1KB 才显示
        self._send_chunk(client, ' ' * 2048 + '\n')

        # 推送历史日志
        snapshot = []
        with self._lock:
            snapshot = list(self._history)
        if snapshot:
            self._send_chunk(client, '\n'.join(snapshot) + '\n')

        with self._lock:
            self._clients.add(client)

        # 保持连接，检测断开
        try:
            while self._running:
                try:
                    if client.recv(1) == b'':
                        break
                except socket.timeout:
                    continue
        except OSError:
            pass
        finally:
            with self._lock:
                self._clients.discard(client)

    @staticmethod
    def _send_chunk(client: socket.socket, text: str) -> None:
        """以 HTTP chunked 格式发送一段文本"""
        data = text.encode('utf-8', errors='replace')
        header = f'{len(data):x}\r\n'.encode()
        client.sendall(header + data + b'\r\n')

    # ---- 广播 ----

    def broadcast(self, message: str) -> None:
        """广播一行日志到所有客户端，并写入历史缓冲区"""
        self._history.append(message)

        if not self._clients:
            return

        frame = message + '\n'
        dead: list[socket.socket] = []
        with self._lock:
            for client in self._clients:
                try:
                    self._send_chunk(client, frame)
                except OSError:
                    dead.append(client)
            for d in dead:
                self._clients.discard(d)

    def stop(self) -> None:
        self._running = False
        with self._lock:
            for client in self._clients:
                try:
                    client.sendall(b'0\r\n\r\n')  # chunked 结束标记
                    client.close()
                except OSError:
                    pass
            self._clients.clear()


# ---- stdout/stderr 重定向 ----

# 过滤噪音关键字（包含则不输出到任何地方）
_NOISE_KEYWORDS = ("QFluentWidgets Pro",)


class _BroadcastStream:
    """替换 sys.stdout/sys.stderr，同时写入原始流 + HTTP 广播"""

    def __init__(self, original, server: LogServer):
        self._original = original
        self._server = server

    def write(self, text: str) -> None:
        if not text:
            return
        if any(k in text for k in _NOISE_KEYWORDS):
            return
        if self._original:
            self._original.write(text)
            self._original.flush()
        stripped = text.rstrip('\n')
        if stripped and self._server:
            self._server.broadcast(stripped)

    def flush(self) -> None:
        if self._original:
            self._original.flush()

    @property
    def encoding(self):
        return self._original.encoding if self._original else 'utf-8'

    def isatty(self) -> bool:
        return False


_redirected = False


def redirect_stdio(server: LogServer) -> None:
    """替换 sys.stdout/sys.stderr，捕获所有 print() 和 traceback

    同时设置 sys.excepthook / threading.excepthook 以捕获未处理异常。
    多次调用安全（幂等）。
    """
    global _redirected
    if _redirected:
        return

    sys.stdout = _BroadcastStream(sys.__stdout__, server)
    sys.stderr = _BroadcastStream(sys.__stderr__, server)

    _original_excepthook = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_tb):
        import traceback
        lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        text = ''.join(lines).rstrip('\n')
        server.broadcast(f'[UNHANDLED] {text}')
        if _original_excepthook is not sys.excepthook:
            try:
                _original_excepthook(exc_type, exc_value, exc_tb)
            except Exception:
                pass

    sys.excepthook = _excepthook

    _original_thread_hook = threading.excepthook

    def _thread_hook(args):
        import traceback
        text = ''.join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback
        ))
        server.broadcast(f'[THREAD] {text}')
        if _original_thread_hook is not threading.excepthook:
            try:
                _original_thread_hook(args)
            except Exception:
                pass

    threading.excepthook = _thread_hook

    _redirected = True
