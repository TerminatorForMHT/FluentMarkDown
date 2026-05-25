"""
最近打开文件的历史记录管理。

持久化到 ~/.fluentmarkdown/recent_files.json，记录最近打开/保存过的文件路径。
"""
import json
import os
from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal


class RecentFilesManager(QObject):
    """管理最近打开的文件列表。"""

    historyChanged = pyqtSignal()

    MAX_RECENT = 20
    _CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".fluentmarkdown")
    _HISTORY_FILE = os.path.join(_CONFIG_DIR, "recent_files.json")

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._recent_files: List[str] = []
        self._load()

    @property
    def recent_files(self) -> List[str]:
        """返回最近文件列表（最新的在前），已自动过滤不存在的文件。"""
        return list(self._recent_files)

    def add(self, file_path: str) -> None:
        """添加一条记录到最近文件列表顶部。"""
        file_path = os.path.abspath(file_path)
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        self._recent_files.insert(0, file_path)
        self._recent_files = self._recent_files[: self.MAX_RECENT]
        self._save()
        self.historyChanged.emit()

    def remove(self, file_path: str) -> None:
        """从历史中移除指定路径。"""
        file_path = os.path.abspath(file_path)
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
            self._save()
            self.historyChanged.emit()

    def clear(self) -> None:
        """清空所有历史记录。"""
        self._recent_files.clear()
        self._save()
        self.historyChanged.emit()

    def _load(self) -> None:
        if not os.path.exists(self._HISTORY_FILE):
            return
        try:
            with open(self._HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # 只保留仍然存在的文件
                self._recent_files = [p for p in data if os.path.isfile(p)]
        except (json.JSONDecodeError, OSError):
            self._recent_files = []

    def _save(self) -> None:
        os.makedirs(self._CONFIG_DIR, exist_ok=True)
        try:
            with open(self._HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._recent_files, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
