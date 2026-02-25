#!/usr/bin/env python3
"""
编译脚本，使用PyInstaller将Markdown编辑器编译为可执行文件
"""
import os
import shutil
import subprocess

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# 输出目录
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "dist")
# 构建目录
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
# 主入口文件
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "app.py")
# 图标文件
ICON_FILE = os.path.join(PROJECT_ROOT, "src", "resources", "Mark.ico")


def clean_build():
    """清理之前的构建文件"""
    print("清理之前的构建文件...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)


def build_exe():
    """使用PyInstaller编译为可执行文件"""
    print("开始编译可执行文件...")
    
    # 获取虚拟环境内的Python解释器路径
    import sys
    python_exe = sys.executable
    
    # 构建PyInstaller命令，使用虚拟环境内的Python来运行PyInstaller
    cmd = [
        python_exe,
        "-m", "PyInstaller",
        "--name", "FluentMarkdown",
        "--onefile",
        "--windowed",
        "--icon", ICON_FILE,
        "--add-data", f"src/resources;src/resources",
        "--collect-submodules", "views",
        "--collect-submodules", "controllers",
        "--collect-submodules", "models",
        "--collect-submodules", "src",
        MAIN_SCRIPT
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    # 执行命令
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode == 0:
        print("编译成功！")
        print(f"可执行文件位于: {os.path.join(OUTPUT_DIR, 'FluentMarkdown.exe')}")
    else:
        print("编译失败！")
        return False
    
    return True


def main():
    """主函数"""
    print("=== Fluent Markdown 编译脚本 ===")
    
    # 清理之前的构建
    clean_build()
    
    # 执行编译
    success = build_exe()
    
    if success:
        print("\n编译完成！")
        print("你可以在 dist 目录中找到可执行文件。")
    else:
        print("\n编译失败，请检查错误信息。")


if __name__ == "__main__":
    main()
