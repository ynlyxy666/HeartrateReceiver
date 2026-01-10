from PyQt5.QtCore import Qt, QTimer, QPoint, QEasingCurve, QPropertyAnimation, pyqtProperty
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPixmap, QBrush, QPolygon, QLinearGradient, QRadialGradient
from collections import deque
from qfluentwidgets import (CardWidget, TitleLabel, BodyLabel, SubtitleLabel,PushButton)
import math


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
        
        # 平均心率相关变量
        self.average_heart_rate = 0             # 当前平均心率
        self.average_data_points = deque(maxlen=100)  # 用于计算平均值的数据点
        self.MIN_POINTS_FOR_AVERAGE = 5         # 计算平均值所需的最小点数
        
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
        # 添加到平均心率计算队列
        self.average_data_points.append(value)
        # 更新Y轴范围
        self._update_y_range()
        # 计算平均心率
        self._calculate_average_heart_rate()
    
    def _calculate_average_heart_rate(self):
        """计算平均心率，从5个点开始计算"""
        if len(self.average_data_points) < self.MIN_POINTS_FOR_AVERAGE:
            self.average_heart_rate = 0
            return
        
        # 计算平均值
        self.average_heart_rate = sum(self.average_data_points) / len(self.average_data_points)
    
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
        
        # 绘制平均心率线
        self._draw_average_line(painter, width, height)
        
        # 绘制1px黑色边框
        border_pen = QPen(QColor(0, 0, 0))
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, width - 1, height - 1)
    
    def _draw_average_line(self, painter, width, height):
        """绘制平均心率线，1px深蓝色横线，并在右端显示数值"""
        if self.average_heart_rate == 0:
            return
        
        # 计算平均线的Y坐标
        average_y = self._normalize_value_to_y(self.average_heart_rate)
        
        # 深蓝色
        deep_blue = QColor(0, 60, 135)
        
        # 设置深蓝色1px线
        average_pen = QPen(deep_blue)
        average_pen.setWidth(1)
        painter.setPen(average_pen)
        
        # 绘制横线
        painter.drawLine(0, average_y, width, average_y)
        
        # 绘制平均心率数值（线的上方，右对齐）
        painter.setPen(deep_blue)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        
        # 格式化平均心率数值（添加前缀"平均 "，四舍五入为整数）
        avg_text = f"平均 {round(self.average_heart_rate)}"
        
        # 获取文本宽度
        text_rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignRight, avg_text)
        text_width = text_rect.width()
        
        # 计算文本位置：线的上方，右边缘与线的右边缘平齐
        text_x = width - text_width - 5  # 右对齐，距离边缘5px
        text_y = average_y - 5  # 线的上方，距离线5px
        
        painter.drawText(text_x, text_y, avg_text)
    
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


