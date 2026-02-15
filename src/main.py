from PyQt5.QtWidgets import QApplication, QVBoxLayout
from PyQt5.QtCore import QTimer
from qfluentwidgets import (
    FluentWidget,
    setTheme,
    Theme,
    SystemThemeListener,
    isDarkTheme
)
from qfluentwidgets.common.config import qconfig
from editor import MarkdownWidget
from utils import setup_high_dpi
import sys

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

if __name__ == "__main__":
    # 设置高分屏幕支持
    setup_high_dpi()
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 创建窗口
    window = MainWindow()
    window.show()
    
    # 启用Mica效果
    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())
    
    # 运行应用
    sys.exit(app.exec_())
