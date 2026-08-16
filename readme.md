# 听澜 · HypeBeat
一款面向游戏主播的桌面端心率监测器。

起于乙巳元旦，名于丙午盛夏。

**听澜 · HypeBeat — A Bluetooth-based Desktop Heart Rate Monitor**

通过 BLE（低功耗蓝牙）实时扫描、连接心率监测设备，可视化心率数据并持久化存储。

A Windows desktop application that scans and connects to BLE heart rate monitors, visualizes real-time heart rate data with dynamic charts, and persists historical data to disk.

***

## 功能概览 | Features

| 功能           | 说明                                            |
| ------------ | --------------------------------------------- |
| **BLE 设备扫描** | 扫描周围所有蓝牙设备，可选自动筛选心率设备（UUID 180d）              |
| **实时心率监测**   | 连接设备后通过 Notification 实时接收心率数据（BPM）            |
| **动态折线图**    | 自绘实时滚动折线图，支持自动 Y 轴缩放（黄金比例算法）、网格、平均心率线         |
| **趋势图**      | 数据从左到右逐渐压扁，展示完整历史趋势                           |
| **悬浮窗**      | 无边框置顶小窗口，实时显示心率，支持单击/双击拖动                     |
| **数据持久化**    | SQLite 数据库存储心率数据，批量写入（50 条一批） |
| **系统托盘**     | 后台运行，托盘菜单快捷操作                                 |
| **自动重连**     | 设备断开后自动重连，可配置重连次数和间隔                          |
| **启动闪屏**     | Win32 原生闪屏，在 PyQt 加载前立即弹出                     |
| **单实例检测**    | 通过命名 Mutex 防止重复启动，自动激活已有窗口                    |
| **主题支持**     | Fluent Design 浅色主题，自动跟随 Windows 强调色           |
| **性能监控**     | 实时显示 CPU / 内存占用，磁盘空间分析                        |
| **文件清理**     | 启动时自动清理 <5KB 的小数据文件                           |
| **关闭确认**     | 可配置关闭行为（直接退出 / 最小化到托盘）                        |

***

## 技术栈 | Tech Stack

| 层级         | 技术                                           |
| ---------- | -------------------------------------------- |
| **UI 框架**  | PySide6 + PySide6-Fluent-Widgets (Fluent Design) |
| **蓝牙通信**   | bleak（跨平台 BLE 库）                             |
| **系统 API** | pywin32 (win32gui, win32api, win32con)       |
| **进程通信**   | mmap 共享内存（`HeartRateSharedMemory`）           |
| **图像处理**   | Pillow (PIL)                                 |
| **系统监控**   | psutil                                       |
| **窗口特效**   | PySideSix-Frameless-Window                    |
| **全量分析/ML** | DuckDB（直接扫描 SQLite / 导出 Parquet）          |
| **编译打包**   | Nuitka (standalone/onefile)                   |

***

## 项目结构 | Project Structure

```
HypeBeat/
├── main.py                  # 程序入口（极简调用）
├── bin/
│   └── app.py               # 启动逻辑（闪屏 → QApplication → 主窗口）
├── core/                    # 核心逻辑层
│   ├── ble/
│   │   ├── scanner.py       # BLE 设备扫描（QThread + BleakScanner）
│   │   └── monitor.py       # 心率监测线程（QThread + BleakClient）
│   └── device/
│       ├── device_manager.py   # 设备管理器（扫描/连接/断开/重连）
│       └── heart_rate_core.py  # 核心配置与状态
├── ui/                      # 用户界面层
│   ├── main_window/
│   │   └── main_window.py   # 主窗口（FluentWindow 导航架构）
│   ├── pages/
│   │   ├── home/            # 主页（设备连接 + 图表）
│   │   ├── widget/          # 小组件页
│   │   ├── data/            # 数据分析与趋势页
│   │   ├── storage/         # 存储和性能页
│   │   └── settings/        # 设置页
│   ├── charts/
│   │   ├── line_chart/      # 动态滚动折线图
│   │   └── trend_chart/     # 历史趋势折线图
│   ├── floating_window/     # 悬浮窗（无边框置顶）
│   ├── tray/                # 系统托盘
│   └── dialogs/             # 对话框（关闭确认等）
├── persistence/
│   └── manager/
│       ├── data_manager.py  # 数据持久化（SQLite 批量写入）
│       └── file_cleaner.py  # 小文件清理
├── system/
│   ├── startup/
│   │   └── app_startup.py   # 冷启动（DPI感知 + 闪屏 + 单实例）
│   ├── settings/
│   │   └── settings_manager.py  # 设置持久化（JSON）
│   └── memory/
│       └── shared_memory.py # mmap 共享内存
├── config/
│   └── config.json          # QFluentWidgets 主题配置
├── resources/               # 资源文件（图标 base64）
├── persistence/
│   ├── export_to_parquet.py # DuckDB 全量导出 Parquet（ML/分析用）
│   └── analyze.py           # DuckDB 全量分析示例（ML 特征原型）
├── build/
│   ├── build.py             # Nuitka 编译脚本（python build/build.py）
│   ├── msvc.bat             # MSVC 编译环境（vcvars64）
│   └── schedule_build.py    # 预约深夜编译小工具
└── requirements.txt         # Python 依赖
```

> 注：README 中安装包（Inno Setup）脚本 `pack.iss` 尚未创建；如需分发安装包请补写该脚本。

***

## 启动流程 | Cold Start Sequence

```
main.py → bin/app.py
  │
  ├── [1] app_startup.start()
  │       ├── 记录 DPI 感知前屏幕宽度
  │       ├── 声明 DPI 感知（SetProcessDpiAwareness）
  │       ├── 显示 Win32 原生闪屏（TOPMOST）
  │       └── 单实例检测（命名 Mutex）
  │
  ├── [2] PySide6 模块加载（闪屏已显示，掩盖耗时）
  │
  ├── [3] HeartRateMonitorWindow.__init__()
  │       ├── 系统托盘
  │       ├── 设置管理器（读取 ~/.heartrate_monitor/settings.json）
  │       ├── 数据管理器（初始化 SQLite 数据库）
  │       ├── 共享内存（mmap 初始化）
  │       ├── 设备管理器
  │       ├── 获取系统主题色并应用
  │       ├── 注册导航页面（主页/小组件/数据/存储/设置）
  │       └── 自动清理小文件
  │
  └── [4] window.show() → 关闭闪屏 → app.exec()
```

***

## 构建与部署 | Build & Deployment

### 开发环境

```bash
pip install -r requirements.txt
python main.py
```

### 编译（Nuitka）

```bash
# 在 hypebeat conda 环境中执行
python build/build.py
```

输出到 `F:/HypeBeatDist/`，生成 `HypeBeat.exe`（onefile，需本机已装 MSVC BuildTools，见 `build/msvc.bat`）。

### 打包安装包（Inno Setup）

`pack.iss` 尚未创建；如需分发安装包，请先用 Inno Setup 编写该脚本（可基于 `F:/HypeBeatDist/HypeBeat.exe` 打包）。

***

## 数据存储 | Data Storage

心率数据使用 SQLite 数据库存储，默认位于用户目录 `~/.heartrate_monitor/hypebeat.db`（可在设置中修改数据目录）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | INTEGER | 自增主键 |
| `ts` | INTEGER | Unix 毫秒时间戳 |
| `hr` | INTEGER | 心率值 (BPM) |

- 每收集 50 条数据批量写入一次数据库（WAL 模式）
- 数据库自动建表，带时间戳索引

***

## 作者 | Author

**EnderHack** & **SilentStudio**
