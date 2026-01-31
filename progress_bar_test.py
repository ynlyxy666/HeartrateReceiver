from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from qfluentwidgets import SubtitleLabel, IndeterminateProgressBar, ProgressBar
from PyQt5.QtGui import QColor
import sys


class ProgressBarTestWindow(QWidget):
    """测试进度条的窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.setWindowTitle("不确定进度条测试")
        self.resize(600, 300)
        
        # 创建布局
        self.layout = QVBoxLayout(self)
        
        # 添加标题
        self.title_label = SubtitleLabel("QfluentWidgets 不确定进度条测试")
        self.layout.addWidget(self.title_label)
        
        # 创建不确定进度条
        self.indeterminate_bar = IndeterminateProgressBar(start=True)
        self.layout.addWidget(self.indeterminate_bar)
        
        # 创建普通进度条（初始隐藏）
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(100)
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)
        
        # 调整布局，使两个进度条在同一位置
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建不确定进度条控制按钮
        self.button_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("暂停", self)
        self.pause_button.clicked.connect(self.pause_indeterminate)
        self.button_layout.addWidget(self.pause_button)
        
        self.resume_button = QPushButton("恢复", self)
        self.resume_button.clicked.connect(self.resume_indeterminate)
        self.button_layout.addWidget(self.resume_button)
        
        self.error_button = QPushButton("错误状态", self)
        self.error_button.clicked.connect(self.error_indeterminate)
        self.button_layout.addWidget(self.error_button)
        
        self.color_button = QPushButton("自定义颜色", self)
        self.color_button.clicked.connect(self.custom_color)
        self.button_layout.addWidget(self.color_button)
        
        self.layout.addLayout(self.button_layout)
    
    def pause_indeterminate(self):
        """暂停不确定进度条"""
        self.indeterminate_bar.pause()
        self.indeterminate_bar.hide()
        self.progress_bar.setValue(100)
        self.progress_bar.show()
    
    def resume_indeterminate(self):
        """恢复不确定进度条"""
        self.progress_bar.hide()
        self.indeterminate_bar.show()
        self.indeterminate_bar.resume()
    
    def error_indeterminate(self):
        """设置不确定进度条为错误状态"""
        self.indeterminate_bar.hide()
        self.progress_bar.setValue(100)
        # 设置错误状态颜色为暗红色 C42B1C
        self.progress_bar.setCustomBarColor(QColor(196, 43, 28), QColor(160, 30, 15))
        self.progress_bar.show()
    
    def custom_color(self):
        """自定义进度条颜色"""
        # 自定义不确定进度条颜色
        self.indeterminate_bar.setCustomBarColor(QColor(255, 0, 0), QColor(0, 255, 110))


if __name__ == "__main__":
    """主函数"""
    app = QApplication(sys.argv)
    window = ProgressBarTestWindow()
    window.show()
    sys.exit(app.exec_())