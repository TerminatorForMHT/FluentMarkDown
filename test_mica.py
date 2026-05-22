#!/usr/bin/env python3
"""
临时版本：测试 Mica 是否能正常工作
"""
import sys
import os

from PyQt5.QtWidgets import (
    QTextEdit, QVBoxLayout, QFrame, QWidget, QStatusBar, QFileDialog
)
from PyQt5.QtCore import Qt,  QPoint, QTimer, QSize
from PyQt5.QtGui import QPainterPath, QRegion, QColor, QIcon

from qfluentwidgets import (
    FluentIcon,
    CommandBar,
    TransparentPushButton,
    CardWidget,
    ComboBox,
    BodyLabel,
    SingleDirectionScrollArea,
    isDarkTheme,
    FluentWidget,
    setTheme,
    Theme,
    SystemThemeListener
)
from qframelesswindow.webengine import FramelessWebEngineView
from qfluentwidgets.common.config import qconfig

import markdown

# 导出功能所需的库
try:
    from fpdf import FPDF
    from docx import Document
    HAS_EXPORT_LIBS = True
except ImportError:
    HAS_EXPORT_LIBS = False


def setup_high_dpi():
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class PreviewThemes:
    @staticmethod
    def get_theme_styles(theme_name):
        themes = {
            "light": {
                "name": "默认",
                "background_color": "transparent",
                "text_color": "#333333",
                "heading_color": "#2c3e50",
                "code_bg": "rgba(255, 255, 255, 0.8)",
                "blockquote_bg": "rgba(255, 255, 255, 0.6)",
                "scrollbar_track": "#f1f1f1",
                "scrollbar_thumb": "#c1c1c1",
                "scrollbar_thumb_hover": "#a8a8a8",
                "link_color": "#3498db"
            },
            "dark": {
                "name": "深色",
                "background_color": "#2d2d2d",
                "text_color": "#e0e0e0",
                "heading_color": "#ffffff",
                "code_bg": "rgba(255, 255, 255, 0.1)",
                "blockquote_bg": "rgba(255, 255, 255, 0.05)",
                "scrollbar_track": "#3d3d3d",
                "scrollbar_thumb": "#5d5d5d",
                "scrollbar_thumb_hover": "#7d7d7d",
                "link_color": "#64b5f6"
            }
        }
        return themes.get(theme_name, themes["light"])

    @staticmethod
    def get_available_themes():
        return ["light", "dark"]


