"""
多 Tab 控制器：协调 Fluent TabBar、QStackedWidget 与多个 MarkdownEditorView。

每个 tab 对应一个 (Document, MarkdownEditorView) 配对。
新建/打开/关闭/切换 tab 的全部逻辑都在这里。
"""
import os
import uuid
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QStackedWidget, QWidget

from qfluentwidgets import InfoBar, InfoBarPosition, MessageBox, TabBar

from controllers.document_controller import DocumentController
from models.document import Document
from models.history import RecentFilesManager, SessionManager
from views.markdown_editor import MarkdownEditorView


class TabController(QObject):
    """多 tab 文档管理控制器。"""

    currentDocumentChanged = pyqtSignal(object)  # emits Document or None

    def __init__(
        self,
        tab_bar: TabBar,
        stack: QStackedWidget,
        document_controller: DocumentController,
        host_widget: QWidget,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._tab_bar = tab_bar
        self._stack = stack
        self._docs = document_controller
        self._host = host_widget

        # routeKey -> (Document, MarkdownEditorView)
        self._editors: Dict[str, MarkdownEditorView] = {}
        self._documents: Dict[str, Document] = {}

        self.recent_files = RecentFilesManager(self)
        self._session = SessionManager()

        self._setup_tab_bar()

    # ---------------- TabBar 初始化 ----------------
    def _setup_tab_bar(self) -> None:
        self._tab_bar.setMovable(True)
        self._tab_bar.setTabMaximumWidth(220)
        self._tab_bar.setTabShadowEnabled(False)
        self._tab_bar.setTabSelectedBackgroundColor(
            "#33000000", "#33ffffff"
        )
        self._tab_bar.setScrollable(True)
        self._tab_bar.setAddButtonVisible(False)

        self._tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tab_bar.currentChanged.connect(self._on_current_changed)

    # ---------------- 外部 API ----------------
    def new_document(self) -> None:
        """新建一个空白文档 tab。"""
        doc = Document(parent=self)
        self._add_tab(doc)

    def open_file_by_path(self, path: str) -> None:
        """直接按路径打开文件（供最近文件列表调用）。"""
        if not path:
            return
        for route_key, document in self._documents.items():
            if document.file_path == path:
                self._tab_bar.setCurrentTab(route_key)
                return
        doc = Document(parent=self)
        try:
            self._docs.open_into(doc, path)
        except Exception as err:  # noqa: BLE001
            self._show_error("打开失败", str(err))
            self.recent_files.remove(path)
            return
        self._add_tab(doc)
        self.recent_files.add(path)

    def open_document(self) -> None:
        """弹对话框选择文件并在新 tab 中打开。"""
        path = self._docs.prompt_open_path(self._host)
        if not path:
            return

        # 如果该文件已被打开，直接切过去
        for route_key, document in self._documents.items():
            if document.file_path == path:
                self._tab_bar.setCurrentTab(route_key)
                return

        doc = Document(parent=self)
        try:
            self._docs.open_into(doc, path)
        except Exception as err:  # noqa: BLE001
            self._show_error("打开失败", str(err))
            return
        self._add_tab(doc)
        self.recent_files.add(path)

    def save_current(self) -> None:
        doc, _ = self._current_pair()
        if not doc:
            return
        try:
            saved_path = self._docs.save(doc, self._host)
        except Exception as err:  # noqa: BLE001
            self._show_error("保存失败", str(err))
            return
        if saved_path:
            self._sync_tab_title(self._current_route_key())
            self._show_success("保存成功", saved_path)
            self.recent_files.add(saved_path)

    def save_current_as(self) -> None:
        doc, _ = self._current_pair()
        if not doc:
            return
        try:
            saved_path = self._docs.save_as(doc, self._host)
        except Exception as err:  # noqa: BLE001
            self._show_error("另存为失败", str(err))
            return
        if saved_path:
            self._sync_tab_title(self._current_route_key())
            self._show_success("已另存为", saved_path)
            self.recent_files.add(saved_path)

    def current_editor(self) -> Optional[MarkdownEditorView]:
        return self._current_pair()[1]

    def current_document(self) -> Optional[Document]:
        return self._current_pair()[0]

    def all_editors(self) -> List[MarkdownEditorView]:
        return list(self._editors.values())

    # ---------------- 内部 ----------------
    def _add_tab(self, document: Document) -> None:
        route_key = uuid.uuid4().hex
        editor = MarkdownEditorView(document)
        editor.setObjectName(f"editor_{route_key}")

        self._editors[route_key] = editor
        self._documents[route_key] = document
        self._stack.addWidget(editor)

        self._tab_bar.addTab(
            routeKey=route_key,
            text=self._build_tab_text(document),
            onClick=lambda rk=route_key: self._activate_by_route(rk),
        )
        self._tab_bar.setCurrentTab(route_key)
        self._stack.setCurrentWidget(editor)
        self.currentDocumentChanged.emit(document)

        document.modifiedChanged.connect(
            lambda _modified, rk=route_key: self._sync_tab_title(rk)
        )
        document.pathChanged.connect(
            lambda _path, rk=route_key: self._sync_tab_title(rk)
        )

    def _activate_by_route(self, route_key: str) -> None:
        editor = self._editors.get(route_key)
        if editor:
            self._stack.setCurrentWidget(editor)
            self.currentDocumentChanged.emit(self._documents.get(route_key))

    def _on_current_changed(self, index: int) -> None:
        if index < 0 or index >= self._tab_bar.count():
            self.currentDocumentChanged.emit(None)
            return
        item = self._tab_bar.tabItem(index)
        if item is None:
            return
        self._activate_by_route(item.routeKey())

    def _on_tab_close_requested(self, index: int) -> None:
        if index < 0 or index >= self._tab_bar.count():
            return
        item = self._tab_bar.tabItem(index)
        if item is None:
            return
        route_key = item.routeKey()
        document = self._documents.get(route_key)

        if document and document.is_modified:
            box = MessageBox(
                "关闭未保存的文档",
                f"“{document.display_name}” 有未保存的修改，确定关闭吗？",
                self._host.window(),
            )
            box.yesButton.setText("放弃修改")
            box.cancelButton.setText("取消")
            if not box.exec():
                return

        self._remove_tab(route_key)

    def _remove_tab(self, route_key: str) -> None:
        editor = self._editors.pop(route_key, None)
        document = self._documents.pop(route_key, None)
        if editor is not None:
            self._stack.removeWidget(editor)
            editor.deleteLater()
        if document is not None:
            document.deleteLater()
        self._tab_bar.removeTabByKey(route_key)

        if self._tab_bar.count() == 0:
            # 切回欢迎页（welcome_page 始终是 stack 的第一个 widget）
            if self._stack.count() > 0:
                self._stack.setCurrentIndex(0)
            self.currentDocumentChanged.emit(None)

    def _current_route_key(self) -> Optional[str]:
        index = self._tab_bar.currentIndex()
        if index < 0:
            return None
        item = self._tab_bar.tabItem(index)
        return item.routeKey() if item else None

    def _current_pair(self):
        rk = self._current_route_key()
        if not rk:
            return None, None
        return self._documents.get(rk), self._editors.get(rk)

    def _sync_tab_title(self, route_key: Optional[str]) -> None:
        if not route_key:
            return
        document = self._documents.get(route_key)
        if document is None:
            return
        index = self._index_of_route(route_key)
        if index < 0:
            return
        self._tab_bar.setTabText(index, self._build_tab_text(document))
        if document.file_path:
            self._tab_bar.setTabToolTip(index, document.file_path)

    def _index_of_route(self, route_key: str) -> int:
        for i in range(self._tab_bar.count()):
            item = self._tab_bar.tabItem(i)
            if item is not None and item.routeKey() == route_key:
                return i
        return -1

    @staticmethod
    def _build_tab_text(document: Document) -> str:
        prefix = "● " if document.is_modified else ""
        return f"{prefix}{document.display_name}"

    # ---------------- InfoBar ----------------
    def _show_error(self, title: str, content: str) -> None:
        InfoBar.error(
            title=title,
            content=content,
            orient=1,  # Qt.Vertical, 文案换行
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self._host.window(),
        )

    def _show_success(self, title: str, content: str) -> None:
        InfoBar.success(
            title=title,
            content=content,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500,
            parent=self._host.window(),
        )

    # ---------------- 会话保存/恢复 ----------------
    def save_session(self) -> None:
        """保存当前所有 tab 的状态，供下次启动恢复。"""
        tabs = []
        for route_key in self._iter_route_keys():
            doc = self._documents.get(route_key)
            if doc is None:
                continue
            tab_info = {
                "file_path": doc.file_path,
                "content": doc.content if doc.is_untitled or doc.is_modified else None,
                "is_modified": doc.is_modified,
            }
            tabs.append(tab_info)

        active_index = self._tab_bar.currentIndex()
        self._session.save_session(tabs, active_index)

    def restore_session(self) -> bool:
        """恢复上次退出时的 tab 状态。成功恢复至少一个 tab 返回 True。"""
        session = self._session.load_session()
        if not session:
            return False

        tabs = session.get("tabs", [])
        if not tabs:
            return False

        restored = False
        for tab_info in tabs:
            file_path = tab_info.get("file_path")
            content = tab_info.get("content")
            is_modified = tab_info.get("is_modified", False)

            doc = Document(parent=self)
            if file_path and os.path.isfile(file_path):
                try:
                    doc.load(file_path)
                    # 如果关闭时有未保存的修改，用保存的内容覆盖
                    if is_modified and content is not None:
                        doc.set_content(content, mark_modified=True)
                except Exception:  # noqa: BLE001
                    continue
            elif content is not None:
                # 未命名文档：恢复内容
                doc.set_content(content, mark_modified=True)
            else:
                continue

            self._add_tab(doc)
            restored = True

        # 恢复激活的 tab
        if restored:
            active_index = session.get("active_index", 0)
            count = self._tab_bar.count()
            if 0 <= active_index < count:
                item = self._tab_bar.tabItem(active_index)
                if item:
                    self._tab_bar.setCurrentTab(item.routeKey())

        return restored

    def _iter_route_keys(self) -> List[str]:
        """按 tab 顺序返回所有 routeKey。"""
        keys = []
        for i in range(self._tab_bar.count()):
            item = self._tab_bar.tabItem(i)
            if item:
                keys.append(item.routeKey())
        return keys
