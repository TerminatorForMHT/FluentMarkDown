from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QFrame, QLabel, QHBoxLayout, QWidget, QStatusBar, QMenu, QAction
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
from models.themes import PreviewThemes

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
        
        # 创建容器和水平布局
        self.container = QWidget(self.editor_card)
        self.container.setStyleSheet("background-color: transparent;")
        self.hBoxLayout = QHBoxLayout(self.container)
        # 确保预览框与容器边缘对齐，使用容器的圆角
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        # 缩小编辑框和预览框之间的间距
        self.hBoxLayout.setSpacing(0)
        
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
        
        # 添加到水平布局，各占50%宽度
        self.hBoxLayout.addWidget(self.scroll_area, 1)
        self.hBoxLayout.addWidget(self.preview_container, 1)
        self.editor_layout.addWidget(self.container, 1)
        
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
        
        # 初始化时更新编辑器样式
        self.update_editor_style()
        self.update_status_bar()
    
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
        self.editor.paste()
    
    def export_file(self):
        """
        导出文件
        """
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export File", "", "PDF Files (*.pdf);;Word Files (*.docx);;All Files (*)")
        if file_path:
            # 这里可以添加具体的导出逻辑
            pass
    
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
            # 调整光标宽度
            self.editor.setCursorWidth(2)
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
            # 调整光标宽度
            self.editor.setCursorWidth(1)
        
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
            self.preview_container.show()  # 确保预览容器显示
            self.is_fullscreen = True
        else:
            # 退出全屏模式
            self.editor.show()  # 显示编辑器
            self.preview_container.show()  # 确保预览容器显示
            self.is_fullscreen = False
