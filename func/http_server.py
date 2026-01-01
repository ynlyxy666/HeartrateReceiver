from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# HTTP 请求处理器
class HeartRateHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>心率显示</title>
    <style>
        body {
            background-color: rgba(0, 0, 0, 0);
            margin: 0px auto;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            font-family: Arial, sans-serif;
        }
        #heart-rate-container {
            text-align: center;
        }
        #heart-rate-number {
            font-size: 120px;
            font-weight: bold;
            color: #ff4444;
            text-shadow: 0 0 10px rgba(255, 68, 68, 0.5);
        }
        #heart-icon {
            font-size: 60px;
            color: #ff4444;
            animation: heartbeat 1s infinite;
        }
        @keyframes heartbeat {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        #unit {
            font-size: 30px;
            color: #ff4444;
        }
    </style>
</head>
<body>
    <div id="heart-rate-container">
        <div id="heart-icon">❤</div>
        <div>
            <span id="heart-rate-number">--</span>
            <span id="unit">BPM</span>
        </div>
    </div>
    <script>
        async function updateHeartRate() {
            try {
                let response = await fetch('/heartrate');
                let heartRate = await response.json();
                document.getElementById('heart-rate-number').textContent = heartRate;
            } catch (err) {
                console.error(err);
            }
        }
        setInterval(updateHeartRate, 1000);
        updateHeartRate();
    </script>
</body>
</html>'''
            self.wfile.write(html_content.encode('utf-8'))
        elif self.path == '/heartrate':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            heart_rate = self.server.get_heart_rate()
            self.wfile.write(str(heart_rate).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

# HTTP 服务器类
class HeartRateHTTPServer:
    def __init__(self, port=3030):
        self.port = port
        self.server = None
        self.server_thread = None
        self.current_heart_rate = 0
    
    def get_heart_rate(self):
        return self.current_heart_rate
    
    def update_heart_rate(self, heart_rate):
        self.current_heart_rate = heart_rate
    
    def start(self):
        if self.server is None:
            self.server = HTTPServer(('127.0.0.1', self.port), HeartRateHTTPRequestHandler)
            self.server.get_heart_rate = self.get_heart_rate
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
    
    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.server_thread = None