class RadialGauge(QWidget):
    """Fluent风格径向仪表盘组件"""
    
    def __init__(self, parent=None, min_value=0, max_value=200):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self._current_value = 0
        self._animated_value = 0
        self.average_value = 0  # 平均心率值
        # 放大图形：从240x240放大到280x280
        self.setFixedSize(280, 280)
        
        # 创建动画
        self.animation = QPropertyAnimation(self, b"animated_value")
        self.animation.setDuration(500)  # 动画持续时间
        self.animation.setEasingCurve(QEasingCurve.OutCubic)  # 缓动曲线
    
    @pyqtProperty(float)
    def animated_value(self):
        return self._animated_value
    
    @animated_value.setter
    def animated_value(self, value):
        self._animated_value = value
        self.update()
    
    def set_value(self, value):
        """设置当前值（带动画）"""
        self.current_value = max(self.min_value, min(self.max_value, value))
        
        # 启动动画
        self.animation.stop()
        self.animation.setStartValue(self._animated_value)
        self.animation.setEndValue(self.current_value)
        self.animation.start()
    
    def set_average_value(self, value):
        """设置平均心率值"""
        self.average_value = max(self.min_value, min(self.max_value, value))
        self.update()
    
    def paintEvent(self, event):
        """绘制Fluent风格仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.HighQualityAntialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 30
        
        # 绘制背景圆环（正半圆）
        background_pen = QPen(QColor(230, 230, 230))
        # 等比例缩小线宽：从24缩小到18
        background_pen.setWidth(18)
        background_pen.setCapStyle(Qt.RoundCap)  # 圆角笔触
        painter.setPen(background_pen)
        
        # 正半圆设置：宽度=高度，居中显示
        diameter = min(self.width(), self.height()) - 60
        x = (self.width() - diameter) // 2
        y = (self.height() - diameter) // 2 + 30  # 向下偏移30px，使半圆居中
        
        # 绘制正半圆：从180度到0度（逆时针）
        painter.drawArc(x, y, diameter, diameter, 180 * 16, -180 * 16)
        
        # 计算当前值对应的角度（正半圆）
        angle_range = 180  # 180度（从左到右）
        value_range = self.max_value - self.min_value
        # 从180度开始，逆时针绘制（负角度）
        angle = -int((self._animated_value / value_range) * angle_range * 16)
        
        # 创建渐变进度颜色（从蓝到红，对应0-200值）
        gradient = QLinearGradient(x, y, x + diameter, y)  # 水平渐变
        gradient.setColorAt(0.0, QColor(0, 180, 255))  # 0值为蓝色
        gradient.setColorAt(0.5, QColor(255, 255, 0))  # 100值为黄色
        gradient.setColorAt(1.0, QColor(255, 80, 80))   # 200值为红色
        
        # 绘制进度圆环（正半圆）
        # 等比例缩小线宽：从24缩小到18
        progress_pen = QPen(gradient, 18, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(progress_pen)
        painter.drawArc(x, y, diameter, diameter, 180 * 16, angle)
        
        # 绘制当前值（Fluent风格字体）
        painter.setPen(QColor(32, 32, 32))
        # 等比例缩小字体：从40缩小到30
        font = QFont("Segoe UI", 30, QFont.Bold)
        painter.setFont(font)
        
        # 绘制当前值并计算其位置
        value_text = str(int(self._animated_value))
        # 计算文本尺寸
        text_rect = painter.boundingRect(0, 0, self.width(), self.height(), Qt.AlignCenter, value_text)
        painter.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, value_text)
        
        # 绘制单位（Fluent风格的灰色），移到数字下边缘处
        # 等比例缩小字体：从18缩小到14
        font = QFont("Segoe UI", 14, QFont.Medium)
        painter.setFont(font)
        painter.setPen(QColor(100, 100, 100))
        
        # 计算BPM位置：数字下边缘处
        # text_rect.bottom() 是数字的下边缘位置
        bpm_y = text_rect.bottom()
        painter.drawText(0, bpm_y - 5, self.width(), 20, Qt.AlignCenter, "BPM")
        
        # 绘制透明半圆导轨（用于计算箭头位置）
        
        # 计算圆心和半径（与实际绘制的半圆完全一致）
        arc_center_x = center_x
        arc_center_y = center_y + 30  # 与arc绘制的y偏移一致
        
        # 绘制平均心率指示箭头
        if self.average_value > 0:
            # 创建外侧同心圆导轨（半径更大）
            outer_radius = radius + 20  # 外侧同心圆半径，比半圆大20px
            
            # 绘制外侧同心圆路径
            from PyQt5.QtGui import QPainterPath
            outer_path = QPainterPath()
            outer_path.moveTo(arc_center_x - outer_radius, arc_center_y)
            outer_path.arcTo(
                arc_center_x - outer_radius, arc_center_y - outer_radius, 
                outer_radius * 2, outer_radius * 2, 
                180, -180  # 从180度开始，逆时针绘制180度
            )
            
            # 计算平均心率对应的比例
            value_ratio = self.average_value / (self.max_value - self.min_value)
            
            # 获取箭头根部位置（外侧同心圆上）
            root_point = outer_path.pointAtPercent(value_ratio)
            root_x = int(root_point.x())
            root_y = int(root_point.y())
            
            # 计算箭头尖端位置（同样在外侧同心圆上，向前延伸）
            # 计算前进方向
            delta = 0.02  # 箭头长度对应的路径比例
            if value_ratio < 1.0 - delta:
                # 正常情况下，箭头尖端在外侧同心圆上向前延伸
                tip_point = outer_path.pointAtPercent(value_ratio + delta)
                tip_x = int(tip_point.x())
                tip_y = int(tip_point.y())
            else:
                # 到达终点时，箭头向前延伸
                # 计算切线方向
                prev_point = outer_path.pointAtPercent(value_ratio - delta)
                curr_point = outer_path.pointAtPercent(value_ratio)
                
                # 切线方向
                tangent_x = curr_point.x() - prev_point.x()
                tangent_y = curr_point.y() - prev_point.y()
                
                # 归一化切线向量
                tangent_length = math.sqrt(tangent_x * tangent_x + tangent_y * tangent_y)
                if tangent_length > 0:
                    tangent_x /= tangent_length
                    tangent_y /= tangent_length
                
                # 计算尖端位置
                tip_x = int(curr_point.x() + tangent_x * 30)
                tip_y = int(curr_point.y() + tangent_y * 30)
            
            # 绘制旋转的小三角（删除箭头线）
            # 确保三角始终可见（修复0和200时消失的问题）
            if root_x > 0 and root_x < self.width() and root_y > 0 and root_y < self.height():
                # 保存当前绘图状态
                painter.save()
                
                # 移动到三角位置
                painter.translate(root_x, root_y)
                
                # 计算旋转角度（指向圆心）
                dx = arc_center_x - root_x
                dy = arc_center_y - root_y
                
                # 避免除零错误
                if dx == 0 and dy == 0:
                    rotation_angle = 0
                else:
                    # 计算从三角位置到圆心的角度
                    rotation_angle = math.atan2(dy, dx) * 180 / math.pi
                
                # 顺时针旋转90°（根据用户要求）
                rotation_angle += 90
                
                # 旋转坐标系
                painter.rotate(rotation_angle)
                
                # 绘制小三角
                triangle_pen = QPen(QColor(255, 100, 100), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                triangle_brush = QBrush(QColor(255, 100, 100))
                painter.setPen(triangle_pen)
                painter.setBrush(triangle_brush)
                
                # 绘制三角形（尖端指向圆心）
                # 等比例缩小三角形大小：从10缩小到7
                triangle_size = 7
                triangle_points = [
                    QPoint(0, -triangle_size),     # 尖端（指向圆心）
                    QPoint(-triangle_size, triangle_size),  # 左底角
                    QPoint(triangle_size, triangle_size)    # 右底角
                ]
                painter.drawPolygon(triangle_points)
                
                # 恢复绘图状态
                painter.restore()


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
        from qfluentwidgets import SegmentedWidget
        
        # 分段控制器
        self.segmented_widget = SegmentedWidget(self)
        self.segmented_widget.addItem("line_chart", "折线图")
        self.segmented_widget.addItem("big_number", "大数字")
        self.segmented_widget.addItem("dashboard", "仪表盘")
        self.segmented_widget.setCurrentItem("line_chart")
        self.segmented_widget.currentItemChanged.connect(self.on_segmented_changed)
        
        # 将分段控制器添加到主布局
        self.main_layout.addWidget(self.segmented_widget)
        
        # 创建三个子页面
        # 1. 折线图页面
        self.line_chart_page = QWidget()
        self.line_chart_layout = QVBoxLayout(self.line_chart_page)
        self.line_chart_layout.setSpacing(0)
        self.line_chart_layout.setContentsMargins(0, 0, 0, 0)
        
        # 动态折线图卡片（与其他卡片等高）
        self.chart_card = CardWidget(self.line_chart_page)
        self.chart_layout = QVBoxLayout(self.chart_card)
        self.chart_layout.setContentsMargins(12, 12, 12, 12)
        self.chart_layout.setSpacing(8)
        
        # 创建顶部水平布局（用于放置两个文本标签）
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(10)
        
        # 左侧文本标签
        from PyQt5.QtWidgets import QLabel
        self.left_label = QLabel("HR")
        self.left_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 24px; font-weight: normal; color: #333;")
        self.left_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        
        # 右上角设备名称标签
        self.right_label = QLabel("请先连接设备")
        self.right_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 16px; font-weight: normal; color: #333;")
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
        self.chart.setFixedHeight(160)  # 与其他卡片显示区域高度一致
        self.chart_layout.addWidget(self.chart)
        
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
        
        # 将卡片添加到折线图页面
        self.line_chart_layout.addWidget(self.chart_card)
        
        # 2. 大数字页面
        self.big_number_page = QWidget()
        self.big_number_layout = QVBoxLayout(self.big_number_page)
        self.big_number_layout.setSpacing(0)
        self.big_number_layout.setContentsMargins(0, 0, 0, 0)
        
        # 大数字卡片（与折线图卡片等高）
        self.big_number_card = CardWidget(self.big_number_page)
        self.big_number_card_layout = QVBoxLayout(self.big_number_card)
        self.big_number_card_layout.setContentsMargins(12, 12, 12, 12)
        self.big_number_card_layout.setSpacing(16)
        
        # 顶部水平布局（用于放置字体切换按钮）
        self.big_number_top_layout = QHBoxLayout()
        self.big_number_top_layout.setSpacing(10)
        
        # 添加弹性空间，将按钮推到右侧
        self.big_number_top_layout.addStretch()
        
        # 字体切换按钮
        from qfluentwidgets import PushButton
        self.font_select_button = PushButton("字")
        self.font_select_button.setFixedSize(32, 32)
        self.font_select_button.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; font-weight: bold;")
        self.font_select_button.clicked.connect(self.select_font)
        
        # 字体列表（使用系统字体）
        self.font_index = 0
        self.fonts = [
            "'Segoe UI'",
            "'Arial'",
            "'Times New Roman'",
            "'Courier New'",
            "'Verdana'",
            "'Georgia'"
        ]
        
        # 固定字号
        self.fixed_font_size = 72
        
        # 将按钮添加到顶部布局
        self.big_number_top_layout.addWidget(self.font_select_button)
        
        # 添加顶部布局到卡片布局
        self.big_number_card_layout.addLayout(self.big_number_top_layout)
        
        # 当前心率标签（最大字体）
        self.current_hr_label = QLabel("0")
        self.current_hr_label.setStyleSheet(f"font-family: {self.fonts[0]}; font-size: {self.fixed_font_size}px; font-weight: bold; color: #333;")
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
        
        # 3. 仪表盘页面
        self.dashboard_page = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_page)
        self.dashboard_layout.setSpacing(0)
        self.dashboard_layout.setContentsMargins(0, 0, 0, 0)
        
        # 仪表盘卡片（与折线图卡片等高）
        self.dashboard_card = CardWidget(self.dashboard_page)
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
        
        # 将三个页面添加到主布局
        self.main_layout.addWidget(self.line_chart_page)
        self.main_layout.addWidget(self.big_number_page)
        self.main_layout.addWidget(self.dashboard_page)
        
        # 初始化只显示第一个页面
        self.big_number_page.hide()
        self.dashboard_page.hide()
    
    def on_segmented_changed(self, current_item):
        """分段控制器切换事件"""
        # 隐藏所有页面
        self.line_chart_page.hide()
        self.big_number_page.hide()
        self.dashboard_page.hide()
        
        # 显示当前选中的页面
        if current_item == "line_chart":
            self.line_chart_page.show()
        elif current_item == "big_number":
            self.big_number_page.show()
        elif current_item == "dashboard":
            self.dashboard_page.show()
    
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
        
        # 更新心率统计
        self.current_heart_rate = heart_rate
        
        # 更新最高心率
        if heart_rate > self.highest_heart_rate:
            self.highest_heart_rate = heart_rate
        
        # 更新最低心率
        if heart_rate < self.lowest_heart_rate and heart_rate > 0:
            self.lowest_heart_rate = heart_rate
        
        # 更新大数字卡片显示
        self.current_hr_label.setText(str(heart_rate))
        
        # 更新平均心率显示
        avg_hr = self.chart.average_heart_rate
        self.average_hr_label.setText(f"平均: {round(avg_hr) if avg_hr > 0 else 0} BPM")
        
        # 更新最高/最低心率显示
        self.minmax_hr_label.setText(f"最高: {self.highest_heart_rate} BPM | 最低: {self.lowest_heart_rate if self.lowest_heart_rate != float('inf') else 0} BPM")
        
        # 更新仪表盘卡片显示
        self.dashboard_gauge.set_value(heart_rate)
        self.dashboard_gauge.set_average_value(round(avg_hr) if avg_hr > 0 else 0)

    def select_font(self):
        """打开字体选择对话框"""
        from PyQt5.QtWidgets import QFontDialog, QColorDialog, QMessageBox
        from PyQt5.QtGui import QFont, QColor
        
        # 获取当前样式
        current_style = self.current_hr_label.styleSheet()
        
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
                new_style = f"font-family: '{font.family()}'; font-size: {self.fixed_font_size}px; font-weight: bold; color: {color.name()};"
                self.current_hr_label.setStyleSheet(new_style)
    
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
