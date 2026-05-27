import json
import os


class MarkdownDocument:
    def __init__(self):
        self.file_path = None
        self.content = ""
        self.is_modified = False
        self.has_file = False
        self._history_file_path = os.path.join(os.path.expanduser("~"), ".fluentmarkdown_history.json")
        self._recent_files = self._load_recent_files()

    def load(self, file_path):
        if not file_path:
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            self.file_path = file_path
            self.has_file = True
            self.is_modified = False
            self._add_to_recent_files(file_path)
            return True
        except Exception:
            return False

    def save(self, file_path=None):
        save_path = file_path or self.file_path
        if not save_path:
            return False
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            self.file_path = save_path
            self.is_modified = False
            self.has_file = True
            return True
        except Exception:
            return False

    def new(self):
        self.file_path = None
        self.content = ""
        self.is_modified = False
        self.has_file = True

    def _load_recent_files(self):
        try:
            if os.path.exists(self._history_file_path):
                with open(self._history_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_recent_files(self):
        try:
            with open(self._history_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._recent_files, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _add_to_recent_files(self, file_path):
        if not file_path:
            return
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        self._recent_files.insert(0, file_path)
        if len(self._recent_files) > 10:
            self._recent_files = self._recent_files[:10]
        self._save_recent_files()

    def get_recent_files(self):
        return self._recent_files.copy()

    def clear_recent_files(self):
        self._recent_files = []
        self._save_recent_files()
