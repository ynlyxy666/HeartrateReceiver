import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView

HTML_CODE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>桌面小组件/OBS直播串流功能说明文档</title>
    <style>
        /* 全局样式 */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
            line-height: 1.6;
        }
        
        /* 容器样式 */
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        /* 头部样式 */
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }
        
        .header .subtitle {
            color: #a0c4ff;
            font-size: 1.1rem;
            font-weight: 300;
        }
        
        /* 内容区域样式 */
        .content {
            padding: 40px;
        }
        
        /* 章节样式 */
        .section {
            margin-bottom: 40px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 15px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .section:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        /* 标题样式 */
        .section h2 {
            color: #1e3c72;
            font-size: 1.8rem;
            margin-bottom: 20px;
            font-weight: 600;
            text-align: center;
            position: relative;
            padding-bottom: 15px;
        }
        
        .section h2::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 4px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 2px;
        }
        
        /* 段落样式 */
        .section p {
            font-size: 1.1rem;
            margin-bottom: 15px;
            text-align: center;
            color: #555;
        }
        
        /* 强调文本样式 */
        .highlight {
            color: #e74c3c !important;
            font-weight: 600;
        }
        
        .warning {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            color: #856404;
            padding: 15px 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: 600;
            text-align: center;
            border-left: 5px solid #ffc107;
        }
        
        /* 代码/文件名样式 */
        .filename {
            background: #e8f4f8;
            color: #2c3e50;
            padding: 3px 8px;
            border-radius: 5px;
            font-family: 'Courier New', Courier, monospace;
            font-weight: 600;
        }
        
        /* 链接样式 */
        a {
            color: #3498db;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            position: relative;
        }
        
        a:hover {
            color: #2980b9;
        }
        
        a::after {
            content: '';
            position: absolute;
            width: 0;
            height: 2px;
            bottom: -2px;
            left: 0;
            background-color: #3498db;
            transition: width 0.3s ease;
        }
        
        a:hover::after {
            width: 100%;
        }
        
        /* 最终提示样式 */
        .final-tip {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            color: #155724;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin-top: 40px;
            border: 2px solid #28a745;
        }
        
        .final-tip h1 {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        /* 按钮样式 */
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1rem;
            margin: 20px 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .container {
                margin: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .content {
                padding: 20px;
            }
            
            .section {
                padding: 20px;
            }
            
            .section h2 {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>桌面小组件/OBS直播串流功能</h1>
            <div class="subtitle">说明文档</div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>这是干什么用的？</h2>
                <p>这款心率接收器不包含桌面小组件功能。这个功能可以用于直播，游戏等诸多场景。此插件用于补充这些功能。</p>
            </div>
            
            <div class="section">
                <h2>怎么下载？</h2>
                <p>https://github.com/ynlyxy666/HeartrateReceiver/releases</p>
                <p>复制到浏览器中，找到<span class="highlight">最新版本</span>的“<span class="filename">pluginXXXX.exe</span>”单击下载。</p>
            </div>
            
            <div class="section">
                <h2>下载完了然后呢？</h2>
                <p>找到下载好的<span class="filename">pluginXXXX.exe</span>，放入C盘下<span class="highlight"><strong><em><u>BHP</u></em></strong></span>文件夹中</p>
                <div class="warning">BHP三个字母必须均大写！！！</div>
                <p>完全关闭并重启程序。（确保任务栏没有驻留图标！）</p>
            </div>
            
            <div class="final-tip">
                <h1>然后就可以用了。</h1>
            </div>
        </div>
    </div>
</body>
</html>
'''

class HtmlViewer(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("说明")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建WebEngineView组件
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # 禁用右键菜单
        self.web_view.setContextMenuPolicy(0)  # Qt.NoContextMenu
        
        # 加载HTML内容
        self.web_view.setHtml(HTML_CODE)
        
    def closeEvent(self, event):
        # 确保WebEngineView资源被正确释放
        self.web_view.deleteLater()
        super().closeEvent(event)

def showHelp(parent=None):
    # 使用现有的QApplication实例，避免重复创建
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    viewer = HtmlViewer(parent)
    viewer.show()
    # 不调用app.exec_()，使用现有的事件循环
    return viewer

if __name__ == "__main__":
    showHelp()