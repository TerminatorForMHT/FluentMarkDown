#!/usr/bin/env python3
"""
Fluent Markdown Editor 主入口文件
"""
import sys
import os

from PyQt5.QtWidgets import QApplication, QVBoxLayout
from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtGui import QIcon
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


class MainWindow(FluentWidget):
    """
    主窗口
    """
    def __init__(self):
        super().__init__()
        
        setTheme(Theme.AUTO)
        
        self.theme_listener = SystemThemeListener(self)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.main_layout.setSpacing(0)
        
        self.markdown_editor = MarkdownWidget(self)
        self.main_layout.addWidget(self.markdown_editor, 1)
        
        self.resize(1000, 700)
        self.setWindowTitle("Fluent Markdown")
        
        self._setup_icon()
        
        qconfig.themeChanged.connect(self.on_theme_changed)
        
        self.theme_listener.start()
    
    def _setup_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, "resources", "mark.ico")
            else:
                icon_path = os.path.join(os.path.dirname(__file__), "resources", "mark.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
    
    def closeEvent(self, e):
        if self.markdown_editor.check_save_on_close():
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
    
    try:
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "resources", "mark.ico")
        else:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "mark.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass
    
    window = MainWindow()
    window.showMaximized()
    
    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())
    
    sys.exit(app.exec_())
