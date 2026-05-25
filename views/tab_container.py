"""
多 Tab 编辑容器视图：Fluent TabBar + QStackedWidget。

仅负责把组件搭起来，所有 tab 的增删切换由 TabController 接管。
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from qfluentwidgets import (
    BodyLabel,
    SubtitleLabel,
    TabBar,
    TabCloseButtonDisplayMode,
    isDarkTheme,
)


class WelcomePage(QWidget):
    """无 tab 时显示的空状态欢迎页。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        self.title_label = SubtitleLabel("Fluent Markdown", self)
        self.title_label.setAlignment(Qt.AlignCenter)

        self.hint_label = BodyLabel(
            "点击「新建」创建文档，或「打开」编辑已有文件\n"
            "也可以从「最近文件」中快速恢复",
            self,
        )
        self.hint_label.setAlignment(Qt.AlignCenter)

        self.shortcut_label = BodyLabel(
            "快捷键提示：Ctrl+滚轮 缩放 · 全屏阅读 · 导出 PDF/DOCX/HTML",
            self,
        )
        self.shortcut_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.shortcut_label)

        self._apply_style()

    def _apply_style(self) -> None:
        is_dark = isDarkTheme()
        secondary = "rgba(255,255,255,0.45)" if is_dark else "rgba(0,0,0,0.45)"
        self.hint_label.setStyleSheet(f"color: {secondary};")
        self.shortcut_label.setStyleSheet(f"color: {secondary}; font-size: 12px;")


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

        # 空状态欢迎页（始终作为 index 0）
        self.welcome_page = WelcomePage(self)
        self.stack.addWidget(self.welcome_page)

        layout.addWidget(self.tab_bar)
        layout.addWidget(self.stack, 1)
