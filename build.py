#!/usr/bin/env python3
"""
编译脚本，使用PyInstaller将Markdown编辑器编译为可执行文件
"""
import os
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "app.py")
ICON_FILE = os.path.join(PROJECT_ROOT, "resources", "icon.ico")


def clean_build():
    print("清理之前的构建文件...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)


def build_exe():
    print("开始编译可执行文件...")

    import sys
    python_exe = sys.executable

    cmd = [
        python_exe,
        "-m", "PyInstaller",
        "--name", "FluentMarkdown",
        "--onefile",
        "--windowed",
        "--icon", ICON_FILE,
        "--add-data", f"resources;resources",
        "--collect-submodules", "views",
        "--collect-submodules", "controllers",
        "--collect-submodules", "models",
        MAIN_SCRIPT
    ]

    print(f"执行命令: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print("编译成功！")
        print(f"可执行文件位于: {os.path.join(OUTPUT_DIR, 'FluentMarkdown.exe')}")
    else:
        print("编译失败！")
        return False

    return True


def main():
    print("=== Fluent Markdown 编译脚本 ===")

    clean_build()

    success = build_exe()

    if success:
        print("\n编译完成！")
        print("你可以在 dist 目录中找到可执行文件。")
    else:
        print("\n编译失败，请检查错误信息。")


if __name__ == "__main__":
    main()
