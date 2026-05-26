"""
主窗口视图：Fluent 风格的薄壳。

只负责：
- 搭好 CommandBar / TabContainer / StatusBar 的骨架
- 启用 Mica + 系统主题监听
- 把交互信号转发给对应的 Controller

任何文件 IO、导出、tab 增删都不在这里实现。
"""
import os
import sys
import tempfile
import uuid
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QShortcut,
    QStatusBar,
    QVBoxLayout,
)

from qfluentwidgets import (
    BodyLabel,
    CommandBar,
    ComboBox,
    Action,
    FluentIcon,
    FluentWidget,
    MessageBox,
    RoundMenu,
    SystemThemeListener,
    Theme,
    isDarkTheme,
    setTheme,
)
from qfluentwidgets.common.config import qconfig

from controllers.document_controller import DocumentController
from controllers.export_controller import ExportController
from controllers.tab_controller import TabController
from controllers.theme_controller import ThemeController
from models.document import Document
from models.history import SettingsManager
from views.tab_container import TabContainer


def _resolve_icon_path() -> Optional[str]:
    """按平台返回应用图标路径，兼容开发环境与 PyInstaller 打包后。

    - macOS  : AppIcon.icns（squircle 圆角，遵守 Big Sur+ 系统图标规范）
    - Windows: mark.ico    （不裁切，遵守 Fluent Design 规范）
    - 其它    : 按 ico → icns 顺序兜底
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_dir = os.path.join(base, "resources")

    if sys.platform == "darwin":
        candidates = ("AppIcon.icns", "mark.ico")
    elif sys.platform.startswith("win"):
        candidates = ("mark.ico", "AppIcon.icns")
    else:
        candidates = ("mark.ico", "AppIcon.icns")

    for name in candidates:
        path = os.path.join(resources_dir, name)
        if os.path.exists(path):
            return path
    return None


class MainWindow(FluentWidget):
    """应用主窗口"""

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        setTheme(Theme.AUTO)
        self.theme_listener = SystemThemeListener(self)

        # Controllers
        self.document_controller = DocumentController(self)
        self.export_controller = ExportController(self)
        self.theme_controller = ThemeController("light", self)
        self.settings = SettingsManager()

        # 布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.main_layout.setSpacing(0)

        # 顶部命令栏
        self.command_bar = CommandBar(self)
        self.command_bar.setAttribute(Qt.WA_TranslucentBackground, True)
        self.command_bar.setStyleSheet("CommandBar { background: transparent; }")
        self.main_layout.addWidget(self.command_bar)

        # 多 tab 容器
        self.tab_container = TabContainer(self)
        self.main_layout.addWidget(self.tab_container, 1)

        # Tab 控制器
        self.tab_controller = TabController(
            tab_bar=self.tab_container.tab_bar,
            stack=self.tab_container.stack,
            document_controller=self.document_controller,
            host_widget=self,
            parent=self,
        )

        # 状态栏
        self.status_bar = QStatusBar(self)
        self._build_status_bar()
        self.main_layout.addWidget(self.status_bar)

        # 命令栏（依赖 tab_controller / theme_controller 已就绪）
        self._build_command_bar()

        # 跨 tab 同步：主题 + 状态栏（必须在 restore_session 之前连接，否则恢复时按钮不会启用）
        self.theme_controller.previewThemeChanged.connect(self._on_preview_theme_changed)
        self.tab_controller.currentDocumentChanged.connect(self._on_current_document_changed)

        # 恢复上次退出时未关闭的 tab
        self.tab_controller.restore_session()

        # 窗口
        self.resize(1100, 720)
        self.setWindowTitle("Fluent Markdown")
        icon_path = _resolve_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        # 主题切换
        qconfig.themeChanged.connect(self._on_system_theme_changed)
        self.theme_listener.start()

        # 自动保存定时器（30 秒间隔）
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setInterval(30_000)
        self._auto_save_timer.timeout.connect(self._do_auto_save)
        if self.settings.get("auto_save", False):
            self._auto_save_timer.start()

        # 首屏预热：窗口显示后，空闲时让 WebEngine 预热渲染管线，
        # 避免用户第一次输入 / 第一次切 tab 卡顿
        QTimer.singleShot(0, self._warmup_web_engine)

    def _warmup_web_engine(self) -> None:
        editor = self.tab_controller.current_editor()
        if editor is not None:
            editor.update_preview()

    # ---------------- 命令栏 ----------------
    def _build_command_bar(self) -> None:
        cb = self.command_bar

        cb.addAction(Action(FluentIcon.ADD, "新建", triggered=self.tab_controller.new_document))
        cb.addAction(Action(FluentIcon.FOLDER, "打开", triggered=self.tab_controller.open_document))
        self._recent_action = Action(FluentIcon.HISTORY, "最近文件", triggered=self._do_show_recent_menu)
        cb.addAction(self._recent_action)
        self._save_action = Action(FluentIcon.SAVE, "保存", triggered=self.tab_controller.save_current)
        self._save_as_action = Action(FluentIcon.SAVE_AS, "另存为", triggered=self.tab_controller.save_current_as)
        cb.addAction(self._save_action)
        cb.addAction(self._save_as_action)
        cb.addSeparator()

        self._copy_action = Action(FluentIcon.COPY, "复制", triggered=self._do_copy)
        self._paste_action = Action(FluentIcon.PASTE, "粘贴", triggered=self._do_paste)
        cb.addAction(self._copy_action)
        cb.addAction(self._paste_action)
        cb.addSeparator()

        self._insert_image_action = Action(FluentIcon.PHOTO, "插入图片", triggered=self._do_insert_image)
        self._fullscreen_action = Action(FluentIcon.VIEW, "全屏阅读", triggered=self._do_toggle_fullscreen)
        cb.addAction(self._insert_image_action)
        cb.addAction(self._fullscreen_action)
        cb.addSeparator()

        self._zoom_in_action = Action(FluentIcon.ZOOM_IN, "放大", triggered=self._do_zoom_in)
        self._zoom_out_action = Action(FluentIcon.ZOOM_OUT, "缩小", triggered=self._do_zoom_out)
        self._zoom_reset_action = Action(FluentIcon.SYNC, "重置", triggered=self._do_zoom_reset)
        cb.addAction(self._zoom_in_action)
        cb.addAction(self._zoom_out_action)
        cb.addAction(self._zoom_reset_action)
        cb.addSeparator()

        self._theme_label = BodyLabel("预览主题:")
        cb.addWidget(self._theme_label)
        self.theme_combo = ComboBox()
        themes = self.theme_controller.available_themes()
        for key in themes:
            self.theme_combo.addItem(self.theme_controller.theme_display_name(key), userData=key)
        current = self.theme_controller.preview_theme
        if current in themes:
            self.theme_combo.setCurrentIndex(themes.index(current))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        cb.addWidget(self.theme_combo)
        cb.addSeparator()

        self._export_action = Action(FluentIcon.SHARE, "导出", triggered=self._do_export)
        cb.addAction(self._export_action)
        cb.addSeparator()

        auto_save_on = self.settings.get("auto_save", False)
        self._auto_save_action = Action(
            FluentIcon.UPDATE,
            "自动保存: 开" if auto_save_on else "自动保存: 关",
            triggered=self._do_toggle_auto_save,
        )
        self._auto_save_action.setCheckable(True)
        self._auto_save_action.setChecked(auto_save_on)
        cb.addAction(self._auto_save_action)

        # 收集需要有文档才生效的 action
        self._editor_actions = [
            self._save_action, self._save_as_action,
            self._copy_action, self._paste_action,
            self._insert_image_action, self._fullscreen_action,
            self._zoom_in_action, self._zoom_out_action, self._zoom_reset_action,
            self._export_action,
        ]
        # 初始状态：无文档，禁用
        self._update_editor_actions_enabled(False)

        # 快捷键
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        """注册全局快捷键。"""
        shortcuts = {
            "Ctrl+N": self.tab_controller.new_document,
            "Ctrl+O": self.tab_controller.open_document,
            "Ctrl+S": self.tab_controller.save_current,
            "Ctrl+Shift+S": self.tab_controller.save_current_as,
            "Ctrl+W": self._do_close_current_tab,
            "F11": self._do_toggle_fullscreen,
            "Ctrl+=": self._do_zoom_in,
            "Ctrl+-": self._do_zoom_out,
            "Ctrl+0": self._do_zoom_reset,
            "Ctrl+E": self._do_export,
            "Ctrl+F": self._do_show_find,
            "Ctrl+H": self._do_show_find_replace,
            "Esc": self._do_hide_find,
        }
        for key, slot in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(slot)

    def _do_show_find(self) -> None:
        """显示查找栏"""
        editor = self.tab_controller.current_editor()
        if editor:
            editor.show_find_bar(with_replace=False)

    def _do_show_find_replace(self) -> None:
        """显示查找+替换栏"""
        editor = self.tab_controller.current_editor()
        if editor:
            editor.show_find_bar(with_replace=True)

    def _do_hide_find(self) -> None:
        """隐藏查找栏"""
        editor = self.tab_controller.current_editor()
        if editor and editor.find_replace_bar.isVisible():
            editor.hide_find_bar()

    def _do_close_current_tab(self) -> None:
        index = self.tab_container.tab_bar.currentIndex()
        if index >= 0:
            self.tab_container.tab_bar.tabCloseRequested.emit(index)

    # ---------------- 状态栏 ----------------
    def _build_status_bar(self) -> None:
        self.char_count_label = BodyLabel("字符: 0", self)
        self.selection_label = BodyLabel("选中: 0", self)
        self.theme_label = BodyLabel("预览主题: 默认", self)
        self.encoding_label = BodyLabel("编码: UTF-8", self)
        self._apply_status_bar_style()

        self.status_bar.addWidget(self.char_count_label)
        self.status_bar.addWidget(self.selection_label)
        self.status_bar.addWidget(self.theme_label)
        self.status_bar.addPermanentWidget(self.encoding_label)

    def _apply_status_bar_style(self) -> None:
        is_dark = isDarkTheme()
        self.status_bar.setStyleSheet(
            "QStatusBar{background:transparent;border:none;padding:2px 8px;}"
            "QStatusBar::item{border:none;}"
        )
        text_color = "#ffffff" if is_dark else "#333333"
        label_style = f"color:{text_color};padding:0 8px;"
        for lbl in (
            self.char_count_label,
            self.selection_label,
            self.theme_label,
            self.encoding_label,
        ):
            lbl.setStyleSheet(label_style)

    def _refresh_status_bar(self) -> None:
        editor = self.tab_controller.current_editor()
        if editor is None:
            self.char_count_label.setText("字符: 0")
            self.selection_label.setText("选中: 0")
            return
        self.char_count_label.setText(f"字符: {editor.char_count()}")
        self.selection_label.setText(f"选中: {editor.selection_length()}")
        self.theme_label.setText(
            f"预览主题: {self.theme_controller.theme_display_name(self.theme_controller.preview_theme)}"
        )

    # ---------------- 信号转发到当前 editor ----------------
    def _current_editor(self):
        return self.tab_controller.current_editor()

    def _do_copy(self) -> None:
        editor = self._current_editor()
        if editor:
            editor.copy()

    def _do_paste(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        clipboard = QApplication.clipboard()
        if clipboard.mimeData().hasImage():
            image = clipboard.image()
            if not image.isNull():
                temp_dir = tempfile.gettempdir()
                file_name = f"image_{uuid.uuid4().hex}.png"
                file_path = os.path.join(temp_dir, file_name)
                if image.save(file_path, "PNG"):
                    editor.insert_text(f"![{file_name}]({file_path})")
                    return
        editor.paste()

    def _do_insert_image(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.svg);;All Files (*)",
        )
        if file_path:
            editor.insert_text(f"![{os.path.basename(file_path)}]({file_path})")

    def _do_toggle_fullscreen(self) -> None:
        editor = self._current_editor()
        if editor:
            editor.toggle_fullscreen()

    def _do_zoom_in(self) -> None:
        editor = self._current_editor()
        if editor:
            editor.zoom_in()
            self._refresh_status_bar()

    def _do_zoom_out(self) -> None:
        editor = self._current_editor()
        if editor:
            editor.zoom_out()
            self._refresh_status_bar()

    def _do_zoom_reset(self) -> None:
        editor = self._current_editor()
        if editor:
            editor.zoom_reset()
            self._refresh_status_bar()

    def _do_export(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        file_path, _ = self.export_controller.prompt_export_path(self)
        if not file_path:
            return
        try:
            self.export_controller.export(file_path, editor.document.content)
        except Exception as err:  # noqa: BLE001
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title="导出失败",
                content=str(err),
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4500,
                parent=self,
            )
            return
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title="导出成功",
            content=file_path,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500,
            parent=self,
        )

    # ---------------- 自动保存 ----------------
    def _do_toggle_auto_save(self) -> None:
        enabled = not self.settings.get("auto_save", False)
        self.settings.set("auto_save", enabled)
        self._auto_save_action.setText("自动保存: 开" if enabled else "自动保存: 关")
        self._auto_save_action.setChecked(enabled)
        if enabled:
            self._auto_save_timer.start()
        else:
            self._auto_save_timer.stop()

    def _do_auto_save(self) -> None:
        """定时自动保存所有已有路径且被修改的文档。"""
        for editor in self.tab_controller.all_editors():
            doc = editor.document
            if doc.is_modified and not doc.is_untitled:
                try:
                    doc.save()
                except Exception:  # noqa: BLE001
                    pass

    # ---------------- 最近文件 ----------------
    def _do_show_recent_menu(self) -> None:
        recent = self.tab_controller.recent_files.recent_files
        menu = RoundMenu("", self)

        if not recent:
            action = Action("暂无记录")
            action.setEnabled(False)
            menu.addAction(action)
        else:
            for path in recent[:10]:
                display = os.path.basename(path)
                action = Action(display)
                action.setToolTip(path)
                action.triggered.connect(
                    lambda checked, p=path: self.tab_controller.open_file_by_path(p)
                )
                menu.addAction(action)
            menu.addSeparator()
            clear_action = Action("清空历史记录")
            clear_action.triggered.connect(self.tab_controller.recent_files.clear)
            menu.addAction(clear_action)

        from PyQt5.QtGui import QCursor
        menu.exec_(QCursor.pos())

    # ---------------- 主题联动 ----------------
    def _on_theme_combo_changed(self, index: int) -> None:
        key = self.theme_combo.itemData(index)
        if key:
            self.theme_controller.set_preview_theme(key)

    def _on_preview_theme_changed(self, theme_key: str) -> None:
        for editor in self.tab_controller.all_editors():
            editor.set_preview_theme(theme_key)
        self._refresh_status_bar()

    def _update_editor_actions_enabled(self, enabled: bool) -> None:
        for action in self._editor_actions:
            action.setEnabled(enabled)
        self.theme_combo.setEnabled(enabled)
        self._theme_label.setEnabled(enabled)

    def _on_current_document_changed(self, document: Optional[Document]) -> None:
        has_doc = document is not None
        self._update_editor_actions_enabled(has_doc)

        editor = self._current_editor()
        if editor is not None:
            try:
                editor.editor.textChanged.disconnect(self._refresh_status_bar)
            except (TypeError, RuntimeError):
                pass
            editor.editor.textChanged.connect(self._refresh_status_bar)
            try:
                editor.editor.selectionChanged.disconnect(self._refresh_status_bar)
            except (TypeError, RuntimeError):
                pass
            editor.editor.selectionChanged.connect(self._refresh_status_bar)
            editor.set_preview_theme(self.theme_controller.preview_theme)
        self._refresh_status_bar()

    def _on_system_theme_changed(self) -> None:
        if self.windowEffect is not None:
            QTimer.singleShot(
                100,
                lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()),
            )
        self._apply_status_bar_style()
        for editor in self.tab_controller.all_editors():
            editor.update_editor_style()
            editor.update_preview()

    # ---------------- 窗口状态自适应 ----------------
    def resizeEvent(self, event):
        super().resizeEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.WindowStateChange:
            self._update_layout_margins()

    def _update_layout_margins(self) -> None:
        """根据窗口状态动态调整布局 margin，解决 Windows 最大化后的偏移问题。"""
        top = self.titleBar.height()
        if sys.platform.startswith("win") and self.isMaximized():
            # Windows 最大化时有不可见的系统边框（通常 7~8px），需要加到四周 margin
            border = 8
            self.main_layout.setContentsMargins(border, top + border, border, border)
        else:
            self.main_layout.setContentsMargins(0, top, 0, 0)

    # ---------------- 拖拽打开文件 ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".md", ".markdown", ".txt")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                self.tab_controller.open_file_by_path(path)
        event.acceptProposedAction()

    # ---------------- 生命周期 ----------------
    def closeEvent(self, e):
        # 检查是否有未保存的文档
        unsaved_docs = []
        for editor in self.tab_controller.all_editors():
            if editor.document.is_modified:
                unsaved_docs.append(editor.document)

        if unsaved_docs:
            # 构建未保存文件列表
            file_list = "\n".join([f"• {doc.display_name}" for doc in unsaved_docs])
            message = f"以下 {len(unsaved_docs)} 个文档有未保存的修改：\n\n{file_list}\n\n确定要放弃修改并退出吗？"
            
            box = MessageBox("未保存的文档", message, self.window())
            box.yesButton.setText("放弃修改")
            box.cancelButton.setText("取消")
            if not box.exec():
                e.ignore()  # 用户取消，阻止关闭
                return
        
        # 没有未保存文档或用户确认放弃，正常退出
        self.tab_controller.save_session()
        self.theme_listener.terminate()
        self.theme_listener.deleteLater()
        super().closeEvent(e)
