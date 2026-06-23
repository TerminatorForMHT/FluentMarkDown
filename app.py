#!/usr/bin/env python3
"""
Fluent Markdown Editor 主入口文件
"""
import sys
import os

from PyQt5.QtWidgets import QApplication, QVBoxLayout
from PyQt5.QtCore import QTimer, QRect
from PyQt5.QtGui import QIcon, QFont
from qfluentwidgets import (
    FluentWidget,
    setTheme,
    Theme,
    SystemThemeListener,
    isDarkTheme
)
from qfluentwidgets.common.config import qconfig

from utils import setup_high_dpi
from views.markdown_editor import MarkdownWidget
from models.settings import AppSettings


def configure_application_font(app):
    """设置应用级字体，避免 Qt 在 macOS 上反复查找缺失的 Segoe UI。"""
    if sys.platform == "darwin":
        font_family = "PingFang SC"
        QFont.insertSubstitution("Segoe UI", font_family)
        QFont.insertSubstitution("Segoe UI Variable", font_family)
    elif sys.platform.startswith("win"):
        font_family = "Microsoft YaHei UI"
    else:
        font_family = "Noto Sans CJK SC"

    app.setFont(QFont(font_family, 12))


def is_rect_visible_on_any_screen(rect):
    """判断窗口左上角是否落在任一屏幕可用区域内，避免 Qt 恢复到屏幕外坐标。"""
    for screen in QApplication.screens():
        if screen.availableGeometry().contains(rect.topLeft()):
            return True
    return False


def center_window_on_primary_screen(window):
    """把窗口移动到主屏幕中央，避免恢复到屏幕外坐标。"""
    screen = QApplication.primaryScreen()
    if not screen:
        return

    available_geometry = screen.availableGeometry()
    window_geometry = window.frameGeometry()
    window_geometry.moveCenter(available_geometry.center())
    window.move(window_geometry.topLeft())


class MainWindow(FluentWidget):
    """
    主窗口
    """
    def __init__(self):
        super().__init__()
        
        setTheme(Theme.AUTO)
        
        self.settings = AppSettings()
        self.theme_listener = SystemThemeListener(self)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.main_layout.setSpacing(0)
        
        self.markdown_editor = MarkdownWidget(self)
        self.main_layout.addWidget(self.markdown_editor, 1)
        
        # 恢复持久化设置
        self._restore_settings()
        self.setWindowTitle("Fluent Markdown")
        
        self._setup_icon()
        
        qconfig.themeChanged.connect(self.on_theme_changed)
        
        self.theme_listener.start()
    
    def _setup_icon(self):
        try:
            icon_name = "icon.icns" if sys.platform == "darwin" else "mark.ico"
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, "resources", icon_name)
            else:
                icon_path = os.path.join(os.path.dirname(__file__), "resources", icon_name)
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
    
    def _restore_settings(self):
        """从持久化设置恢复字号、主题、窗口状态"""
        font_size = self.settings.get("font_size")
        self.markdown_editor.controller.set_font_size(font_size)
        self.markdown_editor.update_editor_style()

        preview_theme = self.settings.get("preview_theme")
        self.markdown_editor.controller.set_theme(preview_theme)
        # 同步主题下拉框
        from models.themes import PreviewThemes
        themes = PreviewThemes.get_available_themes()
        if preview_theme in themes:
            self.markdown_editor.theme_combo.setCurrentIndex(themes.index(preview_theme))

        # 恢复窗口大小和位置
        width = self.settings.get("window_width")
        height = self.settings.get("window_height")
        self.resize(width, height)
        pos_x = self.settings.get("window_x")
        pos_y = self.settings.get("window_y")
        saved_window_rect = QRect(pos_x, pos_y, width, height)
        if is_rect_visible_on_any_screen(saved_window_rect):
            self.move(pos_x, pos_y)
        else:
            center_window_on_primary_screen(self)

    def _save_settings(self):
        """保存当前设置到文件"""
        self.settings.set("font_size", self.markdown_editor.controller.font_size)
        self.settings.set("preview_theme", self.markdown_editor.controller.preview_theme)
        self.settings.set("window_maximized", self.isMaximized())
        if not self.isMaximized():
            geo = self.geometry()
            self.settings.set("window_width", geo.width())
            self.settings.set("window_height", geo.height())
            self.settings.set("window_x", geo.x())
            self.settings.set("window_y", geo.y())
        self.settings.save()

    def closeEvent(self, e):
        if self.markdown_editor.check_save_on_close():
            self._save_settings()
            self.theme_listener.terminate()
            self.theme_listener.deleteLater()
            super().closeEvent(e)
        else:
            e.ignore()
    
    def on_theme_changed(self):
        if self.windowEffect is not None:
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))
        
        self.markdown_editor.update_editor_style()
        self.markdown_editor.update_preview()
        
        is_dark = isDarkTheme()
        style = """
            QStatusBar {
                background-color: transparent;
                border: none;
                padding: 2px 8px;
            }
            QStatusBar::item {
                border: none;
            }
        """
        self.markdown_editor.status_bar.setStyleSheet(style)
        
        text_color = "#ffffff" if is_dark else "#333333"
        label_style = f"color: {text_color}; padding: 0 0px;"
        self.markdown_editor.char_count_label.setStyleSheet(label_style)
        self.markdown_editor.selection_label.setStyleSheet(label_style)
        self.markdown_editor.theme_label.setStyleSheet(label_style)
        self.markdown_editor.encoding_label.setStyleSheet(label_style)


if __name__ == "__main__":
    setup_high_dpi()
    
    app = QApplication(sys.argv)
    configure_application_font(app)
    
    try:
        icon_name = "icon.icns" if sys.platform == "darwin" else "mark.ico"
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "resources", icon_name)
        else:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", icon_name)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass
    
    window = MainWindow()
    if window.settings.get("window_maximized"):
        window.showMaximized()
    else:
        window.show()
    
    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())
    
    sys.exit(app.exec_())
