from __future__ import annotations

import struct
import zlib
from pathlib import Path


ICON_DIR = Path("ios/JapaneseCoach/JapaneseCoach/Assets.xcassets/AppIcon.appiconset")


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc)
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc & 0xFFFFFFFF)


def write_png(path: Path, width: int, height: int) -> None:
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            blend = (x + y) / max(width + height - 2, 1)
            red = int(180 + 55 * blend)
            green = int(64 + 40 * (1 - blend))
            blue = int(46 + 28 * (1 - blend))
            alpha = 255
            row.extend((red, green, blue, alpha))
        rows.append(bytes(row))

    raw = b"".join(rows)
    compressed = zlib.compress(raw, level=9)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", compressed) + _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    sizes = {
        "icon-20@2x.png": 40,
        "icon-20@3x.png": 60,
        "icon-29@2x.png": 58,
        "icon-29@3x.png": 87,
        "icon-40@2x.png": 80,
        "icon-40@3x.png": 120,
        "icon-60@2x.png": 120,
        "icon-60@3x.png": 180,
        "icon-1024.png": 1024,
    }
    for name, size in sizes.items():
        write_png(ICON_DIR / name, size, size)


if __name__ == "__main__":
    main()
