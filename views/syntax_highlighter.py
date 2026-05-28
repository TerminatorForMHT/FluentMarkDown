"""Markdown 语法高亮器"""

import re
from PyQt5.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont
)


class MarkdownHighlighter(QSyntaxHighlighter):
    """Markdown 语法高亮，支持明暗主题"""

    def __init__(self, document, is_dark=False):
        super().__init__(document)
        self._is_dark = is_dark
        self._build_rules()

    def set_dark_mode(self, is_dark):
        self._is_dark = is_dark
        self._build_rules()
        self.rehighlight()

    def _color(self, light_hex, dark_hex):
        return QColor(dark_hex if self._is_dark else light_hex)

    def _build_rules(self):
        self._rules = []

        # --- 标题 ---
        heading_format = QTextCharFormat()
        heading_format.setForeground(self._color("#0550ae", "#79c0ff"))
        heading_format.setFontWeight(QFont.Bold)
        self._rules.append((re.compile(r'^#{1,6}\s+.+', re.MULTILINE), heading_format))

        # --- 粗体 ---
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Bold)
        bold_format.setForeground(self._color("#24292f", "#e6edf3"))
        self._rules.append((re.compile(r'\*\*[^*]+\*\*'), bold_format))
        self._rules.append((re.compile(r'__[^_]+__'), bold_format))

        # --- 斜体 ---
        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        italic_format.setForeground(self._color("#24292f", "#e6edf3"))
        self._rules.append((re.compile(r'(?<!\*)\*(?!\*)[^*]+\*(?!\*)'), italic_format))
        self._rules.append((re.compile(r'(?<!_)_(?!_)[^_]+_(?!_)'), italic_format))

        # --- 行内代码 ---
        code_format = QTextCharFormat()
        code_format.setForeground(self._color("#cf222e", "#ff7b72"))
        code_format.setFontFamily("Consolas, 'SF Mono', Menlo, monospace")
        self._rules.append((re.compile(r'`[^`\n]+`'), code_format))

        # --- 链接 ---
        link_format = QTextCharFormat()
        link_format.setForeground(self._color("#0969da", "#58a6ff"))
        self._rules.append((re.compile(r'\[([^\]]+)\]\([^)]+\)'), link_format))

        # --- 图片 ---
        image_format = QTextCharFormat()
        image_format.setForeground(self._color("#8250df", "#d2a8ff"))
        self._rules.append((re.compile(r'!\[([^\]]*)\]\([^)]+\)'), image_format))

        # --- 引用 ---
        quote_format = QTextCharFormat()
        quote_format.setForeground(self._color("#57606a", "#8b949e"))
        quote_format.setFontItalic(True)
        self._rules.append((re.compile(r'^>\s+.+', re.MULTILINE), quote_format))

        # --- 无序列表标记 ---
        list_format = QTextCharFormat()
        list_format.setForeground(self._color("#cf222e", "#ff7b72"))
        list_format.setFontWeight(QFont.Bold)
        self._rules.append((re.compile(r'^\s*[-*+]\s', re.MULTILINE), list_format))

        # --- 有序列表标记 ---
        ordered_format = QTextCharFormat()
        ordered_format.setForeground(self._color("#cf222e", "#ff7b72"))
        ordered_format.setFontWeight(QFont.Bold)
        self._rules.append((re.compile(r'^\s*\d+\.\s', re.MULTILINE), ordered_format))

        # --- 分割线 ---
        hr_format = QTextCharFormat()
        hr_format.setForeground(self._color("#d0d7de", "#484f58"))
        self._rules.append((re.compile(r'^(-{3,}|\*{3,}|_{3,})\s*$', re.MULTILINE), hr_format))

        # --- 删除线 ---
        strike_format = QTextCharFormat()
        strike_format.setForeground(self._color("#57606a", "#8b949e"))
        strike_format.setFontStrikeOut(True)
        self._rules.append((re.compile(r'~~[^~]+~~'), strike_format))

        # --- 代码块围栏 ---
        fence_format = QTextCharFormat()
        fence_format.setForeground(self._color("#6e7781", "#7d8590"))
        fence_format.setFontFamily("Consolas, 'SF Mono', Menlo, monospace")
        self._code_fence_format = fence_format

    def highlightBlock(self, text):
        # 处理代码块状态
        previous_state = self.previousBlockState()
        current_state = 0

        if previous_state == 1:
            # 在代码块内部
            if re.match(r'^```', text):
                self.setFormat(0, len(text), self._code_fence_format)
                current_state = 0
            else:
                self.setFormat(0, len(text), self._code_fence_format)
                current_state = 1
            self.setCurrentBlockState(current_state)
            return

        if re.match(r'^```', text):
            self.setFormat(0, len(text), self._code_fence_format)
            self.setCurrentBlockState(1)
            return

        self.setCurrentBlockState(0)

        # 应用单行规则
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)
