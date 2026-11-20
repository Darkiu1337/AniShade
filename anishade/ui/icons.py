"""Runtime-drawn app icon (no image assets needed)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


def make_logo(size: int = 64) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)

    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#6b8aff"))
    gradient.setColorAt(1.0, QColor("#8b5cf6"))

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.27, size * 0.27)
    painter.fillPath(path, gradient)

    # stylised "A" made of two strokes, crisp at any size
    painter.setPen(QPen(QColor(255, 255, 255, 240), max(2.0, size * 0.085), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    left = QPointF(size * 0.28, size * 0.74)
    top = QPointF(size * 0.5, size * 0.24)
    right = QPointF(size * 0.72, size * 0.74)
    painter.drawLine(left, top)
    painter.drawLine(top, right)
    painter.setPen(QPen(QColor(255, 255, 255, 235), max(1.6, size * 0.07), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(size * 0.37, size * 0.58), QPointF(size * 0.63, size * 0.58))

    # accent dot
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#3ddc97"))
    painter.drawEllipse(QPointF(size * 0.78, size * 0.24), size * 0.065, size * 0.065)
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(make_logo(size))
    return icon
