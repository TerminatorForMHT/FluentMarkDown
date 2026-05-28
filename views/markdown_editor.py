import os
import urllib.parse
import tempfile
import uuid

from PyQt5.QtWidgets import (
    QTextEdit, QVBoxLayout, QHBoxLayout, QFrame, QWidget, QStatusBar,
    QFileDialog, QSplitter, QApplication, QLineEdit, QPushButton
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QCryptographicHash, QEvent, pyqtSlot
from PyQt5.QtGui import QPainterPath, QRegion, QColor, QTextCursor, QTextCharFormat

from qfluentwidgets import (
    FluentIcon, CommandBar, TransparentPushButton, TransparentToolButton, CardWidget,
    ComboBox, BodyLabel, isDarkTheme, MessageBox,
    DropDownPushButton, RoundMenu, Action
)
from qframelesswindow.webengine import FramelessWebEngineView

from models.document import MarkdownDocument
from controllers.editor_controller import EditorController
from controllers.export_controller import ExportController
from views.line_number_editor import LineNumberEditor
from views.syntax_highlighter import MarkdownHighlighter


class MarkdownWidget(QFrame):
    """Markdown 编辑和预览界面"""

    PREVIEW_RADIUS = 8
    PREVIEW_UPDATE_DELAY = 300
    PREVIEW_UPDATE_DELAY_LARGE = 600  # 大文件用更长 debounce
    LARGE_FILE_THRESHOLD = 5000  # 超过此字符数视为大文件

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
        self._setup_find_replace_bar()
        self._setup_editor_preview()
        self._setup_status_bar()

    def _setup_command_bar(self):
        self.command_bar = CommandBar(self)

        # ── 文件 ──
        self._add_icon_button('new', FluentIcon.ADD, "新建 Ctrl+N", self.new_file)
        self._add_icon_button('open', FluentIcon.FOLDER, "打开 Ctrl+O", self.open_file_dialog)
        self._add_icon_button('save', FluentIcon.SAVE, "保存 Ctrl+S", self.save_file_dialog)

        self._history_menu = RoundMenu(parent=self)
        recent_button = DropDownPushButton(FluentIcon.HISTORY, "最近", self)
        recent_button.setMenu(self._history_menu)
        self.command_bar.addWidget(recent_button)

        self.command_bar.addSeparator()

        # ── 格式 ──
        format_menu = RoundMenu(parent=self)
        format_menu.addAction(Action(FluentIcon.FONT, "加粗  Ctrl+B", triggered=self._toggle_bold))
        format_menu.addAction(Action(FluentIcon.ALIGNMENT, "斜体  Ctrl+I", triggered=self._toggle_italic))
        format_menu.addAction(Action(FluentIcon.REMOVE, "删除线", triggered=self._insert_strikethrough))
        format_menu.addSeparator()
        format_menu.addAction(Action(FluentIcon.CODE, "行内代码  Ctrl+Shift+K", triggered=self._insert_code))
        format_menu.addAction(Action(FluentIcon.COMMAND_PROMPT, "代码块", triggered=self._insert_code_block))
        format_menu.addSeparator()
        format_menu.addAction(Action(FluentIcon.LINK, "链接  Ctrl+K", triggered=self._insert_link))
        format_menu.addAction(Action(FluentIcon.PHOTO, "插入图片", triggered=self.insert_image))
        format_menu.addSeparator()
        format_menu.addAction(Action(FluentIcon.FONT_SIZE, "标题", triggered=self._insert_heading))
        format_menu.addAction(Action(FluentIcon.MENU, "列表", triggered=self._insert_list_item))
        format_menu.addAction(Action(FluentIcon.CHAT, "引用", triggered=self._insert_quote))

        format_button = DropDownPushButton(FluentIcon.EDIT, "格式", self)
        format_button.setMenu(format_menu)
        self.command_bar.addWidget(format_button)

        self.command_bar.addSeparator()

        # ── 视图 ──
        self._add_icon_button('fullscreen', FluentIcon.FULL_SCREEN, "全屏阅读", self.toggle_fullscreen)
        self._add_icon_button('fullscreen_edit', FluentIcon.EDIT, "全屏编辑", self.toggle_editor_fullscreen)
        self._add_icon_button('zoom_in', FluentIcon.ZOOM_IN, "放大", self.zoom_in)
        self._add_icon_button('zoom_out', FluentIcon.ZOOM_OUT, "缩小", self.zoom_out)

        self.command_bar.addSeparator()

        # ── 主题 ──
        self._setup_theme_menu()

        self.command_bar.addSeparator()

        # ── 导出 ──
        self._add_icon_button('export', FluentIcon.SHARE, "导出", self.export_file)

        self.vBoxLayout.addWidget(self.command_bar)

    def _add_command_button(self, name, icon, text, callback):
        button = TransparentPushButton(icon, text)
        button.clicked.connect(callback)
        self.command_bar.addWidget(button)
        self._command_bar_buttons[name] = button

    def _add_icon_button(self, name, icon, tooltip, callback):
        button = TransparentToolButton(icon)
        button.setToolTip(tooltip)
        button.setFixedSize(36, 30)
        button.clicked.connect(callback)
        self.command_bar.addWidget(button)
        self._command_bar_buttons[name] = button

    def _setup_find_replace_bar(self):
        """创建 VS Code 风格的查找替换面板（右侧固定宽度浮动）"""
        self._find_regex_mode = False
        self._find_case_sensitive = False
        self._find_whole_word = False

        self.find_replace_bar = QFrame(self)
        self.find_replace_bar.setObjectName("findReplaceBar")
        self.find_replace_bar.setAttribute(Qt.WA_TranslucentBackground, True)
        self.find_replace_bar.hide()

        outer_layout = QHBoxLayout(self.find_replace_bar)
        outer_layout.setContentsMargins(0, 4, 0, 4)
        outer_layout.setSpacing(0)

        # 面板主体容器（固定宽度，左对齐）
        panel = QFrame()
        panel.setObjectName("findPanel")
        panel.setFixedWidth(420)

        # 面板后加弹性占位把它推到最左
        outer_layout.addWidget(panel)
        outer_layout.addStretch(1)
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(2, 4, 6, 4)
        panel_layout.setSpacing(0)

        # 左侧折叠箭头
        self.toggle_replace_btn = QPushButton("▶")
        self.toggle_replace_btn.setFixedSize(20, 52)
        self.toggle_replace_btn.setToolTip("切换替换")
        self.toggle_replace_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_replace_btn.clicked.connect(self._toggle_replace_row)
        panel_layout.addWidget(self.toggle_replace_btn, 0, Qt.AlignTop)

        # 右侧行容器
        rows_widget = QWidget()
        rows_layout = QVBoxLayout(rows_widget)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(4)

        # === 查找行 ===
        find_row = QHBoxLayout()
        find_row.setSpacing(2)

        # 输入框 + 内嵌模式按钮的容器
        find_input_container = QHBoxLayout()
        find_input_container.setSpacing(0)
        find_input_container.setContentsMargins(0, 0, 0, 0)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("查找")
        self.find_input.returnPressed.connect(self._find_next)
        self.find_input.textChanged.connect(self._on_find_text_changed)
        find_input_container.addWidget(self.find_input, 1)

        # 匹配模式按钮（紧贴输入框右侧）
        self.case_btn = QPushButton("Aa")
        self.case_btn.setFixedSize(26, 24)
        self.case_btn.setCheckable(True)
        self.case_btn.setToolTip("区分大小写")
        self.case_btn.setCursor(Qt.PointingHandCursor)
        self.case_btn.toggled.connect(self._on_case_toggled)
        find_input_container.addWidget(self.case_btn)

        self.word_btn = QPushButton("ab")
        self.word_btn.setFixedSize(26, 24)
        self.word_btn.setCheckable(True)
        self.word_btn.setToolTip("全字匹配")
        self.word_btn.setCursor(Qt.PointingHandCursor)
        self.word_btn.toggled.connect(self._on_word_toggled)
        find_input_container.addWidget(self.word_btn)

        self.regex_btn = QPushButton(".*")
        self.regex_btn.setFixedSize(26, 24)
        self.regex_btn.setCheckable(True)
        self.regex_btn.setToolTip("正则表达式")
        self.regex_btn.setCursor(Qt.PointingHandCursor)
        self.regex_btn.toggled.connect(self._on_regex_toggled)
        find_input_container.addWidget(self.regex_btn)

        find_row.addLayout(find_input_container, 1)

        # 匹配计数
        self.find_count_label = BodyLabel("", self)
        self.find_count_label.setFixedWidth(68)
        self.find_count_label.setAlignment(Qt.AlignCenter)
        find_row.addWidget(self.find_count_label)

        # 上一个 / 下一个 / 关闭
        self.find_prev_btn = QPushButton("↑")
        self.find_prev_btn.setFixedSize(26, 26)
        self.find_prev_btn.setToolTip("上一个")
        self.find_prev_btn.setCursor(Qt.PointingHandCursor)
        self.find_prev_btn.clicked.connect(self._find_prev)
        find_row.addWidget(self.find_prev_btn)

        self.find_next_btn = QPushButton("↓")
        self.find_next_btn.setFixedSize(26, 26)
        self.find_next_btn.setToolTip("下一个")
        self.find_next_btn.setCursor(Qt.PointingHandCursor)
        self.find_next_btn.clicked.connect(self._find_next)
        find_row.addWidget(self.find_next_btn)

        self.find_close_btn = QPushButton("×")
        self.find_close_btn.setFixedSize(26, 26)
        self.find_close_btn.setToolTip("关闭 (Esc)")
        self.find_close_btn.setCursor(Qt.PointingHandCursor)
        self.find_close_btn.clicked.connect(self._close_find_replace)
        find_row.addWidget(self.find_close_btn)

        rows_layout.addLayout(find_row)

        # === 替换行 ===
        self.replace_row_widget = QWidget()
        replace_row = QHBoxLayout(self.replace_row_widget)
        replace_row.setContentsMargins(0, 0, 0, 0)
        replace_row.setSpacing(2)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("替换")
        replace_row.addWidget(self.replace_input, 1)

        # 匹配计数位的占位
        spacer_count = QWidget()
        spacer_count.setFixedWidth(68)
        replace_row.addWidget(spacer_count)

        self.replace_btn = QPushButton("⇄")
        self.replace_btn.setFixedSize(26, 26)
        self.replace_btn.setToolTip("替换当前")
        self.replace_btn.setCursor(Qt.PointingHandCursor)
        self.replace_btn.clicked.connect(self._replace_current)
        replace_row.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("⇄*")
        self.replace_all_btn.setFixedSize(26, 26)
        self.replace_all_btn.setToolTip("全部替换")
        self.replace_all_btn.setCursor(Qt.PointingHandCursor)
        self.replace_all_btn.clicked.connect(self._replace_all)
        replace_row.addWidget(self.replace_all_btn)

        # 对齐关闭按钮
        spacer_close = QWidget()
        spacer_close.setFixedWidth(26)
        replace_row.addWidget(spacer_close)

        rows_layout.addWidget(self.replace_row_widget)
        self.replace_row_widget.hide()

        panel_layout.addWidget(rows_widget, 1)

        self._apply_find_bar_style()
        self.vBoxLayout.addWidget(self.find_replace_bar)

    def _apply_find_bar_style(self):
        is_dark = isDarkTheme()
        bg = "transparent"
        border_clr = "rgba(255,255,255,0.06)" if is_dark else "rgba(0,0,0,0.08)"
        input_bg = "rgba(60,60,60,1)" if is_dark else "rgba(255,255,255,1)"
        input_border = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.12)"
        input_color = "#cccccc" if is_dark else "#1e1e1e"
        btn_bg = "transparent"
        btn_hover = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.06)"
        btn_color = "#cccccc" if is_dark else "#424242"
        accent = "#0078d4"
        accent_bg = "rgba(0,120,212,0.15)" if is_dark else "rgba(0,120,212,0.12)"
        count_color = "rgba(255,255,255,0.45)" if is_dark else "rgba(0,0,0,0.4)"
        font = "'Segoe UI Variable','Segoe UI',-apple-system,'PingFang SC','Microsoft YaHei',sans-serif"

        self.find_replace_bar.setStyleSheet(f"""
            QFrame#findReplaceBar {{
                background: {bg};
                border-bottom: 1px solid {border_clr};
                border: none;
            }}
        """)
        input_style = f"""
            QLineEdit {{
                background: {input_bg}; border: 1px solid {input_border};
                border-radius: 3px; padding: 3px 8px;
                font-family: {font}; font-size: 13px; color: {input_color};
            }}
            QLineEdit:focus {{ border-color: {accent}; }}
        """
        self.find_input.setStyleSheet(input_style)
        self.replace_input.setStyleSheet(input_style)

        self.find_replace_bar.findChild(QFrame, "findPanel").setStyleSheet(f"""
            QFrame#findPanel {{
                background: transparent;
                border: none;
            }}
        """)

        small_btn_style = f"""
            QPushButton {{
                background: {btn_bg}; color: {btn_color};
                border: none; border-radius: 3px;
                font-family: {font}; font-size: 14px; font-weight: 500;
            }}
            QPushButton:hover {{ background: {btn_hover}; }}
            QPushButton:pressed {{ background: {btn_hover}; }}
        """
        for btn in [self.find_prev_btn, self.find_next_btn, self.find_close_btn,
                     self.replace_btn, self.replace_all_btn, self.toggle_replace_btn]:
            btn.setStyleSheet(small_btn_style)

        # 模式按钮（Aa, ab, .*）共用选中态样式
        mode_btn_style = f"""
            QPushButton {{
                background: {btn_bg}; color: {btn_color};
                border: 1px solid transparent; border-radius: 3px;
                font-family: 'Consolas','SF Mono','Menlo',monospace;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {btn_hover}; }}
            QPushButton:checked {{
                background: {accent_bg}; color: {accent};
                border-color: {accent};
            }}
        """
        for btn in [self.case_btn, self.word_btn, self.regex_btn]:
            btn.setStyleSheet(mode_btn_style)
        self.find_count_label.setStyleSheet(
            f"color: {count_color}; font-size: 12px; background: transparent; border: none;"
        )

    def _toggle_replace_row(self):
        visible = self.replace_row_widget.isVisible()
        self.replace_row_widget.setVisible(not visible)
        self.toggle_replace_btn.setText("▼" if not visible else "▶")

    def _on_case_toggled(self, checked):
        self._find_case_sensitive = checked
        self._update_find_count()

    def _on_word_toggled(self, checked):
        self._find_whole_word = checked
        self._update_find_count()

    def _on_regex_toggled(self, checked):
        self._find_regex_mode = checked
        self._update_find_count()

    def _on_find_text_changed(self):
        self._update_find_count()

    def toggle_find(self):
        """Ctrl+F：打开/聚焦查找面板"""
        if not self.document.has_file:
            return
        if self.find_replace_bar.isVisible():
            self.find_input.setFocus()
            self.find_input.selectAll()
            return
        self.find_replace_bar.show()
        self._apply_find_bar_style()
        self.find_input.setFocus()
        selected = self.editor.textCursor().selectedText()
        if selected:
            self.find_input.setText(selected)
        self.find_input.selectAll()
        self._update_find_count()

    def _close_find_replace(self):
        self.find_replace_bar.hide()
        self._clear_find_highlights()
        self.editor.setFocus()

    def _get_find_matches(self):
        """获取所有匹配位置（支持大小写、全字、正则）"""
        import re
        keyword = self.find_input.text()
        if not keyword:
            return []
        text = self.editor.toPlainText()
        flags = 0 if self._find_case_sensitive else re.IGNORECASE

        if self._find_regex_mode:
            try:
                pattern = keyword
                if self._find_whole_word:
                    pattern = r'\b' + pattern + r'\b'
                return [(m.start(), m.end()) for m in re.finditer(pattern, text, flags)]
            except re.error:
                return []
        else:
            pattern = re.escape(keyword)
            if self._find_whole_word:
                pattern = r'\b' + pattern + r'\b'
            try:
                return [(m.start(), m.end()) for m in re.finditer(pattern, text, flags)]
            except re.error:
                return []

    def _find_next(self):
        matches = self._get_find_matches()
        if not matches:
            return
        cursor = self.editor.textCursor()
        current_pos = cursor.position()
        for start, end in matches:
            if start >= current_pos:
                self._select_range(start, end)
                self._update_find_count()
                return
        self._select_range(matches[0][0], matches[0][1])
        self._update_find_count()

    def _find_prev(self):
        matches = self._get_find_matches()
        if not matches:
            return
        cursor = self.editor.textCursor()
        current_pos = cursor.selectionStart()
        for start, end in reversed(matches):
            if end <= current_pos:
                self._select_range(start, end)
                self._update_find_count()
                return
        self._select_range(matches[-1][0], matches[-1][1])
        self._update_find_count()

    def _select_range(self, start, end):
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    def _replace_current(self):
        import re
        keyword = self.find_input.text()
        replacement = self.replace_input.text()
        if not keyword:
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            is_match = False
            if self._find_regex_mode:
                try:
                    is_match = bool(re.fullmatch(keyword, selected))
                except re.error:
                    pass
            else:
                is_match = selected == keyword
            if is_match:
                if self._find_regex_mode:
                    try:
                        new_text = re.sub(keyword, replacement, selected)
                    except re.error:
                        new_text = replacement
                else:
                    new_text = replacement
                cursor.insertText(new_text)
                self.editor.setTextCursor(cursor)
        self._find_next()
        self._update_find_count()

    def _replace_all(self):
        import re
        keyword = self.find_input.text()
        replacement = self.replace_input.text()
        if not keyword:
            return
        text = self.editor.toPlainText()
        if self._find_regex_mode:
            try:
                new_text, count = re.subn(keyword, replacement, text)
            except re.error:
                self.find_count_label.setText("正则错误")
                return
        else:
            count = text.count(keyword)
            new_text = text.replace(keyword, replacement)
        if count == 0:
            return
        cursor = self.editor.textCursor()
        pos = cursor.position()
        self.editor.setPlainText(new_text)
        cursor = self.editor.textCursor()
        cursor.setPosition(min(pos, len(new_text)))
        self.editor.setTextCursor(cursor)
        self.find_count_label.setText(f"已替换 {count} 个")

    def _update_find_count(self):
        keyword = self.find_input.text()
        if not keyword:
            self.find_count_label.setText("")
            return
        matches = self._get_find_matches()
        count = len(matches)
        if self._find_regex_mode and count == 0:
            import re
            try:
                re.compile(keyword)
                self.find_count_label.setText("无匹配")
            except re.error:
                self.find_count_label.setText("正则无效")
        elif count == 0:
            self.find_count_label.setText("无匹配")
        else:
            self.find_count_label.setText(f"{count} 个匹配")

    def _clear_find_highlights(self):
        cursor = self.editor.textCursor()
        cursor.clearSelection()
        self.editor.setTextCursor(cursor)

    # ─── Markdown 格式化快捷操作 ───

    def _wrap_selection(self, wrapper):
        """用 wrapper 包裹选中文本，若已包裹则移除"""
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        wrap_len = len(wrapper)

        if selected.startswith(wrapper) and selected.endswith(wrapper) and len(selected) > wrap_len * 2:
            cursor.insertText(selected[wrap_len:-wrap_len])
        elif selected:
            cursor.insertText(f"{wrapper}{selected}{wrapper}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{wrapper}{wrapper}")
            cursor.setPosition(pos + wrap_len)
            self.editor.setTextCursor(cursor)

    def _toggle_bold(self):
        if not self.document.has_file:
            return
        self._wrap_selection("**")

    def _toggle_italic(self):
        if not self.document.has_file:
            return
        self._wrap_selection("*")

    def _insert_link(self):
        if not self.document.has_file:
            return
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        if selected:
            cursor.insertText(f"[{selected}](url)")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 3)
            self.editor.setTextCursor(cursor)
        else:
            pos = cursor.position()
            cursor.insertText("[text](url)")
            cursor.setPosition(pos + 1)
            cursor.setPosition(pos + 5, QTextCursor.KeepAnchor)
            self.editor.setTextCursor(cursor)

    def _insert_code(self):
        if not self.document.has_file:
            return
        self._wrap_selection("`")

    def _insert_heading(self):
        if not self.document.has_file:
            return
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        block_text = cursor.block().text()
        import re
        heading_match = re.match(r'^(#{1,6})\s', block_text)
        if heading_match:
            level = len(heading_match.group(1))
            if level < 6:
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, level)
                cursor.insertText("#" * (level + 1))
            else:
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, level + 1)
                cursor.removeSelectedText()
        else:
            cursor.insertText("# ")
        self.editor.setTextCursor(cursor)

    def _insert_list_item(self):
        if not self.document.has_file:
            return
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        block_text = cursor.block().text()
        if block_text.lstrip().startswith("- "):
            pass
        else:
            cursor.insertText("- ")
        self.editor.setTextCursor(cursor)

    def _insert_quote(self):
        if not self.document.has_file:
            return
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        block_text = cursor.block().text()
        if block_text.startswith("> "):
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 2)
            cursor.removeSelectedText()
        else:
            cursor.insertText("> ")
        self.editor.setTextCursor(cursor)

    def _insert_code_block(self):
        if not self.document.has_file:
            return
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        if selected:
            cursor.insertText(f"```\n{selected}\n```")
        else:
            pos = cursor.position()
            cursor.insertText("```\n\n```")
            cursor.setPosition(pos + 4)
            self.editor.setTextCursor(cursor)

    def _insert_strikethrough(self):
        if not self.document.has_file:
            return
        self._wrap_selection("~~")

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

        self.editor = LineNumberEditor()
        self.editor.setPlaceholderText("Write Markdown here...")
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.installEventFilter(self)

        # 语法高亮器
        is_dark = isDarkTheme()
        self._highlighter = MarkdownHighlighter(self.editor.document(), is_dark)
        self.editor.set_dark_mode(is_dark)

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

        # 自定义 Page：外部链接用系统浏览器打开
        from PyQt5.QtWebEngineWidgets import QWebEnginePage
        from PyQt5.QtGui import QDesktopServices

        class ExternalLinkPage(QWebEnginePage):
            def acceptNavigationRequest(self, url, nav_type, is_main_frame):
                if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
                    QDesktopServices.openUrl(url)
                    return False
                return super().acceptNavigationRequest(url, nav_type, is_main_frame)

        custom_page = ExternalLinkPage(self.preview)
        self.preview.setPage(custom_page)

        try:
            self.preview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        except Exception:
            pass
        
        # 启用本地文件访问和图片加载
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings
        settings = self.preview.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

        self.preview_layout.addWidget(self.preview)

        self.splitter.addWidget(self.editor)
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

    def _setup_shortcuts(self):
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence

        QShortcut(QKeySequence("Ctrl+N"), self, self.new_file)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_file_dialog)
        QShortcut(QKeySequence("Ctrl+S"), self, self._shortcut_save)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self, self.toggle_editor_fullscreen)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+F"), self, self.toggle_find)
        QShortcut(QKeySequence("Escape"), self, self._close_find_replace)
        QShortcut(QKeySequence("Ctrl+B"), self, self._toggle_bold)
        QShortcut(QKeySequence("Ctrl+I"), self, self._toggle_italic)
        QShortcut(QKeySequence("Ctrl+K"), self, self._insert_link)
        QShortcut(QKeySequence("Ctrl+Shift+K"), self, self._insert_code)

    def _shortcut_save(self):
        """Ctrl+S：有路径直接保存，无路径弹出另存为"""
        if not self.document.has_file:
            return
        if self.document.file_path:
            self.save_file()
        else:
            self.save_file_dialog()

    def _connect_signals(self):
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.selectionChanged.connect(self.update_status_bar)
        self.editor.verticalScrollBar().valueChanged.connect(self._sync_preview_scroll)

        self._setup_shortcuts()
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
        content = self.editor.toPlainText()
        self.controller.set_content(content)
        self.update_status_bar()

        if self._preview_updating:
            self._preview_dirty = True
            return
        delay = self.PREVIEW_UPDATE_DELAY_LARGE if len(content) > self.LARGE_FILE_THRESHOLD else self.PREVIEW_UPDATE_DELAY
        self._preview_timer.stop()
        self._preview_timer.start(delay)

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
        content_bytes = content.encode('utf-8')
        current_md5 = QCryptographicHash.hash(content_bytes, QCryptographicHash.Md5).toHex().data().decode()

        if current_md5 == self._last_md5:
            return

        self._preview_updating = True
        is_dark = isDarkTheme()

        # 增量更新：如果页面已加载且只是内容变化，用 JS 替换 DOM 而非重载整个页面
        if self._last_md5 is not None and hasattr(self, '_preview_loaded') and self._preview_loaded:
            import markdown
            html_body = markdown.markdown(content, extensions=['fenced_code', 'extra', 'tables'])
            html_body = self.controller._convert_image_paths(html_body)
            # 转义 JS 字符串中的特殊字符
            escaped = html_body.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
            js = f'''
                (function() {{
                    var el = document.querySelector(".scroll");
                    if (el) {{
                        var scrollRatio = el.scrollTop / Math.max(1, el.scrollHeight - el.clientHeight);
                        el.innerHTML = `{escaped}`;
                        document.querySelectorAll("pre code").forEach(function(block) {{
                            if (!block.classList.contains("language-mermaid")) {{
                                try {{ hljs.highlightElement(block); }} catch(e) {{}}
                            }}
                        }});
                        var mermaidBlocks = document.querySelectorAll("pre code.language-mermaid");
                        if (mermaidBlocks.length > 0) {{
                            try {{
                                mermaidBlocks.forEach(function(block, idx) {{
                                    var pre = block.parentElement;
                                    var container = document.createElement("div");
                                    container.className = "mermaid";
                                    container.id = "mermaid-" + idx;
                                    container.textContent = block.textContent;
                                    pre.replaceWith(container);
                                }});
                                mermaid.run();
                            }} catch(e) {{}}
                        }}
                        document.querySelectorAll("pre").forEach(function(pre) {{
                            if (pre.querySelector(".copy-button")) return;
                            var btn = document.createElement("button");
                            btn.className = "copy-button";
                            btn.textContent = "复制";
                            pre.appendChild(btn);
                            btn.addEventListener("click", function() {{
                                var code = pre.querySelector("code");
                                if (!code) return;
                                var ta = document.createElement("textarea");
                                ta.value = code.textContent;
                                ta.style.cssText = "position:fixed;left:-9999px";
                                document.body.appendChild(ta);
                                ta.select();
                                try {{ document.execCommand("copy"); btn.textContent = "已复制"; btn.classList.add("copied"); }} catch(e) {{ btn.textContent = "失败"; }}
                                document.body.removeChild(ta);
                                setTimeout(function() {{ btn.textContent = "复制"; btn.classList.remove("copied"); }}, 2000);
                            }});
                        }});
                        var maxScroll = el.scrollHeight - el.clientHeight;
                        el.scrollTop = maxScroll * scrollRatio;
                    }}
                }})();
            '''
            self.preview.page().runJavaScript(js)
        else:
            html = self.controller.render_preview(is_dark=is_dark)
            from PyQt5.QtCore import QUrl
            if self.document.file_path:
                base_url = QUrl.fromLocalFile(os.path.dirname(self.document.file_path) + '/')
            else:
                base_url = QUrl.fromLocalFile(os.getcwd() + '/')
            self.preview.setHtml(html, base_url)
            self._preview_loaded = True

        self.controller._cached_html_template = None
        self._last_md5 = current_md5
        self._preview_updating = False

        if self._preview_dirty:
            self._preview_dirty = False
            QTimer.singleShot(0, self._do_preview_update)

        self._updatePreviewRoundMask()

    def update_editor_style(self):
        is_dark = isDarkTheme()
        size = self.controller.font_size
        text_color = "#ffffff" if is_dark else "#333333"
        cursor_width = 3 if is_dark else 2

        if is_dark:
            sb_track = "#3d3d3d"
            sb_thumb = "#5d5d5d"
            sb_hover = "#7d7d7d"
        else:
            sb_track = "#f1f1f1"
            sb_thumb = "#c1c1c1"
            sb_hover = "#a8a8a8"

        self.editor.setStyleSheet(f'''
            QPlainTextEdit {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: {text_color};
                font-size: {size}px;
                selection-background-color: rgba(100, 149, 237, 0.3);
            }}
        ''')
        self.editor.verticalScrollBar().setStyleSheet(f'''
            QScrollBar:vertical {{
                background: {sb_track};
                width: 8px;
                border: none;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {sb_thumb};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {sb_hover};
            }}
            QScrollBar::add-line:vertical {{
                height: 0px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }}
            QScrollBar::sub-line:vertical {{
                height: 0px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        ''')
        self.editor.setCursorWidth(cursor_width)

        # 同步暗色模式到行号和高亮器
        self.editor.set_dark_mode(is_dark)
        if hasattr(self, '_highlighter'):
            self._highlighter.set_dark_mode(is_dark)

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
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
        self.document.is_modified = False
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
            self.editor.blockSignals(True)
            self.editor.setPlainText(self.document.content)
            self.editor.blockSignals(False)
            self.document.is_modified = False
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
        # 添加 file:// 协议前缀，确保 WebEngineView 能正确加载本地图片
        from PyQt5.QtCore import QUrl
        return QUrl.fromLocalFile(path).toString()

    def _restore_split_view(self):
        """恢复到左右分栏的默认状态"""
        self.editor.show()
        self.preview_container.show()
        w = self.splitter.width()
        self.splitter.setSizes([w // 2, w // 2])
        self.editor_layout.setContentsMargins(1, 1, 1, 1)
        self.card_container_layout.setContentsMargins(5, 5, 5, 5)
        self.is_fullscreen = False
        self.is_editor_fullscreen = False

    def toggle_fullscreen(self):
        if not self.document.has_file:
            return
        if not self.is_fullscreen:
            # 先恢复所有控件可见性，再进入全屏阅读
            self.preview_container.show()
            self.editor.hide()
            self.splitter.setSizes([0, self.splitter.width()])
            self.editor_layout.setContentsMargins(0, 0, 0, 0)
            self.card_container_layout.setContentsMargins(0, 0, 0, 0)
            self.is_fullscreen = True
            self.is_editor_fullscreen = False
        else:
            self._restore_split_view()
        self._updatePreviewRoundMask()

    def toggle_editor_fullscreen(self):
        if not self.document.has_file:
            return
        if not self.is_editor_fullscreen:
            # 先恢复所有控件可见性，再进入全屏编辑
            self.editor.show()
            self.preview_container.hide()
            w = self.splitter.width()
            self.splitter.setSizes([w, 0])
            self.editor_layout.setContentsMargins(0, 0, 0, 0)
            self.card_container_layout.setContentsMargins(0, 0, 0, 0)
            self.is_editor_fullscreen = True
            self.is_fullscreen = False
        else:
            self._restore_split_view()
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
        print(f"DEBUG - 导出内容长度: {len(content)}")
        print(f"DEBUG - 内容前200字符: {content[:200] if content else '空'}")
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
            self._export_pdf_via_webengine(file_path)
            return
        elif ext == '.docx':
            success, message = ExportController.export_word(file_path, content)
        elif ext == '.html':
            success, message = ExportController.export_html(file_path, content)

        self._show_info_dialog("导出成功" if success else "导出失败", message)

    def _export_pdf_via_webengine(self, file_path):
        """通过 WebEngineView 导出 PDF，完美支持中文和样式"""
        from PyQt5.QtCore import QMarginsF, QUrl
        from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
        from PyQt5.QtGui import QPageLayout, QPageSize

        html = self.controller.render_preview(is_dark=False)
        # 去掉容器高度限制和 overflow 裁剪，让内容自然展开
        html = html.replace('height: 100%;', 'height: auto;')
        html = html.replace('overflow: hidden;', 'overflow: visible;')
        html = html.replace('overflow-y: auto;', 'overflow-y: visible;')
        temp_view = QWebEngineView()
        if self.document.file_path:
            base_url = QUrl.fromLocalFile(os.path.dirname(self.document.file_path) + '/')
        else:
            base_url = QUrl.fromLocalFile(os.getcwd() + '/')

        def on_load_finished(ok):
            if not ok:
                self._show_info_dialog("导出失败", "页面加载失败")
                temp_view.deleteLater()
                return
            page_layout = QPageLayout(
                QPageSize(QPageSize.A4),
                QPageLayout.Portrait,
                QMarginsF(15, 15, 15, 15)
            )
            temp_view.page().printToPdf(
                lambda data: self._on_pdf_exported(data, file_path, temp_view),
                page_layout
            )

        temp_view.loadFinished.connect(on_load_finished)
        temp_view.setHtml(html, base_url)

    def _create_fluent_dialog(self, width, height):
        """创建 Fluent Design 风格弹窗基础框架"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGraphicsDropShadowEffect
        from PyQt5.QtCore import Qt, QPoint

        is_dark = isDarkTheme()

        class DraggableDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self._drag_pos = None

            def mousePressEvent(self, event):
                if event.button() == Qt.LeftButton:
                    self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    event.accept()

            def mouseMoveEvent(self, event):
                if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
                    self.move(event.globalPos() - self._drag_pos)
                    event.accept()

            def mouseReleaseEvent(self, event):
                self._drag_pos = None

        dialog = DraggableDialog(self.window())
        dialog.setWindowTitle("")
        dialog.setFixedSize(width + 40, height + 40)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)

        card = QWidget(dialog)
        card.setGeometry(20, 10, width, height)
        card.setObjectName("fluentDialogCard")

        bg_color = "rgba(44, 44, 44, 0.96)" if is_dark else "rgba(255, 255, 255, 0.96)"
        border_color = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        top_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(255, 255, 255, 0.8)"

        card.setStyleSheet(f"""
            QWidget#fluentDialogCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-top: 1px solid {top_border};
                border-radius: 8px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 1)
        shadow_color = QColor(0, 0, 0, 70 if is_dark else 35)
        shadow.setColor(shadow_color)
        card.setGraphicsEffect(shadow)

        return dialog, card, is_dark

    def _fluent_colors(self, is_dark):
        """获取 Fluent Design 配色"""
        return {
            "title": "#ffffff" if is_dark else "#1a1a1a",
            "body": "rgba(255,255,255,0.7)" if is_dark else "rgba(0,0,0,0.6)",
            "accent": "#60CDFF" if is_dark else "#005FB8",
            "accent_hover": "#4DB8E8" if is_dark else "#004C95",
            "accent_pressed": "#3AAAD4" if is_dark else "#003A75",
            "subtle_bg": "rgba(255,255,255,0.06)" if is_dark else "rgba(0,0,0,0.03)",
            "subtle_hover": "rgba(255,255,255,0.09)" if is_dark else "rgba(0,0,0,0.05)",
            "subtle_pressed": "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.03)",
            "subtle_border": "rgba(255,255,255,0.07)" if is_dark else "rgba(0,0,0,0.06)",
            "divider": "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.06)",
        }

    def _on_pdf_exported(self, pdf_data, file_path, temp_view):
        """PDF 导出回调"""
        try:
            with open(file_path, 'wb') as f:
                f.write(pdf_data.data())
            self._show_info_dialog("导出成功", f"PDF 已成功导出到:\n{file_path}")
        except Exception as e:
            self._show_info_dialog("导出失败", f"写入 PDF 文件时出错:\n{str(e)}")
        finally:
            temp_view.deleteLater()

    def _show_info_dialog(self, title, content):
        from PyQt5.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        from PyQt5.QtCore import Qt

        dialog, card, is_dark = self._create_fluent_dialog(420, 200)
        colors = self._fluent_colors(is_dark)
        font_family = "'Segoe UI Variable', 'Segoe UI', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif"

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {colors['title']}; font-family: {font_family}; font-size: 16px; font-weight: 600; background: transparent; border: none;")
        layout.addWidget(title_label)
        layout.addSpacing(8)

        # 内容
        content_label = QLabel(content)
        content_label.setStyleSheet(f"color: {colors['body']}; font-family: {font_family}; font-size: 13px; line-height: 20px; background: transparent; border: none;")
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        layout.addStretch(1)

        # 分割线
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {colors['divider']}; border: none;")
        layout.addWidget(divider)
        layout.addSpacing(16)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.setFixedSize(120, 32)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['accent']};
                color: {"#000000" if is_dark else "#ffffff"};
                font-family: {font_family};
                font-size: 13px; font-weight: 600;
                border: none; border-radius: 4px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ background-color: {colors['accent_hover']}; }}
            QPushButton:pressed {{ background-color: {colors['accent_pressed']}; }}
        """)
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def _show_yes_no_dialog(self, title, content):
        from PyQt5.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QDialog
        from PyQt5.QtCore import Qt

        dialog, card, is_dark = self._create_fluent_dialog(460, 210)
        colors = self._fluent_colors(is_dark)
        font_family = "'Segoe UI Variable', 'Segoe UI', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif"

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {colors['title']}; font-family: {font_family}; font-size: 16px; font-weight: 600; background: transparent; border: none;")
        layout.addWidget(title_label)
        layout.addSpacing(8)

        # 内容
        content_label = QLabel(content)
        content_label.setStyleSheet(f"color: {colors['body']}; font-family: {font_family}; font-size: 13px; line-height: 20px; background: transparent; border: none;")
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        layout.addStretch(1)

        # 分割线
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {colors['divider']}; border: none;")
        layout.addWidget(divider)
        layout.addSpacing(16)

        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedSize(120, 32)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['accent']};
                color: {"#000000" if is_dark else "#ffffff"};
                font-family: {font_family};
                font-size: 13px; font-weight: 600;
                border: none; border-radius: 4px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ background-color: {colors['accent_hover']}; }}
            QPushButton:pressed {{ background-color: {colors['accent_pressed']}; }}
        """)
        save_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(save_btn)

        discard_btn = QPushButton("不保存")
        discard_btn.setFixedSize(120, 32)
        discard_btn.setCursor(Qt.PointingHandCursor)
        discard_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['subtle_bg']};
                color: {colors['title']};
                font-family: {font_family};
                font-size: 13px; font-weight: 400;
                border: 1px solid {colors['subtle_border']};
                border-radius: 4px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ background-color: {colors['subtle_hover']}; }}
            QPushButton:pressed {{ background-color: {colors['subtle_pressed']}; }}
        """)
        discard_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(discard_btn)

        layout.addLayout(button_layout)

        result = dialog.exec()
        return result == QDialog.Accepted

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
        if not self.document.has_file:
            return True
        if self.document.is_modified:
            ret = self._show_yes_no_dialog(
                "文件已修改",
                f"是否保存对 {self.document.file_path or 'untitled.md'} 的更改？"
            )
            if ret:
                if self.document.file_path:
                    self.save_file()
                else:
                    self.save_file_dialog()
        return True

    def _sync_preview_scroll(self):
        """编辑器滚动时同步预览滚动位置"""
        scrollbar = self.editor.verticalScrollBar()
        max_val = scrollbar.maximum()
        if max_val <= 0:
            return
        ratio = scrollbar.value() / max_val
        js = f"syncScrollTo({ratio});"
        try:
            self.preview.page().runJavaScript(js)
        except Exception:
            pass

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
