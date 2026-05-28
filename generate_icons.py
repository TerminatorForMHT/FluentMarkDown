#!/usr/bin/env python3
"""
图标生成工具 - 将SVG图标转换为多平台图标格式
支持 Windows (.ico) 和 Mac (.icns)
使用PyQt5的SVG渲染功能
"""
import os
import sys
import struct
import time

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QImage, QPainterPath, QRegion
from PyQt5.QtCore import QSize, Qt, QRect
from PyQt5.QtSvg import QSvgRenderer

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")

WINDOWS_ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]
MAC_ICON_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def svg_to_pixmap(svg_path, size, scale=4.0):
    """将SVG转换为QPixmap（4倍超采样抗锯齿）"""
    render_size = int(size * scale)

    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        print(f"    SVG无效: {svg_path}")
        return None

    pixmap = QPixmap(render_size, render_size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    if render_size != size:
        pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    return pixmap


def svg_to_image(svg_path, size, scale=4.0):
    """将SVG转换为QImage（4倍超采样抗锯齿）"""
    render_size = int(size * scale)

    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        print(f"    SVG无效: {svg_path}")
        return None

    image = QImage(render_size, render_size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    if render_size != size:
        image = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    return image


def create_windows_ico(svg_path, output_path, sizes=None):
    """生成Windows ICO文件"""
    if sizes is None:
        sizes = WINDOWS_ICON_SIZES

    print(f"  生成 Windows ICO: {output_path}")

    png_paths = []
    temp_dir = os.path.join(RESOURCES_DIR, "temp_ico")
    if os.path.exists(temp_dir):
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    os.makedirs(temp_dir, exist_ok=True)

    for size in sizes:
        png_path = os.path.join(temp_dir, f"icon_{size}.png")
        pixmap = svg_to_pixmap(svg_path, size)
        if pixmap:
            pixmap.save(png_path, "PNG")
            png_paths.append((size, png_path))
            print(f"    ✓ {size}x{size}")

    if not png_paths:
        print("  没有生成任何PNG图像")
        return False

    try:
        from PIL import Image
    except ImportError:
        print("  Pillow 未安装，无法生成ICO")
        return False

    images = []
    for size, path in png_paths:
        img = Image.open(path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        images.append((size, img))

    if images:
        # 按尺寸从大到小排序，最大的作为基础图像
        images.sort(key=lambda x: x[0], reverse=True)
        base_image = images[0][1]
        append_images = [img for _, img in images[1:]]
        base_image.save(
            output_path,
            format='ICO',
            append_images=append_images
        )
        print(f"  ✓ ICO 文件已生成: {output_path}")

    for img in images:
        img[1].close()

    for _, path in png_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    if os.path.exists(temp_dir):
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass

    return True


def create_mac_icns(svg_path, output_path, sizes=None):
    """生成Mac ICNS文件"""
    if sizes is None:
        sizes = MAC_ICON_SIZES

    print(f"  生成 Mac ICNS: {output_path}")

    png_paths = []
    temp_dir = os.path.join(RESOURCES_DIR, "temp_icns")
    if os.path.exists(temp_dir):
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    os.makedirs(temp_dir, exist_ok=True)

    for size in sizes:
        png_path = os.path.join(temp_dir, f"icon_{size}x{size}.png")
        pixmap = svg_to_pixmap(svg_path, size)
        if pixmap:
            pixmap.save(png_path, "PNG")
            png_paths.append((size, png_path))
            print(f"    ✓ {size}x{size}")

    if not png_paths:
        print("  没有生成任何PNG图像")
        return False

    success = create_icns_pure_python(png_paths, output_path)

    for _, path in png_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    if os.path.exists(temp_dir):
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass

    return success


def create_icns_pure_python(png_paths, output_path):
    """使用纯Python方法创建ICNS文件"""
    print("  使用纯Python方法创建ICNS...")

    try:
        from PIL import Image
    except ImportError:
        print("  Pillow 未安装，无法生成ICNS")
        return False

    type_map = {
        16: b'icp4',
        32: b'icp5',
        64: b'icp6',
        128: b'ic07',
        256: b'ic08',
        512: b'ic09',
        1024: b'ic10'
    }

    chunks = []
    images = []

    for size, path in png_paths:
        img = Image.open(path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        images.append(img)

        import io
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_data = img_buffer.getvalue()

        type_code = type_map.get(size, f'ic{size:02d}'.encode('ascii'))
        chunk = type_code + struct.pack('>I', len(img_data) + 8) + img_data
        chunks.append(chunk)

    with open(output_path, 'wb') as f:
        f.write(b'icns')
        total_size = 8 + sum(len(c) for c in chunks)
        f.write(struct.pack('>I', total_size))

        for chunk in chunks:
            f.write(chunk)

    for img in images:
        img.close()

    print(f"  ✓ ICNS 文件已生成: {output_path}")
    return True


def generate_platform_icons():
    """为主流平台生成图标"""
    windows_svg = os.path.join(RESOURCES_DIR, "icoWin.svg")
    mac_svg = os.path.join(RESOURCES_DIR, "icoMac.svg")

    if not os.path.exists(windows_svg):
        print(f"错误: Windows SVG 文件不存在: {windows_svg}")
        return False

    if not os.path.exists(mac_svg):
        print(f"错误: Mac SVG 文件不存在: {mac_svg}")
        return False

    print("\n=== 开始生成图标 ===\n")

    print("【Windows 图标 (icon.ico)】")
    windows_ico = os.path.join(RESOURCES_DIR, "icon.ico")
    create_windows_ico(windows_svg, windows_ico)

    print("\n【Windows 图标 (mark.ico)】")
    mark_ico = os.path.join(RESOURCES_DIR, "mark.ico")
    create_windows_ico(windows_svg, mark_ico)

    print("\n【Mac 图标】")
    mac_icns = os.path.join(RESOURCES_DIR, "icon.icns")
    create_mac_icns(mac_svg, mac_icns)

    print("\n【通用PNG图标】")
    generate_utility_icons(windows_svg, mac_svg)

    print("\n=== 图标生成完成 ===")
    return True


def generate_utility_icons(win_svg, mac_svg):
    """生成各种实用场景的图标"""
    utility_sizes = {
        'app_icon': 256,
        'document_icon': 64,
        'toolbar_icon': 24,
        'notification_icon': 16
    }

    for name, size in utility_sizes.items():
        for platform, svg in [('win', win_svg), ('mac', mac_svg)]:
            output_path = os.path.join(RESOURCES_DIR, f"{name}_{platform}.png")
            pixmap = svg_to_pixmap(svg, size)
            if pixmap:
                pixmap.save(output_path, "PNG")
                print(f"  ✓ {name}_{platform}.png ({size}x{size})")


def main():
    print("=== Fluent Markdown 图标生成工具 ===\n")

    app = QApplication([])

    generate_platform_icons()


if __name__ == "__main__":
    main()
