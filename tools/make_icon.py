"""Generate assets/anishade.ico from the vector logo (no Pillow needed)."""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from anishade.ui.icons import make_logo  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(size: int) -> bytes:
    pixmap = make_logo(size)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(data)


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 - required for QPixmap
    images = [(size, png_bytes(size)) for size in SIZES]

    header = struct.pack("<HHH", 0, 1, len(images))
    entries = bytearray()
    offset = 6 + 16 * len(images)
    for size, data in images:
        dimension = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset
        )
        offset += len(data)

    target = ROOT / "assets" / "anishade.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(header + bytes(entries) + b"".join(data for _, data in images))
    print("wrote", target, target.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
