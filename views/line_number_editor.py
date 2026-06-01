"""带行号和当前行高亮的代码编辑器，基于 QPlainTextEdit"""

from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt5.QtCore import Qt, QRect, QSize, QEvent, QUrl, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QTextFormat, QFont, QKeyEvent, QTextCursor


class LineNumberArea(QWidget):
    """行号区域"""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class LineNumberEditor(QPlainTextEdit):
    """带行号显示和当前行高亮的 Markdown 编辑器"""

    # 拖拽信号：图片文件路径列表 / md文件路径
    image_dropped = pyqtSignal(list)
    md_file_dropped = pyqtSignal(str)

    # 括号配对表
    BRACKET_PAIRS = {
        '(': ')',
        '[': ']',
        '{': '}',
        '"': '"',
        "'": "'",
        '`': '`',
    }

    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._is_dark = False
        self._show_line_numbers = True
        self.setAcceptDrops(True)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def set_dark_mode(self, is_dark):
        self._is_dark = is_dark
        self._line_number_area.update()
        self._highlight_current_line()

    def line_number_area_width(self):
        if not self._show_line_numbers:
            return 0
        digits = max(1, len(str(self.blockCount())))
        space = 12 + self.fontMetrics().horizontalAdvance('9') * digits + 12
        return space

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        content_rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(content_rect.left(), content_rect.top(),
                  self.line_number_area_width(), content_rect.height())
        )

    def showEvent(self, event):
        super().showEvent(event)
        self._update_line_number_area_width(0)
        content_rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(content_rect.left(), content_rect.top(),
                  self.line_number_area_width(), content_rect.height())
        )

    def _highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            if self._is_dark:
                line_color = QColor(255, 255, 255, 15)
            else:
                line_color = QColor(0, 0, 0, 12)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        if not self._show_line_numbers:
            return
        painter = QPainter(self._line_number_area)

        # 行号区背景透明
        painter.fillRect(event.rect(), QColor(0, 0, 0, 0))

        # 分隔线
        separator_color = QColor(255, 255, 255, 20) if self._is_dark else QColor(0, 0, 0, 15)
        area_width = self._line_number_area.width()
        painter.setPen(separator_color)
        painter.drawLine(area_width - 1, event.rect().top(), area_width - 1, event.rect().bottom())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        current_line = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_line:
                    if self._is_dark:
                        painter.setPen(QColor(255, 255, 255, 200))
                    else:
                        painter.setPen(QColor(0, 0, 0, 180))
                else:
                    if self._is_dark:
                        painter.setPen(QColor(255, 255, 255, 80))
                    else:
                        painter.setPen(QColor(0, 0, 0, 100))

                painter.drawText(0, top, area_width - 14, self.fontMetrics().height(),
                                 Qt.AlignRight | Qt.AlignVCenter, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

        painter.end()

    def dragEnterEvent(self, event):
        """接受图片和 .md 文件拖入"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if path.endswith(self.IMAGE_EXTENSIONS) or path.endswith('.md'):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """处理拖拽放下：图片插入标记，md 文件发信号打开"""
        if event.mimeData().hasUrls():
            image_paths = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith('.md'):
                    self.md_file_dropped.emit(path)
                    event.acceptProposedAction()
                    return
                if path.lower().endswith(self.IMAGE_EXTENSIONS):
                    image_paths.append(path)
            if image_paths:
                self.image_dropped.emit(image_paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """处理自动缩进、括号补全和智能输入"""
        key_text = event.text()

        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._handle_auto_indent()
            return

        if event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._indent_selection(increase=True)
            else:
                cursor.insertText("    ")
            return

        if event.key() == Qt.Key_Backtab:
            self._indent_selection(increase=False)
            return

        # 括号/引号自动补全
        if key_text in self.BRACKET_PAIRS:
            cursor = self.textCursor()
            closing = self.BRACKET_PAIRS[key_text]
            if cursor.hasSelection():
                # 用配对符号包裹选中文本
                selected = cursor.selectedText()
                cursor.insertText(f"{key_text}{selected}{closing}")
                # 光标放在闭合符号前
                cursor.movePosition(QTextCursor.Left)
                self.setTextCursor(cursor)
            else:
                cursor.insertText(key_text + closing)
                cursor.movePosition(QTextCursor.Left)
                self.setTextCursor(cursor)
            return

        # 输入闭合符号时如果下一个字符就是它，跳过而非重复插入
        if key_text and key_text in self.BRACKET_PAIRS.values():
            cursor = self.textCursor()
            doc = self.document()
            pos = cursor.position()
            if pos < doc.characterCount():
                next_char_cursor = QTextCursor(doc)
                next_char_cursor.setPosition(pos)
                next_char_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                if next_char_cursor.selectedText() == key_text:
                    cursor.movePosition(QTextCursor.Right)
                    self.setTextCursor(cursor)
                    return

        # Backspace 删除空括号对
        if event.key() == Qt.Key_Backspace:
            cursor = self.textCursor()
            if not cursor.hasSelection() and cursor.position() > 0:
                pos = cursor.position()
                doc = self.document()
                # 获取前一个字符
                prev_cursor = QTextCursor(doc)
                prev_cursor.setPosition(pos - 1)
                prev_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                prev_char = prev_cursor.selectedText()
                # 获取后一个字符
                if pos < doc.characterCount() and prev_char in self.BRACKET_PAIRS:
                    next_cursor = QTextCursor(doc)
                    next_cursor.setPosition(pos)
                    next_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                    next_char = next_cursor.selectedText()
                    if next_char == self.BRACKET_PAIRS[prev_char]:
                        # 同时删除配对的两个符号
                        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
                        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 2)
                        cursor.removeSelectedText()
                        return

        super().keyPressEvent(event)

    def _handle_auto_indent(self):
        """回车时自动缩进，并延续列表标记"""
        cursor = self.textCursor()
        block_text = cursor.block().text()

        # 计算当前行缩进
        indent = ""
        for char in block_text:
            if char in (' ', '\t'):
                indent += char
            else:
                break

        stripped = block_text.strip()

        # 检查是否为列表项
        import re
        list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.*)', block_text)

        if list_match:
            prefix_indent = list_match.group(1)
            marker = list_match.group(2)
            content = list_match.group(3)

            if not content:
                # 空列表项：删除当前行标记，插入空行
                cursor.movePosition(QTextCursor.StartOfBlock)
                cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.insertText("\n")
                self.setTextCursor(cursor)
                return

            # 递增有序列表编号
            if re.match(r'\d+\.', marker):
                number = int(marker.rstrip('.'))
                new_marker = f"{number + 1}."
            else:
                new_marker = marker

            cursor.insertText(f"\n{prefix_indent}{new_marker} ")
            self.setTextCursor(cursor)
            return

        # 普通行：保持缩进
        cursor.insertText(f"\n{indent}")
        self.setTextCursor(cursor)

    def _indent_selection(self, increase=True):
        """缩进/反缩进选中的行"""
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(start)
        start_block = cursor.blockNumber()
        cursor.setPosition(end)
        end_block = cursor.blockNumber()

        cursor.beginEditBlock()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.StartOfBlock)

        for _ in range(end_block - start_block + 1):
            if increase:
                cursor.insertText("    ")
            else:
                line_text = cursor.block().text()
                if line_text.startswith("    "):
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
                    cursor.removeSelectedText()
                elif line_text.startswith("\t"):
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
                    cursor.removeSelectedText()
            cursor.movePosition(QTextCursor.NextBlock)

        cursor.endEditBlock()
