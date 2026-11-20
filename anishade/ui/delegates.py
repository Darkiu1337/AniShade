"""Item delegates: game cards and Anime4K variant rows, painted by hand."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from .theme import MUTED, SUCCESS, TEXT, WARNING

ROLE_TITLE = Qt.UserRole + 10
ROLE_SUBTITLE = Qt.UserRole + 11
ROLE_STATUS = Qt.UserRole + 12
ROLE_STATUS_KIND = Qt.UserRole + 13
ROLE_RESOLUTION = Qt.UserRole + 14
ROLE_COST = Qt.UserRole + 15
ROLE_DESC = Qt.UserRole + 16
ROLE_FAMILY = Qt.UserRole + 17

_STATUS_COLORS = {
    "ok": QColor(SUCCESS),
    "warn": QColor(WARNING),
    "pending": QColor("#79828f"),
    "error": QColor("#ff7b7b"),
}


def _rounded(painter: QPainter, rect: QRect, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


class _BaseDelegate(QStyledItemDelegate):
    row_height = 58

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(0, self.row_height)

    def _background(self, painter: QPainter, option, rect: QRect) -> None:
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        path = _rounded(painter, rect, 9)
        if selected:
            painter.fillPath(path, QColor(91, 124, 250, 42))
            painter.setPen(QPen(QColor(91, 124, 250, 150), 1))
            painter.drawPath(path)
        elif hovered:
            painter.fillPath(path, QColor(255, 255, 255, 11))


class GameDelegate(_BaseDelegate):
    row_height = 60

    def paint(self, painter: QPainter, option, index) -> None:  # noqa: C901
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = option.rect.adjusted(5, 3, -5, -3)
        self._background(painter, option, rect)

        title = str(index.data(ROLE_TITLE) or "")
        subtitle = str(index.data(ROLE_SUBTITLE) or "")
        status = str(index.data(ROLE_STATUS) or "")
        kind = str(index.data(ROLE_STATUS_KIND) or "pending")

        status_font = QFont(option.font)
        status_font.setPointSizeF(8.3)
        status_metrics = QFontMetrics(status_font)
        status_width = status_metrics.horizontalAdvance(status) + 22

        left = rect.left() + 12
        right = rect.right() - 12 - status_width

        title_font = QFont(option.font)
        title_font.setPointSizeF(10.4)
        title_font.setWeight(QFont.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(TEXT if option.state & QStyle.State_Selected else "#e9edf5"))
        title_metrics = QFontMetrics(title_font)
        painter.drawText(
            QRect(left, rect.top() + 8, max(10, right - left), 22),
            Qt.AlignLeft | Qt.AlignVCenter,
            title_metrics.elidedText(title, Qt.ElideRight, max(10, right - left)),
        )

        sub_font = QFont(option.font)
        sub_font.setPointSizeF(8.4)
        painter.setFont(sub_font)
        painter.setPen(QColor(MUTED))
        sub_metrics = QFontMetrics(sub_font)
        painter.drawText(
            QRect(left, rect.top() + 29, max(10, right - left), 18),
            Qt.AlignLeft | Qt.AlignVCenter,
            sub_metrics.elidedText(subtitle, Qt.ElideRight, max(10, right - left)),
        )

        color = _STATUS_COLORS.get(kind, _STATUS_COLORS["pending"])
        dot_rect = QRect(rect.right() - 12 - status_width + 2, rect.center().y() - 3, 6, 6)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(dot_rect)

        painter.setFont(status_font)
        painter.setPen(color if kind != "pending" else QColor(MUTED))
        painter.drawText(
            QRect(dot_rect.right() + 6, rect.center().y() - 9, status_width, 18),
            Qt.AlignLeft | Qt.AlignVCenter,
            status,
        )
        painter.restore()


class VariantDelegate(_BaseDelegate):
    row_height = 62

    def paint(self, painter: QPainter, option, index) -> None:  # noqa: C901
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = option.rect.adjusted(5, 3, -5, -3)
        self._background(painter, option, rect)

        title = str(index.data(ROLE_TITLE) or "")
        desc = str(index.data(ROLE_DESC) or "")
        resolution = str(index.data(ROLE_RESOLUTION) or "")
        cost = int(index.data(ROLE_COST) or 1)
        family = str(index.data(ROLE_FAMILY) or "")

        left = rect.left() + 12

        # family badge
        badge_font = QFont(option.font)
        badge_font.setPointSizeF(7.4)
        badge_font.setWeight(QFont.DemiBold)
        badge_metrics = QFontMetrics(badge_font)
        badge_w = badge_metrics.horizontalAdvance(family) + 14
        badge_rect = QRect(left, rect.top() + 10, badge_w, 17)
        badge_color = QColor(91, 124, 250, 60) if family.upper() == "CNN" else QColor(61, 220, 151, 45)
        painter.setBrush(badge_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(badge_rect, 6, 6)
        painter.setFont(badge_font)
        painter.setPen(QColor("#c9d4ff") if family.upper() == "CNN" else QColor("#a8e9cf"))
        painter.drawText(badge_rect, Qt.AlignCenter, family.upper())

        title_font = QFont(option.font)
        title_font.setPointSizeF(10.2)
        title_font.setWeight(QFont.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(TEXT))
        title_x = badge_rect.right() + 9
        title_metrics = QFontMetrics(title_font)
        res_font = QFont(option.font)
        res_font.setPointSizeF(8.3)
        res_metrics = QFontMetrics(res_font)
        res_w = res_metrics.horizontalAdvance(resolution) + 8
        title_w = rect.right() - 12 - res_w - title_x
        painter.drawText(
            QRect(title_x, rect.top() + 8, max(10, title_w), 20),
            Qt.AlignLeft | Qt.AlignVCenter,
            title_metrics.elidedText(title, Qt.ElideRight, max(10, title_w)),
        )
        painter.setFont(res_font)
        painter.setPen(QColor(MUTED))
        painter.drawText(
            QRect(rect.right() - 12 - res_w, rect.top() + 8, res_w, 20),
            Qt.AlignRight | Qt.AlignVCenter,
            resolution,
        )

        desc_font = QFont(option.font)
        desc_font.setPointSizeF(8.3)
        painter.setFont(desc_font)
        painter.setPen(QColor(MUTED))
        desc_metrics = QFontMetrics(desc_font)
        cost_w = 46
        desc_w = rect.width() - (left - rect.left()) - 12 - cost_w
        painter.drawText(
            QRect(left, rect.top() + 30, max(10, desc_w), 24),
            Qt.AlignLeft | Qt.AlignVCenter,
            desc_metrics.elidedText(desc, Qt.ElideRight, max(10, desc_w)),
        )

        # cost bars, right aligned
        bars = min(8, max(1, cost))
        bar_w, gap, h = 3, 3, 12
        total = bars * bar_w + (bars - 1) * gap
        x = rect.right() - 12 - total
        y = rect.top() + 36
        for bar in range(bars):
            alpha = 235 - bar * 18
            painter.setBrush(QColor(91, 124, 250, max(90, alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRect(x + bar * (bar_w + gap), y, bar_w, h), 1.5, 1.5)
        painter.restore()
