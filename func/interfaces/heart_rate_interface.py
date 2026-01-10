from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPixmap
from collections import deque
from qfluentwidgets import (CardWidget, TitleLabel, BodyLabel, SubtitleLabel,PushButton)


class DynamicLineChart(QWidget):
    """动态折线图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 常量定义
        self.GRID_SPACE = 10  # 网格间隔
        self.MOVE_STEP = 1    # 移动步长（能够被间隔整除）
        self.MAX_Y = 200      # Y轴最大值（心率最大刻度）
        self.MIN_Y = 0        # Y轴最小值
        
        # 变量初始化
        self.grid_xp_arr = []  # 网格竖线X坐标数组
        self.point_lst = []     # 点坐标数组
        self.point_values = []  # 每个点对应的原始值（用于等比例缩放）
        self.yp_queue = deque() # 数值队列
        self.x_offset = 0       # 网格偏移量
        self.current_value = 0  # 当前数值
        
        # 自动调节Y轴范围的变量
        self.value_history = deque(maxlen=40)  # 存储最近40个值用于计算范围
        self.auto_adjust_enabled = True        # 是否启用自动调节
        self.min_range = 30                     # 最小范围，确保变化明显
        self.padding_ratio = 0.10               # 上余量比例
        
        # 原始数值历史记录（保存所有点的原始值，用于等比例缩放）
        self.raw_values = deque(maxlen=100)     # 存储最近100个原始值
        
        # 平滑过渡变量
        self.target_max_y = 200                 # 目标MAX_Y
        self.smoothing_factor = 0.15            # 平滑因子（0-1，越小越平滑）
        self.update_counter = 0                 # 更新计数器
        self.update_threshold = 3               # 更新阈值（避免频繁更新）
        
        # 初始化Y轴范围
        self.MIN_Y = 0
        self.MAX_Y = 200
        
        # 设置最小高度
        self.setMinimumHeight(180)
        
        # 初始化数据
        self._init_data()
        
        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.draw_chart)
        self.timer.start(500)  # 500ms 刷新一次，约 2fps
    
    def _init_data(self):
        """初始化数据结构"""
        # 初始化坐标点个数为宽/步长+1
        point_count = self.width() // self.MOVE_STEP + 1
        self.point_lst = []
        self.point_values = []
        
        # 初始化坐标点为X轴基线位置
        for i in range(point_count):
            point = QPoint(i * self.MOVE_STEP, self.height())
            self.point_lst.append(point)
            self.point_values.append(0)  # 初始值为0
    
    def add_value(self, value):
        """添加新的数值到队列"""
        self.yp_queue.append(value)
        # 添加到历史记录用于自动调节Y轴范围
        self.value_history.append(value)
        # 保存原始值用于等比例缩放
        self.raw_values.append(value)
        # 更新Y轴范围
        self._update_y_range()
    
    def _update_y_range(self):
        """根据历史数据自动更新Y轴范围（MIN_Y固定为0，只调整MAX_Y）"""
        if not self.auto_adjust_enabled or len(self.value_history) < 5:
            self.target_max_y = 200
            return
        
        # 计算历史数据的最大值
        max_val = max(self.value_history)
        
        # 计算上余量
        padding = max_val * self.padding_ratio
        self.target_max_y = max_val + padding
        
        # 边界检查：确保范围在合理范围内
        self._check_range_bounds()
        
        # 四舍五入到最近的10（如144->150）
        self.target_max_y = round(self.target_max_y / 10) * 10
        
        # 最终边界检查
        self._check_range_bounds()
        
        # 平滑过渡：逐步更新MAX_Y
        self._smooth_range_update()
        
        # 如果MAX_Y发生了显著变化，重新计算所有点的Y坐标
        if abs(self.MAX_Y - self.target_max_y) > 5:
            self._recalculate_all_points()
    
    def _smooth_range_update(self):
        """平滑更新Y轴范围，避免频繁缩放导致的闪烁"""
        # 计算差值
        diff_max = self.target_max_y - self.MAX_Y
        
        # 如果差值很小，直接更新
        if abs(diff_max) < 0.5:
            self.MAX_Y = self.target_max_y
            return
        
        # 使用平滑因子逐步更新
        self.MAX_Y += diff_max * self.smoothing_factor
    
    def _check_range_bounds(self):
        """边界检查机制，防止极端缩放比例"""
        # 确保MIN_Y固定为0
        self.MIN_Y = 0
        
        # 确保MAX_Y至少为min_range
        if self.MAX_Y < self.min_range:
            self.MAX_Y = self.min_range
        
        if self.target_max_y < self.min_range:
            self.target_max_y = self.min_range
        
        # 确保MAX_Y不超过生理极限（心率一般不超过250）
        max_limit = 250
        if self.MAX_Y > max_limit:
            self.MAX_Y = max_limit
        
        if self.target_max_y > max_limit:
            self.target_max_y = max_limit
    
    def _normalize_value_to_y(self, value):
        """将数值归一化并转换为Y坐标（等比例缩放，MIN_Y固定为0）"""
        range_y = self.MAX_Y - self.MIN_Y
        
        # 边界检查：防止除零错误
        if range_y <= 0:
            range_y = self.min_range
        
        # 归一化到0-1范围
        normalized_value = (value - self.MIN_Y) / range_y
        
        # 限制在0-1范围内（防止超出边界）
        normalized_value = max(0.0, min(1.0, normalized_value))
        
        # 转换为Y坐标（垂直方向等比例）
        y_pos = self.height() - int(normalized_value * self.height())
        
        # 边界检查：确保Y坐标在可视区域内
        y_pos = max(0, min(self.height(), y_pos))
        
        return y_pos
    
    def _recalculate_all_points(self):
        """重新计算所有点的Y坐标（当MAX_Y变化时调用）"""
        if len(self.point_values) == 0:
            return
        
        # 使用point_values中保存的原始值重新计算所有点的Y坐标
        for i in range(len(self.point_values)):
            y_pos = self._normalize_value_to_y(self.point_values[i])
            self.point_lst[i].setY(y_pos)
    
    def draw_chart(self):
        """绘制折线图（优化版本，确保流畅性）"""
        # 偏移量计算
        self.x_offset += 1
        if self.x_offset == self.GRID_SPACE // self.MOVE_STEP:
            self.x_offset = 0
        
        # 如果队列中有新的Y坐标点，则输出
        if len(self.yp_queue) > 0:
            self.current_value = self.yp_queue.popleft()
        
        # 每执行一次函数，Y坐标向前移动一位
        for i in range(len(self.point_lst) - 1):
            self.point_lst[i].setY(self.point_lst[i + 1].y())
            # 同步更新point_values
            self.point_values[i] = self.point_values[i + 1]
        
        # 按比例更新最后一位坐标点
        if len(self.point_lst) > 0:
            last_index = len(self.point_lst) - 1
            self.point_lst[last_index].setX(self.width())
            
            # 使用优化的归一化方法计算Y坐标
            y_pos = self._normalize_value_to_y(self.current_value)
            self.point_lst[last_index].setY(y_pos)
            # 保存当前值到point_values
            self.point_values[last_index] = self.current_value
        
        # 触发重绘
        self.update()
    
    def paintEvent(self, event):
        """绘制事件（双缓冲绘图）"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取画布尺寸
        width = self.width()
        height = self.height()
        
        # 设置裁剪区域，限制在卡片范围内
        painter.setClipRect(0, 0, width, height)
        
        # 绘制浅红色背景
        painter.fillRect(0, 0, width, height, QColor(255, 255, 255))
        
        # 绘制网格
        self._draw_grid(painter, width, height)
        
        # 绘制折线
        self._draw_line(painter, width, height)
        
        # 绘制1px黑色边框
        border_pen = QPen(QColor(0, 0, 0))
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, width - 1, height - 1)
    
    def _draw_grid(self, painter, width, height):
        """绘制网格背景"""
        # 设置网格线颜色（深红色）
        pen = QPen(QColor(220, 220, 220))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # 初始化网格竖线X坐标数组
        self.grid_xp_arr = []
        
        # 计算竖线数量，确保覆盖整个宽度
        import math
        grid_count = math.ceil(width / self.GRID_SPACE) + 1
        
        # 画竖线（根据偏移量实现动态效果）
        for i in range(grid_count):
            x_pos = self.GRID_SPACE * i - self.x_offset * self.MOVE_STEP
            self.grid_xp_arr.append(x_pos)
            painter.drawLine(int(x_pos), 0, int(x_pos), height)
        
        # 画横线
        for i in range(height // self.GRID_SPACE + 1):
            y_pos = self.GRID_SPACE * i
            painter.drawLine(0, y_pos, width, y_pos)
    
    def _draw_line(self, painter, width, height):
        """绘制折线和填充区域"""
        if len(self.point_lst) < 2:
            return
        
        # 先绘制填充区域（半透明红色）
        from PyQt5.QtGui import QBrush, QPainterPath
        
        # 创建填充路径
        fill_path = QPainterPath()
        fill_path.moveTo(self.point_lst[0])
        
        # 添加所有折线点
        for i in range(1, len(self.point_lst)):
            fill_path.lineTo(self.point_lst[i])
        
        # 闭合路径到底部
        fill_path.lineTo(width, height)
        fill_path.lineTo(0, height)
        fill_path.closeSubpath()
        
        # 设置填充颜色（半透明红色）
        fill_brush = QBrush(QColor(255,143,143,50))  # 50表示透明度
        painter.setBrush(fill_brush)
        painter.setPen(Qt.NoPen)  # 不绘制边框
        painter.drawPath(fill_path)
        
        # 设置折线颜色（深红色）
        pen = QPen(QColor(220, 9, 9))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # 画笔移动到起点位置
        start_point = self.point_lst[0]
        # 连线各个点
        for i in range(len(self.point_lst) - 1):
            p1 = self.point_lst[i]
            p2 = self.point_lst[i + 1]
            painter.drawLine(p1, p2)

    def resizeEvent(self, event):
        """窗口大小改变时重新初始化数据"""
        super().resizeEvent(event)
        self._init_data()


class HeartRateInterface(QWidget):
    """心率界面 - 集成动态折线图"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("heart_rate_interface")
        self.parent = parent
        self.setup_ui()
        self.current_device_name = None  # 存储当前连接的设备名称
    
    def setup_ui(self):
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 动态折线图卡片
        self.chart_card = CardWidget(self)
        self.chart_layout = QVBoxLayout(self.chart_card)
        self.chart_layout.setContentsMargins(20, 20, 20, 20)
        self.chart_layout.setSpacing(10)
        
        # 创建顶部水平布局（用于放置两个文本标签）
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(10)
        
        # 左侧文本标签
        from PyQt5.QtWidgets import QLabel
        self.left_label = QLabel("HR")
        self.left_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 28px; font-weight: normal; color: #333;")
        self.left_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        
        # 右上角设备名称标签
        self.right_label = QLabel("请先连接设备")
        self.right_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 18px; font-weight: normal; color: #333;")
        self.right_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        
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
        self.top_label.setAlignment(Qt.AlignLeft)
        
        # 右侧文本标签："当前范围"
        self.top_right_label = QLabel("当前范围")
        self.top_right_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);")
        self.top_right_label.setAlignment(Qt.AlignRight)
        
        # 添加弹性空间，让文本标签分别靠在两侧
        self.second_row_layout.addWidget(self.top_label)
        self.second_row_layout.addStretch()
        self.second_row_layout.addWidget(self.top_right_label)
        
        # 将第二行布局添加到卡片布局
        self.chart_layout.addLayout(self.second_row_layout)
        
        # 创建动态折线图
        self.chart = DynamicLineChart()
        self.chart_layout.addWidget(self.chart)
        
        # 将卡片添加到主布局
        self.main_layout.addWidget(self.chart_card)
        
        # 创建底部水平布局（用于放置"37.5秒"和"0"）- 移到卡片内部
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setSpacing(10)
        
        # 左下角文本标签："37.5秒"
        self.bottom_left_label = QLabel("37.5秒")
        self.bottom_left_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);")
        
        # 右下角文本标签："当前范围"
        self.bottom_right_label = QLabel("当前范围")
        self.bottom_right_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: rgb(100, 100, 100);")
        
        # 添加弹性空间，让文本标签分别靠在两侧
        self.bottom_layout.addWidget(self.bottom_left_label)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.bottom_right_label)
        
        # 将底部布局添加到卡片布局（而不是主布局）
        self.chart_layout.addLayout(self.bottom_layout)
        
        # 添加弹性空间，让卡片居中
        self.main_layout.addStretch()
    
    def update_heart_rate(self, heart_rate):
        """更新心率数值"""
        # 添加到折线图，包括0值
        self.chart.add_value(heart_rate)
        # 更新HR显示（HR后面空两格显示数字）
        self.left_label.setText(f"HR  {heart_rate}")
        # 更新右上角显示MAX_Y值
        self.top_right_label.setText(f"{int(self.chart.MAX_Y)}")
        # 右下角始终显示0
        self.bottom_right_label.setText("0")

    def update_status(self, status):
        """更新状态信息"""
        if "设备连接成功" in status:
            # 从父窗口获取当前连接的设备名称
            if self.parent and hasattr(self.parent, 'core') and self.parent.core.selected_device:
                device_name = self.parent.core.selected_device.name
                if device_name:
                    self.current_device_name = device_name
                    self.right_label.setText(device_name)
                else:
                    self.right_label.setText("未知设备")
            else:
                self.right_label.setText("未知设备")
        elif "已断开连接" in status or "请先连接设备" in status:
            self.current_device_name = None
            self.right_label.setText("请先连接设备")
