"""
文档数据模型
"""
import os
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal


class Document(QObject):
    """
    单个 Markdown 文档的数据模型。

    职责：
    - 保存文档内容、磁盘路径
    - 跟踪修改状态（脏标记）
    - 文件读写的底层封装
    """

    pathChanged = pyqtSignal(str)
    modifiedChanged = pyqtSignal(bool)
    contentLoaded = pyqtSignal(str)

    UNTITLED_NAME = "未命名"

    def __init__(self, file_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._file_path: Optional[str] = None
        self._content: str = ""
        self._is_modified: bool = False
        self._encoding: str = "UTF-8"

        if file_path:
            self.load(file_path)

    # ---------------- 属性 ----------------
    @property
    def file_path(self) -> Optional[str]:
        return self._file_path

    @property
    def content(self) -> str:
        return self._content

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    @property
    def is_untitled(self) -> bool:
        return self._file_path is None

    @property
    def display_name(self) -> str:
        """tab 标题展示用的名字。"""
        if self._file_path:
            return os.path.basename(self._file_path)
        return self.UNTITLED_NAME

    # ---------------- 内容 ----------------
    def set_content(self, text: str, mark_modified: bool = True) -> None:
        if text == self._content:
            return
        self._content = text
        if mark_modified:
            self._set_modified(True)

    def set_content_silent(self, text: str) -> None:
        """仅更新内部内容，不触发任何信号、不改 modified 标记。

        视图层在 QTextEdit 文本变化后想把"新文本"原样推给 Document
        但又不想把 modified 翻成 False / 二次触发逻辑时使用。
        """
        self._content = text

    def _set_modified(self, value: bool) -> None:
        if value == self._is_modified:
            return
        self._is_modified = value
        self.modifiedChanged.emit(value)

    # ---------------- 磁盘 IO ----------------
    def load(self, file_path: str) -> None:
        """
        从磁盘读取文件内容。会抛出异常，调用方负责捕获并提示用户。
        """
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        self._file_path = file_path
        self._content = text
        self._encoding = "UTF-8"
        self._set_modified(False)
        self.pathChanged.emit(file_path)
        self.contentLoaded.emit(text)

    def save(self, file_path: Optional[str] = None) -> str:
        """
        保存到指定路径；不传则保存到当前路径。返回最终的保存路径。
        会抛出异常，调用方负责捕获并提示用户。
        """
        target = file_path or self._file_path
        if not target:
            raise ValueError("未指定保存路径")

        with open(target, "w", encoding="utf-8") as f:
            f.write(self._content)

        path_changed = target != self._file_path
        self._file_path = target
        self._set_modified(False)
        if path_changed:
            self.pathChanged.emit(target)
        return target
