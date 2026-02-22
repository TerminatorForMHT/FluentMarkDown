from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QFrame, QLabel, QHBoxLayout, QWidget, QStatusBar, QMenu, QAction, QFileDialog
from qfluentwidgets import (
    FluentIcon,
    CommandBar,
    TransparentPushButton,
    CardWidget,
    ComboBox,
    BodyLabel,
    ScrollBar,
    SmoothScrollBar,
    SingleDirectionScrollArea
)
from PyQt5.QtCore import Qt
from qframelesswindow.webengine import FramelessWebEngineView
import markdown
import os
from models.themes import PreviewThemes

# 导出功能所需的库
try:
    from fpdf import FPDF
    from docx import Document
    HAS_EXPORT_LIBS = True
except ImportError:
    HAS_EXPORT_LIBS = False

class MarkdownWidget(QFrame):
    """
    Markdown 编辑和预览界面
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("markdownInterface")
        self.is_fullscreen = False
        self.preview_theme = "light"  # 默认预览框主题
        
        # 创建主布局
        self.vBoxLayout = QVBoxLayout(self)
        # 留出标题栏的空间
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        
        # 创建命令栏（不使用卡片容器）
        self.command_bar = CommandBar(self)
        self.setup_command_bar()
        
        # 创建一个容器来放置编辑和预览卡片
        self.card_container = QWidget(self)
        self.card_container_layout = QVBoxLayout(self.card_container)
        # 设置容器与主窗口边缘的间距
        self.card_container_layout.setContentsMargins(5, 5, 5, 5)
        self.card_container_layout.setSpacing(0)
        
        # 创建编辑和预览卡片
        self.editor_card = CardWidget(self.card_container)
        self.editor_card.setStyleSheet("background-color: transparent;")
        self.editor_layout = QVBoxLayout(self.editor_card)
        # 确保编辑框和预览框与CardWidget容器之间有间距
        self.editor_layout.setContentsMargins(1, 1, 1, 1)
        self.editor_layout.setSpacing(0)
        
        # 使用QSplitter替代QHBoxLayout，实现可调整宽度
        from PyQt5.QtWidgets import QSplitter
        self.splitter = QSplitter(Qt.Horizontal, self.editor_card)
        self.splitter.setStyleSheet('''
            QSplitter {
                background-color: transparent;
            }
            QSplitter::handle {
                width: 4px;
                background-color: rgba(100, 149, 237, 0.3);
            }
            QSplitter::handle:hover {
                background-color: rgba(100, 149, 237, 0.6);
            }
        ''')
        
        # 将分隔器添加到编辑布局
        self.editor_layout.addWidget(self.splitter, 1)
        
        # 将编辑卡片添加到容器中
        self.card_container_layout.addWidget(self.editor_card, 1)
        
        # 创建编辑窗口
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write Markdown here...")
        # 关闭编辑框原生的横竖滑动条
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 优化光标，使其更明显
        self.editor.setStyleSheet('''
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 8px 0px 0px 8px;
            padding: 10px;
            color: #333333;
            selection-background-color: rgba(100, 149, 237, 0.3);
        ''')
        
        # 创建单方向滚动区域，设置为竖直方向
        self.scroll_area = SingleDirectionScrollArea(orient=Qt.Vertical, parent=self.editor_card)
        # 设置滚动区域的样式，确保没有边框和背景色
        self.scroll_area.setStyleSheet('''
            QScrollArea {
                background: transparent;
                border: none;
            }
        ''')
        self.scroll_area.setWidget(self.editor)
        # 确保编辑框填充整个滚动区域
        self.scroll_area.setWidgetResizable(True)
        
        # 创建预览容器
        self.preview_container = CardWidget(self.editor_card)
        self.preview_container.setStyleSheet("""
            background-color: white;
            border: none;
            border-radius: 0px 8px 8px 0px;
        """)
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(0)
        
        # 创建预览窗口
        self.preview = FramelessWebEngineView(self.preview_container)
        self.preview.setStyleSheet("""
            background-color: transparent;
            border: none;
            border-radius: 0px 8px 8px 0px;
        """)
        self.preview_layout.addWidget(self.preview)
        
        # 添加到分隔器，各占50%宽度
        self.splitter.addWidget(self.scroll_area)
        self.splitter.addWidget(self.preview_container)
        # 设置初始大小比例
        self.splitter.setSizes([500, 500])
        # 设置拉伸因子，确保两边都能随窗口大小调整
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        
        # 创建状态栏（不使用卡片容器）
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("background-color: transparent;")
        self.setup_status_bar()
        
        # 添加到布局
        self.vBoxLayout.addWidget(self.command_bar)
        self.vBoxLayout.addWidget(self.card_container, 1)
        self.vBoxLayout.addWidget(self.status_bar)
        
        # 连接信号
        self.editor.textChanged.connect(self.update_preview)
        self.editor.selectionChanged.connect(self.update_status_bar)
        
        # 初始化时更新编辑器样式和预览
        self.update_editor_style()
        self.update_status_bar()
        self.update_preview()
    
    def setup_command_bar(self):
        """
        设置命令栏
        """
        # 新建文件
        new_button = TransparentPushButton(FluentIcon.ADD, "新建")
        new_button.clicked.connect(self.new_file)
        self.command_bar.addWidget(new_button)
        
        # 打开文件
        open_button = TransparentPushButton(FluentIcon.FOLDER, "打开")
        open_button.clicked.connect(self.open_file_dialog)
        self.command_bar.addWidget(open_button)
        
        # 保存文件
        save_button = TransparentPushButton(FluentIcon.SAVE, "保存")
        save_button.clicked.connect(self.save_file_dialog)
        self.command_bar.addWidget(save_button)
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 复制
        copy_button = TransparentPushButton(FluentIcon.COPY, "复制")
        copy_button.clicked.connect(self.copy)
        self.command_bar.addWidget(copy_button)
        
        # 粘贴
        paste_button = TransparentPushButton(FluentIcon.PASTE, "粘贴")
        paste_button.clicked.connect(self.paste)
        self.command_bar.addWidget(paste_button)
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 全屏阅读
        fullscreen_button = TransparentPushButton(FluentIcon.ZOOM_IN, "全屏阅读")
        fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.command_bar.addWidget(fullscreen_button)
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 预览主题菜单
        self.setup_theme_menu()
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 插入图片
        image_button = TransparentPushButton(FluentIcon.PHOTO, "插入图片")
        image_button.clicked.connect(self.insert_image)
        self.command_bar.addWidget(image_button)
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 导出
        export_button = TransparentPushButton(FluentIcon.SHARE, "导出")
        export_button.clicked.connect(self.export_file)
        self.command_bar.addWidget(export_button)
    
    def setup_theme_menu(self):
        """
        设置主题菜单
        """
        try:
            # 创建主题标签
            self.theme_label = BodyLabel("预览主题:")
            
            # 创建主题下拉框
            self.theme_combo = ComboBox()
            
            # 添加主题选项
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
            
            # 连接索引改变信号
            self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
            
            # 添加到命令栏
            self.command_bar.addWidget(self.theme_label)
            self.command_bar.addWidget(self.theme_combo)
        except Exception as e:
            print(f"Error setting up theme menu: {e}")
    
    def on_theme_changed(self, index):
        """
        主题下拉框索引改变处理
        
        Args:
            index: 选中的索引
        """
        try:
            themes = PreviewThemes.get_available_themes()
            if 0 <= index < len(themes):
                theme_name = themes[index]
                self.set_preview_theme(theme_name)
        except Exception as e:
            print(f"Error changing theme: {e}")
    
    def set_preview_theme(self, theme_name):
        """
        设置预览框主题
        
        Args:
            theme_name: 主题名称
        """
        try:
            self.preview_theme = theme_name
            self.update_preview()
            
            # 更新下拉框选中状态
            if hasattr(self, 'theme_combo'):
                themes = PreviewThemes.get_available_themes()
                if theme_name in themes:
                    index = themes.index(theme_name)
                    self.theme_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error setting theme: {e}")
    
    def open_file_dialog(self):
        """
        打开文件对话框
        """
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Markdown Files (*.md);;All Files (*)")
        self.open_file(file_path)
    
    def save_file_dialog(self):
        """
        保存文件对话框
        """
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Markdown Files (*.md);;All Files (*)")
        self.save_file(file_path)
    
    def new_file(self):
        """
        新建文件
        """
        self.editor.clear()
    
    def copy(self):
        """
        复制
        """
        self.editor.copy()
    
    def paste(self):
        """
        粘贴
        """
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QClipboard, QImage
        import tempfile
        
        # 获取剪贴板
        clipboard = QApplication.clipboard()
        
        # 检查剪贴板是否包含图片
        if clipboard.mimeData().hasImage():
            # 从剪贴板获取图片
            image = clipboard.image()
            
            if not image.isNull():
                # 创建临时目录
                temp_dir = tempfile.gettempdir()
                
                # 生成唯一的文件名
                import uuid
                file_name = f"image_{uuid.uuid4().hex}.png"
                file_path = os.path.join(temp_dir, file_name)
                
                # 保存图片
                if image.save(file_path, "PNG"):
                    # 构建Markdown图片语法
                    markdown_image = f"![{file_name}]({file_path})"
                    
                    # 在当前光标位置插入图片
                    cursor = self.editor.textCursor()
                    cursor.insertText(markdown_image)
                    
                    # 更新预览
                    self.update_preview()
                    return
        
        # 如果不是图片，执行普通粘贴
        self.editor.paste()
    
    def export_file(self):
        """
        导出文件
        """
        file_path, file_type = QFileDialog.getSaveFileName(
            self, "Export File", "", 
            "PDF Files (*.pdf);;Word Files (*.docx);;HTML Files (*.html);;All Files (*)"
        )
        if file_path:
            print(f"Export path selected: {file_path}")
            markdown_text = self.editor.toPlainText()
            
            # 确保文件有正确的扩展名
            if not file_path.endswith(('.pdf', '.docx', '.html')):
                # 根据选择的文件类型添加扩展名
                if 'PDF Files' in file_type:
                    file_path += '.pdf'
                elif 'Word Files' in file_type:
                    file_path += '.docx'
                elif 'HTML Files' in file_type:
                    file_path += '.html'
            
            print(f"Final export path: {file_path}")
            
            # 根据文件扩展名确定导出格式
            ext = os.path.splitext(file_path)[1].lower()
            print(f"Export format: {ext}")
            
            if ext == '.pdf':
                self.export_to_pdf(file_path, markdown_text)
            elif ext == '.docx':
                self.export_to_word(file_path, markdown_text)
            elif ext == '.html':
                self.export_to_html(file_path, markdown_text)
            else:
                print(f"Unsupported format: {ext}")
    
    def export_to_pdf(self, file_path, markdown_text):
        """
        导出为PDF
        """
        if not HAS_EXPORT_LIBS:
            print("Error: fpdf library not installed. Please install with 'pip install fpdf'")
            return
        
        try:
            # 创建PDF对象
            pdf = FPDF()
            pdf.add_page()
            
            # 设置字体为支持中文的字体
            # 注意：fpdf默认不支持中文，这里使用一种简单的方法处理
            # 对于包含中文的文本，我们将其转换为纯文本并确保编码正确
            pdf.set_font("Arial", size=12)
            
            # 转换Markdown为纯文本，并确保编码正确
            lines = markdown_text.split('\n')
            
            for line in lines:
                # 处理标题
                if line.startswith('# '):
                    pdf.set_font("Arial", 'B', size=16)
                    # 尝试处理中文
                    try:
                        pdf.cell(200, 10, txt=line[2:], ln=True, align='L')
                    except UnicodeEncodeError:
                        # 如果有编码错误，尝试转换为纯文本
                        safe_text = line[2:].encode('ascii', 'ignore').decode('ascii')
                        pdf.cell(200, 10, txt=safe_text, ln=True, align='L')
                    pdf.set_font("Arial", size=12)
                elif line.startswith('## '):
                    pdf.set_font("Arial", 'B', size=14)
                    try:
                        pdf.cell(200, 10, txt=line[3:], ln=True, align='L')
                    except UnicodeEncodeError:
                        safe_text = line[3:].encode('ascii', 'ignore').decode('ascii')
                        pdf.cell(200, 10, txt=safe_text, ln=True, align='L')
                    pdf.set_font("Arial", size=12)
                elif line.startswith('### '):
                    pdf.set_font("Arial", 'B', size=12)
                    try:
                        pdf.cell(200, 10, txt=line[4:], ln=True, align='L')
                    except UnicodeEncodeError:
                        safe_text = line[4:].encode('ascii', 'ignore').decode('ascii')
                        pdf.cell(200, 10, txt=safe_text, ln=True, align='L')
                    pdf.set_font("Arial", size=12)
                else:
                    # 普通文本
                    try:
                        pdf.multi_cell(200, 10, txt=line, align='L')
                    except UnicodeEncodeError:
                        safe_text = line.encode('ascii', 'ignore').decode('ascii')
                        pdf.multi_cell(200, 10, txt=safe_text, align='L')
            
            # 保存PDF
            pdf.output(file_path)
            print(f"Exported to PDF: {file_path}")
        except Exception as e:
            print(f"Error exporting to PDF: {e}")
    
    def export_to_word(self, file_path, markdown_text):
        """
        导出为Word
        """
        if not HAS_EXPORT_LIBS:
            print("Error: python-docx library not installed. Please install with 'pip install python-docx'")
            return
        
        try:
            # 创建Word文档
            doc = Document()
            
            # 转换Markdown为Word格式
            lines = markdown_text.split('\n')
            
            for line in lines:
                # 处理标题
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=3)
                elif line.startswith('```'):
                    # 代码块
                    pass  # 简化处理
                elif line.startswith('> '):
                    # 引用
                    doc.add_paragraph(line[2:], style='Intense Quote')
                else:
                    # 普通文本
                    if line.strip():
                        doc.add_paragraph(line)
            
            # 保存Word文档
            doc.save(file_path)
            print(f"Exported to Word: {file_path}")
        except Exception as e:
            print(f"Error exporting to Word: {e}")
    
    def export_to_html(self, file_path, markdown_text):
        """
        导出为HTML
        """
        try:
            # 转换Markdown为HTML
            html = markdown.markdown(markdown_text, extensions=['fenced_code'])
            
            # 添加基本HTML结构
            full_html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Markdown Export</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 20px;
                    }
                    h1, h2, h3 {
                        color: #333;
                    }
                    code {
                        background-color: #f4f4f4;
                        padding: 2px 4px;
                        border-radius: 3px;
                    }
                    pre {
                        background-color: #f4f4f4;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }
                    blockquote {
                        border-left: 4px solid #ddd;
                        margin: 10px 0;
                        padding: 10px 15px;
                        background-color: #f9f9f9;
                    }
                </style>
            </head>
            <body>
                ''' + html + '''
            </body>
            </html>
            '''
            
            # 保存HTML文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            print(f"Exported to HTML: {file_path}")
        except Exception as e:
            print(f"Error exporting to HTML: {e}")
    
    def setup_status_bar(self):
        """
        设置状态栏
        """
        # 创建状态栏标签
        self.char_count_label = QLabel("字符: 0", self)
        self.selection_label = QLabel("选中: 0", self)
        self.encoding_label = QLabel("编码: UTF-8", self)
        theme_info = PreviewThemes.get_theme_styles(self.preview_theme)
        self.theme_label = QLabel(f"预览主题: {theme_info['name']}", self)
        
        # 添加到状态栏
        self.status_bar.addWidget(self.char_count_label)
        self.status_bar.addWidget(self.selection_label)
        self.status_bar.addWidget(self.theme_label)
        self.status_bar.addPermanentWidget(self.encoding_label)
    
    def update_status_bar(self):
        """
        更新状态栏信息
        """
        # 计算字符数
        text = self.editor.toPlainText()
        char_count = len(text)
        
        # 计算选中字符数
        selected_text = self.editor.textCursor().selectedText()
        selection_count = len(selected_text)
        
        # 更新主题显示
        theme_info = PreviewThemes.get_theme_styles(self.preview_theme)
        theme_text = f"预览主题: {theme_info['name']}"
        
        # 更新状态栏标签
        self.char_count_label.setText(f"字符: {char_count}")
        self.selection_label.setText(f"选中: {selection_count}")
        self.theme_label.setText(theme_text)
    
    def update_editor_style(self):
        """
        根据当前主题更新编辑器样式
        """
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        
        if is_dark:
            # 深色模式样式
            self.editor.setStyleSheet('''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #ffffff;
                selection-background-color: rgba(100, 149, 237, 0.3);
            ''')
            # 调整光标宽度，使其更明显
            self.editor.setCursorWidth(3)
        else:
            # 浅色模式样式
            self.editor.setStyleSheet('''
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px;
                color: #333333;
                selection-background-color: rgba(100, 149, 237, 0.3);
            ''')
            # 调整光标宽度，使其更明显
            self.editor.setCursorWidth(2)
        
        # 确保滚动区域的样式保持正确
        self.scroll_area.setStyleSheet('''
            QScrollArea {
                background: transparent;
                border: none;
            }
        ''')
    
    def update_preview(self):
        """
        更新预览窗口
        """
        markdown_text = self.editor.toPlainText()
        # 确保正确处理代码块
        html = markdown.markdown(markdown_text, extensions=['fenced_code'])
        
        # 获取主题样式
        theme_styles = PreviewThemes.get_theme_styles(self.preview_theme)
        
        # 根据预览主题设置样式
        background_color = theme_styles["background_color"]
        text_color = theme_styles["text_color"]
        heading_color = theme_styles["heading_color"]
        code_bg = theme_styles["code_bg"]
        blockquote_bg = theme_styles["blockquote_bg"]
        scrollbar_track = theme_styles["scrollbar_track"]
        scrollbar_thumb = theme_styles["scrollbar_thumb"]
        scrollbar_thumb_hover = theme_styles["scrollbar_thumb_hover"]
        link_color = theme_styles["link_color"]
        
        # 添加样式到预览 HTML
        styled_html = '''
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                html, body {
                    background-color: ''' + background_color + ''';
                    color: ''' + text_color + ''';
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                    font-size: 16px;
                    height: 100%;
                    overflow: hidden;
                }
                .content {
                    padding: 20px;
                    height: 100%;
                    overflow-y: auto;
                    background-color: ''' + background_color + ''';
                }
                /* 适配Fluent Design风格的滚动条 */
                ::-webkit-scrollbar {
                    width: 8px;
                    height: 8px;
                }
                ::-webkit-scrollbar-track {
                    background: ''' + scrollbar_track + ''';
                    border-radius: 4px;
                }
                ::-webkit-scrollbar-thumb {
                    background: ''' + scrollbar_thumb + ''';
                    border-radius: 4px;
                }
                ::-webkit-scrollbar-thumb:hover {
                    background: ''' + scrollbar_thumb_hover + ''';
                }
                h1, h2, h3, h4, h5, h6 {
                    color: ''' + heading_color + ''';
                    margin-top: 20px;
                    margin-bottom: 10px;
                }
                p {
                    margin-bottom: 10px;
                }
                code {
                    background-color: ''' + code_bg + ''';
                    padding: 2px 4px;
                    border-radius: 3px;
                }
                pre {
                    background-color: ''' + code_bg + ''';
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                    margin: 10px 0;
                }
                blockquote {
                    border-left: 4px solid rgba(100, 149, 237, 0.5);
                    margin: 10px 0;
                    padding: 10px 15px;
                    background-color: ''' + blockquote_bg + ''';
                }
                a {
                    color: ''' + link_color + ''';
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
                ul, ol {
                    padding-left: 20px;
                    margin: 10px 0;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }
                th {
                    background-color: ''' + code_bg + ''';
                }
            </style>
        </head>
        <body>
            <div class="content">
                ''' + html + '''
            </div>
        </body>
        </html>
        '''
        self.preview.setHtml(styled_html)
        # 更新状态栏信息
        self.update_status_bar()
    
    def open_file(self, file_path):
        """
        打开文件
        """
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor.setPlainText(content)
    
    def save_file(self, file_path):
        """
        保存文件
        """
        if file_path:
            content = self.editor.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    

    

    
    def toggle_fullscreen(self):
        """
        切换全屏阅读模式
        """
        if not self.is_fullscreen:
            # 进入全屏模式
            self.editor.hide()  # 隐藏编辑器
            
            # 调整分隔器，让预览容器占据整个宽度
            if hasattr(self, 'splitter'):
                # 获取分隔器中的所有部件
                widgets = [self.splitter.widget(i) for i in range(self.splitter.count())]
                # 找到预览容器的索引
                preview_index = -1
                for i, widget in enumerate(widgets):
                    if widget == self.preview_container:
                        preview_index = i
                        break
                # 设置分隔器大小，让预览容器占据整个宽度
                if preview_index != -1:
                    total_width = self.splitter.width()
                    sizes = [0] * self.splitter.count()
                    sizes[preview_index] = total_width
                    self.splitter.setSizes(sizes)
            
            # 移除所有边距，确保预览框占满整个宽度
            if hasattr(self, 'editor_layout'):
                self.editor_layout.setContentsMargins(0, 0, 0, 0)
            if hasattr(self, 'preview_layout'):
                self.preview_layout.setContentsMargins(0, 0, 0, 0)
            if hasattr(self, 'card_container_layout'):
                self.card_container_layout.setContentsMargins(0, 0, 0, 0)
            if hasattr(self, 'vBoxLayout'):
                self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
            
            # 调整预览容器样式，移除边框和圆角
            self.preview_container.setStyleSheet("""
                background-color: white;
                border: none;
                border-radius: 0px;
            """)
            
            # 调整editor_card样式，移除边框
            self.editor_card.setStyleSheet("background-color: transparent; border: none;")
            
            # 调整card_container样式，确保没有边距
            if hasattr(self, 'card_container'):
                self.card_container.setStyleSheet("background-color: transparent; padding: 0px;")
            
            # 强制布局更新
            self.updateGeometry()
            self.card_container.adjustSize()
            self.editor_card.adjustSize()
            self.resize(self.size())  # 强制窗口重绘
            
            self.is_fullscreen = True
        else:
            # 退出全屏模式
            # 显示编辑器
            self.editor.show()  # 显示编辑器
            
            # 重置分隔器，让编辑框和预览容器平分空间
            if hasattr(self, 'splitter'):
                total_width = self.splitter.width()
                half_width = total_width // 2
                sizes = [half_width, half_width]
                self.splitter.setSizes(sizes)
            
            # 恢复边距
            if hasattr(self, 'editor_layout'):
                self.editor_layout.setContentsMargins(1, 1, 1, 1)
            if hasattr(self, 'preview_layout'):
                self.preview_layout.setContentsMargins(0, 0, 0, 0)
            if hasattr(self, 'card_container_layout'):
                self.card_container_layout.setContentsMargins(5, 5, 5, 5)
            if hasattr(self, 'vBoxLayout'):
                self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
            
            # 恢复预览容器样式
            self.preview_container.setStyleSheet("""
                background-color: white;
                border: none;
                border-radius: 0px 8px 8px 0px;
            """)
            
            # 恢复editor_card样式
            self.editor_card.setStyleSheet("background-color: transparent;")
            
            # 恢复card_container样式
            if hasattr(self, 'card_container'):
                self.card_container.setStyleSheet("")
            
            # 强制布局更新
            self.updateGeometry()
            self.card_container.adjustSize()
            self.editor_card.adjustSize()
            self.resize(self.size())  # 强制窗口重绘
            
            self.is_fullscreen = False
    
    def insert_image(self):
        """
        插入图片
        """
        # 打开文件对话框选择图片
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.svg);;All Files (*)"
        )
        
        if file_path:
            # 获取图片文件名
            image_name = os.path.basename(file_path)
            
            # 构建Markdown图片语法
            markdown_image = f"![{image_name}]({file_path})"
            
            # 在当前光标位置插入图片
            cursor = self.editor.textCursor()
            cursor.insertText(markdown_image)
            
            # 更新预览
            self.update_preview()
