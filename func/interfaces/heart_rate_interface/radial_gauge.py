from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygon, QLinearGradient, QPainterPath
from PyQt5.QtWidgets import QWidget
import math


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
    
    @property
    def current_value(self):
        return self._current_value
    
    @current_value.setter
    def current_value(self, value):
        self._current_value = value
    
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