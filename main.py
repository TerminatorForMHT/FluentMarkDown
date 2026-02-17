import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from controllers.main import MainWindow
from controllers.main import setup_high_dpi

if __name__ == "__main__":
    # 设置高分屏幕支持
    setup_high_dpi()
    
    # 创建应用
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # 创建窗口
    window = MainWindow()
    window.show()
    
    # 启用Mica效果
    from qfluentwidgets import isDarkTheme
    if hasattr(window, 'windowEffect') and window.windowEffect is not None:
        window.windowEffect.setMicaEffect(window.winId(), isDarkTheme())
    
    # 运行应用
    sys.exit(app.exec_())
