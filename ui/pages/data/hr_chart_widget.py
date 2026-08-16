"""
心率趋势图组件（Matplotlib × PyQt6）
背景透明，嵌入卡片使用
"""
import numpy as np
import matplotlib
matplotlib.use("qtagg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import QWidget, QVBoxLayout

# ── 配色 ──
NEON_CYAN   = "#0EA5E9"
NEON_PINK   = "#F43F5E"
NEON_GREEN  = "#10B981"
NEON_ORANGE = "#F59E0B"
TEXT_MUTED  = "#64748B"
TEXT_GLOW   = "#0F172A"
DARK_CARD   = "#FFFFFF"

plt.style.use("default")
plt.rcParams.update({
    "axes.facecolor":    DARK_CARD,
    "axes.edgecolor":    "#E2E8F0",
    "axes.labelcolor":   TEXT_MUTED,
    "axes.titlecolor":   TEXT_GLOW,
    "axes.grid":         False,
    "grid.color":        "#E2E8F0",
    "grid.alpha":        0.6,
    "grid.linestyle":    "--",
    "grid.linewidth":    0.5,
    "xtick.color":       TEXT_MUTED,
    "ytick.color":       TEXT_MUTED,
    "text.color":        TEXT_GLOW,
    "figure.facecolor":  DARK_CARD,
    "font.size":         10,
})


def _create_chart_canvas(timestamps, values, file_count) -> FigureCanvas:
    """绘制心率折线图，返回透明背景的 canvas"""
    fig = Figure(figsize=(10, 5.6), dpi=144)
    fig.patch.set_visible(False)  # 透明

    ax = fig.add_subplot(111)
    ax.patch.set_visible(False)   # 透明

    x = np.arange(len(values))
    y = np.array(values)

    avg_hr = np.mean(y)
    max_hr = np.max(y)
    min_hr = np.min(y)

    # 渐变填充
    ax.fill_between(x, y, alpha=0.08, color=NEON_CYAN)
    ax.fill_between(x, y, alpha=0.04, color=NEON_PINK)

    # 发光层 + 主线条
    ax.plot(x, y, color=NEON_CYAN, linewidth=5, alpha=0.12, solid_capstyle="round")
    ax.plot(x, y, color=NEON_CYAN, linewidth=1.8, solid_capstyle="round",
            label="Heart Rate (BPM)", alpha=0.92)

    # 端点
    ax.scatter(x[0],  y[0],  color=NEON_CYAN, s=70, zorder=10,
               edgecolors=TEXT_GLOW, linewidths=1.5)
    ax.scatter(x[0],  y[0],  color=NEON_CYAN, s=140, zorder=9, alpha=0.15)
    ax.scatter(x[-1], y[-1], color=NEON_PINK, s=70, zorder=10,
               edgecolors=TEXT_GLOW, linewidths=1.5)
    ax.scatter(x[-1], y[-1], color=NEON_PINK, s=140, zorder=9, alpha=0.15)

    # 平均线
    ax.axhline(y=avg_hr, color=NEON_GREEN, linewidth=0.8, linestyle="--",
               alpha=0.5, label=f"Avg: {avg_hr:.0f} BPM")

    # 整体趋势线
    TREND_SAMPLES = 600
    bins = np.array_split(y, TREND_SAMPLES)
    trend_raw = np.array([b.mean() for b in bins])
    window_len = len(trend_raw) // 4
    if window_len % 2 == 0:
        window_len += 1
    pad = window_len // 2
    kernel = np.hanning(window_len)
    kernel = kernel / kernel.sum()
    trend_padded = np.pad(trend_raw, pad, mode="edge")
    trend_smooth = np.convolve(trend_padded, kernel, mode="same")
    trend_y = trend_smooth[pad:-pad]
    bin_size = len(y) / TREND_SAMPLES
    trend_x = np.arange(TREND_SAMPLES) * bin_size + bin_size / 2
    ax.plot(trend_x, trend_y, color=NEON_ORANGE, linewidth=1.8, linestyle="--",
            alpha=0.8, label=f"Trend ({TREND_SAMPLES} sma)", zorder=6)

    # 轴
    ax.tick_params(colors=TEXT_MUTED, labelsize=8)
    for spine_name in ["top", "right"]:
        ax.spines[spine_name].set_visible(False)
    for spine_name in ["left", "bottom"]:
        ax.spines[spine_name].set_color("#CBD5E1")
        ax.spines[spine_name].set_linewidth(0.5)

    legend = ax.legend(
        framealpha=0.8, facecolor="#FFFFFF", edgecolor="#CBD5E1",
        labelcolor=TEXT_GLOW, fontsize=9, loc="upper right",
        handlelength=2, borderpad=0.5
    )
    legend.get_frame().set_linewidth(0.5)

    info = (f"  {len(y):,} pts  ·  "
            f"max {max_hr}  ·  min {min_hr}  ·  avg {avg_hr:.0f} BPM")
    ax.text(0.5, -0.11, info, transform=ax.transAxes, ha="center",
            fontsize=8, color=TEXT_MUTED, alpha=0.6)

    fig.tight_layout(pad=1.8)
    return FigureCanvas(fig)


class HeartRateChart(QWidget):
    """心率趋势图组件，嵌入卡片使用，背景透明"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 初始空图表
        self.fig = Figure(dpi=144)
        self.fig.patch.set_visible(False)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background: transparent;")
        layout.addWidget(self.canvas)

    def update_data(self, timestamps, values, file_count):
        """用外部数据刷新图表"""
        if not values:
            return
        new_canvas = _create_chart_canvas(timestamps, values, file_count)
        new_canvas.setStyleSheet("background: transparent;")

        # 替换 canvas
        layout = self.layout()
        layout.removeWidget(self.canvas)
        self.canvas.deleteLater()
        self.canvas = new_canvas
        layout.addWidget(self.canvas)
