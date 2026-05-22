"""
多 Tab 编辑容器视图：Fluent TabBar + QStackedWidget。

仅负责把组件搭起来，所有 tab 的增删切换由 TabController 接管。
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from qfluentwidgets import TabBar, TabCloseButtonDisplayMode


class TabContainer(QWidget):
    """承载多 tab 的容器视图。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tabContainer")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_bar = TabBar(self)
        self.tab_bar.setCloseButtonDisplayMode(TabCloseButtonDisplayMode.ALWAYS)
        self.tab_bar.setTabsClosable(True)

        self.stack = QStackedWidget(self)
        self.stack.setAttribute(Qt.WA_TranslucentBackground, True)
        self.stack.setStyleSheet("QStackedWidget { background: transparent; }")

        layout.addWidget(self.tab_bar)
        layout.addWidget(self.stack, 1)
