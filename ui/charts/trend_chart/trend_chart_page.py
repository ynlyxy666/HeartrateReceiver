import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import CardWidget
from collections import deque

# 字体设置：使用系统字体名称，避免硬编码路径
FONT_CN = FontProperties(family='Microsoft YaHei', size=9)

# 实时图表最多保留的数据点数（滑动窗口，避免无限累积与全量重绘卡顿）
MAX_POINTS = 600


class TrendChartPage(QWidget):
    """趋势折线图页面（matplotlib 实现）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = deque(maxlen=MAX_POINTS)
        self.setup_ui()

    def setup_ui(self):
        # 主布局
        self.trend_chart_layout = QVBoxLayout(self)
        self.trend_chart_layout.setSpacing(0)
        self.trend_chart_layout.setContentsMargins(0, 0, 0, 0)

        # 动态折线图卡片
        self.chart_card = CardWidget(self)
        self.chart_layout = QVBoxLayout(self.chart_card)
        self.chart_layout.setContentsMargins(12, 12, 12, 12)
        self.chart_layout.setSpacing(8)

        # 顶部水平布局（用于放置"趋势"标签）
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(10)

        self.left_label = QLabel("HR")
        self.left_label.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 24px; font-weight: normal; color: #333;"
        )
        self.left_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        self.device_label = QLabel("未连接设备")
        self.device_label.setStyleSheet(
            "font-family: '微软雅黑'; font-size: 16px; font-weight: normal; color: #333;"
        )
        self.device_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        self.top_layout.addWidget(self.left_label)
        self.top_layout.addStretch()
        self.top_layout.addWidget(self.device_label)
        self.chart_layout.addLayout(self.top_layout)

        # 第二行水平布局（用于放置"心率"和"当前范围"）
        self.second_row_layout = QHBoxLayout()
        self.second_row_layout.setSpacing(10)

        self.top_label = QLabel("心率")
        self.top_label.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);"
        )
        self.top_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.top_right_label = QLabel("当前范围")
        self.top_right_label.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);"
        )
        self.top_right_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.second_row_layout.addWidget(self.top_label)
        self.second_row_layout.addStretch()
        self.second_row_layout.addWidget(self.top_right_label)

        self.chart_layout.addLayout(self.second_row_layout)

        # matplotlib 画布
        self.fig = Figure()
        self.fig.patch.set_facecolor('none')
        self.fig.subplots_adjust(left=0.01, bottom=0.01, right=0.99, top=0.99)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFixedHeight(180)
        self.chart_layout.addWidget(self.canvas)

        # 底部水平布局
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setSpacing(10)

        self.bottom_left_label = QLabel("0")
        self.bottom_left_label.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);"
        )

        self.bottom_right_label = QLabel("当前")
        self.bottom_right_label.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);"
        )

        self.bottom_layout.addWidget(self.bottom_left_label)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.bottom_right_label)

        self.chart_layout.addLayout(self.bottom_layout)

        self.trend_chart_layout.addWidget(self.chart_card)

        # 初始化空白图表
        self._refresh_chart()

    def _style_axes(self):
        """移除坐标轴刻度，使用浅灰色外框"""
        for spine in self.ax.spines.values():
            spine.set_visible(True)
            spine.set_color('#E0E0E0')
            spine.set_linewidth(1)
        self.ax.tick_params(axis='both', which='both', length=0)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

    def _refresh_chart(self):
        """清空 axes 并完全重绘图表"""
        self.ax.clear()
        self.ax.set_facecolor('none')

        data = list(self.data)
        n = len(data)

        if n == 0:
            self._style_axes()
            self.canvas.draw()
            return

        x = list(range(n))

        # 绘制红色折线
        self.ax.plot(x, data, color='#DC0909', linewidth=1.5)

        # 绘制半透明红色填充区域（曲线到 Y=0）
        self.ax.fill_between(x, data, 0, color='#FF8F8F', alpha=0.15)

        # 如果数据点 >= 5：计算平均值、绘制蓝色虚线、标注文字
        if n >= 5:
            avg = sum(data) / n
            self.ax.axhline(y=avg, color='#003C87', linewidth=1, linestyle='--')
            self.ax.text(
                n - 1, avg, f"平均 {round(avg)}",
                fontsize=9, color='#003C87',
                horizontalalignment='right',
                verticalalignment='bottom',
                fontproperties=FONT_CN
            )
        else:
            avg = sum(data) / n if n > 0 else 0

        # Y 轴自动缩放
        actual_max = max(data)
        avg_val = avg if n >= 5 else (sum(data) / n if n > 0 else 0)
        max_y = max(actual_max * 1.15, avg_val * 1.618, 30)
        max_y = round(max_y / 10) * 10  # 四舍五入到最近的 10
        max_y = min(max_y, 250)          # 上限 250
        self.ax.set_ylim(0, max_y)

        # X 轴自适应
        self.ax.set_xlim(0, n - 1 if n > 1 else 1)

        self._style_axes()
        self.canvas.draw()

    def update_heart_rate(self, heart_rate):
        """添加心率数据点并刷新图表"""
        self.data.append(heart_rate)
        self._refresh_chart()
        # 更新右上角标签显示当前 Y 轴最大值
        self.top_right_label.setText(f"{int(self.ax.get_ylim()[1])}")

    def set_device_name(self, name):
        """设置右上角设备名称"""
        self.device_label.setText(name)

    def clear_data(self):
        """清空所有历史数据并刷新空白图表"""
        count = len(self.data)
        self.data.clear()
        self._refresh_chart()
        self.top_right_label.setText("当前范围")
        print(f"[ChartData] 已清空历史数据 ({count} 条)")
