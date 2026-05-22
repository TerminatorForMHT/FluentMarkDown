"""
主题控制器：协调系统主题（亮/暗）与预览主题（PreviewThemes）的切换。
"""
from typing import Callable, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from models.themes import PreviewThemes


class ThemeController(QObject):
    """全局共享的预览主题状态。"""

    previewThemeChanged = pyqtSignal(str)

    def __init__(self, default_theme: str = "light", parent: Optional[QObject] = None):
        super().__init__(parent)
        self._preview_theme = default_theme

    @property
    def preview_theme(self) -> str:
        return self._preview_theme

    def available_themes(self) -> List[str]:
        return PreviewThemes.get_available_themes()

    def theme_display_name(self, theme_key: str) -> str:
        return PreviewThemes.get_theme_styles(theme_key)["name"]

    def set_preview_theme(self, theme_key: str) -> None:
        if theme_key == self._preview_theme:
            return
        if theme_key not in self.available_themes():
            return
        self._preview_theme = theme_key
        self.previewThemeChanged.emit(theme_key)

    def bind(self, slot: Callable[[str], None]) -> None:
        """便捷绑定。"""
        self.previewThemeChanged.connect(slot)
