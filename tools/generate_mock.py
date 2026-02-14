"""
モック画像ジェネレータ — 純Python版
Generates mock cable inspection images using only built-in Python modules.
Creates simple BMP files and registers them in metadata.csv.
"""
import csv
import os
import struct
import random
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def _create_bmp(width: int, height: int, pixels: list[list[tuple[int, int, int]]]) -> bytes:
    """
    RGB pixel data から BMP ファイルバイト列を生成する。
    pixels[y][x] = (R, G, B)
    """
    row_size = (width * 3 + 3) & ~3
    pixel_data_size = row_size * height
    file_size = 54 + pixel_data_size

    header = struct.pack('<2sIHHI',
        b'BM', file_size, 0, 0, 54
    )

    dib = struct.pack('<IiiHHIIiiII',
        40, width, height, 1, 24, 0,
        pixel_data_size, 2835, 2835, 0, 0
    )

    pixel_bytes = bytearray()
    for y in range(height - 1, -1, -1):
        for x in range(width):
            r, g, b = pixels[y][x]
            pixel_bytes.extend([b, g, r])
        padding = row_size - width * 3
        pixel_bytes.extend(b'\x00' * padding)

    return header + dib + bytes(pixel_bytes)


def _make_image(width, height, bg):
    return [[bg for _ in range(width)] for _ in range(height)]


def _draw_rect(pixels, x1, y1, x2, y2, color):
    h = len(pixels)
    w = len(pixels[0])
    for y in range(max(0, y1), min(h, y2)):
        for x in range(max(0, x1), min(w, x2)):
            pixels[y][x] = color


def _draw_line_h(pixels, x1, x2, y, color, thickness=2):
    h = len(pixels)
    w = len(pixels[0])
    for dy in range(thickness):
        yy = y + dy
        if 0 <= yy < h:
            for x in range(max(0, x1), min(w, x2)):
                pixels[yy][x] = color


def _vary(base, amount=20):
    return tuple(max(0, min(255, c + random.randint(-amount, amount))) for c in base)


def generate_ok_image():
    w, h = 320, 240
    bg = _vary((20, 20, 25), 5)
    pixels = _make_image(w, h, bg)
    cy = h // 2
    cable_color = _vary((55, 55, 65))
    conn_color = _vary((170, 170, 180))

    _draw_rect(pixels, 10, cy - 22, w // 2 + 20, cy + 22, cable_color)
    cx1, cx2 = w // 2 + 15, w // 2 + 90
    ct, cb = cy - 28, cy + 28
    _draw_rect(pixels, cx1, ct, cx2, cb, conn_color)

    pin_color = (210, 175, 45)
    pin_count = 5
    for i in range(pin_count):
        py = ct + 8 + i * ((cb - ct - 16) // (pin_count - 1))
        _draw_line_h(pixels, cx1 + 8, cx2 - 8, py, pin_color, 2)

    wire_colors = [(190, 45, 45), (45, 45, 190), (45, 160, 45), (190, 190, 45)]
    for i, wc in enumerate(wire_colors):
        wy = cy - 14 + i * 9
        _draw_line_h(pixels, w // 2 - 10, cx1 + 5, wy, wc, 2)

    return _create_bmp(w, h, pixels)


def generate_ng_image(defect_type):
    w, h = 320, 240
    bg = _vary((20, 20, 25), 5)
    pixels = _make_image(w, h, bg)
    cy = h // 2
    cable_color = _vary((55, 55, 65))
    conn_color = _vary((170, 170, 180))

    _draw_rect(pixels, 10, cy - 22, w // 2 + 20, cy + 22, cable_color)
    cx1, cx2 = w // 2 + 15, w // 2 + 90
    ct, cb = cy - 28, cy + 28
    _draw_rect(pixels, cx1, ct, cx2, cb, conn_color)

    pin_color = (210, 175, 45)
    pin_count = 5
    bent_pin = random.randint(0, pin_count - 1) if defect_type == "bent" else -1
    missing_pin = pin_count // 2 if defect_type == "missing" else -1

    for i in range(pin_count):
        if i == missing_pin:
            continue
        py = ct + 8 + i * ((cb - ct - 16) // (pin_count - 1))
        if i == bent_pin:
            _draw_line_h(pixels, cx1 + 8, cx2 - 8, py + random.choice([-6, 6]), pin_color, 2)
        else:
            _draw_line_h(pixels, cx1 + 8, cx2 - 8, py, pin_color, 2)

    wire_colors = [(190, 45, 45), (45, 45, 190), (45, 160, 45), (190, 190, 45)]
    for i, wc in enumerate(wire_colors):
        wy = cy - 14 + i * 9
        if defect_type == "exposed" and i == 0:
            _draw_line_h(pixels, w // 2 - 30, cx1 + 5, wy, (200, 140, 70), 3)
        elif defect_type == "loose" and i == len(wire_colors) - 1:
            _draw_line_h(pixels, w // 2 - 10, cx1 + 5, wy + 10, wc, 2)
        else:
            _draw_line_h(pixels, w // 2 - 10, cx1 + 5, wy, wc, 2)

    if defect_type == "scratch":
        for _ in range(random.randint(3, 6)):
            sx = random.randint(cx1, cx2 - 5)
            sy = random.randint(ct, cb - 5)
            _draw_line_h(pixels, sx, sx + random.randint(5, 15), sy, (180, 50, 50), 2)

    return _create_bmp(w, h, pixels)


def _register_in_csv(filepath, filename, label):
    """メタデータCSVに画像を登録する"""
    csv_exists = os.path.exists(config.METADATA_CSV)
    with open(config.METADATA_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not csv_exists:
            writer.writerow([
                "timestamp", "filename", "filepath", "label",
                "cable_id", "file_size_bytes",
            ])
        file_size = os.path.getsize(filepath)
        writer.writerow([
            datetime.now().isoformat(),
            filename,
            filepath,
            label,
            f"MOCK-{label.upper()}",
            file_size,
        ])


def main():
    ok_count = 20
    ng_count = 10
    defect_types = ["bent", "missing", "exposed", "loose", "scratch"]

    # 既存の metadata.csv をクリア（モック再生成時）
    if os.path.exists(config.METADATA_CSV):
        os.remove(config.METADATA_CSV)
        print("  既存の metadata.csv をクリアしました")

    print("モック画像を生成中...")
    print(f"  OK画像: {ok_count}枚 → {config.OK_DIR}")
    print(f"  NG画像: {ng_count}枚 → {config.NG_DIR}")

    for i in range(ok_count):
        data = generate_ok_image()
        filename = f"mock_ok_{i + 1:03d}.bmp"
        filepath = os.path.join(config.OK_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(data)
        _register_in_csv(filepath, filename, "ok")
        print(f"  ✓ {filename}")

    for i in range(ng_count):
        defect = defect_types[i % len(defect_types)]
        filename = f"mock_ng_{i + 1:03d}.bmp"
        filepath = os.path.join(config.NG_DIR, filename)
        data = generate_ng_image(defect)
        with open(filepath, "wb") as f:
            f.write(data)
        _register_in_csv(filepath, filename, "ng")
        print(f"  ✓ {filename}")

    print(f"\n完了！ 合計 {ok_count + ng_count} 枚生成し、metadata.csv に登録しました。")


if __name__ == "__main__":
    main()
