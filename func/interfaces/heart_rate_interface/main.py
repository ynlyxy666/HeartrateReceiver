from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFontDialog, QColorDialog, QMessageBox
from PyQt5.QtGui import QFont, QColor
from qfluentwidgets import SegmentedWidget
from .line_chart_page import LineChartPage
from .big_number_page import BigNumberPage
from .dashboard_page import DashboardPage
from .trend_chart_page import TrendChartPage


class HeartRateInterface(QWidget):
    """心率界面 - 集成动态折线图"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("heart_rate_interface")
        self.parent = parent
        self.setup_ui()
        self.current_device_name = None  # 存储当前连接的设备名称
        # 心率统计变量
        self.current_heart_rate = 0
        self.highest_heart_rate = 0
        self.lowest_heart_rate = float('inf')
    
    def setup_ui(self):
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 添加分段控制器
        self.segmented_widget = SegmentedWidget(self)
        self.segmented_widget.addItem("line_chart", "折线图")
        self.segmented_widget.addItem("big_number", "大数字")
        self.segmented_widget.addItem("dashboard", "仪表盘")
        self.segmented_widget.addItem("trend_chart", "趋势折线")
        self.segmented_widget.setCurrentItem("line_chart")
        self.segmented_widget.currentItemChanged.connect(self.on_segmented_changed)
        
        # 将分段控制器添加到主布局
        self.main_layout.addWidget(self.segmented_widget)
        
        # 创建四个子页面
        self.line_chart_page = LineChartPage(self)
        self.big_number_page = BigNumberPage(self)
        self.dashboard_page = DashboardPage(self)
        self.trend_chart_page = TrendChartPage(self)
        
        # 连接大数字页面的字体选择按钮信号
        self.big_number_page.font_select_button.clicked.connect(self.select_font)
        
        # 将四个页面添加到主布局
        self.main_layout.addWidget(self.line_chart_page)
        self.main_layout.addWidget(self.big_number_page)
        self.main_layout.addWidget(self.dashboard_page)
        self.main_layout.addWidget(self.trend_chart_page)
        
        # 初始化只显示第一个页面
        self.big_number_page.hide()
        self.dashboard_page.hide()
        self.trend_chart_page.hide()
    
    def on_segmented_changed(self, current_item):
        """分段控制器切换事件"""
        # 隐藏所有页面
        self.line_chart_page.hide()
        self.big_number_page.hide()
        self.dashboard_page.hide()
        self.trend_chart_page.hide()
        
        # 显示当前选中的页面
        if current_item == "line_chart":
            self.line_chart_page.show()
        elif current_item == "big_number":
            self.big_number_page.show()
        elif current_item == "dashboard":
            self.dashboard_page.show()
        elif current_item == "trend_chart":
            self.trend_chart_page.show()
    
    def update_heart_rate(self, heart_rate):
        """更新心率数值"""
        # 添加到折线图，包括0值
        self.line_chart_page.chart.add_value(heart_rate)
        # 更新HR显示（HR后面空两格显示数字）
        self.line_chart_page.left_label.setText(f"HR  {heart_rate}")
        # 更新右上角显示MAX_Y值
        self.line_chart_page.top_right_label.setText(f"{int(self.line_chart_page.chart.MAX_Y)}")
        # 右下角始终显示0
        self.line_chart_page.bottom_right_label.setText("0")
        
        # 更新心率统计
        self.current_heart_rate = heart_rate
        
        # 更新最高心率
        if heart_rate > self.highest_heart_rate:
            self.highest_heart_rate = heart_rate
        
        # 更新最低心率
        if heart_rate < self.lowest_heart_rate and heart_rate > 0:
            self.lowest_heart_rate = heart_rate
        
        # 更新大数字卡片显示
        self.big_number_page.current_hr_label.setText(str(heart_rate))
        
        # 更新平均心率显示
        avg_hr = self.line_chart_page.chart.average_heart_rate
        self.big_number_page.average_hr_label.setText(f"平均: {round(avg_hr) if avg_hr > 0 else 0} BPM")
        
        # 更新最高/最低心率显示
        self.big_number_page.minmax_hr_label.setText(f"最高: {self.highest_heart_rate} BPM | 最低: {self.lowest_heart_rate if self.lowest_heart_rate != float('inf') else 0} BPM")
        
        # 更新仪表盘卡片显示
        self.dashboard_page.dashboard_gauge.set_value(heart_rate)
        self.dashboard_page.dashboard_gauge.set_average_value(round(avg_hr) if avg_hr > 0 else 0)
        
        # 更新趋势折线图显示
        self.trend_chart_page.update_heart_rate(heart_rate)
    
    def select_font(self):
        """打开字体选择对话框"""
        # 获取当前样式
        current_style = self.big_number_page.current_hr_label.styleSheet()
        
        # 提取当前字体和颜色信息作为默认值
        # 默认字体
        default_font = QFont("Segoe UI")
        
        # 解析当前样式中的字体家族
        import re
        font_match = re.search(r"font-family: '(.*?)';", current_style)
        if font_match:
            default_font.setFamily(font_match.group(1))
        
        # 默认颜色（红色）
        default_color = QColor(255, 0, 0)  # #FF0000
        
        # 解析当前样式中的颜色
        color_match = re.search(r"color: (#.*?);", current_style)
        if color_match:
            default_color = QColor(color_match.group(1))
        
        # 打开字体对话框，设置当前字体为默认值
        font, ok = QFontDialog.getFont(default_font)
        if ok:
            # 打开颜色对话框，设置当前颜色为默认值
            color = QColorDialog.getColor(default_color)
            if color.isValid():
                # 检查颜色是否接近白色（RGB均大于192）
                r, g, b, _ = color.getRgb()
                if r > 220 and g > 220 and b > 220:
                    QMessageBox.warning(
                        self,
                        "颜色警告",
                        "您选择的颜色接近白色，可能导致显示不清晰，请考虑使用深色。",
                        QMessageBox.Ok
                    )
                
                # 更新当前心率标签的样式
                new_style = f"font-family: '{font.family()}'; font-size: {self.big_number_page.fixed_font_size}px; font-weight: bold; color: {color.name()};"
                self.big_number_page.current_hr_label.setStyleSheet(new_style)
    
    def update_status(self, status):
        """更新状态信息"""
        if "设备连接成功" in status:
            # 从父窗口获取当前连接的设备名称
            if self.parent and hasattr(self.parent, 'core') and self.parent.core.selected_device:
                device_name = self.parent.core.selected_device.name
                if device_name:
                    self.current_device_name = device_name
                    self.line_chart_page.right_label.setText(device_name)
                    self.trend_chart_page.right_label.setText(device_name)
                else:
                    self.line_chart_page.right_label.setText("未知设备")
                    self.trend_chart_page.right_label.setText("未知设备")
            else:
                self.line_chart_page.right_label.setText("未知设备")
                self.trend_chart_page.right_label.setText("未知设备")
        elif "已断开连接" in status or "请先连接设备" in status:
            self.current_device_name = None
            self.line_chart_page.right_label.setText("请先连接设备")
            self.trend_chart_page.right_label.setText("请先连接设备")