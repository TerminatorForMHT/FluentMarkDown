"""
历史记录与会话恢复管理。

- RecentFilesManager: 最近打开文件列表，持久化到 ~/.fluentmarkdown/recent_files.json
- SessionManager: 上次退出时未关闭的 tab 状态，持久化到 ~/.fluentmarkdown/session.json
"""
import json
import os
from typing import Any, Dict, List, Optional

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


class SettingsManager:
    """简单的应用设置持久化（~/.fluentmarkdown/settings.json）。"""

    _CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".fluentmarkdown")
    _SETTINGS_FILE = os.path.join(_CONFIG_DIR, "settings.json")

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def _load(self) -> None:
        if not os.path.exists(self._SETTINGS_FILE):
            return
        try:
            with open(self._SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._data = data
        except (json.JSONDecodeError, OSError):
            pass

    def _save(self) -> None:
        os.makedirs(self._CONFIG_DIR, exist_ok=True)
        try:
            with open(self._SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass


class SessionManager:
    """退出时保存打开的 tab 状态，下次启动时恢复。

    持久化到 ~/.fluentmarkdown/session.json，结构：
    {
      "tabs": [
        {"file_path": "/path/to/file.md", "content": null, "is_modified": false},
        {"file_path": null, "content": "未保存的文本...", "is_modified": true}
      ],
      "active_index": 0
    }
    """

    _CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".fluentmarkdown")
    _SESSION_FILE = os.path.join(_CONFIG_DIR, "session.json")

    def save_session(self, tabs: List[Dict[str, Any]], active_index: int) -> None:
        """保存当前会话状态。"""
        data = {"tabs": tabs, "active_index": active_index}
        os.makedirs(self._CONFIG_DIR, exist_ok=True)
        try:
            with open(self._SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def load_session(self) -> Optional[Dict[str, Any]]:
        """加载上次的会话状态，不存在或格式错误返回 None。"""
        if not os.path.exists(self._SESSION_FILE):
            return None
        try:
            with open(self._SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "tabs" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def clear_session(self) -> None:
        """清除会话文件。"""
        try:
            if os.path.exists(self._SESSION_FILE):
                os.remove(self._SESSION_FILE)
        except OSError:
            pass
