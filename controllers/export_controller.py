"""
导出控制器：把当前 Markdown 文本导出为 PDF / DOCX / HTML。

PDF 使用 reportlab（支持中文），相比 fpdf 不会因为 latin-1 编码炸掉。
若 reportlab 不可用，则回退用 Qt 的 QTextDocument + QPrinter。
"""
import os
from typing import Optional, Tuple

import markdown as md_lib
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QFileDialog, QWidget


EXPORT_FILTER = (
    "PDF Files (*.pdf);;Word Files (*.docx);;HTML Files (*.html);;All Files (*)"
)


class ExportController(QObject):
    """文档导出控制器。"""

    def prompt_export_path(self, parent_widget: QWidget) -> Tuple[Optional[str], str]:
        """弹出导出对话框，返回 (路径, 选中的过滤器名)。取消返回 (None, '')。"""
        file_path, file_type = QFileDialog.getSaveFileName(
            parent_widget, "导出文件", "", EXPORT_FILTER
        )
        if not file_path:
            return None, ""

        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            if "PDF" in file_type:
                file_path += ".pdf"
            elif "Word" in file_type:
                file_path += ".docx"
            elif "HTML" in file_type:
                file_path += ".html"
        return file_path, file_type

    def export(self, file_path: str, markdown_text: str) -> None:
        """根据扩展名分派到具体导出方法。会抛出异常，调用方负责捕获。"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            self._export_pdf(file_path, markdown_text)
        elif ext == ".docx":
            self._export_docx(file_path, markdown_text)
        elif ext in (".html", ".htm"):
            self._export_html(file_path, markdown_text)
        else:
            raise ValueError(f"不支持的导出格式：{ext}")

    # ---------------- PDF ----------------
    def _export_pdf(self, file_path: str, markdown_text: str) -> None:
        html = md_lib.markdown(
            markdown_text, extensions=["fenced_code", "tables"]
        )

        # 优先用 Qt 内置：QTextDocument + QPrinter，原生支持 unicode
        from PyQt5.QtGui import QTextDocument
        from PyQt5.QtPrintSupport import QPrinter

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)

        doc = QTextDocument()
        doc.setHtml(self._wrap_html(html))
        doc.print_(printer)

    # ---------------- DOCX ----------------
    def _export_docx(self, file_path: str, markdown_text: str) -> None:
        try:
            from docx import Document as DocxDocument
        except ImportError as e:
            raise RuntimeError("缺少依赖 python-docx，请先 `pip install python-docx`") from e

        doc = DocxDocument()
        for raw_line in markdown_text.split("\n"):
            line = raw_line.rstrip()
            if line.startswith("# "):
                doc.add_heading(line[2:], level=1)
            elif line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.startswith("### "):
                doc.add_heading(line[4:], level=3)
            elif line.startswith("#### "):
                doc.add_heading(line[5:], level=4)
            elif line.startswith(("- ", "* ", "+ ")):
                doc.add_paragraph(line[2:], style="List Bullet")
            elif line.strip():
                doc.add_paragraph(line)
        doc.save(file_path)

    # ---------------- HTML ----------------
    def _export_html(self, file_path: str, markdown_text: str) -> None:
        html = md_lib.markdown(
            markdown_text, extensions=["fenced_code", "tables"]
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self._wrap_html(html))

    # ---------------- 工具 ----------------
    @staticmethod
    def _wrap_html(body_html: str) -> str:
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<style>"
            "body{font-family: 'PingFang SC','Microsoft YaHei',Arial,sans-serif;"
            "font-size:14px;line-height:1.7;color:#222;padding:24px;}"
            "h1,h2,h3,h4{color:#1f2328;margin:18px 0 10px;}"
            "code{background:#f6f8fa;padding:2px 4px;border-radius:3px;}"
            "pre{background:#f6f8fa;padding:12px;border-radius:6px;overflow:auto;}"
            "blockquote{border-left:4px solid #d0d7de;color:#57606a;"
            "padding:0 12px;margin:8px 0;}"
            "table{border-collapse:collapse;}"
            "th,td{border:1px solid #d0d7de;padding:6px 10px;}"
            "</style></head><body>"
            f"{body_html}"
            "</body></html>"
        )
