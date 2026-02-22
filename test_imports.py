#!/usr/bin/env python3
"""
测试导入是否正常
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing imports...")

# 测试基本导入
try:
    from PyQt5.QtWidgets import QApplication, QVBoxLayout
    print("✓ PyQt5.QtWidgets imported successfully")
except Exception as e:
    print(f"✗ PyQt5.QtWidgets import failed: {e}")

try:
    from PyQt5.QtCore import QTimer, QSize
    print("✓ PyQt5.QtCore imported successfully")
except Exception as e:
    print(f"✗ PyQt5.QtCore import failed: {e}")

try:
    from PyQt5.QtGui import QIcon
    print("✓ PyQt5.QtGui imported successfully")
except Exception as e:
    print(f"✗ PyQt5.QtGui import failed: {e}")

try:
    from qfluentwidgets import (
        FluentWidget,
        setTheme,
        Theme,
        SystemThemeListener,
        isDarkTheme
    )
    print("✓ qfluentwidgets imported successfully")
except Exception as e:
    print(f"✗ qfluentwidgets import failed: {e}")

try:
    from views.markdown_editor import MarkdownWidget
    print("✓ views.markdown_editor imported successfully")
except Exception as e:
    print(f"✗ views.markdown_editor import failed: {e}")

print("Import test completed.")
