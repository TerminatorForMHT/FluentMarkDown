#!/usr/bin/env python3
"""
构建多平台 App 图标。

源图：resources/new_ico.svg (1024x1024)
产物：
- resources/AppIcon.icns   —— macOS，套 squircle 圆角（22.37% × 边长），符合 Big Sur+ 系统规范
- resources/mark.ico       —— Windows，不裁切、不加圆角，遵守 Fluent Design 规范
- resources/iconset/       —— 中间产物，多尺寸 png（开发可见，git 不追踪）

依赖：Pillow + cairosvg + 系统自带 iconutil（macOS）。
用法：python scripts/build_icons.py
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw
except ImportError as e:  # pragma: no cover
    print(f"缺少依赖：{e}。请先 `pip install -r requirements.txt`")
    sys.exit(1)

# 用 PyQt5 自带 QSvgRenderer 渲染 SVG，免去 cairo 等系统库依赖
from PyQt5.QtCore import QSize, Qt  # noqa: E402
from PyQt5.QtGui import QImage, QPainter  # noqa: E402
from PyQt5.QtSvg import QSvgRenderer  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

# QSvgRenderer 需要一个 QApplication（即使不开窗口）
_QAPP = QApplication.instance() or QApplication(sys.argv)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = PROJECT_ROOT / "resources"
# macOS：满底渐变背景 + squircle 裁切 → Dock 圆角矩形
MAC_SOURCE_SVG = RESOURCES / "new_ico_v2.svg"
# Windows：透明背景，只保留图形主体（Fluent Design 规范：无容器形状）
WIN_SOURCE_SVG = RESOURCES / "new_ico_win.svg"
ICONSET_DIR = RESOURCES / "iconset"

# Windows .ico 尺寸：Fluent Design 不做圆角裁切
WIN_ICO_SIZES: Tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)

# macOS .icns 尺寸：必须用 iconutil 的标准命名 + 含 @2x
MAC_ICONSET_SPEC: Tuple[Tuple[str, int], ...] = (
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
)

# macOS squircle 圆角比例（Big Sur+ 系统图标标准 ≈ 22.37% × 边长）
SQUIRCLE_RADIUS_RATIO = 0.2237


def render_svg(svg_path: Path, size: int) -> Image.Image:
    """用 QSvgRenderer 把 SVG 渲染成指定边长的方形 RGBA PIL Image。"""
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"SVG 无效：{svg_path}")

    qimg = QImage(size, size, QImage.Format_ARGB32)
    qimg.fill(0)  # 全透明背景
    painter = QPainter(qimg)
    painter.setRenderHints(
        QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing
    )
    renderer.render(painter)
    painter.end()

    # QImage -> bytes -> PIL.Image（ARGB32 = BGRA 字节序）
    buf = qimg.bits()
    buf.setsize(qimg.byteCount())
    data = bytes(buf)
    pil = Image.frombytes("RGBA", (size, size), data, "raw", "BGRA")
    return pil


def apply_squircle_mask(img: Image.Image, radius_ratio: float = SQUIRCLE_RADIUS_RATIO) -> Image.Image:
    """给方形图加圆角矩形蒙版（macOS squircle 风格）。"""
    if img.width != img.height:
        raise ValueError("apply_squircle_mask 要求输入为正方形")
    size = img.width
    radius = int(round(size * radius_ratio))

    # 用 4x 倍率绘制蒙版后下采样，得到平滑边缘
    scale = 4
    big_size = size * scale
    big_radius = radius * scale
    mask = Image.new("L", (big_size, big_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, big_size, big_size),
        radius=big_radius,
        fill=255,
    )
    mask = mask.resize((size, size), Image.LANCZOS)

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask=mask)
    return result


def build_windows_ico(svg_path: Path, out_path: Path, sizes: Tuple[int, ...] = WIN_ICO_SIZES) -> None:
    """生成 Windows .ico（不裁切、保持原 SVG 完整形状）。"""
    # 渲染最大尺寸，再 LANCZOS 下采样 → 边缘比直接 SVG 渲染更稳定
    base = render_svg(svg_path, max(sizes))
    frames: List[Image.Image] = []
    for s in sizes:
        if s == base.width:
            frames.append(base)
        else:
            frames.append(base.resize((s, s), Image.LANCZOS))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Pillow 保存 ico 时把 sizes 列表传给 sizes 参数即可一次性写多帧
    frames[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"  ✓ Windows ICO: {out_path.relative_to(PROJECT_ROOT)} ({', '.join(str(s) for s in sizes)})")


def build_macos_icns(svg_path: Path, iconset_dir: Path, out_path: Path) -> None:
    """生成 macOS .icns（套 squircle 圆角）。"""
    if shutil.which("iconutil") is None:
        raise RuntimeError("找不到 iconutil（仅 macOS 自带），无法生成 .icns")

    # iconutil 要求目录后缀必须是 .iconset
    iconset_path = iconset_dir.with_suffix(".iconset")
    if iconset_path.exists():
        shutil.rmtree(iconset_path)
    iconset_path.mkdir(parents=True)

    # 渲染最大尺寸 1024，剩下的从它下采样 → 几何一致
    base = render_svg(svg_path, 1024)
    rounded_cache: dict[int, Image.Image] = {}

    for fname, size in MAC_ICONSET_SPEC:
        if size not in rounded_cache:
            resized = base if size == 1024 else base.resize((size, size), Image.LANCZOS)
            rounded_cache[size] = apply_squircle_mask(resized)
        rounded_cache[size].save(iconset_path / fname, format="PNG")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["iconutil", "-c", "icns", str(iconset_path), "-o", str(out_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"iconutil 失败：{result.stderr}")

    print(f"  ✓ macOS ICNS:  {out_path.relative_to(PROJECT_ROOT)} (squircle radius={SQUIRCLE_RADIUS_RATIO:.2%})")
    # 保留 iconset 目录作为调试快照
    shutil.rmtree(iconset_dir, ignore_errors=True)
    iconset_path.rename(iconset_dir)


def main() -> int:
    for label, path in [("macOS SVG", MAC_SOURCE_SVG), ("Windows SVG", WIN_SOURCE_SVG)]:
        if not path.exists():
            print(f"找不到 {label}：{path}")
            return 1

    print(f"macOS   源: {MAC_SOURCE_SVG.relative_to(PROJECT_ROOT)}")
    print(f"Windows 源: {WIN_SOURCE_SVG.relative_to(PROJECT_ROOT)}")
    print("=" * 60)

    # Windows：透明背景，不裁切
    build_windows_ico(WIN_SOURCE_SVG, RESOURCES / "mark.ico")

    # macOS：满底背景 + squircle 圆角
    if sys.platform == "darwin":
        build_macos_icns(MAC_SOURCE_SVG, ICONSET_DIR, RESOURCES / "AppIcon.icns")
    else:
        print("  · 非 macOS 平台，跳过 .icns 生成（请在 macOS 上重跑）")

    print("=" * 60)
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
