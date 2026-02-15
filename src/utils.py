from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


def setup_high_dpi():
    """
    设置高分屏幕支持
    """
    # 启用高分屏幕支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def get_theme_config(is_dark):
    """
    获取主题配置
    """
    from config import theme_config
    return theme_config["dark"] if is_dark else theme_config["light"]
