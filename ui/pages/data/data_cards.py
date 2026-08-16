from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import SimpleCardWidget, IndeterminateProgressBar, IndeterminateProgressRing
from ui.pages.data.hr_chart_widget import HeartRateChart


class DataTabPage(QWidget):
    """数据标签页模板——每个标签页共用相同的布局结构

    布局:
        大卡片 → 内含 HeartRateChart + 居中不确定进度条覆盖层
        三张小卡片 1:1:1 → 每张独立覆盖层（进度环 + 加载文字）
        两张小卡片 1:1 → 每张独立覆盖层（进度环 + 加载文字）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._small_overlays = {}  # card → overlay widget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 第一行：大卡片（内嵌心率趋势图）
        self.dataChartCard = SimpleCardWidget(self)
        self.dataChartCardLayout = QVBoxLayout(self.dataChartCard)
        self.dataChartCardLayout.setContentsMargins(10, 8, 10, 8)
        self.chart = HeartRateChart(self.dataChartCard)
        self.dataChartCardLayout.addWidget(self.chart)
        self.dataChartCard.setFixedHeight(300)
        layout.addWidget(self.dataChartCard)

        # === 大卡片覆盖层：居中不确定进度条 + 加载文字 ===
        self._big_overlay = QWidget(self.dataChartCard)
        self._big_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._big_overlay.setStyleSheet("background: transparent;")
        overlay_layout = QVBoxLayout(self._big_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setSpacing(8)
        self._big_progress = IndeterminateProgressBar(self._big_overlay)
        self._big_progress.setFixedWidth(200)
        overlay_layout.addWidget(self._big_progress)
        self._big_label = QLabel("加载中……", self._big_overlay)
        self._big_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self._big_label)
        self._big_overlay.setGeometry(self.dataChartCard.rect())
        self.dataChartCard.installEventFilter(self)

        # 第二行：三张小卡片 1:1:1
        threeLayout = QHBoxLayout()
        threeLayout.setContentsMargins(0, 0, 0, 0)
        threeLayout.setSpacing(16)

        self.avgHrCard = SimpleCardWidget(self)
        self.midCard = SimpleCardWidget(self)
        self.rightCard = SimpleCardWidget(self)

        for card in [self.avgHrCard, self.midCard, self.rightCard]:
            card.setFixedHeight(300)
            self._small_overlays[card] = self._create_small_overlay(card)

        # avgHrCard 左上角放 "平均心率" label（安排了内容 → 隐藏其覆盖层）
        avg_layout = QVBoxLayout(self.avgHrCard)
        avg_layout.setContentsMargins(12, 8, 12, 8)
        self.avg_hr_label = QLabel("平均心率", self.avgHrCard)
        self.avg_hr_label.setStyleSheet(
            "font-size: 13px; color: #334155; font-weight: 600;"
        )
        avg_layout.addWidget(self.avg_hr_label, 0, Qt.AlignCenter)
        avg_layout.addStretch(1)
        self.hide_small_loading(self.avgHrCard)

        threeLayout.addWidget(self.avgHrCard, 1)
        threeLayout.addWidget(self.midCard, 1)
        threeLayout.addWidget(self.rightCard, 1)

        layout.addLayout(threeLayout)

        # 第三行：两张小卡片 1:1
        twoLayout = QHBoxLayout()
        twoLayout.setContentsMargins(0, 0, 0, 0)
        twoLayout.setSpacing(16)

        self.bottomLeftCard = SimpleCardWidget(self)
        self.bottomRightCard = SimpleCardWidget(self)

        for card in [self.bottomLeftCard, self.bottomRightCard]:
            card.setFixedHeight(300)
            self._small_overlays[card] = self._create_small_overlay(card)

        twoLayout.addWidget(self.bottomLeftCard, 1)
        twoLayout.addWidget(self.bottomRightCard, 1)

        layout.addLayout(twoLayout)

        # 底部弹性空间
        layout.addStretch(1)

    def _create_small_overlay(self, card):
        """为小卡片创建覆盖层（进度环 + 加载文字），用法同大卡片遮罩"""
        overlay = QWidget(card)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        overlay.setStyleSheet("background: transparent;")
        ol_layout = QVBoxLayout(overlay)
        ol_layout.setAlignment(Qt.AlignCenter)
        ol_layout.setSpacing(8)
        ring = IndeterminateProgressRing(overlay)
        ring.setFixedSize(60, 60)
        ol_layout.addWidget(ring)
        label = QLabel("加载中……", overlay)
        label.setAlignment(Qt.AlignCenter)
        ol_layout.addWidget(label)
        overlay.setGeometry(card.rect())
        card.installEventFilter(self)
        return overlay

    def hide_loading(self):
        """隐藏大卡片覆盖层（图表加载完成后调用）"""
        self._big_overlay.hide()

    def hide_small_loading(self, card):
        """隐藏指定小卡片的覆盖层（内容就绪后调用）"""
        if card in self._small_overlays:
            self._small_overlays[card].hide()

    def eventFilter(self, obj, event):
        if obj is self.dataChartCard and event.type() == QEvent.Type.Resize:
            self._big_overlay.setGeometry(self.dataChartCard.rect())
        elif obj in self._small_overlays and event.type() == QEvent.Type.Resize:
            self._small_overlays[obj].setGeometry(obj.rect())
        return super().eventFilter(obj, event)

    def set_big_card_height(self, height: int):
        """设置大卡片的固定高度"""
        self.dataChartCard.setFixedHeight(height)

    def set_small_card_height(self, height: int):
        """设置所有小卡片的固定高度"""
        for card in [self.avgHrCard, self.midCard, self.rightCard,
                     self.bottomLeftCard, self.bottomRightCard]:
            card.setFixedHeight(height)
