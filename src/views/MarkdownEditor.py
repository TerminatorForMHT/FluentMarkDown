from PyQt5.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QStatusBar, QLabel
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    CardWidget,
    CommandBar,
    TransparentPushButton,
    FluentIcon,
    isDarkTheme
)
from qframelesswindow.webengine import FramelessWebEngineView
from utils import get_theme_config
import markdown

class MarkdownEditor(QWidget):
    """
    Markdown 编辑和预览组件
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("markdownEditor")
        
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        # 命令栏
        self.command_bar = CommandBar(self)
        self.setup_command_bar()
        self.main_layout.addWidget(self.command_bar)
        
        # 编辑和预览卡片
        self.editor_card = CardWidget(self)
        self.editor_card.setStyleSheet("background-color: transparent;")
        self.editor_layout = QVBoxLayout(self.editor_card)
        self.editor_layout.setContentsMargins(10, 10, 10, 10)
        self.editor_layout.setSpacing(10)
        
        # 编辑和预览容器
        self.container = QWidget(self.editor_card)
        self.container.setStyleSheet("background-color: transparent;")
        self.hbox_layout = QHBoxLayout(self.container)
        self.hbox_layout.setContentsMargins(0, 0, 0, 0)
        self.hbox_layout.setSpacing(10)
        
        # 编辑器
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write Markdown here...")
        self.setup_editor()
        
        # 预览
        self.preview = FramelessWebEngineView(self.editor_card)
        self.setup_preview()
        
        # 添加到布局
        self.hbox_layout.addWidget(self.editor, 1)
        self.hbox_layout.addWidget(self.preview, 1)
        self.editor_layout.addWidget(self.container, 1)
        self.main_layout.addWidget(self.editor_card, 1)
        
        # 状态栏
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("background-color: transparent;")
        self.setup_status_bar()
        self.main_layout.addWidget(self.status_bar)
        
        # 连接信号
        self.editor.textChanged.connect(self.update_preview)
        self.editor.selectionChanged.connect(self.update_status_bar)
        
        # 初始化
        self.update_preview()
        self.update_status_bar()
    
    def setup_command_bar(self):
        """
        设置命令栏
        """
        # 新建
        new_btn = TransparentPushButton(FluentIcon.ADD, "新建")
        new_btn.clicked.connect(self.new_file)
        self.command_bar.addWidget(new_btn)
        
        # 打开
        open_btn = TransparentPushButton(FluentIcon.FOLDER, "打开")
        open_btn.clicked.connect(self.open_file_dialog)
        self.command_bar.addWidget(open_btn)
        
        # 保存
        save_btn = TransparentPushButton(FluentIcon.SAVE, "保存")
        save_btn.clicked.connect(self.save_file_dialog)
        self.command_bar.addWidget(save_btn)
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 复制
        copy_btn = TransparentPushButton(FluentIcon.COPY, "复制")
        copy_btn.clicked.connect(self.copy)
        self.command_bar.addWidget(copy_btn)
        
        # 粘贴
        paste_btn = TransparentPushButton(FluentIcon.PASTE, "粘贴")
        paste_btn.clicked.connect(self.paste)
        self.command_bar.addWidget(paste_btn)
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 全屏
        fullscreen_btn = TransparentPushButton(FluentIcon.ZOOM_IN, "全屏")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.command_bar.addWidget(fullscreen_btn)
        
        # 分隔符
        self.command_bar.addSeparator()
        
        # 导出
        export_btn = TransparentPushButton(FluentIcon.SHARE, "导出")
        export_btn.clicked.connect(self.export_file)
        self.command_bar.addWidget(export_btn)
    
    def setup_editor(self):
        """
        设置编辑器
        """
        from config import EDITOR_CONFIG
        
        self.editor.setStyleSheet(f"""
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: {EDITOR_CONFIG['border_radius']}px;
            padding: {EDITOR_CONFIG['padding']}px;
            color: #333333;
            selection-background-color: {EDITOR_CONFIG['selection_bg']};
            caret-color: {EDITOR_CONFIG['caret_color']};
            font-size: {EDITOR_CONFIG['font_size']}px;
            line-height: {EDITOR_CONFIG['line_spacing']};
        """)
    
    def setup_preview(self):
        """
        设置预览
        """
        self.preview.setStyleSheet("""
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 8px;
        """)
    
    def setup_status_bar(self):
        """
        设置状态栏
        """
        # 字符数
        self.char_count_label = QLabel("字符: 0", self)
        self.status_bar.addWidget(self.char_count_label)
        
        # 选中字符数
        self.selection_label = QLabel("选中: 0", self)
        self.status_bar.addWidget(self.selection_label)
        
        # 编码
        self.encoding_label = QLabel("编码: UTF-8", self)
        self.status_bar.addPermanentWidget(self.encoding_label)
    
    def new_file(self):
        """
        新建文件
        """
        self.editor.clear()
    
    def open_file_dialog(self):
        """
        打开文件对话框
        """
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            self.open_file(file_path)
    
    def save_file_dialog(self):
        """
        保存文件对话框
        """
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            self.save_file(file_path)
    
    def open_file(self, file_path):
        """
        打开文件
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor.setPlainText(content)
        except Exception as e:
            pass
    
    def save_file(self, file_path):
        """
        保存文件
        """
        try:
            content = self.editor.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            pass
    
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
    
    def toggle_fullscreen(self):
        """
        切换全屏
        """
        if hasattr(self, 'is_fullscreen') and self.is_fullscreen:
            # 退出全屏
            self.editor.show()
            self.preview.show()
            self.is_fullscreen = False
        else:
            # 进入全屏
            self.editor.hide()
            self.preview.show()
            self.is_fullscreen = True
    
    def export_file(self):
        """
        导出文件
        """
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export File", "", "PDF Files (*.pdf);;Word Files (*.docx);;All Files (*)"
        )
        if file_path:
            pass
    
    def update_preview(self):
        """
        更新预览
        """
        content = self.editor.toPlainText()
        html = markdown.markdown(content)
        
        # 获取主题配置
        is_dark = isDarkTheme()
        theme = get_theme_config(is_dark)
        
        # 生成HTML
        styled_html = f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    background-color: transparent;
                    color: {theme['text_color']};
                    margin: 20px;
                    font-family: Arial, sans-serif;
                    font-size: 16px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: {theme['heading_color']};
                }}
                code {{
                    background-color: {theme['code_bg']};
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                pre {{
                    background-color: {theme['code_bg']};
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                blockquote {{
                    border-left: 4px solid rgba(100, 149, 237, 0.5);
                    margin: 10px 0;
                    padding: 10px 15px;
                    background-color: {theme['blockquote_bg']};
                }}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        
        self.preview.setHtml(styled_html)
    
    def update_status_bar(self):
        """
        更新状态栏
        """
        # 字符数
        char_count = len(self.editor.toPlainText())
        self.char_count_label.setText(f"字符: {char_count}")
        
        # 选中字符数
        selection_count = len(self.editor.textCursor().selectedText())
        self.selection_label.setText(f"选中: {selection_count}")
