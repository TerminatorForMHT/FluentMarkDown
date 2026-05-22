"""
文档控制器：负责文件 IO（打开 / 保存 / 另存为）并把结果落到 Document 模型上。

视图只负责显示对话框结果和错误提示，所有真正的读写都走这里。
"""
import os
from typing import Optional

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QFileDialog, QWidget

from models.document import Document


MARKDOWN_FILTER = "Markdown Files (*.md *.markdown);;All Files (*)"


class DocumentController(QObject):
    """文档级别的文件 IO 控制器。"""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    # ---------------- 打开 ----------------
    def prompt_open_path(self, parent_widget: QWidget) -> Optional[str]:
        """弹出打开文件对话框，返回选择的路径；用户取消返回 None。"""
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget, "打开文件", "", MARKDOWN_FILTER
        )
        return file_path or None

    def open_into(self, document: Document, file_path: str) -> None:
        """把磁盘文件读入到指定 Document。"""
        document.load(file_path)

    # ---------------- 保存 ----------------
    def save(self, document: Document, parent_widget: QWidget) -> Optional[str]:
        """
        保存文档：
        - 已有路径：直接覆盖
        - 未命名：弹出另存为对话框
        返回最终保存路径，用户取消则返回 None。
        """
        if document.is_untitled:
            return self.save_as(document, parent_widget)
        document.save()
        return document.file_path

    def save_as(self, document: Document, parent_widget: QWidget) -> Optional[str]:
        """另存为，返回最终路径或 None。"""
        default_name = document.display_name
        if not default_name.lower().endswith((".md", ".markdown")):
            default_name = f"{default_name}.md"

        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget, "保存文件", default_name, MARKDOWN_FILTER
        )
        if not file_path:
            return None

        # 修复点：用户在原生对话框里未必带扩展名，这里自动补 .md
        if not os.path.splitext(file_path)[1]:
            file_path += ".md"

        document.save(file_path)
        return file_path
