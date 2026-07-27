from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """全局应用信号 - 用于 UI 和逻辑层解耦"""

    # 心率相关
    heart_rate_updated = Signal(int)
    heart_rate_stats_updated = Signal(int, int)  # max, min

    # 设备扫描相关
    scan_started = Signal()
    scan_finished = Signal(list)
    scan_failed = Signal(str)
    device_found = Signal(object)  # DeviceInfo
    device_updated = Signal(object)
    device_list_cleared = Signal()

    # 设备连接相关
    device_connecting = Signal()
    device_connected = Signal(str)  # device name
    device_disconnected = Signal()
    connection_status_changed = Signal(str)
    connection_error = Signal(str)
    connection_state_changed = Signal(object)  # 连接状态变更，参数为 ConnectionState 枚举对象（int 类型兼容）
    reconnect_progress = Signal(int, int)  # 重连进度（当前次数，最大次数）
    reconnect_success = Signal()  # 重连成功
    reconnect_failed = Signal()  # 重连失败
    chart_data_clear_requested = Signal()  # 请求清空图表数据

    # UI → 逻辑 动作信号 (HomePage 触发, MainWindow 中介, DeviceManager 响应)
    scan_requested = Signal(bool)     # filter_heart_rate_devices
    connect_requested = Signal(str)   # selected device text
    disconnect_requested = Signal()

    # UI 状态控制信号 (DeviceManager → UI)
    ui_scan_state_changed = Signal(bool, str)  # enabled, text
    ui_progress_state_changed = Signal(bool, bool)  # indeterminate visible, progress visible
    ui_connect_state_changed = Signal(bool, bool)  # connect enabled, disconnect enabled
    ui_list_enabled_changed = Signal(bool)
    ui_checkbox_enabled_changed = Signal(bool)

    # 通知/提示
    info_bar_requested = Signal(str, str, str)  # type (info, warn, error, success), title, content

    # 系统监控 (CPU/内存)
    cpu_info_updated = Signal(float, float, float)
    memory_info_updated = Signal(int, int, float, int, float, float)

    # 磁盘/存储
    disk_space_updated = Signal(float, float, float)  # total_gb, used_gb, percent

    # 导航
    navigate_to_storage = Signal()

    # 设置变更
    settings_changed = Signal(str, object)
