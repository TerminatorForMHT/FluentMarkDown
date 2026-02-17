# Fluent Markdown Editor

一个支持 Mica 效果的 Markdown 编辑器，使用 PyQt5 和 PyQt-Fluent-Widgets 构建。

## 功能特性

- 实时 Markdown 预览
- 支持 Mica 效果（Windows 11）
- Fluent Design 风格界面
- 高分屏幕自适应
- 文件打开/保存功能
- 主题切换功能
- 多种预览主题支持

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 编译为可执行文件

```bash
# 安装 PyInstaller
pip install pyinstaller

# 运行编译脚本
python build.py
```

编译完成后，可执行文件将位于 `dist` 目录中。

## 项目结构

```
MarkdownEditor/
├── src/               # 源代码目录
│   ├── controllers/   # 控制器
│   │   ├── __init__.py
│   │   └── main.py    # 主窗口控制器
│   ├── models/        # 模型
│   │   ├── __init__.py
│   │   └── themes.py  # 主题定义
│   ├── views/         # 视图
│   │   ├── __init__.py
│   │   └── markdown_editor.py  # Markdown 编辑组件
│   ├── resources/     # 资源文件
│   │   └── Mark.ico   # 应用图标
│   ├── __init__.py
│   ├── config.py      # 配置文件
│   └── utils.py       # 工具函数
├── main.py            # 主程序入口
├── build.py           # 编译脚本
├── README.md          # 项目说明
└── requirements.txt   # 依赖项
```
