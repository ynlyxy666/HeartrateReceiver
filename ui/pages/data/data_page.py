from datetime import datetime, timedelta

import threading

import numpy as np
import matplotlib
matplotlib.use("qtagg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, QEvent, QTimer, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel
from qfluentwidgets import SegmentedWidget, ScrollArea, ToolButton, FluentIcon
from ui.pages.data.data_cards import DataTabPage


# ── 图表样式常量 ──
CHART_COLOR = "#0EA5E9"
CHART_LINE_WIDTH = 1.8
CHART_FILL_ALPHA = 0.08
TICK_COLOR = "#94A3B8"
GRID_COLOR = "#CBD5E1"
SPINE_COLOR = "#CBD5E1"
LABEL_TEXT_COLOR = "#334155"

MAX_POINTS = 800
MIN_POINTS = 150


# ── 纯业务函数 ──

def _range_label_text(time_filter, now, fmt):
    """生成标签页的理论时间范围文本"""
    if time_filter is None:
        return "数据（全部）"
    start_dt = datetime.fromtimestamp(time_filter)
    return f"数据（{fmt(start_dt)}-{fmt(now)}）"


def _compute_time_filters(now):
    """计算各标签页的时间过滤起点，返回与 tabNames 对应的列表"""
    now_ts = now.timestamp()
    year_start    = datetime(now.year, 1, 1).timestamp()
    quarter_mon   = ((now.month - 1) // 3) * 3 + 1
    quarter_start = datetime(now.year, quarter_mon, 1).timestamp()
    month_start   = datetime(now.year, now.month, 1).timestamp()
    week_start    = datetime.combine(
        now - timedelta(days=now.weekday()), datetime.min.time()
    ).timestamp()
    day_ago       = now_ts - 86400
    return [None, year_start, quarter_start, month_start, week_start, day_ago]


def _filter_data(timestamps, values, filter_ts):
    """按时间戳过滤，返回 (ts_filt, vals_filt)"""
    if filter_ts is None:
        return list(timestamps), list(values)  # 保证总是 list
    pairs = [(t, v) for t, v in zip(timestamps, values) if t >= filter_ts]
    if not pairs:
        return [], []
    return list(zip(*pairs))


def _downsample(values, max_points=MAX_POINTS):
    """超过 max_points 时分箱均值降采样"""
    arr = np.array(values)
    if len(arr) <= max_points:
        return arr
    bins = np.array_split(arr, max_points)
    return np.array([b.mean() for b in bins])


# ── 图表渲染（数据 → Figure） ──

def _build_chart_figure(ts_filt, vals_filt):
    """根据过滤后的数据构建完整的 Figure，返回 (fig, ts_filt)"""
    if len(vals_filt) < MIN_POINTS:
        fig = Figure(dpi=144)
        fig.patch.set_visible(False)
        ax = fig.add_subplot(111)
        ax.patch.set_visible(False)
        ax.text(0.5, 0.5, "数据过少", transform=ax.transAxes,
                ha="center", va="center", color=TICK_COLOR, fontsize=10)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(colors=TICK_COLOR, labelsize=7)
        return fig

    y = _downsample(vals_filt)
    x = np.arange(len(y))

    fig = Figure(dpi=144)
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0.05, right=0.97, bottom=0.12, top=0.95)

    ax = fig.add_subplot(111)
    ax.patch.set_visible(False)
    ax.plot(x, y, color=CHART_COLOR, linewidth=CHART_LINE_WIDTH)
    ax.fill_between(x, y, alpha=CHART_FILL_ALPHA, color=CHART_COLOR)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min() - 5, y.max() + 5)
    ax.tick_params(colors=TICK_COLOR, labelsize=7, pad=2,
                   top=False, right=False, length=2)
    ax.tick_params(axis="x", length=0)
    ax.xaxis.set_tick_params(labelbottom=False)
    ax.grid(axis="y", alpha=0.25, color=GRID_COLOR,
            linewidth=0.5, linestyle="--")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(SPINE_COLOR)
        ax.spines[s].set_linewidth(0.8)

    # x 轴两端日期
    date_start = datetime.fromtimestamp(ts_filt[0]).strftime("%Y-%m-%d")
    date_end   = datetime.fromtimestamp(ts_filt[-1]).strftime("%Y-%m-%d")
    ax.text(0, -0.04, date_start, transform=ax.get_xaxis_transform(),
            ha="left", va="top", color=TICK_COLOR, fontsize=6.5)
    ax.text(len(x) - 1, -0.04, date_end, transform=ax.get_xaxis_transform(),
            ha="right", va="top", color=TICK_COLOR, fontsize=6.5)

    return fig


