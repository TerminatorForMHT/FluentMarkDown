"""
Markdown 编辑器视图（纯视图组件）。

职责：
- 左侧 QTextEdit 编辑、右侧 FramelessWebEngineView 实时预览
- Mica 透明 + 圆角裁剪
- 只暴露信号 / 方法供 Controller 调用，不做任何文件 IO 或导出
"""
import json

import markdown as md_lib

from PyQt5.QtCore import Qt, QPoint, QEvent, QTimer
from PyQt5.QtGui import QPainterPath, QRegion, QColor
from PyQt5.QtWidgets import (
    QFrame,
    QSplitter,
    QVBoxLayout,
)

from qfluentwidgets import (
    TextEdit,
    isDarkTheme,
)
from qframelesswindow.webengine import FramelessWebEngineView

from models.document import Document
from models.themes import PreviewThemes


# 进程级共享的 Markdown 解析器（线程不安全，但 UI 线程是单线程）
_MD_RENDERER = md_lib.Markdown(
    extensions=["fenced_code", "tables"],
    output_format="html5",
)


def _render_markdown(text: str) -> str:
    _MD_RENDERER.reset()
    return _MD_RENDERER.convert(text)


class MarkdownEditorView(QFrame):
    """单文档的编辑 + 预览视图。

    性能策略：
    - 输入时只走 *增量* JS DOM 更新（runJavaScript 修改 #md-body innerHTML），
      不重建整页；同时用 QTimer 把高频 textChanged 合并到 120ms 的尾随调用。
    - 只有主题 / 字号 / 首次加载才会执行昂贵的 setHtml（整页重建）。
    - 非可见状态下跳过预览渲染，再次可见时一次性补刷。
    """

    PREVIEW_RADIUS = 8
    MIN_FONT_SIZE = 8
    MAX_FONT_SIZE = 32
    DEFAULT_FONT_SIZE = 16
    PREVIEW_DEBOUNCE_MS = 120

    def __init__(self, document: Document, parent=None):
        super().__init__(parent)
        self.setObjectName("markdownEditorView")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._document = document
        self._preview_theme = "light"
        self._font_size = self.DEFAULT_FONT_SIZE
        self._is_fullscreen = False
        self._suppress_text_signal = False

        # 性能状态
        self._page_loaded = False        # setHtml 后页面是否已 loadFinished
        self._html_dirty = True          # 当前主题/字号下页面是否需要重建
        self._body_dirty = False         # 是否有待应用的 body 更新
        self._pending_body_html = ""     # 等待 flush 到 webview 的最新 body
        self._last_pushed_body = None    # 上一次推到页面的 body，用于去重
        self._last_rendered_md = None    # 上一次解析的 md，用于跳过空更新

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(self.PREVIEW_DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._flush_preview)

        self._build_ui()
        self._wire_signals()

        # 初次填充（不触发 textChanged 链路）
        self._suppress_text_signal = True
        self.editor.setPlainText(document.content)
        self._suppress_text_signal = False

        self.update_editor_style()
        # 不立即 setHtml，等首次 showEvent 时再渲染，避免后台 tab 预热抢主线程
        self._html_dirty = True
        self._body_dirty = True

    # ---------------- 对外属性 ----------------
    @property
    def document(self) -> Document:
        return self._document

    @property
    def preview_theme(self) -> str:
        return self._preview_theme

    @property
    def font_size(self) -> int:
        return self._font_size

    @property
    def is_fullscreen(self) -> bool:
        return self._is_fullscreen

    # ---------------- UI 构建 ----------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setStyleSheet(
            "QSplitter{background-color:transparent;}"
            "QSplitter::handle{width:4px;background-color:rgba(100,149,237,0.25);}"
            "QSplitter::handle:hover{background-color:rgba(100,149,237,0.55);}"
        )
        layout.addWidget(self.splitter, 1)

        # 左：编辑区 —— 使用 qfluentwidgets.TextEdit，自带 Fluent 风格的细滚动条 + 平滑滚动
        self.editor = TextEdit(self)
        self.editor.setPlaceholderText("在这里输入 Markdown…")
        # 按需显示：内容超出才出滚动条；横向因为有自动换行，关掉
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setLineWrapMode(TextEdit.WidgetWidth)
        self.editor.setFrameShape(QFrame.NoFrame)
        self.editor.installEventFilter(self)

        # 让 viewport（真正绘制文本的子控件）也透明，否则滚动条滑动时露出 QTextEdit 默认白底
        self.editor.setAttribute(Qt.WA_TranslucentBackground, True)
        self.editor.viewport().setAutoFillBackground(False)
        self.editor.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        # 直接给 viewport 上一层透明 QSS：优先级高于 palette，能盖住 fluent-widgets 内部对 palette 的覆写
        self.editor.viewport().setStyleSheet("background: transparent;")

        # 去掉 fluent-widgets TextEdit 聚焦时底部那条主题色横线（由内部 EditLayer 覆盖层绘制）
        layer = getattr(self.editor, "layer", None)
        if layer is not None:
            layer.hide()
            layer.setEnabled(False)

        # 右：预览容器（透明 + 圆角 mask）
        self.preview_container = QFrame(self)
        self.preview_container.setObjectName("previewContainer")
        self.preview_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview_container.setStyleSheet(
            "QFrame#previewContainer{background:transparent;border:none;}"
        )
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        self.preview = FramelessWebEngineView(self.preview_container)
        self.preview.setAttribute(Qt.WA_TranslucentBackground, True)
        self.preview.setStyleSheet("background:transparent;border:none;")
        try:
            self.preview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        except Exception:
            pass
        preview_layout.addWidget(self.preview)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview_container)
        self.splitter.setSizes([500, 500])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self._update_preview_round_mask()

    def _wire_signals(self) -> None:
        self.editor.textChanged.connect(self._on_text_changed)
        self._document.contentLoaded.connect(self._on_document_reloaded)
        self.preview.loadFinished.connect(self._on_page_load_finished)

    # ---------------- 文档同步 ----------------
    def _on_text_changed(self) -> None:
        if self._suppress_text_signal:
            return
        # 把最新文本静默灌进 Document，不触发 contentLoaded / 重渲
        text = self.editor.toPlainText()
        self._document.set_content_silent(text)
        # 单独维护 modified 标志（只在第一次变化时翻一次）
        if not self._document.is_modified:
            self._document._set_modified(True)  # noqa: SLF001
        self._schedule_preview()

    def _on_document_reloaded(self, text: str) -> None:
        """外部 load 文件后，把内容回灌到 QTextEdit（不重复解析、不打脏）。"""
        self._suppress_text_signal = True
        try:
            self.editor.setPlainText(text)
        finally:
            self._suppress_text_signal = False
        # 文档刚被载入，预览需要立即重建（首次 setHtml）
        self._html_dirty = True
        self._body_dirty = True
        self._last_rendered_md = None
        self._schedule_preview(immediate=True)

    def _on_page_load_finished(self, ok: bool) -> None:
        self._page_loaded = bool(ok)
        if self._page_loaded and self._body_dirty:
            # 整页加载完成后立刻补一次最新 body
            self._flush_preview(force_body=True)

    # ---------------- 主题/字号 ----------------
    def set_preview_theme(self, theme_key: str) -> None:
        if theme_key == self._preview_theme:
            return
        self._preview_theme = theme_key
        self._html_dirty = True
        self._schedule_preview(immediate=True)

    def set_font_size(self, size: int) -> None:
        size = max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, size))
        if size == self._font_size:
            return
        self._font_size = size
        self.update_editor_style()
        self._html_dirty = True
        self._schedule_preview(immediate=True)

    def zoom_in(self) -> None:
        self.set_font_size(self._font_size + 2)

    def zoom_out(self) -> None:
        self.set_font_size(self._font_size - 2)

    def zoom_reset(self) -> None:
        self.set_font_size(self.DEFAULT_FONT_SIZE)

    # ---------------- 编辑器样式 ----------------
    def update_editor_style(self) -> None:
        is_dark = isDarkTheme()
        text_color = "#ffffff" if is_dark else "#333333"
        # 滚动条按 Fluent Design 规范：轨道全透明，滑块半透明三态
        if is_dark:
            thumb_color = "rgba(255, 255, 255, 0.28)"
            thumb_hover = "rgba(255, 255, 255, 0.45)"
            thumb_press = "rgba(255, 255, 255, 0.55)"
        else:
            thumb_color = "rgba(0, 0, 0, 0.28)"
            thumb_hover = "rgba(0, 0, 0, 0.45)"
            thumb_press = "rgba(0, 0, 0, 0.55)"

        self.editor.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px 0px 0px 8px;
                padding: 10px 4px 10px 10px;
                color: {text_color};
                font-size: {self._font_size}px;
                selection-background-color: rgba(100, 149, 237, 0.3);
            }}

            /* Fluent 风格：轨道透明，滑块细 + 半透明三态 */
            QTextEdit QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 4px 2px 4px 0;
                border: none;
            }}
            QTextEdit QScrollBar::handle:vertical {{
                background: {thumb_color};
                min-height: 28px;
                border-radius: 3px;
            }}
            QTextEdit QScrollBar::handle:vertical:hover {{
                background: {thumb_hover};
            }}
            QTextEdit QScrollBar::handle:vertical:pressed {{
                background: {thumb_press};
            }}
            QTextEdit QScrollBar::add-line:vertical,
            QTextEdit QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
                border: none;
            }}
            QTextEdit QScrollBar::add-page:vertical,
            QTextEdit QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            """
        )
        self.editor.setCursorWidth(3 if is_dark else 2)

    # ---------------- 圆角 mask ----------------
    def _update_preview_round_mask(self) -> None:
        if not hasattr(self, "preview_container"):
            return
        if self._is_fullscreen:
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
        self.preview_container.setMask(
            QRegion(path.toFillPolygon().toPolygon())
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview_round_mask()

    # ---------------- 全屏 ----------------
    def toggle_fullscreen(self) -> bool:
        if not self._is_fullscreen:
            self.editor.hide()
            self.splitter.setSizes([0, self.splitter.width()])
            self._is_fullscreen = True
        else:
            self.editor.show()
            w = self.splitter.width()
            self.splitter.setSizes([w // 2, w // 2])
            self._is_fullscreen = False
        self._update_preview_round_mask()
        return self._is_fullscreen

    # ---------------- Ctrl + 滚轮 缩放 ----------------
    def eventFilter(self, obj, event):
        if obj is self.editor and event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True
        return False

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    # ---------------- 编辑动作 ----------------
    def copy(self) -> None:
        self.editor.copy()

    def paste(self) -> None:
        self.editor.paste()

    def insert_text(self, text: str) -> None:
        self.editor.textCursor().insertText(text)

    def char_count(self) -> int:
        return len(self.editor.toPlainText())

    def selection_length(self) -> int:
        return len(self.editor.textCursor().selectedText())

    # ---------------- 预览：调度 + 渲染 ----------------
    def update_preview(self) -> None:
        """兼容旧调用方：直接立刻刷新预览。"""
        self._schedule_preview(immediate=True)

    def _schedule_preview(self, immediate: bool = False) -> None:
        """合并高频请求；不可见时跳过，可见时再补。"""
        self._body_dirty = True
        if not self.isVisible():
            # 后台 tab：不绘制，回到前台时 showEvent 会触发 flush
            return
        if immediate:
            self._debounce_timer.stop()
            self._flush_preview()
            return
        if not self._debounce_timer.isActive():
            self._debounce_timer.start()

    def _flush_preview(self, force_body: bool = False) -> None:
        """真正把当前文本推到 WebEngine。"""
        if not self._body_dirty and not self._html_dirty and not force_body:
            return

        md_text = self.editor.toPlainText()
        if md_text == self._last_rendered_md and not self._html_dirty and not force_body:
            # 文本未变 + 模板未变：无事可做
            self._body_dirty = False
            return

        html_body = _render_markdown(md_text)
        self._last_rendered_md = md_text
        self._pending_body_html = html_body

        if self._html_dirty or not self._page_loaded:
            # 整页重建路径：仅在主题/字号/首次变化时走
            self._rebuild_page(html_body)
            self._html_dirty = False
            self._body_dirty = False
            return

        # 增量路径：只替换 #md-body 的 innerHTML
        if html_body == self._last_pushed_body:
            self._body_dirty = False
            return

        js = f"window.__setBody && window.__setBody({json.dumps(html_body)});"
        self.preview.page().runJavaScript(js)
        self._last_pushed_body = html_body
        self._body_dirty = False

    def _rebuild_page(self, html_body: str) -> None:
        """昂贵路径：setHtml 整页重建。"""
        ts = PreviewThemes.get_theme_styles(self._preview_theme)
        is_dark = isDarkTheme()

        if self._preview_theme == "light" and is_dark:
            text_color = "#e0e0e0"
            heading_color = "#ffffff"
            code_bg = "rgba(255, 255, 255, 0.1)"
            blockquote_bg = "rgba(255, 255, 255, 0.05)"
            link_color = "#64b5f6"
            bg = "transparent"
        else:
            text_color = ts["text_color"]
            heading_color = ts["heading_color"]
            code_bg = ts["code_bg"]
            blockquote_bg = ts["blockquote_bg"]
            link_color = ts["link_color"]
            bg = ts["background_color"]

        # 预览区滚动条与编辑器保持一致的 Fluent 风格：轨道透明，滑块按"内容是否深底"自适应
        is_dark_surface = is_dark or self._preview_theme in (
            "dark", "midnight", "forest", "ocean", "purple", "neon"
        )
        scrollbar_track = "transparent"
        if is_dark_surface:
            scrollbar_thumb = "rgba(255, 255, 255, 0.28)"
            scrollbar_thumb_hover = "rgba(255, 255, 255, 0.45)"
            scrollbar_thumb_active = "rgba(255, 255, 255, 0.55)"
        else:
            scrollbar_thumb = "rgba(0, 0, 0, 0.28)"
            scrollbar_thumb_hover = "rgba(0, 0, 0, 0.45)"
            scrollbar_thumb_active = "rgba(0, 0, 0, 0.55)"

        styled_html = _PREVIEW_TEMPLATE.format(
            text_color=text_color,
            heading_color=heading_color,
            code_bg=code_bg,
            blockquote_bg=blockquote_bg,
            scrollbar_track=scrollbar_track,
            scrollbar_thumb=scrollbar_thumb,
            scrollbar_thumb_hover=scrollbar_thumb_hover,
            scrollbar_thumb_active=scrollbar_thumb_active,
            link_color=link_color,
            bg=bg,
            font_size=self._font_size,
            radius=self.PREVIEW_RADIUS,
            body=html_body,
        )
        self._page_loaded = False
        self.preview.setHtml(styled_html)
        self._last_pushed_body = html_body
        self._update_preview_round_mask()

    # ---------------- 可见性 ----------------
    def showEvent(self, event):
        super().showEvent(event)
        # 切回这个 tab 时如果有待应用更新，立即刷新
        if self._body_dirty or self._html_dirty:
            QTimer.singleShot(0, self._flush_preview)


_PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  html, body {{
    margin: 0; padding: 0; height: 100%;
    overflow: hidden; background: transparent !important;
    color: {text_color};
    font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
    font-size: {font_size}px;
  }}
  .content {{
    height: 100%; background: {bg};
    border-top-right-radius: {radius}px;
    border-bottom-right-radius: {radius}px;
    overflow: hidden;
  }}
  .scroll {{
    height: 100%; overflow-y: auto;
    box-sizing: border-box; padding: 20px 20px 36px 20px;
  }}
  /* Fluent 风格滚动条：与编辑器统一 */
  ::-webkit-scrollbar {{ width: 6px; height: 6px; background: transparent; }}
  ::-webkit-scrollbar-track {{ background: {scrollbar_track}; }}
  ::-webkit-scrollbar-thumb {{
    background: {scrollbar_thumb};
    border-radius: 3px;
    min-height: 28px;
    transition: background 120ms ease;
  }}
  ::-webkit-scrollbar-thumb:hover {{ background: {scrollbar_thumb_hover}; }}
  ::-webkit-scrollbar-thumb:active {{ background: {scrollbar_thumb_active}; }}
  ::-webkit-scrollbar-button {{ height: 0; width: 0; display: none; }}
  ::-webkit-scrollbar-corner {{ background: transparent; }}
  h1,h2,h3,h4,h5,h6 {{ color: {heading_color}; margin: 20px 0 10px; }}
  p {{ margin: 0 0 10px; }}
  code {{ background: {code_bg}; padding: 2px 4px; border-radius: 3px; color: {text_color}; }}
  pre {{ position: relative; background: {code_bg}; padding: 10px;
        border-radius: 5px; overflow-x: auto; margin: 10px 0; color: {text_color}; }}
  pre code {{ background: transparent; padding: 0; border-radius: 0; }}
  blockquote {{ border-left: 4px solid rgba(100,149,237,0.5);
                margin: 10px 0; padding: 10px 15px; background: {blockquote_bg}; }}
  a {{ color: {link_color}; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
  th, td {{ border: 1px solid rgba(0,0,0,0.12); padding: 8px; text-align: left; }}
  th {{ background: {code_bg}; }}
</style>
</head><body>
  <div class="content"><div class="scroll" id="md-scroll">
    <div id="md-body">{body}</div>
  </div></div>
  <script>
    // 提供给宿主调用的增量更新入口：只换 #md-body 的内容，不重建整页
    window.__setBody = function(html) {{
      var el = document.getElementById('md-body');
      if (el) {{ el.innerHTML = html; }}
    }};
  </script>
</body></html>
"""
