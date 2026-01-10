from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from qfluentwidgets import CardWidget
from .radial_gauge import RadialGauge


class DashboardPage(QWidget):
    """仪表盘页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # 主布局
        self.dashboard_layout = QVBoxLayout(self)
        self.dashboard_layout.setSpacing(0)
        self.dashboard_layout.setContentsMargins(0, 0, 0, 0)
        
        # 仪表盘卡片（与折线图卡片等高）
        self.dashboard_card = CardWidget(self)
        self.dashboard_card_layout = QVBoxLayout(self.dashboard_card)
        self.dashboard_card_layout.setContentsMargins(12, 12, 12, 12)
        self.dashboard_card_layout.setSpacing(0)
        
        # 添加RadialGauge组件
        self.dashboard_gauge = RadialGauge(self, 0, 200)
        
        # 添加图例（置于页面底部，一行）
        self.dashboard_legend = QLabel("箭头：当前心率平均值")
        self.dashboard_legend.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: #666;")
        self.dashboard_legend.setAlignment(Qt.AlignCenter)
        
        # 添加到卡片布局，居中显示
        self.dashboard_card_layout.addStretch()
        self.dashboard_card_layout.addWidget(self.dashboard_gauge, alignment=Qt.AlignCenter)
        self.dashboard_card_layout.addSpacing(12)  # 添加间距
        self.dashboard_card_layout.addWidget(self.dashboard_legend)
        self.dashboard_card_layout.addStretch()
        
        # 将卡片添加到仪表盘页面
        self.dashboard_layout.addWidget(self.dashboard_card)