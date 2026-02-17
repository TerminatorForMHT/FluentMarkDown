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
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
        from PyQt5.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "Mark.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
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
    
    # 设置应用图标
    from PyQt5.QtGui import QIcon
    import os
    icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "Mark.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建窗口
    window = MainWindow()
    window.show()
    
    # 启用Mica效果
    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())
    
    # 运行应用
    sys.exit(app.exec_())