#!/usr/bin/env python3
"""
Fluent Markdown Editor 主入口文件
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication, QVBoxLayout
from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtGui import QIcon
from qfluentwidgets import (
    FluentWidget,
    setTheme,
    Theme,
    SystemThemeListener,
    isDarkTheme
)
from qfluentwidgets.common.config import qconfig

# 导入Markdown编辑器组件
from views.markdown_editor import MarkdownWidget


# 高分屏设置
def setup_high_dpi():
    """
    设置高分屏支持
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    
    # 设置Qt高DPI缩放策略
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class MainWindow(FluentWidget):
    """
    主窗口
    """
    def __init__(self):
        super().__init__()
        
        # 设置主题
        setTheme(Theme.AUTO)
        
        # 创建主题监听器
        self.theme_listener = SystemThemeListener(self)
        
        # 主布局
        self.main_layout = QVBoxLayout(self)
        # 留出标题栏的空间
        self.main_layout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建Markdown编辑器
        self.markdown_editor = MarkdownWidget(self)
        self.main_layout.addWidget(self.markdown_editor, 1)
        
        # 窗口设置
        self.resize(1000, 700)
        self.setWindowTitle("Fluent Markdown")
        
        # 设置窗口图标
        try:
            import sys
            if getattr(sys, 'frozen', False):
                # 编译后使用PyInstaller的临时目录
                icon_path = os.path.join(sys._MEIPASS, "src", "resources", "mark.ico")
            else:
                # 开发环境使用绝对路径
                icon_path = os.path.join(os.path.dirname(__file__), "src", "resources", "mark.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            # 忽略图标设置错误，确保应用程序能在沙盒环境中运行
            pass
        
        # 连接主题变化信号
        qconfig.themeChanged.connect(self.on_theme_changed)
        
        # 启动主题监听器
        self.theme_listener.start()
    
    def closeEvent(self, e):
        """
        关闭事件
        """
        # 停止主题监听器
        self.theme_listener.terminate()
        self.theme_listener.deleteLater()
        super().closeEvent(e)
    
    def on_theme_changed(self):
        """
        主题变化处理
        """
        # 重置Mica效果
        if self.windowEffect is not None:
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))
        
        # 更新编辑器样式
        self.markdown_editor.update_editor_style()
        # 更新预览
        self.markdown_editor.update_preview()
        # 更新状态栏样式
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        if is_dark:
            self.markdown_editor.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: transparent;
                    border: none;
                    padding: 2px 8px;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
        else:
            self.markdown_editor.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: transparent;
                    border: none;
                    padding: 2px 8px;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
        
        # 更新状态栏标签颜色和间距
        text_color = "#ffffff" if is_dark else "#333333"
        label_style = f"color: {text_color}; padding: 0 0px;"
        self.markdown_editor.char_count_label.setStyleSheet(label_style)
        self.markdown_editor.selection_label.setStyleSheet(label_style)
        self.markdown_editor.theme_label.setStyleSheet(label_style)
        self.markdown_editor.encoding_label.setStyleSheet(label_style)


if __name__ == "__main__":
    # 设置高分屏幕支持
    setup_high_dpi()
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用图标
    try:
        import sys
        if getattr(sys, 'frozen', False):
            # 编译后使用PyInstaller的临时目录
            icon_path = os.path.join(sys._MEIPASS, "src", "resources", "mark.ico")
        else:
            # 开发环境使用绝对路径
            icon_path = os.path.join(os.path.dirname(__file__), "src", "resources", "mark.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        # 忽略图标设置错误，确保应用程序能在沙盒环境中运行
        pass
    
    # 创建窗口
    window = MainWindow()
    window.show()
    
    # 启用Mica效果
    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())
    
    # 运行应用
    sys.exit(app.exec_())
