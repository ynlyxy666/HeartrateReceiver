import matplotlib
matplotlib.use('QtAgg')
from collections import deque
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import CardWidget

# 字体设置：使用系统字体名称，避免硬编码路径
FONT_CN = FontProperties(family='Microsoft YaHei', size=9)


class LineChartPage(QWidget):
    """折线图页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = deque(maxlen=100)
        self.setup_ui()

    def setup_ui(self):
        # 主布局
        self.line_chart_layout = QVBoxLayout(self)
        self.line_chart_layout.setSpacing(0)
        self.line_chart_layout.setContentsMargins(0, 0, 0, 0)

        # 动态折线图卡片（与其他卡片等高）
        self.chart_card = CardWidget(self)
        self.chart_layout = QVBoxLayout(self.chart_card)
        self.chart_layout.setContentsMargins(12, 12, 12, 12)
        self.chart_layout.setSpacing(8)

        # 创建顶部水平布局（用于放置两个文本标签）
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(10)

        # 左侧文本标签
        self.left_label = QLabel("HR")
        self.left_label.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 24px; font-weight: normal; color: #333;"
        )
        self.left_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        # 右上角设备名称标签
        self.right_label = QLabel("请先连接设备")
        self.right_label.setStyleSheet(
            "font-family: 'Segoe UI'; font-size: 16px; font-weight: normal; color: #333;"
        )
        self.right_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        # 添加弹性空间，让文本标签分别靠在两侧
        self.top_layout.addWidget(self.left_label)
        self.top_layout.addStretch()
        self.top_layout.addWidget(self.right_label)

        # 将顶部布局添加到卡片布局
        self.chart_layout.addLayout(self.top_layout)

        # 创建第二行水平布局（用于放置"心率"和"当前范围"）
        self.second_row_layout = QHBoxLayout()
        self.second_row_layout.setSpacing(10)

        # 左侧文本标签："心率"
        self.top_label = QLabel("心率")
        self.top_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);")
        self.top_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # 右侧文本标签："当前范围"
        self.top_right_label = QLabel("当前范围")
        self.top_right_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);")
        self.top_right_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # 添加弹性空间，让文本标签分别靠在两侧
        self.second_row_layout.addWidget(self.top_label)
        self.second_row_layout.addStretch()
        self.second_row_layout.addWidget(self.top_right_label)

        # 将第二行布局添加到卡片布局
        self.chart_layout.addLayout(self.second_row_layout)

        # 创建 matplotlib 画布
        self.fig = Figure()
        self.fig.patch.set_facecolor('none')
        self.fig.subplots_adjust(left=0.01, bottom=0.01, right=0.99, top=0.99)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFixedHeight(180)
        self.chart_layout.addWidget(self.canvas)

        # 创建底部水平布局
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setSpacing(10)

        # 左下角文本标签："37.5秒前"
        self.bottom_left_label = QLabel("37.5秒前")
        self.bottom_left_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);")

        # 右下角文本标签："0"
        self.bottom_right_label = QLabel("0")
        self.bottom_right_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);")

        # 添加弹性空间，让文本标签分别靠在两侧
        self.bottom_layout.addWidget(self.bottom_left_label)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.bottom_right_label)

        # 将底部布局添加到卡片布局
        self.chart_layout.addLayout(self.bottom_layout)

        # 将卡片添加到折线图页面
        self.line_chart_layout.addWidget(self.chart_card)

        # 初始绘制空图表
        self._refresh_chart()

    def _refresh_chart(self):
        """重绘 matplotlib 图表"""
        self.ax.clear()

        data = list(self.data)
        avg = 0

        if data:
            x = list(range(len(data)))

            # 绘制红色折线
            self.ax.plot(x, data, color='#DC0909', linewidth=1.5, zorder=3)

            # 绘制半透明红色填充区域（从曲线到Y=0）
            self.ax.fill_between(x, data, 0, color='#FF8F8F', alpha=0.15, zorder=2)

            # 如果数据点 >= 5 个：计算平均值，绘制蓝色虚线
            if len(data) >= 5:
                avg = sum(data) / len(data)
                self.ax.axhline(y=avg, color='#003C87', linewidth=1, linestyle='--', zorder=4)
                self.ax.annotate(
                    f'平均 {avg:.1f}',
                    xy=(x[-1], avg),
                    xytext=(0, 0),
                    textcoords='offset points',
                    fontsize=9,
                    color='#003C87',
                    ha='right',
                    va='bottom',
                    fontproperties=FONT_CN
                )

            # Y轴自动缩放
            actual_max = max(data)
            avg_for_scale = avg if len(data) >= 5 else 0
            max_y = max(actual_max * 1.15, avg_for_scale * 1.618, 30)
            max_y = min(round(max_y / 10) * 10, 250)
        else:
            max_y = 200

        # 设置坐标轴范围
        self.ax.set_xlim(0, 99)
        self.ax.set_ylim(0, max_y)

        # 样式：浅灰色外框
        for spine in self.ax.spines.values():
            spine.set_visible(True)
            spine.set_color('#E0E0E0')
            spine.set_linewidth(1)

        # 移除坐标轴刻度
        self.ax.tick_params(
            which='both',
            bottom=False,
            top=False,
            left=False,
            right=False,
            labelbottom=False,
            labelleft=False
        )

        # 透明背景
        self.ax.set_facecolor('none')
        self.fig.patch.set_facecolor('none')

        self.canvas.draw()

    def add_value(self, heart_rate):
        """添加数据点并刷新图表"""
        self.data.append(heart_rate)
        self._refresh_chart()

        # 更新 top_right_label 显示当前范围（最大Y值）
        data = list(self.data)
        if data:
            actual_max = max(data)
            avg = sum(data) / len(data) if len(data) >= 5 else 0
            max_y = max(actual_max * 1.15, avg * 1.618, 30)
            max_y = min(round(max_y / 10) * 10, 250)
            self.top_right_label.setText(str(int(max_y)))

        # 更新 bottom_right_label 显示最新心率值
        self.bottom_right_label.setText(str(heart_rate))

    def set_receiving_state(self, is_receiving):
        """空方法，保留兼容性"""
        pass
