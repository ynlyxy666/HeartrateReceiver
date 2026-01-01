from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu
from PyQt5.QtGui import QPixmap
from qfluentwidgets import TitleLabel, CardWidget, BodyLabel, PushButton
import webbrowser

class WidgetsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("widgets_interface")
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.title_label = TitleLabel("小组件")
        
        self.card1 = CardWidget(self)
        self.card1.setFixedHeight(120)
        self.card1.setCursor(Qt.PointingHandCursor)
        self.card1.installEventFilter(self)
        
        card1_layout = QHBoxLayout(self.card1)
        card1_layout.setContentsMargins(20, 20, 20, 20)
        card1_layout.setSpacing(20)
        
        card1_text = BodyLabel("<b>JSON/OBS 数据接口</b><br>提供 HTTP 服务用于 OBS 直播<br>单击卡片打开文档<br><span style='color: green;'>端口: 3030</span>")
        card1_text.setWordWrap(True)
        
        self.card1_button = PushButton("启动服务", self.card1)
        self.card1_button.setFixedWidth(100)
        self.card1_button.clicked.connect(self.toggle_http_server)
        
        card1_layout.addWidget(card1_text, 1)
        card1_layout.addWidget(self.card1_button, 0, Qt.AlignCenter)
        
        self.http_server_running = False
        
        self.card2 = CardWidget(self)
        self.card2.setFixedHeight(120)
        self.card2.setCursor(Qt.PointingHandCursor)
        self.card2.installEventFilter(self)
        
        card2_layout = QHBoxLayout(self.card2)
        card2_layout.setContentsMargins(20, 20, 20, 20)
        card2_layout.setSpacing(20)
        
        card2_text = BodyLabel("<b>实时心率波动图，点击启动</b><br>专为极客设计<br><span style='color: red;'>组件设置，关闭在右键菜单里<br>主窗口关闭时小窗口不关闭</span>")
        card2_text.setWordWrap(True)
        
        card2_image = QLabel()
        card2_image.setFixedSize(130, 98)
        pixmap = QPixmap("src/cp2.png")
        if not pixmap.isNull():
            card2_image.setPixmap(pixmap.scaled(130, 98, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        card2_image.setAlignment(Qt.AlignCenter)
        
        card2_layout.addWidget(card2_text, 1)
        card2_layout.addWidget(card2_image, 0, Qt.AlignCenter)
        
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.card1)
        self.main_layout.addWidget(self.card2)
        self.main_layout.addStretch()
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于处理卡片的点击和右键菜单"""
        if obj == self.card1:
            if event.type() == event.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    webbrowser.open("https://www.bilibili.com/opus/1083188488624406549")
                    return True
                elif event.button() == Qt.RightButton:
                    self.show_card1_context_menu(event.globalPos())
                    return True
        elif obj == self.card2:
            if event.type() == event.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.parent.open_heart_rate_window()
                    return True
                elif event.button() == Qt.RightButton:
                    self.show_card2_context_menu(event.globalPos())
                    return True
        return super().eventFilter(obj, event)
    
    def show_card1_context_menu(self, position):
        """显示卡片1的右键菜单"""
        menu = QMenu(self)
        
        if self.http_server_running:
            action_stop = menu.addAction("停止服务")
        else:
            action_start = menu.addAction("启动服务")
        
        action = menu.exec_(position)
        
        if action == action_start:
            self.toggle_http_server()
        elif action == action_stop:
            self.toggle_http_server()
    
    def toggle_http_server(self):
        """切换 HTTP 服务器状态"""
        if self.http_server_running:
            self.parent.stop_http_server()
            self.http_server_running = False
            self.card1_button.setText("启动服务")
        else:
            self.parent.start_http_server()
            self.http_server_running = True
            self.card1_button.setText("停止服务")
    
    def show_card2_context_menu(self, position):
        """显示卡片2的右键菜单"""
        menu = QMenu(self)
        
        # 添加菜单项
        action_settings = menu.addAction("设置")
        action_about = menu.addAction("关于")
        
        # 显示菜单并获取用户选择
        action = menu.exec_(position)
        
        if action == action_settings:
            print("打开设置")
        elif action == action_about:
            print("显示关于信息")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.card1.underMouse():
                print("卡片1被点击")
            elif self.card2.underMouse():
                print("卡片2被点击")