class MarkdownWidget(QFrame):
    PREVIEW_RADIUS = 8

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("markdownInterface")
        self.is_fullscreen = False
        self.preview_theme = "light"
        self.font_size = 16

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self.command_bar = CommandBar(self)
        self.setup_command_bar()

        self.card_container = QWidget(self)
        self.card_container_layout = QVBoxLayout(self.card_container)
        self.card_container_layout.setContentsMargins(5, 5, 5, 5)
        self.card_container_layout.setSpacing(0)

        self.editor_card = CardWidget(self.card_container)
        self.editor_card.setStyleSheet("background-color: transparent;")
        self.editor_layout = QVBoxLayout(self.editor_card)
        self.editor_layout.setContentsMargins(1, 1, 1, 1)
        self.editor_layout.setSpacing(0)

        from PyQt5.QtWidgets import QSplitter
        self.splitter = QSplitter(Qt.Horizontal, self.editor_card)
        self.splitter.setStyleSheet("""
            QSplitter { background-color: transparent; }
            QSplitter::handle { width: 4px; background-color: rgba(100,149,237,0.25); }
            QSplitter::handle:hover { background-color: rgba(100,149,237,0.55); }
        """)
        self.editor_layout.addWidget(self.splitter, 1)
        self.card_container_layout.addWidget(self.editor_card, 1)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write Markdown here...")
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_area = SingleDirectionScrollArea(orient=Qt.Vertical, parent=self.editor_card)
        self.scroll_area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.scroll_area.setWidget(self.editor)
        self.scroll_area.setWidgetResizable(True)

        self.preview_container = QFrame(self.editor_card)
        self.preview_container.setObjectName("previewContainer")
        self.preview_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview_container.setStyleSheet("""
            QFrame#previewContainer{
                background: transparent;
                border: none;
            }
        """)
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(0)

        self.preview = FramelessWebEngineView(self.preview_container)
        self.preview.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview.setStyleSheet("background: transparent; border: none;")
        try:
            self.preview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        except Exception:
            pass

        self.preview_layout.addWidget(self.preview)

        self.splitter.addWidget(self.scroll_area)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([500, 500])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.status_bar = QStatusBar(self)
        is_dark = isDarkTheme()
        if is_dark:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: transparent;
                    border: none;
                    padding: 2px 8px;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
        else:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: transparent;
                    border: none;
                    padding: 2px 8px;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
        self.setup_status_bar()

        self.vBoxLayout.addWidget(self.command_bar)
        self.vBoxLayout.addWidget(self.card_container, 1)
        self.vBoxLayout.addWidget(self.status_bar)

        self.editor.textChanged.connect(self.update_preview)
        self.editor.selectionChanged.connect(self.update_status_bar)

        self.update_editor_style()
        self.update_preview()

    def _updatePreviewRoundMask(self):
        if not hasattr(self, "preview_container"):
            return
        if self.is_fullscreen:
            self.preview_container.clearMask()
            return

        r = self.PREVIEW_RADIUS
        rect = self.preview_container.rect()
        if rect.isNull():
            return

        path = QPainterPath()
        path.moveTo(rect.topLeft())
        path.lineTo(rect.topRight() - QPoint(r, 0))
        path.quadTo(rect.topRight(), rect.topRight() + QPoint(0, r))
        path.lineTo(rect.bottomRight() - QPoint(0, r))
        path.quadTo(rect.bottomRight(), rect.bottomRight() - QPoint(r, 0))
        path.lineTo(rect.bottomLeft())
        path.closeSubpath()

        region = QRegion(path.toFillPolygon().toPolygon())
        self.preview_container.setMask(region)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._updatePreviewRoundMask()

    def setup_command_bar(self):
        self.theme_label_cmd = BodyLabel("预览主题:")
        self.theme_combo = ComboBox()

        themes = PreviewThemes.get_available_themes()
        theme_names = []
        for theme in themes:
            theme_info = PreviewThemes.get_theme_styles(theme)
            theme_names.append(theme_info["name"])

        self.theme_combo.addItems(theme_names)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

        self.command_bar.addWidget(self.theme_label_cmd)
        self.command_bar.addWidget(self.theme_combo)

    def on_theme_changed(self, index):
        themes = PreviewThemes.get_available_themes()
        if 0 <= index < len(themes):
            self.set_preview_theme(themes[index])

    def set_preview_theme(self, theme_name):
        self.preview_theme = theme_name
        self.update_preview()

    def setup_status_bar(self):
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()

        self.char_count_label = BodyLabel("字符: 0", self)
        self.selection_label = BodyLabel("选中: 0", self)
        self.encoding_label = BodyLabel("编码: UTF-8", self)

        theme_info = PreviewThemes.get_theme_styles(self.preview_theme)
        self.theme_label = BodyLabel(f"预览主题: {theme_info['name']}", self)

        text_color = "#ffffff" if is_dark else "#333333"
        label_style = f"color: {text_color}; padding: 0 8px;"
        self.char_count_label.setStyleSheet(label_style)
        self.selection_label.setStyleSheet(label_style)
        self.theme_label.setStyleSheet(label_style)
        self.encoding_label.setStyleSheet(label_style)

        self.status_bar.addWidget(self.char_count_label)
        self.status_bar.addWidget(self.selection_label)
        self.status_bar.addWidget(self.theme_label)
        self.status_bar.addPermanentWidget(self.encoding_label)

    def update_status_bar(self):
        text = self.editor.toPlainText()
        self.char_count_label.setText(f"字符: {len(text)}")
        self.selection_label.setText(f"选中: {len(self.editor.textCursor().selectedText())}")

    def update_editor_style(self):
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        if is_dark:
            self.editor.setStyleSheet("""
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #ffffff;
                font-size: 16px;
                selection-background-color: rgba(100, 149, 237, 0.3);
            """)
            self.editor.setCursorWidth(3)
        else:
            self.editor.setStyleSheet("""
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #333333;
                font-size: 16px;
                selection-background-color: rgba(100, 149, 237, 0.3);
            """)
            self.editor.setCursorWidth(2)

    def update_preview(self):
        md_text = self.editor.toPlainText()
        html = markdown.markdown(md_text, extensions=['fenced_code'])

        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()

        ts = PreviewThemes.get_theme_styles(self.preview_theme)
        bg = ts["background_color"]

        if self.preview_theme == "light":
            if is_dark:
                text_color = "#e0e0e0"
                heading_color = "#ffffff"
                code_bg = "rgba(255, 255, 255, 0.1)"
                blockquote_bg = "rgba(255, 255, 255, 0.05)"
                scrollbar_track = "#3d3d3d"
                scrollbar_thumb = "#5d5d5d"
                scrollbar_thumb_hover = "#7d7d7d"
                link_color = "#64b5f6"
            else:
                text_color = ts["text_color"]
                heading_color = ts["heading_color"]
                code_bg = ts["code_bg"]
                blockquote_bg = ts["blockquote_bg"]
                scrollbar_track = ts["scrollbar_track"]
                scrollbar_thumb = ts["scrollbar_thumb"]
                scrollbar_thumb_hover = ts["scrollbar_thumb_hover"]
                link_color = ts["link_color"]
        else:
            text_color = ts["text_color"]
            heading_color = ts["heading_color"]
            code_bg = ts["code_bg"]
            blockquote_bg = ts["blockquote_bg"]
            scrollbar_track = ts["scrollbar_track"]
            scrollbar_thumb = ts["scrollbar_thumb"]
            scrollbar_thumb_hover = ts["scrollbar_thumb_hover"]
            link_color = ts["link_color"]

        r = self.PREVIEW_RADIUS

        styled_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  html, body {
    margin: 0; padding: 0; height: 100%;
    overflow: hidden; background: transparent !important;
    color: """ + text_color + """;
    font-family: Arial, sans-serif;
    font-size: 16px;
  }
  .content {
    height: 100%;
    background: """ + bg + """;
    border-top-right-radius: """ + str(r) + """px;
    border-bottom-right-radius: """ + str(r) + """px;
    overflow: hidden;
  }
  .scroll {
    height: 100%; overflow-y: auto;
    box-sizing: border-box; padding: 20px 20px 36px 20px;
  }
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-track { background: """ + scrollbar_track + """; border-radius: 4px; }
  ::-webkit-scrollbar-thumb { background: """ + scrollbar_thumb + """; border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: """ + scrollbar_thumb_hover + """; }

  h1,h2,h3,h4,h5,h6 { color: """ + heading_color + """; margin: 20px 0 10px; }
  p { margin: 0 0 10px; }
  code { background: """ + code_bg + """; padding: 2px 4px; border-radius: 3px; color: """ + text_color + """; }
  pre { position: relative; background: """ + code_bg + """; padding: 10px; border-radius: 5px; overflow-x: auto; margin: 10px 0; color: """ + text_color + """; }
  pre code { background: transparent; padding: 0; border-radius: 0; }
  blockquote {
    border-left: 4px solid rgba(100,149,237,0.5);
    margin: 10px 0; padding: 10px 15px;
    background: """ + blockquote_bg + """;
  }
  a { color: """ + link_color + """; text-decoration: none; }
  a:hover { text-decoration: underline; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; }
  th, td { border: 1px solid rgba(0,0,0,0.12); padding: 8px; text-align: left; }
  th { background: """ + code_bg + """; }
