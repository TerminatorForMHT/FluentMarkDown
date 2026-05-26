from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
from PyQt5.QtCore import QRegularExpression


class MarkdownHighlighter(QSyntaxHighlighter):
    """Markdown 语法高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dark = False
        self._formats = {}
        self._update_formats()

    def set_dark_mode(self, is_dark: bool):
        """切换暗色/亮色主题"""
        if self._is_dark == is_dark:
            return
        self._is_dark = is_dark
        self._update_formats()
        self.rehighlight()

    def _update_formats(self):
        """根据当前主题更新格式配置"""
        if self._is_dark:
            # 暗色主题配色
            self._formats = {
                "heading": self._create_format(color="#61afef", bold=True),
                "bold": self._create_format(bold=True),
                "italic": self._create_format(italic=True),
                "inline_code": self._create_format(
                    color="#abb2bf", background="rgba(40, 44, 52, 0.8)"
                ),
                "code_block": self._create_format(
                    color="#98c379", background="rgba(40, 44, 52, 0.6)"
                ),
                "link": self._create_format(color="#61afef"),
                "list": self._create_format(color="#e5c07b"),
                "quote": self._create_format(color="#5c6370", italic=True),
            }
        else:
            # 亮色主题配色
            self._formats = {
                "heading": self._create_format(color="#007acc", bold=True),
                "bold": self._create_format(bold=True),
                "italic": self._create_format(italic=True),
                "inline_code": self._create_format(
                    color="#333333", background="rgba(240, 240, 240, 0.8)"
                ),
                "code_block": self._create_format(
                    color="#22863a", background="rgba(246, 248, 250, 0.8)"
                ),
                "link": self._create_format(color="#0366d6"),
                "list": self._create_format(color="#d73a49"),
                "quote": self._create_format(color="#6a737d", italic=True),
            }

    def _create_format(self, color=None, bold=False, italic=False, background=None):
        """创建文本格式"""
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        if background:
            bg_color = QColor(background)
            fmt.setBackground(bg_color)
        return fmt

    def highlightBlock(self, text):
        """高亮当前文本块"""
        # 标题 (# ~ ######)
        self._highlight_headings(text)
        
        # 粗体 (**text**)
        self._highlight_pattern(text, r"\*\*(.+?)\*\*", "bold")
        
        # 斜体 (*text*) - 注意不要匹配到 **
        self._highlight_pattern(text, r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", "italic")
        
        # 行内代码 (`code`)
        self._highlight_inline_code(text)
        
        # 链接 [text](url)
        self._highlight_links(text)
        
        # 列表 (- /* /+ /1.)
        self._highlight_lists(text)
        
        # 引用 (> )
        self._highlight_quotes(text)
        
        # 代码块 (```) - 需要跨行状态处理，这里简化处理单行内的 ```
        self._highlight_code_blocks(text)

    def _highlight_headings(self, text):
        """高亮标题"""
        pattern = QRegularExpression(r"^(#{1,6})\s+(.*)$")
        match = pattern.match(text)
        if match.hasMatch():
            length = match.capturedLength(1) + match.capturedLength(2) + 1  # # + 空格 + 内容
            self.setFormat(0, length, self._formats["heading"])

    def _highlight_pattern(self, text, pattern_str, format_key):
        """高亮通用模式"""
        pattern = QRegularExpression(pattern_str)
        it = pattern.globalMatch(text)
        while it.hasNext():
            match = it.next()
            start = match.capturedStart()
            length = match.capturedLength()
            self.setFormat(start, length, self._formats[format_key])

    def _highlight_inline_code(self, text):
        """高亮行内代码"""
        pattern = QRegularExpression(r"`([^`]+)`")
        it = pattern.globalMatch(text)
        while it.hasNext():
            match = it.next()
            start = match.capturedStart()
            length = match.capturedLength()
            self.setFormat(start, length, self._formats["inline_code"])

    def _highlight_links(self, text):
        """高亮链接"""
        pattern = QRegularExpression(r"\[([^\]]+)\]\(([^)]+)\)")
        it = pattern.globalMatch(text)
        while it.hasNext():
            match = it.next()
            start = match.capturedStart()
            length = match.capturedLength()
            self.setFormat(start, length, self._formats["link"])

    def _highlight_lists(self, text):
        """高亮列表标记"""
        # 无序列表: -, *, +
        pattern_unordered = QRegularExpression(r"^(\s*)([-*+])\s+")
        match = pattern_unordered.match(text)
        if match.hasMatch():
            length = match.capturedLength(1) + match.capturedLength(2) + 1
            self.setFormat(0, length, self._formats["list"])
            return
        
        # 有序列表: 1. 
        pattern_ordered = QRegularExpression(r"^(\s*)(\d+\.)\s+")
        match = pattern_ordered.match(text)
        if match.hasMatch():
            length = match.capturedLength(1) + match.capturedLength(2) + 1
            self.setFormat(0, length, self._formats["list"])

    def _highlight_quotes(self, text):
        """高亮引用"""
        pattern = QRegularExpression(r"^(\s*)>\s+")
        match = pattern.match(text)
        if match.hasMatch():
            length = match.capturedLength(1) + 1  # > 和后面的空格
            self.setFormat(0, length, self._formats["quote"])

    def _highlight_code_blocks(self, text):
        """高亮代码块标记"""
        if text.strip().startswith("```"):
            self.setFormat(0, len(text), self._formats["code_block"])
