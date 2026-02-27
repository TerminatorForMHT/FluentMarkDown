import os
import markdown

from PyQt5.QtWidgets import (
    QTextEdit, QVBoxLayout, QFrame, QWidget, QStatusBar, QFileDialog
)
from PyQt5.QtCore import Qt,  QPoint
from PyQt5.QtGui import QPainterPath, QRegion, QColor

from qfluentwidgets import (
    FluentIcon,
    CommandBar,
    TransparentPushButton,
    CardWidget,
    ComboBox,import os
import markdown

from PyQt5.QtWidgets import (
    QTextEdit, QVBoxLayout, QFrame, QWidget, QStatusBar, QFileDialog
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainterPath, QRegion, QColor

from qfluentwidgets import (
    FluentIcon,
    CommandBar,
    TransparentPushButton,
    CardWidget,
    ComboBox,
    BodyLabel,
    SingleDirectionScrollArea,
    isDarkTheme
)
from qframelesswindow.webengine import FramelessWebEngineView

from src.models.themes import PreviewThemes

try:
    from fpdf import FPDF
    from docx import Document
    HAS_EXPORT_LIBS = True
except ImportError:
    HAS_EXPORT_LIBS = False


class MarkdownWidget(QFrame):
    """Markdown 编辑+预览"""

    PREVIEW_RADIUS = 8

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("markdownInterface")
        self.is_fullscreen = False
        self.preview_theme = "light"

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self.command_bar = CommandBar(self)
        self.setup_command_bar()

        self.card_container = QWidget(self)
        self.card_container_layout = QVBoxLayout(self.card_container)
        self.card_container_layout.setContentsMargins(5, 5, 5, 5)
        self.card_container_layout.setSpacing(0)

        # 外层 editor_card 用 CardWidget 可以，但要确保透明，别挡 Mica
        self.editor_card = CardWidget(self.card_container)
        self.editor_card.setAttribute(Qt.WA_TranslucentBackground, True)
        self.editor_card.setStyleSheet("background: transparent; border: none;")
        self.editor_layout = QVBoxLayout(self.editor_card)
        self.editor_layout.setContentsMargins(1, 1, 1, 1)
        self.editor_layout.setSpacing(0)

        from PyQt5.QtWidgets import QSplitter
        self.splitter = QSplitter(Qt.Horizontal, self.editor_card)
        self.splitter.setStyleSheet('''
            QSplitter { background-color: transparent; }
            QSplitter::handle {
                width: 4px;
                background-color: rgba(100, 149, 237, 0.25);
            }
            QSplitter::handle:hover {
                background-color: rgba(100, 149, 237, 0.55);
            }
        ''')
        self.editor_layout.addWidget(self.splitter, 1)
        self.card_container_layout.addWidget(self.editor_card, 1)

        # 左侧编辑器
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write Markdown here...")
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_area = SingleDirectionScrollArea(orient=Qt.Vertical, parent=self.editor_card)
        self.scroll_area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.scroll_area.setWidget(self.editor)
        self.scroll_area.setWidgetResizable(True)

        # 右侧容器：必须是普通 QWidget/QFrame，不能是 CardWidget（CardWidget 会画白底/阴影挡 Mica）
        self.preview_container = QFrame(self.editor_card)
        self.preview_container.setObjectName("previewContainer")
        self.preview_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview_container.setStyleSheet("QFrame#previewContainer{background:transparent;border:none;}")

        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(0)

        self.preview = FramelessWebEngineView(self.preview_container)
        self.preview.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview.setStyleSheet("background: transparent; border: none;")

        # 关键：WebEngine 默认白底，必须把 page 背景刷成透明
        try:
            self.preview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        except Exception:
            pass

        self.preview_layout.addWidget(self.preview)

        self.splitter.addWidget(self.scroll_area)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([500, 500])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("background: transparent;")
        self.setup_status_bar()

        self.vBoxLayout.addWidget(self.command_bar)
        self.vBoxLayout.addWidget(self.card_container, 1)
        self.vBoxLayout.addWidget(self.status_bar)

        self.editor.textChanged.connect(self.update_preview)
        self.editor.selectionChanged.connect(self.update_status_bar)

        self.update_editor_style()
        self.update_status_bar()
        self.update_preview()
        self._updatePreviewRoundMask()

    # ---------------- 圆角裁剪（只裁右上/右下，解决直角溢出） ----------------
    def _updatePreviewRoundMask(self):
        if self.is_fullscreen:
            self.preview_container.clearMask()
            return

        r = self.PREVIEW_RADIUS
        rect = self.preview_container.rect()
        if rect.isNull():
            return

        path = QPainterPath()
        path.moveTo(rect.topLeft())
        path.lineTo(rect.topRight() - QPoint(r, 0))
        path.quadTo(rect.topRight(), rect.topRight() + QPoint(0, r))
        path.lineTo(rect.bottomRight() - QPoint(0, r))
        path.quadTo(rect.bottomRight(), rect.bottomRight() - QPoint(r, 0))
        path.lineTo(rect.bottomLeft())
        path.closeSubpath()

        region = QRegion(path.toFillPolygon().toPolygon())
        self.preview_container.setMask(region)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._updatePreviewRoundMask()

    # ---------------- 命令栏 ----------------
    def setup_command_bar(self):
        new_button = TransparentPushButton(FluentIcon.ADD, "新建")
        new_button.clicked.connect(self.new_file)
        self.command_bar.addWidget(new_button)

        open_button = TransparentPushButton(FluentIcon.FOLDER, "打开")
        open_button.clicked.connect(self.open_file_dialog)
        self.command_bar.addWidget(open_button)

        save_button = TransparentPushButton(FluentIcon.SAVE, "保存")
        save_button.clicked.connect(self.save_file_dialog)
        self.command_bar.addWidget(save_button)

        self.command_bar.addSeparator()

        copy_button = TransparentPushButton(FluentIcon.COPY, "复制")
        copy_button.clicked.connect(self.copy)
        self.command_bar.addWidget(copy_button)

        paste_button = TransparentPushButton(FluentIcon.PASTE, "粘贴")
        paste_button.clicked.connect(self.paste)
        self.command_bar.addWidget(paste_button)

        self.command_bar.addSeparator()

        fullscreen_button = TransparentPushButton(FluentIcon.ZOOM_IN, "全屏阅读")
        fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.command_bar.addWidget(fullscreen_button)

        self.command_bar.addSeparator()
        self.setup_theme_menu()
        self.command_bar.addSeparator()

        image_button = TransparentPushButton(FluentIcon.PHOTO, "插入图片")
        image_button.clicked.connect(self.insert_image)
        self.command_bar.addWidget(image_button)

        self.command_bar.addSeparator()

        export_button = TransparentPushButton(FluentIcon.SHARE, "导出")
        export_button.clicked.connect(self.export_file)
        self.command_bar.addWidget(export_button)

    def setup_theme_menu(self):
        self.theme_label_cmd = BodyLabel("预览主题:")
        self.theme_combo = ComboBox()

        themes = PreviewThemes.get_available_themes()
        names = [PreviewThemes.get_theme_styles(t)["name"] for t in themes]
        self.theme_combo.addItems(names)
        self.theme_combo.setCurrentIndex(themes.index(self.preview_theme))

        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

        self.command_bar.addWidget(self.theme_label_cmd)
        self.command_bar.addWidget(self.theme_combo)

    def on_theme_changed(self, index):
        themes = PreviewThemes.get_available_themes()
        if 0 <= index < len(themes):
            self.preview_theme = themes[index]
            self.update_preview()
            self.update_status_bar()

    # ---------------- 状态栏 ----------------
    def setup_status_bar(self):
        self.char_count_label = BodyLabel("字符: 0", self)
        self.selection_label = BodyLabel("选中: 0", self)
        self.encoding_label = BodyLabel("编码: UTF-8", self)

        theme_info = PreviewThemes.get_theme_styles(self.preview_theme)
        self.theme_label = BodyLabel(f"预览主题: {theme_info['name']}", self)

        self.status_bar.addWidget(self.char_count_label)
        self.status_bar.addWidget(self.selection_label)
        self.status_bar.addWidget(self.theme_label)
        self.status_bar.addPermanentWidget(self.encoding_label)

    def update_status_bar(self):
        text = self.editor.toPlainText()
        self.char_count_label.setText(f"字符: {len(text)}")
        self.selection_label.setText(f"选中: {len(self.editor.textCursor().selectedText())}")
        theme_info = PreviewThemes.get_theme_styles(self.preview_theme)
        self.theme_label.setText(f"预览主题: {theme_info['name']}")

    # ---------------- 编辑器样式 ----------------
    def update_editor_style(self):
        if isDarkTheme():
            self.editor.setStyleSheet('''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #ffffff;
                selection-background-color: rgba(100,149,237,0.3);
            ''')
            self.editor.setCursorWidth(3)
        else:
            self.editor.setStyleSheet('''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #333333;
                selection-background-color: rgba(100,149,237,0.3);
            ''')
            self.editor.setCursorWidth(2)

    # ---------------- 预览：让 light 真透出 Mica，其他主题照常铺底 ----------------
    def update_preview(self):
        md_text = self.editor.toPlainText()
        html = markdown.markdown(md_text, extensions=['fenced_code'])

        ts = PreviewThemes.get_theme_styles(self.preview_theme)
        bg = ts["background_color"]   # light=transparent -> Mica 透出
        text_color = ts["text_color"]
        heading_color = ts["heading_color"]
        code_bg = ts["code_bg"]
        blockquote_bg = ts["blockquote_bg"]
        scrollbar_track = ts["scrollbar_track"]
        scrollbar_thumb = ts["scrollbar_thumb"]
        scrollbar_thumb_hover = ts["scrollbar_thumb_hover"]
        link_color = ts["link_color"]
        r = self.PREVIEW_RADIUS

        # 结构说明：
        # html/body 永远透明 => webview 角落可以透出 Mica（配合 page 背景透明）
        # .content 负责圆角裁剪 overflow:hidden
        # .scroll 负责滚动（修复滚动到底部显示不全）
        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  html, body {{
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
    background: transparent !important;
    color: {text_color};
    font-family: Arial, sans-serif;
    font-size: 16px;
  }}

  .content {{
    height: 100%;
    background: {bg};
    border-top-right-radius: {r}px;
    border-bottom-right-radius: {r}px;
    overflow: hidden;
  }}

  .scroll {{
    height: 100%;
    overflow-y: auto;
    box-sizing: border-box;
    padding: 20px 20px 36px 20px;
  }}

  ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
  ::-webkit-scrollbar-track {{ background: {scrollbar_track}; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb {{ background: {scrollbar_thumb}; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {scrollbar_thumb_hover}; }}

  h1,h2,h3,h4,h5,h6 {{ color: {heading_color}; margin: 20px 0 10px; }}
  p {{ margin: 0 0 10px; }}

  code {{ background: {code_bg}; padding: 2px 4px; border-radius: 3px; }}
  pre {{ background: {code_bg}; padding: 10px; border-radius: 5px; overflow-x: auto; margin: 10px 0; }}

  blockquote {{
    border-left: 4px solid rgba(100,149,237,0.5);
    margin: 10px 0;
    padding: 10px 15px;
    background: {blockquote_bg};
  }}

  a {{ color: {link_color}; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
  <div class="content">
    <div class="scroll">
      {html}
    </div>
  </div>
</body>
</html>
"""
        self.preview.setHtml(styled_html)
        self._updatePreviewRoundMask()
        self.update_status_bar()

    # ---------------- 基础功能 ----------------
    def new_file(self):
        self.editor.clear()

    def copy(self):
        self.editor.copy()

    def paste(self):
        from PyQt5.QtWidgets import QApplication
        import tempfile, uuid

        cb = QApplication.clipboard()
        if cb.mimeData().hasImage():
            image = cb.image()
            if not image.isNull():
                temp_dir = tempfile.gettempdir()
                file_name = f"image_{uuid.uuid4().hex}.png"
                file_path = os.path.join(temp_dir, file_name)
                if image.save(file_path, "PNG"):
                    self.editor.textCursor().insertText(f"![{file_name}]({file_path})")
                    self.update_preview()
                    return
        self.editor.paste()

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Markdown Files (*.md);;All Files (*)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())

    def save_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Markdown Files (*.md);;All Files (*)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())

    def insert_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.svg);;All Files (*)"
        )
        if file_path:
            image_name = os.path.basename(file_path)
            self.editor.textCursor().insertText(f"![{image_name}]({file_path})")
            self.update_preview()

    def toggle_fullscreen(self):
        if not self.is_fullscreen:
            self.editor.hide()
            self.splitter.setSizes([0, self.splitter.width()])
            self.card_container_layout.setContentsMargins(0, 0, 0, 0)
            self.editor_layout.setContentsMargins(0, 0, 0, 0)
            self.is_fullscreen = True
        else:
            self.editor.show()
            w = self.splitter.width()
            self.splitter.setSizes([w // 2, w // 2])
            self.card_container_layout.setContentsMargins(5, 5, 5, 5)
            self.editor_layout.setContentsMargins(1, 1, 1, 1)
            self.is_fullscreen = False

        self._updatePreviewRoundMask()

    # ---------------- 导出（保留接口） ----------------
    def export_file(self):
        file_path, file_type = QFileDialog.getSaveFileName(
            self, "Export File", "",
            "PDF Files (*.pdf);;Word Files (*.docx);;HTML Files (*.html);;All Files (*)"
        )
        if not file_path:
            return

        markdown_text = self.editor.toPlainText()

        if not file_path.endswith(('.pdf', '.docx', '.html')):
            if 'PDF Files' in file_type:
                file_path += '.pdf'
            elif 'Word Files' in file_type:
                file_path += '.docx'
            elif 'HTML Files' in file_type:
                file_path += '.html'

        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            self.export_to_pdf(file_path, markdown_text)
        elif ext == '.docx':
            self.export_to_word(file_path, markdown_text)
        elif ext == '.html':
            self.export_to_html(file_path, markdown_text)

    def export_to_pdf(self, file_path, markdown_text):
        if not HAS_EXPORT_LIBS:
            print("Error: fpdf not installed. pip install fpdf")
            return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for line in markdown_text.split('\n'):
                try:
                    pdf.multi_cell(0, 8, line)
                except UnicodeEncodeError:
                    pdf.multi_cell(0, 8, line.encode('ascii', 'ignore').decode('ascii'))
            pdf.output(file_path)
        except Exception as e:
            print(f"Error exporting to PDF: {e}")

    def export_to_word(self, file_path, markdown_text):
        if not HAS_EXPORT_LIBS:
            print("Error: python-docx not installed. pip install python-docx")
            return
        try:
            doc = Document()
            for line in markdown_text.split('\n'):
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=3)
                else:
                    if line.strip():
                        doc.add_paragraph(line)
            doc.save(file_path)
        except Exception as e:
            print(f"Error exporting to Word: {e}")

    def export_to_html(self, file_path, markdown_text):
        try:
            html = markdown.markdown(markdown_text, extensions=['fenced_code'])
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"<!doctype html><meta charset='utf-8'><body>{html}</body>")
        except Exception as e:
            print(f"Error exporting to HTML: {e}")

    BodyLabel
)
from qframelesswindow.webengine import FramelessWebEngineView

from src.models.themes import PreviewThemes

# 导出功能所需的库
try:
    from fpdf import FPDF
    from docx import Document
    HAS_EXPORT_LIBS = True
except ImportError:
    HAS_EXPORT_LIBS = False


class MarkdownWidget(QFrame):
    """Markdown 编辑和预览界面"""

    PREVIEW_RADIUS = 8

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("markdownInterface")
        self.is_fullscreen = False
        self.preview_theme = "light"

        # 主布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        # 命令栏
        self.command_bar = CommandBar(self)
        self.setup_command_bar()

        # 容器
        self.card_container = QWidget(self)
        self.card_container_layout = QVBoxLayout(self.card_container)
        self.card_container_layout.setContentsMargins(5, 5, 5, 5)
        self.card_container_layout.setSpacing(0)

        # 编辑/预览卡片（外层仍然用 CardWidget 没问题）
        self.editor_card = CardWidget(self.card_container)
        self.editor_card.setStyleSheet("background-color: transparent;")
        self.editor_layout = QVBoxLayout(self.editor_card)
        self.editor_layout.setContentsMargins(1, 1, 1, 1)
        self.editor_layout.setSpacing(0)

        # splitter
        from PyQt5.QtWidgets import QSplitter
        self.splitter = QSplitter(Qt.Horizontal, self.editor_card)
        self.splitter.setStyleSheet('''
            QSplitter { background-color: transparent; }
            QSplitter::handle { width: 4px; background-color: rgba(100,149,237,0.25); }
            QSplitter::handle:hover { background-color: rgba(100,149,237,0.55); }
        ''')
        self.editor_layout.addWidget(self.splitter, 1)
        self.card_container_layout.addWidget(self.editor_card, 1)

        # 左侧编辑器
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write Markdown here...")
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_area = SingleDirectionScrollArea(orient=Qt.Vertical, parent=self.editor_card)
        self.scroll_area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.scroll_area.setWidget(self.editor)
        self.scroll_area.setWidgetResizable(True)

        # 右侧预览容器：关键修复点 —— 不用 CardWidget，避免它自己画白底/阴影挡住 Mica
        self.preview_container = QFrame(self.editor_card)
        self.preview_container.setObjectName("previewContainer")
        self.preview_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview_container.setStyleSheet("""
            QFrame#previewContainer{
                background: transparent;
                border: none;
            }
        """)
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(0)

        # WebEngine 预览
        self.preview = FramelessWebEngineView(self.preview_container)
        self.preview.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview.setStyleSheet("background: transparent; border: none;")
        # 关键：让 WebEngine 页面背景真正透明（否则默认白）
        try:
            self.preview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        except Exception:
            pass

        self.preview_layout.addWidget(self.preview)

        # 加入 splitter
        self.splitter.addWidget(self.scroll_area)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([500, 500])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        # 状态栏
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("background-color: transparent;")
        self.setup_status_bar()

        # 主布局装载
        self.vBoxLayout.addWidget(self.command_bar)
        self.vBoxLayout.addWidget(self.card_container, 1)
        self.vBoxLayout.addWidget(self.status_bar)

        # 信号
        self.editor.textChanged.connect(self.update_preview)
        self.editor.selectionChanged.connect(self.update_status_bar)

        # 初始化
        self.update_editor_style()
        self.update_status_bar()
        self.update_preview()
        self._updatePreviewRoundMask()

    # ---------------- 圆角裁剪（只裁右上/右下） ----------------
    def _updatePreviewRoundMask(self):
        if not hasattr(self, "preview_container"):
            return

        if self.is_fullscreen:
            self.preview_container.clearMask()
            return

        r = self.PREVIEW_RADIUS
        rect = self.preview_container.rect()
        if rect.isNull():
            return

        path = QPainterPath()
        path.moveTo(rect.topLeft())
        path.lineTo(rect.topRight() - QPoint(r, 0))
        path.quadTo(rect.topRight(), rect.topRight() + QPoint(0, r))
        path.lineTo(rect.bottomRight() - QPoint(0, r))
        path.quadTo(rect.bottomRight(), rect.bottomRight() - QPoint(r, 0))
        path.lineTo(rect.bottomLeft())
        path.closeSubpath()

        region = QRegion(path.toFillPolygon().toPolygon())
        self.preview_container.setMask(region)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._updatePreviewRoundMask()

    # ---------------- 命令栏 ----------------
    def setup_command_bar(self):
        new_button = TransparentPushButton(FluentIcon.ADD, "新建")
        new_button.clicked.connect(self.new_file)
        self.command_bar.addWidget(new_button)

        open_button = TransparentPushButton(FluentIcon.FOLDER, "打开")
        open_button.clicked.connect(self.open_file_dialog)
        self.command_bar.addWidget(open_button)

        save_button = TransparentPushButton(FluentIcon.SAVE, "保存")
        save_button.clicked.connect(self.save_file_dialog)
        self.command_bar.addWidget(save_button)

        self.command_bar.addSeparator()

        copy_button = TransparentPushButton(FluentIcon.COPY, "复制")
        copy_button.clicked.connect(self.copy)
        self.command_bar.addWidget(copy_button)

        paste_button = TransparentPushButton(FluentIcon.PASTE, "粘贴")
        paste_button.clicked.connect(self.paste)
        self.command_bar.addWidget(paste_button)

        self.command_bar.addSeparator()

        fullscreen_button = TransparentPushButton(FluentIcon.ZOOM_IN, "全屏阅读")
        fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.command_bar.addWidget(fullscreen_button)

        self.command_bar.addSeparator()

        self.setup_theme_menu()

        self.command_bar.addSeparator()

        image_button = TransparentPushButton(FluentIcon.PHOTO, "插入图片")
        image_button.clicked.connect(self.insert_image)
        self.command_bar.addWidget(image_button)

        self.command_bar.addSeparator()

        export_button = TransparentPushButton(FluentIcon.SHARE, "导出")
        export_button.clicked.connect(self.export_file)
        self.command_bar.addWidget(export_button)

    def setup_theme_menu(self):
        self.theme_label_cmd = BodyLabel("预览主题:")
        self.theme_combo = ComboBox()

        themes = PreviewThemes.get_available_themes()
        theme_names = []
        current_index = 0
        for i, theme in enumerate(themes):
            theme_info = PreviewThemes.get_theme_styles(theme)
            theme_names.append(theme_info["name"])
            if theme == self.preview_theme:
                current_index = i

        self.theme_combo.addItems(theme_names)
        self.theme_combo.setCurrentIndex(current_index)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

        self.command_bar.addWidget(self.theme_label_cmd)
        self.command_bar.addWidget(self.theme_combo)

    def on_theme_changed(self, index):
        themes = PreviewThemes.get_available_themes()
        if 0 <= index < len(themes):
            self.set_preview_theme(themes[index])

    def set_preview_theme(self, theme_name):
        self.preview_theme = theme_name
        self.update_preview()
        self.update_status_bar()

        themes = PreviewThemes.get_available_themes()
        if theme_name in themes:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(themes.index(theme_name))
            self.theme_combo.blockSignals(False)

    # ---------------- 状态栏 ----------------
    def setup_status_bar(self):
        self.char_count_label = BodyLabel("字符: 0", self)
        self.selection_label = BodyLabel("选中: 0", self)
        self.encoding_label = BodyLabel("编码: UTF-8", self)

        theme_info = PreviewThemes.get_theme_styles(self.preview_theme)
        self.theme_label = BodyLabel(f"预览主题: {theme_info['name']}", self)

        self.status_bar.addWidget(self.char_count_label)
        self.status_bar.addWidget(self.selection_label)
        self.status_bar.addWidget(self.theme_label)
        self.status_bar.addPermanentWidget(self.encoding_label)

    def update_status_bar(self):
        text = self.editor.toPlainText()
        self.char_count_label.setText(f"字符: {len(text)}")
        self.selection_label.setText(f"选中: {len(self.editor.textCursor().selectedText())}")

        theme_info = PreviewThemes.get_theme_styles(self.preview_theme)
        self.theme_label.setText(f"预览主题: {theme_info['name']}")

    # ---------------- 编辑器样式 ----------------
    def update_editor_style(self):
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        if is_dark:
            self.editor.setStyleSheet('''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #ffffff;
                selection-background-color: rgba(100, 149, 237, 0.3);
            ''')
            self.editor.setCursorWidth(3)
        else:
            self.editor.setStyleSheet('''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #333333;
                selection-background-color: rgba(100, 149, 237, 0.3);
            ''')
            self.editor.setCursorWidth(2)

    # ---------------- 预览：Mica + 圆角 + 底部滚动修复 ----------------
    def update_preview(self):
        md_text = self.editor.toPlainText()
        html = markdown.markdown(md_text, extensions=['fenced_code'])

        ts = PreviewThemes.get_theme_styles(self.preview_theme)
        bg = ts["background_color"]  # light=transparent -> 透出 Mica
        text_color = ts["text_color"]
        heading_color = ts["heading_color"]
        code_bg = ts["code_bg"]
        blockquote_bg = ts["blockquote_bg"]
        scrollbar_track = ts["scrollbar_track"]
        scrollbar_thumb = ts["scrollbar_thumb"]
        scrollbar_thumb_hover = ts["scrollbar_thumb_hover"]
        link_color = ts["link_color"]
        r = self.PREVIEW_RADIUS

        # 关键点：
        # - html/body 永远透明 -> 角落透出 Mica
        # - .content 用主题 bg（浅色 transparent 直接透出 Mica；其他主题为实色）
        # - .content 负责圆角裁剪（overflow:hidden）
        # - .scroll 负责滚动，避免底部显示不全
        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  html, body {{
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
    background: transparent !important;
    color: {text_color};
    font-family: Arial, sans-serif;
    font-size: 16px;
  }}

  .content {{
    height: 100%;
    background: {bg};
    border-top-right-radius: {r}px;
    border-bottom-right-radius: {r}px;
    overflow: hidden;
  }}

  .scroll {{
    height: 100%;
    overflow-y: auto;
    box-sizing: border-box;
    padding: 20px 20px 36px 20px;
  }}

  ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
  ::-webkit-scrollbar-track {{ background: {scrollbar_track}; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb {{ background: {scrollbar_thumb}; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {scrollbar_thumb_hover}; }}

  h1,h2,h3,h4,h5,h6 {{ color: {heading_color}; margin: 20px 0 10px; }}
  p {{ margin: 0 0 10px; }}

  code {{ background: {code_bg}; padding: 2px 4px; border-radius: 3px; }}
  pre {{ background: {code_bg}; padding: 10px; border-radius: 5px; overflow-x: auto; margin: 10px 0; }}

  blockquote {{
    border-left: 4px solid rgba(100,149,237,0.5);
    margin: 10px 0;
    padding: 10px 15px;
    background: {blockquote_bg};
  }}

  a {{ color: {link_color}; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
  th, td {{ border: 1px solid rgba(0,0,0,0.12); padding: 8px; text-align: left; }}
  th {{ background: {code_bg}; }}
</style>
</head>
<body>
  <div class="content">
    <div class="scroll">
      {html}
    </div>
  </div>
</body>
</html>
"""
        self.preview.setHtml(styled_html)
        self._updatePreviewRoundMask()
        self.update_status_bar()

    # ---------------- 基础功能 ----------------
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Markdown Files (*.md);;All Files (*)")
        self.open_file(file_path)

    def save_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Markdown Files (*.md);;All Files (*)")
        self.save_file(file_path)

    def open_file(self, file_path):
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())

    def save_file(self, file_path):
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())

    def new_file(self):
        self.editor.clear()

    def copy(self):
        self.editor.copy()

    def paste(self):
        from PyQt5.QtWidgets import QApplication
        import tempfile, uuid

        clipboard = QApplication.clipboard()
        if clipboard.mimeData().hasImage():
            image = clipboard.image()
            if not image.isNull():
                temp_dir = tempfile.gettempdir()
                file_name = f"image_{uuid.uuid4().hex}.png"
                file_path = os.path.join(temp_dir, file_name)
                if image.save(file_path, "PNG"):
                    self.editor.textCursor().insertText(f"![{file_name}]({file_path})")
                    self.update_preview()
                    return
        self.editor.paste()

    def insert_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.svg);;All Files (*)"
        )
        if file_path:
            image_name = os.path.basename(file_path)
            self.editor.textCursor().insertText(f"![{image_name}]({file_path})")
            self.update_preview()

    def toggle_fullscreen(self):
        if not self.is_fullscreen:
            self.editor.hide()
            self.splitter.setSizes([0, self.splitter.width()])
            self.editor_layout.setContentsMargins(0, 0, 0, 0)
            self.card_container_layout.setContentsMargins(0, 0, 0, 0)
            self.is_fullscreen = True
        else:
            self.editor.show()
            w = self.splitter.width()
            self.splitter.setSizes([w // 2, w // 2])
            self.editor_layout.setContentsMargins(1, 1, 1, 1)
            self.card_container_layout.setContentsMargins(5, 5, 5, 5)
            self.is_fullscreen = False

        self._updatePreviewRoundMask()

    # ---------------- 导出（保持原逻辑，略） ----------------
    def export_file(self):
        file_path, file_type = QFileDialog.getSaveFileName(
            self, "Export File", "",
            "PDF Files (*.pdf);;Word Files (*.docx);;HTML Files (*.html);;All Files (*)"
        )
        if not file_path:
            return

        markdown_text = self.editor.toPlainText()

        if not file_path.endswith(('.pdf', '.docx', '.html')):
            if 'PDF Files' in file_type:
                file_path += '.pdf'
            elif 'Word Files' in file_type:
                file_path += '.docx'
            elif 'HTML Files' in file_type:
                file_path += '.html'

        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            self.export_to_pdf(file_path, markdown_text)
        elif ext == '.docx':
            self.export_to_word(file_path, markdown_text)
        elif ext == '.html':
            self.export_to_html(file_path, markdown_text)

    def export_to_pdf(self, file_path, markdown_text):
        if not HAS_EXPORT_LIBS:
            print("Error: fpdf not installed. pip install fpdf")
            return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for line in markdown_text.split('\n'):
                try:
                    pdf.multi_cell(0, 8, line)
                except UnicodeEncodeError:
                    pdf.multi_cell(0, 8, line.encode('ascii', 'ignore').decode('ascii'))
            pdf.output(file_path)
        except Exception as e:
            print(f"Error exporting to PDF: {e}")

    def export_to_word(self, file_path, markdown_text):
        if not HAS_EXPORT_LIBS:
            print("Error: python-docx not installed. pip install python-docx")
            return
        try:
            doc = Document()
            for line in markdown_text.split('\n'):
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=3)
                else:
                    if line.strip():
                        doc.add_paragraph(line)
            doc.save(file_path)
        except Exception as e:
            print(f"Error exporting to Word: {e}")

    def export_to_html(self, file_path, markdown_text):
        try:
            html = markdown.markdown(markdown_text, extensions=['fenced_code'])
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"<!doctype html><meta charset='utf-8'><body>{html}</body>")
        except Exception as e:
            print(f"Error exporting to HTML: {e}")
