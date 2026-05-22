#!/usr/bin/env python3
"""
Fluent Markdown Editor 入口（薄壳）。

UI / 逻辑按 MVC 拆分到根目录下的 models / views / controllers 三个包，
本文件只负责：
1. 修正 sys.path，让仓库根目录可被作为 import 根
2. 启用高 DPI
3. 创建 QApplication / MainWindow 并启动 Mica
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import isDarkTheme
from views.main_window import MainWindow, _resolve_icon_path


def setup_high_dpi() -> None:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)


def _apply_macos_dock_icon(icon_path: str) -> None:
    try:
        from AppKit import NSApplication, NSImage
    except ImportError:
        return

    image = NSImage.alloc().initWithContentsOfFile_(icon_path)
    if image is None:
        return
    NSApplication.sharedApplication().setApplicationIconImage_(image)


def main() -> int:
    setup_high_dpi()
    import PyQt5.QtWebEngineWidgets
    app = QApplication(sys.argv)

    icon_path = _resolve_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
        if sys.platform == "darwin":
            _apply_macos_dock_icon(icon_path)

    window = MainWindow()
    window.showMaximized()

    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
