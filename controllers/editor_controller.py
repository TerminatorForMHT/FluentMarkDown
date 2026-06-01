import markdown
import os
import re


class EditorController:
    def __init__(self, document):
        self.document = document
        self.preview_theme = "light"
        self.font_size = 16
        self._last_md5 = None
        self._cached_html_template = None

    def set_content(self, content):
        self.document.content = content
        self.document.is_modified = True

    def get_content(self):
        return self.document.content

    def set_theme(self, theme):
        self.preview_theme = theme
        self._last_md5 = None
        self._cached_html_template = None

    def set_font_size(self, size):
        self.font_size = size
        self._last_md5 = None
        self._cached_html_template = None

    def _convert_image_paths(self, html):
        """将 HTML 中的图片路径转换为 file:// 协议"""
        from PyQt5.QtCore import QUrl
        
        # 获取当前文档所在目录
        base_dir = os.path.dirname(self.document.file_path) if self.document.file_path else os.getcwd()
        
        # 匹配 <img> 标签的 src 属性
        def replace_path(match):
            src = match.group(1)
            # 如果已经是 http/https/data 协议，保持原样
            if src.startswith(('http://', 'https://', 'data:', 'file://')):
                return f'<img src="{src}"'
            
            # 如果是绝对路径（Windows 或 Unix）
            if os.path.isabs(src):
                file_url = QUrl.fromLocalFile(src).toString()
                return f'<img src="{file_url}"'
            
            # 如果是相对路径，基于文档目录解析
            full_path = os.path.normpath(os.path.join(base_dir, src))
            if os.path.exists(full_path):
                file_url = QUrl.fromLocalFile(full_path).toString()
                return f'<img src="{file_url}"'
            
            # 如果路径不存在，保持原样
            return f'<img src="{src}"'
        
        # 使用正则替换图片路径
        html = re.sub(r'<img\s+src="([^"]+)"', replace_path, html)
        return html

    def render_preview(self, is_dark=False):
        ts = self._get_theme_styles(is_dark)
        # 添加更多扩展支持图片和其他格式
        html = markdown.markdown(self.document.content, extensions=['fenced_code', 'extra', 'tables'])
        # 转换图片路径为 file:// 协议
        html = self._convert_image_paths(html)
        return self._build_html(html, ts, is_dark)

    def _get_theme_styles(self, is_dark):
        from models.themes import PreviewThemes
        ts = PreviewThemes.get_theme_styles(self.preview_theme)
        
        if self.preview_theme == "light" and is_dark:
            ts["text_color"] = "#e0e0e0"
            ts["heading_color"] = "#ffffff"
            ts["code_bg"] = "rgba(255, 255, 255, 0.1)"
            ts["blockquote_bg"] = "rgba(255, 255, 255, 0.05)"
            ts["scrollbar_track"] = "#3d3d3d"
            ts["scrollbar_thumb"] = "#5d5d5d"
            ts["scrollbar_thumb_hover"] = "#7d7d7d"
            ts["link_color"] = "#64b5f6"
        
        return ts

    def _build_html(self, html, ts, is_dark=False):
        from models.html_template import PreviewHtmlBuilder
        builder = PreviewHtmlBuilder(ts, self.font_size, is_dark)
        return builder.build(html)