</style>
</head>
<body>
  <div class="content"><div class="scroll">
    """ + html + """
  </div></div>
</body>
</html>
"""
        self.preview.setHtml(styled_html)
        self._updatePreviewRoundMask()


class MainWindow(FluentWidget):
    def __init__(self):
        super().__init__()

        setTheme(Theme.AUTO)

        self.theme_listener = SystemThemeListener(self)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.main_layout.setSpacing(0)

        self.markdown_editor = MarkdownWidget(self)
        self.main_layout.addWidget(self.markdown_editor, 1)

        self.resize(1100, 720)
        self.setWindowTitle("Fluent Markdown - Test")

        qconfig.themeChanged.connect(self.on_theme_changed)
        self.theme_listener.start()

    def closeEvent(self, e):
        self.theme_listener.terminate()
        self.theme_listener.deleteLater()
        super().closeEvent(e)

    def on_theme_changed(self):
        if self.windowEffect is not None:
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))
        self.markdown_editor.update_editor_style()
        self.markdown_editor.update_preview()
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        if is_dark:
            self.markdown_editor.status_bar.setStyleSheet("""
                QStatusBar { background-color: transparent; border: none; padding: 2px 8px; }
                QStatusBar::item { border: none; }
            """)
        else:
            self.markdown_editor.status_bar.setStyleSheet("""
                QStatusBar { background-color: transparent; border: none; padding: 2px 8px; }
                QStatusBar::item { border: none; }
            """)
        text_color = "#ffffff" if is_dark else "#333333"
        label_style = f"color: {text_color}; padding: 0 0px;"
        self.markdown_editor.char_count_label.setStyleSheet(label_style)
        self.markdown_editor.selection_label.setStyleSheet(label_style)
        self.markdown_editor.theme_label.setStyleSheet(label_style)
        self.markdown_editor.encoding_label.setStyleSheet(label_style)


if __name__ == "__main__":
    setup_high_dpi()
    import PyQt5.QtWebEngineWidgets
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())

    sys.exit(app.exec_())

