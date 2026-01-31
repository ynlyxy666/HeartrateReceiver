from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import CardWidget, PushButton


class BigNumberPage(QWidget):
    """大数字页面"""
    
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.fixed_font_size = 72
        self.setup_ui()
    
    def setup_ui(self):
        # 主布局
        self.big_number_layout = QVBoxLayout(self)
        self.big_number_layout.setSpacing(0)
        self.big_number_layout.setContentsMargins(0, 0, 0, 0)
        
        # 大数字卡片（与折线图卡片等高）
        self.big_number_card = CardWidget(self)
        self.big_number_card_layout = QVBoxLayout(self.big_number_card)
        self.big_number_card_layout.setContentsMargins(12, 12, 12, 12)
        self.big_number_card_layout.setSpacing(16)
        
        # 顶部水平布局（用于放置字体切换按钮）
        self.big_number_top_layout = QHBoxLayout()
        self.big_number_top_layout.setSpacing(10)
        
        # 添加弹性空间，将按钮推到右侧
        self.big_number_top_layout.addStretch()
        
        # 字体切换按钮
        self.font_select_button = PushButton("字")
        self.font_select_button.setFixedSize(32, 32)
        self.font_select_button.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; font-weight: bold;")
        
        # 将按钮添加到顶部布局
        self.big_number_top_layout.addWidget(self.font_select_button)
        
        # 添加顶部布局到卡片布局
        self.big_number_card_layout.addLayout(self.big_number_top_layout)
        
        # 当前心率标签（最大字体）
        self.current_hr_label = QLabel("0")
        # 从配置文件加载字体设置
        font_family = 'Segoe UI'
        font_color = '#333'
        if self.settings_manager:
            font_family = self.settings_manager.get("big_number_font_family", "Segoe UI")
            font_color = self.settings_manager.get("big_number_font_color", "#333")
        self.current_hr_label.setStyleSheet(f"font-family: '{font_family}'; font-size: {self.fixed_font_size}px; font-weight: bold; color: {font_color};")
        self.current_hr_label.setAlignment(Qt.AlignCenter)
        
        # 创建固定高度的容器来放置当前心率标签
        self.hr_display_container = QWidget()
        self.hr_display_layout = QVBoxLayout(self.hr_display_container)
        self.hr_display_layout.setSpacing(16)
        self.hr_display_layout.setContentsMargins(0, 0, 0, 0)
        
        # 当前心率标签
        self.hr_display_layout.addWidget(self.current_hr_label)
        
        # 创建固定高度的统计信息容器
        self.stats_container = QWidget()
        self.stats_container.setFixedHeight(80)  # 固定高度，防止自动变化
        self.stats_layout = QVBoxLayout(self.stats_container)
        self.stats_layout.setSpacing(8)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        
        # 平均心率标签（中等字体）
        self.average_hr_label = QLabel("平均: 0 BPM")
        self.average_hr_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 24px; font-weight: normal; color: #666;")
        self.average_hr_label.setAlignment(Qt.AlignCenter)
        
        # 最高/最低心率标签（小字体）
        self.minmax_hr_label = QLabel("最高: 0 BPM | 最低: 0 BPM")
        self.minmax_hr_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 16px; font-weight: normal; color: #999;")
        self.minmax_hr_label.setAlignment(Qt.AlignCenter)
        
        # 将统计标签添加到固定高度的容器
        self.stats_layout.addWidget(self.average_hr_label)
        self.stats_layout.addWidget(self.minmax_hr_label)
        
        # 添加到卡片布局
        self.big_number_card_layout.addWidget(self.hr_display_container)
        self.big_number_card_layout.addWidget(self.stats_container)
        self.big_number_card_layout.addStretch()
        
        # 将卡片添加到大数字页面
        self.big_number_layout.addWidget(self.big_number_card)