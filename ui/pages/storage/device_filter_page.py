from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from qfluentwidgets import PushButton, FluentIcon, TitleLabel


class DeviceFilterPage(QFrame):
    """设备筛选配置页面 - 不在导航栏显示，通过超链接进入"""

    def __init__(self, parent=None, back_callback=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self.setObjectName("deviceFilterPage")

        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(20, 20, 20, 20)
        self.mainLayout.setSpacing(20)

        # 顶部返回按钮行
        self.topLayout = QHBoxLayout()
        self.topLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout.setSpacing(8)

        self.backButton = PushButton(FluentIcon.LEFT_ARROW, "返回", self)
        self.backButton.setObjectName("backButton")
        self.backButton.clicked.connect(self._on_back_clicked)
        self.topLayout.addWidget(self.backButton)

        self.topLayout.addStretch()

        self.mainLayout.addLayout(self.topLayout)

        # 页面标题
        self.pageTitle = TitleLabel("设备筛选配置", self)
        self.mainLayout.addWidget(self.pageTitle)

        self.mainLayout.addStretch()

    def _on_back_clicked(self):
        if self.back_callback:
            self.back_callback()
