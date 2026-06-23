"""应用设置持久化"""

import json
import os


class AppSettings:
    """管理应用设置的读写，存储到 ~/.fluentmarkdown_settings.json"""

    DEFAULT_SETTINGS = {
        "font_size": 16,
        "preview_theme": "light",
        "window_width": 1000,
        "window_height": 700,
        "window_x": -1,
        "window_y": -1,
        "window_maximized": True,
    }

    def __init__(self):
        self._path = os.path.join(os.path.expanduser("~"), ".fluentmarkdown_settings.json")
        self._data = dict(self.DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        try:
            if os.path.exists(self._path):
                with open(self._path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                self._data.update(saved)
        except Exception:
            pass

    def save(self):
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self._data[key] = value
