# Markdown Editor

一个支持 Mica 效果的 Markdown 编辑器，使用 PyQt5 和 PyQt-Fluent-Widgets 构建。

## 功能特性

- 实时 Markdown 预览
- 支持 Mica 效果（Windows 11）
- Fluent Design 风格界面
- 高分屏幕自适应
- 文件打开/保存功能

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python src/main.py
```

## 项目结构

```
MarkdownEditor/
├── src/               # 源代码目录
│   ├── __init__.py
│   ├── main.py        # 主程序入口
│   ├── editor.py      # Markdown 编辑组件
│   └── utils.py       # 工具函数
├── resources/         # 资源文件目录
├── tests/             # 测试文件目录
├── README.md          # 项目说明
└── requirements.txt   # 依赖项
```