class _WheelAwareScrollArea(ScrollArea):
    """ScrollArea 变体：将内嵌 matplotlib 画布的滚轮事件转发到自身，

    解决顶部大卡片（HeartRateChart / FigureCanvas）拦截滚轮事件
    导致页面无法滚动的问题。
    """
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            delta = event.angleDelta().y()
            self.scrollDelagate.vScrollBar.scrollValue(-delta)
            return True
        return super().eventFilter(obj, event)


class DataPage(QFrame):
    """数据分析与趋势页面"""

    # 后台线程读取数据完成后，携带结果回到 UI 线程（token 用于丢弃过期结果）
    _data_ready = Signal(int, object)

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setObjectName("dataPage")
        self._chart_loaded = False
        self._load_token = 0
        self._data_ready.connect(self._on_data_ready)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # SegmentedWidget 导航栏
        self.segmentedWidget = SegmentedWidget(self)
        self.segmentedWidget.setFixedWidth(500)
        segmentedLayout = QHBoxLayout()
        segmentedLayout.setContentsMargins(0, 0, 0, 0)
        segmentedLayout.addStretch()
        segmentedLayout.addWidget(self.segmentedWidget)
        segmentedLayout.addStretch()
        layout.addLayout(segmentedLayout)

        # 堆叠页面容器
        self.stackedWidget = QStackedWidget(self)
        layout.addWidget(self.stackedWidget)

        # 定义标签页
        self.tabNames = ["所有", "今年", "季度", "本月", "本周", "24h"]
        self.tabs = []

        for name in self.tabNames:
            page = DataTabPage(self)
            scroll = _WheelAwareScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            scroll.enableTransparentBackground()
            page.chart.canvas.installEventFilter(scroll)

            self.stackedWidget.addWidget(scroll)
            self.tabs.append(scroll)

            self.segmentedWidget.addItem(
                routeKey=name,
                text=name,
                onClick=lambda checked, tab_name=name: self.stackedWidget.setCurrentWidget(
                    self.tabs[self.tabNames.index(tab_name)]
                )
            )

        self.stackedWidget.setCurrentWidget(self.tabs[0])
        self.segmentedWidget.setCurrentItem(self.tabNames[0])
        self.stackedWidget.currentChanged.connect(self._on_current_index_changed)

        # 悬浮按钮：不加入布局，与子页面完全脱节（不随标签页切换变化）
        self.floatButton = ToolButton(FluentIcon.SYNC, self)
        self.floatButton.setFixedSize(40, 40)
        self.floatButton.setStyleSheet(
            "QToolButton { background-color: white; border-radius: 8px;"
            " border: 1px solid #E2E8F0; }"
            "QToolButton:hover { background-color: #F1F5F9; }"
            "QToolButton:pressed { background-color: #E2E8F0; }"
        )
        self._update_float_button_pos()
        self.floatButton.clicked.connect(self._load_charts)

        # 延迟加载——构造只搭 UI，不碰 DB 和 matplotlib
        QTimer.singleShot(0, self._lazy_load_charts)

    def resizeEvent(self, event):
        """窗口尺寸变化时让悬浮按钮保持固定在右下角"""
        super().resizeEvent(event)
        self._update_float_button_pos()

    def _update_float_button_pos(self):
        """将悬浮按钮定位到页面右下角（距右、下边缘各 30px）"""
        btn = self.floatButton
        btn.move(self.width() - btn.width() - 30,
                 self.height() - btn.height() - 30)

    # ── 懒加载入口 ──

    def _lazy_load_charts(self):
        """页面首次渲染完成后加载所有标签页的图表"""
        if self._chart_loaded:
            return
        self._chart_loaded = True
        self._load_charts()

    def _load_charts(self):
        """从 data_manager 拉取最新数据并重建所有标签页图表（首次加载与悬浮按钮刷新共用）

        数据库读取与时间过滤/降采样在后台线程完成，避免大数据量时阻塞 UI；
        matplotlib 绘图仍在 UI 线程执行（数据已过滤，点数很小，成本可忽略）。
        """
        if self.data_manager is None:
            self._hide_all_big_overlays()
            return

        # 令牌机制：快速连点刷新时，旧的加载结果到达后会被丢弃
        self._load_token += 1
        token = self._load_token
        threading.Thread(target=self._charts_worker, args=(token,), daemon=True).start()

    def _charts_worker(self, token):
        """后台线程：单次扫描 + 各标签页窗口 numpy 采样（不碰 matplotlib）

        一次有序扫描出全量数据，再用掩码为 6 个时间窗口各取 ≤MAX_POINTS 个
        均匀采样点——内存有界、耗时与数据量近似线性且只扫一遍，几十万/百万条
        数据也能秒级完成。
        """
        try:
            now = datetime.now()
            fmt = lambda dt: f"{dt.year}.{dt.month}.{dt.day}"
            time_filters = _compute_time_filters(now)

            windows = []
            for i, filter_ts in enumerate(time_filters):
                start_ms = int(filter_ts * 1000) if filter_ts is not None else None
                windows.append((i, start_ms))

            sampled = self.data_manager.get_sampled_heart_rate_windows(
                windows, max_points=MAX_POINTS
            )

            results = []
            any_data = False
            for i, filter_ts in enumerate(time_filters):
                ts_filt, vals_filt, total = sampled[i]
                if total > 0:
                    any_data = True
                results.append((i, ts_filt, vals_filt, filter_ts, now, fmt))

            if not any_data:
                self._data_ready.emit(token, None)
                return
            self._data_ready.emit(token, results)
        except Exception as e:
            print(f"[DataPage] 后台加载失败: {e}")
            self._data_ready.emit(token, None)

    def _on_data_ready(self, token, results):
        """UI 线程：将后台计算结果渲染到各标签页"""
        if token != self._load_token:
            return  # 已发起新的加载，丢弃过期结果
        if results is None:
            self._hide_all_big_overlays()
            return

        for i, ts_filt, vals_filt, filter_ts, now, fmt in results:
            tab_scroll = self.tabs[i]
            page = tab_scroll.widget()
            fig = _build_chart_figure(ts_filt, vals_filt)
            self._apply_chart_to_card(page, tab_scroll, fig, filter_ts, now, fmt)

    # ── UI 操作 ──

    def _apply_chart_to_card(self, page, scroll, fig, filter_ts, now, fmt):
        """将 Figure 替换进大卡片，添加 label，安装事件过滤"""
        big_layout = page.dataChartCard.layout()

        # 移除上一次刷新留下的 label，避免重复累积
        old_label = getattr(page, "_range_label", None)
        if old_label is not None:
            big_layout.removeWidget(old_label)
            old_label.deleteLater()
            page._range_label = None

        # 替换原有 HeartRateChart
        big_layout.removeWidget(page.chart)
        page.chart.deleteLater()

        # 顶部 label
        label = QLabel(_range_label_text(filter_ts, now, fmt), page.dataChartCard)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"font-size: 14px; color: {LABEL_TEXT_COLOR}; font-weight: 600;"
        )
        big_layout.addWidget(label)
        page._range_label = label

        # 图表
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background: transparent;")
        big_layout.addWidget(canvas, 1)

        page.chart = canvas
        canvas.installEventFilter(scroll)
        page.hide_loading()

    def _hide_all_big_overlays(self):
        """data_manager 不可用或无数据时隐藏所有大卡片覆盖层"""
        for tab_scroll in self.tabs:
            page = tab_scroll.widget()
            page.hide_loading()

    def _on_current_index_changed(self, index):
        self.segmentedWidget.setCurrentItem(self.tabNames[index])
