import os
import urllib.parse
import tempfile
import uuid

from PyQt5.QtWidgets import (
    QTextEdit, QVBoxLayout, QFrame, QWidget, QStatusBar, QFileDialog, QSplitter, QApplication
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QCryptographicHash, QEvent
from PyQt5.QtGui import QPainterPath, QRegion, QColor

from qfluentwidgets import (
    FluentIcon, CommandBar, TransparentPushButton, CardWidget,
    ComboBox, BodyLabel, SingleDirectionScrollArea, isDarkTheme, MessageBox,
    DropDownPushButton, RoundMenu, Action
)
from qframelesswindow.webengine import FramelessWebEngineView

from models.document import MarkdownDocument
from controllers.editor_controller import EditorController
from controllers.export_controller import ExportController


class MarkdownWidget(QFrame):
    """Markdown 编辑和预览界面"""

    PREVIEW_RADIUS = 8
    PREVIEW_UPDATE_DELAY = 300

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("markdownInterface")
        
        self.document = MarkdownDocument()
        self.controller = EditorController(self.document)
        
        self.is_fullscreen = False
        self.is_editor_fullscreen = False
        
        self._preview_updating = False
        self._preview_dirty = False
        self._last_md5 = None
        self._command_bar_buttons = {}
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_interval = 30000
        self._history_menu = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._do_preview_update)

        self._setup_ui()
        self._connect_signals()
        
        QTimer.singleShot(0, self._show_welcome_page)

    def _setup_ui(self):
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self._setup_command_bar()
        self._setup_editor_preview()
        self._setup_status_bar()

    def _setup_command_bar(self):
        self.command_bar = CommandBar(self)
        
        self._add_command_button('new', FluentIcon.ADD, "新建", self.new_file)
        self._add_command_button('open', FluentIcon.FOLDER, "打开", self.open_file_dialog)
        
        self._history_menu = RoundMenu(parent=self)
        recent_button = DropDownPushButton(FluentIcon.HISTORY, "最近", self)
        recent_button.setMenu(self._history_menu)
        self.command_bar.addWidget(recent_button)
        
        self._add_command_button('save', FluentIcon.SAVE, "保存", self.save_file_dialog)
        
        self.command_bar.addSeparator()
        
        self._add_command_button('copy', FluentIcon.COPY, "复制", self.copy)
        self._add_command_button('paste', FluentIcon.PASTE, "粘贴", self.paste)
        
        self.command_bar.addSeparator()
        
        self._add_command_button('fullscreen', FluentIcon.ZOOM_IN, "全屏阅读", self.toggle_fullscreen)
        self._add_command_button('fullscreen_edit', FluentIcon.EDIT, "全屏编辑", self.toggle_editor_fullscreen)
        
        self.command_bar.addSeparator()
        
        self._setup_theme_menu()
        
        self.command_bar.addSeparator()
        
        self._add_command_button('image', FluentIcon.PHOTO, "插入图片", self.insert_image)
        
        self.command_bar.addSeparator()
        
        self._add_command_button('zoom_in', FluentIcon.ZOOM_IN, "放大", self.zoom_in)
        self._add_command_button('zoom_out', FluentIcon.ZOOM_OUT, "缩小", self.zoom_out)
        self._add_command_button('zoom_reset', FluentIcon.HOME, "重置", self.zoom_reset)
        
        self.command_bar.addSeparator()
        
        self._add_command_button('export', FluentIcon.SHARE, "导出", self.export_file)
        
        self.vBoxLayout.addWidget(self.command_bar)

    def _add_command_button(self, name, icon, text, callback):
        button = TransparentPushButton(icon, text)
        button.clicked.connect(callback)
        self.command_bar.addWidget(button)
        self._command_bar_buttons[name] = button

    def _setup_theme_menu(self):
        from models.themes import PreviewThemes
        
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

    def _setup_editor_preview(self):
        self.card_container = QWidget(self)
        self.card_container_layout = QVBoxLayout(self.card_container)
        self.card_container_layout.setContentsMargins(5, 5, 5, 5)
        self.card_container_layout.setSpacing(0)

        self.editor_card = CardWidget(self.card_container)
        self.editor_card.setStyleSheet("background-color: transparent;")
        self.editor_layout = QVBoxLayout(self.editor_card)
        self.editor_layout.setContentsMargins(1, 1, 1, 1)
        self.editor_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal, self.editor_card)
        self.splitter.setStyleSheet('''
            QSplitter { background-color: transparent; }
            QSplitter::handle { width: 0px; background-color: transparent; }
        ''')
        self.splitter.setHandleWidth(0)
        self.splitter.setEnabled(False)
        self.editor_layout.addWidget(self.splitter, 1)
        self.card_container_layout.addWidget(self.editor_card, 1)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write Markdown here...")
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.installEventFilter(self)

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

        self.vBoxLayout.addWidget(self.card_container, 1)

    def _setup_status_bar(self):
        self.status_bar = QStatusBar(self)
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
        self.status_bar.setStyleSheet(style)

        self.char_count_label = BodyLabel("字符: 0", self)
        self.selection_label = BodyLabel("选中: 0", self)
        self.encoding_label = BodyLabel("编码: UTF-8", self)
        self.theme_label = BodyLabel("预览主题: 默认", self)

        text_color = "#ffffff" if is_dark else "#333333"
        label_style = f"color: {text_color}; padding: 0 8px;"
        for label in [self.char_count_label, self.selection_label, self.theme_label, self.encoding_label]:
            label.setStyleSheet(label_style)

        self.status_bar.addWidget(self.char_count_label)
        self.status_bar.addWidget(self.selection_label)
        self.status_bar.addWidget(self.theme_label)
        self.status_bar.addPermanentWidget(self.encoding_label)

        self.vBoxLayout.addWidget(self.status_bar)

    def _connect_signals(self):
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.selectionChanged.connect(self.update_status_bar)

        self._update_command_bar_enabled()
        self._update_history_menu()
        self.update_editor_style()

    def _show_welcome_page(self):
        self.document.has_file = False
        self.editor.clear()
        self.editor.hide()
        self.preview.setHtml(self._generate_welcome_html())
        self.splitter.setSizes([0, self.splitter.width()])

    def _generate_welcome_html(self):
        is_dark = isDarkTheme()
        if is_dark:
            body_color = "rgba(255, 255, 255, 0.9)"
            h1_color = "rgba(255, 255, 255, 0.85)"
            p_color = "rgba(255, 255, 255, 0.6)"
            shortcut_bg = "rgba(255, 255, 255, 0.1)"
            shortcut_key_bg = "rgba(255, 255, 255, 0.15)"
            shortcut_key_color = "rgba(255, 255, 255, 0.9)"
        else:
            body_color = "rgba(0, 0, 0, 0.9)"
            h1_color = "rgba(0, 0, 0, 0.85)"
            p_color = "rgba(0, 0, 0, 0.6)"
            shortcut_bg = "rgba(0, 0, 0, 0.06)"
            shortcut_key_bg = "rgba(0, 0, 0, 0.1)"
            shortcut_key_color = "rgba(0, 0, 0, 0.8)"
        return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: transparent;
            color: {body_color};
        }}
        .container {{
            text-align: center;
            padding: 40px;
        }}
        .icon {{
            font-size: 72px;
            margin-bottom: 24px;
        }}
        h1 {{
            font-size: 36px;
            font-weight: 600;
            margin-bottom: 16px;
            letter-spacing: 1px;
            color: {h1_color};
        }}
        p {{
            font-size: 18px;
            margin-bottom: 32px;
            line-height: 1.6;
            color: {p_color};
        }}
        .shortcuts {{
            display: flex;
            gap: 24px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .shortcut {{
            background: {shortcut_bg};
            padding: 12px 20px;
            border-radius: 8px;
        }}
        .shortcut-key {{
            background: {shortcut_key_bg};
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 600;
            margin-right: 8px;
            color: {shortcut_key_color};
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📝</div>
        <h1>FluentMarkDown</h1>
        <p>新建或打开 Markdown 文件开始编辑</p>
        <div class="shortcuts">
            <div class="shortcut">
                <span class="shortcut-key">Ctrl+N</span>新建文件
            </div>
            <div class="shortcut">
                <span class="shortcut-key">Ctrl+O</span>打开文件
            </div>
        </div>
    </div>
</body>
</html>
'''

    def _hide_welcome_page(self):
        self._preview_updating = False
        self.editor.show()
        self.splitter.setEnabled(True)
        w = self.splitter.width()
        self.splitter.setSizes([w // 2, w // 2])

    def _update_command_bar_enabled(self):
        enabled = self.document.has_file
        for name, btn in self._command_bar_buttons.items():
            if btn and name not in ('new', 'open'):
                btn.setEnabled(enabled)
        if hasattr(self, 'theme_combo') and self.theme_combo:
            self.theme_combo.setEnabled(enabled)
        if hasattr(self, 'theme_label_cmd') and self.theme_label_cmd:
            self.theme_label_cmd.setEnabled(enabled)

    def _update_history_menu(self):
        self._history_menu.clear()
        recent_files = self.document.get_recent_files()
        if not recent_files:
            action = Action("无历史文件", self._history_menu)
            action.setEnabled(False)
            self._history_menu.addAction(action)
        else:
            for file_path in recent_files:
                file_name = os.path.basename(file_path)
                action = Action(file_name, self._history_menu)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked, fp=file_path: self.open_file(fp))
                self._history_menu.addAction(action)
            self._history_menu.addSeparator()
            clear_action = Action("清除历史", self._history_menu)
            clear_action.triggered.connect(self._clear_recent_files)
            self._history_menu.addAction(clear_action)

    def _clear_recent_files(self):
        self.document.clear_recent_files()
        self._update_history_menu()

    def _on_text_changed(self):
        if not self.document.has_file:
            return
        self.document.is_modified = True
        self.controller.set_content(self.editor.toPlainText())
        self.update_status_bar()
        
        if self._preview_updating:
            self._preview_dirty = True
            return
        self._preview_timer.stop()
        self._preview_timer.start(self.PREVIEW_UPDATE_DELAY)

    def _do_preview_update(self):
        if not self.document.has_file:
            return
        if self._preview_updating:
            self._preview_dirty = True
            return
        self.update_preview()
        while self._preview_dirty:
            self._preview_dirty = False
            self.update_preview()

    def update_preview(self):
        content = self.controller.get_content()
        current_md5 = QCryptographicHash.hash(content.encode('utf-8'), QCryptographicHash.Md5).toHex().data().decode()
        
        if current_md5 == self._last_md5 and self.controller._cached_html_template:
            self.preview.setHtml(self.controller._cached_html_template)
            return
        
        self._preview_updating = True
        
        html = self.controller.render_preview(is_dark=isDarkTheme())
        self.preview.setHtml(html)
        
        self.controller._cached_html_template = html
        self._last_md5 = current_md5
        self._preview_updating = False
        
        if self._preview_dirty:
            self._preview_dirty = False
            QTimer.singleShot(0, self._do_preview_update)
        
        self._updatePreviewRoundMask()

    def update_editor_style(self):
        is_dark = isDarkTheme()
        size = self.controller.font_size
        if is_dark:
            self.editor.setStyleSheet(f'''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #ffffff;
                font-size: {size}px;
                selection-background-color: rgba(100, 149, 237, 0.3);
            ''')
            self.editor.setCursorWidth(3)
        else:
            self.editor.setStyleSheet(f'''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #333333;
                font-size: {size}px;
                selection-background-color: rgba(100, 149, 237, 0.3);
            ''')
            self.editor.setCursorWidth(2)

    def update_status_bar(self):
        text = self.editor.toPlainText()
        self.char_count_label.setText(f"字符: {len(text)}")
        self.selection_label.setText(f"选中: {len(self.editor.textCursor().selectedText())}")
        
        from models.themes import PreviewThemes
        theme_info = PreviewThemes.get_theme_styles(self.controller.preview_theme)
        self.theme_label.setText(f"预览主题: {theme_info['name']}")

    def on_theme_changed(self, index):
        from models.themes import PreviewThemes
        themes = PreviewThemes.get_available_themes()
        if 0 <= index < len(themes):
            self.controller.set_theme(themes[index])
            self._last_md5 = None
            self.controller._cached_html_template = None
            self.update_preview()
            self.update_status_bar()

    def new_file(self):
        self.document.new()
        self.editor.clear()
        self._hide_welcome_page()
        self._update_command_bar_enabled()
        self._start_auto_save_timer()
        QTimer.singleShot(0, self._do_preview_update)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Markdown Files (*.md);;All Files (*)")
        self.open_file(file_path)

    def open_file(self, file_path):
        if not file_path:
            return
        
        if self.document.load(file_path):
            self.editor.setPlainText(self.document.content)
            self.controller.set_content(self.document.content)
            self._hide_welcome_page()
            self._update_command_bar_enabled()
            self._update_history_menu()
            self._start_auto_save_timer()
            QTimer.singleShot(0, self._do_preview_update)

    def save_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Markdown Files (*.md);;All Files (*)")
        self.save_file(file_path)

    def save_file(self, file_path=None):
        if self.document.save(file_path):
            self.document.is_modified = False
            self._start_auto_save_timer()

    def copy(self):
        self.editor.copy()

    def paste(self):
        clipboard = QApplication.clipboard()
        if clipboard.mimeData().hasImage():
            image = clipboard.image()
            if not image.isNull():
                temp_dir = tempfile.gettempdir()
                file_name = f"image_{uuid.uuid4().hex}.png"
                file_path = os.path.join(temp_dir, file_name)
                if image.save(file_path, "PNG"):
                    file_url = self._local_path_to_url(file_path)
                    self.editor.textCursor().insertText(f"![{file_name}]({file_url})")
                    self.controller.set_content(self.editor.toPlainText())
                    self.update_preview()
                    return
        self.editor.paste()

    def insert_image(self):
        if not self.document.has_file:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.svg);;All Files (*)"
        )
        if file_path:
            image_name = os.path.basename(file_path)
            file_url = self._local_path_to_url(file_path)
            self.editor.textCursor().insertText(f"![{image_name}]({file_url})")
            self.controller.set_content(self.editor.toPlainText())
            self.update_preview()

    def _local_path_to_url(self, path):
        return urllib.parse.quote(path.replace('\\', '/'), safe=':/')

    def toggle_fullscreen(self):
        if not self.document.has_file:
            return
        if not self.is_fullscreen:
            self.editor.hide()
            self.splitter.setSizes([0, self.splitter.width()])
            self.editor_layout.setContentsMargins(0, 0, 0, 0)
            self.card_container_layout.setContentsMargins(0, 0, 0, 0)
            self.is_fullscreen = True
            self.is_editor_fullscreen = False
        else:
            self.editor.show()
            w = self.splitter.width()
            self.splitter.setSizes([w // 2, w // 2])
            self.editor_layout.setContentsMargins(1, 1, 1, 1)
            self.card_container_layout.setContentsMargins(5, 5, 5, 5)
            self.is_fullscreen = False
        self._updatePreviewRoundMask()

    def toggle_editor_fullscreen(self):
        if not self.document.has_file:
            return
        if not self.is_editor_fullscreen:
            self.preview_container.hide()
            w = self.splitter.width()
            self.splitter.setSizes([w, 0])
            self.editor_layout.setContentsMargins(0, 0, 0, 0)
            self.card_container_layout.setContentsMargins(0, 0, 0, 0)
            self.scroll_area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
            self.is_editor_fullscreen = True
            self.is_fullscreen = False
        else:
            self.preview_container.show()
            w = self.splitter.width()
            self.splitter.setSizes([w // 2, w // 2])
            self.editor_layout.setContentsMargins(1, 1, 1, 1)
            self.card_container_layout.setContentsMargins(5, 5, 5, 5)
            self.scroll_area.setStyleSheet("")
            self.is_editor_fullscreen = False
        self._updatePreviewRoundMask()

    def zoom_in(self):
        if not self.document.has_file:
            return
        new_size = min(self.controller.font_size + 2, 32)
        self.controller.set_font_size(new_size)
        self.update_editor_style()
        self.update_preview()

    def zoom_out(self):
        if not self.document.has_file:
            return
        new_size = max(self.controller.font_size - 2, 8)
        self.controller.set_font_size(new_size)
        self.update_editor_style()
        self.update_preview()

    def zoom_reset(self):
        if not self.document.has_file:
            return
        self.controller.set_font_size(16)
        self.update_editor_style()
        self.update_preview()

    def export_file(self):
        if not self.document.has_file:
            return
        file_path, file_type = QFileDialog.getSaveFileName(
            self, "Export File", "",
            "PDF Files (*.pdf);;Word Files (*.docx);;HTML Files (*.html);;All Files (*)"
        )
        if not file_path:
            return

        content = self.controller.get_content()
        ext = os.path.splitext(file_path)[1].lower()
        
        if not ext:
            if 'PDF Files' in file_type:
                ext = '.pdf'
                file_path += ext
            elif 'Word Files' in file_type:
                ext = '.docx'
                file_path += ext
            elif 'HTML Files' in file_type:
                ext = '.html'
                file_path += ext

        success, message = False, ""
        if ext == '.pdf':
            success, message = ExportController.export_pdf(file_path, content)
        elif ext == '.docx':
            success, message = ExportController.export_word(file_path, content)
        elif ext == '.html':
            success, message = ExportController.export_html(file_path, content)

        self._show_info_dialog("导出成功" if success else "导出失败", message)

    def _show_info_dialog(self, title, content):
        is_dark = isDarkTheme()
        bg_color = "rgba(30, 30, 30, 0.95)" if is_dark else "rgba(255, 255, 255, 0.95)"
        w = MessageBox(title, content, self)
        w.setStyleSheet(f"QDialog {{ background-color: {bg_color}; }}")
        w.exec()

    def _show_yes_no_dialog(self, title, content):
        is_dark = isDarkTheme()
        bg_color = "rgba(30, 30, 30, 0.95)" if is_dark else "rgba(255, 255, 255, 0.95)"
        w = MessageBox(title, content, self)
        w.setStyleSheet(f"QDialog {{ background-color: {bg_color}; }}")
        return w.exec()

    def _auto_save(self):
        if self.document.has_file and self.document.is_modified and self.document.file_path:
            try:
                with open(self.document.file_path, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
                self.document.is_modified = False
            except Exception:
                pass

    def _start_auto_save_timer(self):
        self._auto_save_timer.start(self._auto_save_interval)

    def check_save_on_close(self):
        if self.document.has_file and self.document.is_modified:
            ret = self._show_yes_no_dialog(
                "文件已修改",
                f"是否保存对 {self.document.file_path or 'untitled.md'} 的更改？"
            )
            if ret:
                self.save_file()
                return True
            else:
                return True
        return False

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

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._updatePreviewRoundMask()
    
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.editor and event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True
        return False
