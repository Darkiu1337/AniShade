"""Small reusable widgets."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import ACCENT, ACCENT_HOVER


class Card(QFrame):
    """Rounded panel with an optional title and header actions."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(10)

        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        if title:
            self.header.addWidget(self.title_label)
            self.header.addStretch(1)
            outer.addLayout(self.header)

        self.content = QVBoxLayout()
        self.content.setSpacing(9)
        outer.addLayout(self.content)

    def add_header_widget(self, widget: QWidget) -> None:
        self.header.addWidget(widget)

    def add(self, widget: QWidget) -> QWidget:
        self.content.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self.content.addLayout(layout)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFixedHeight(1)


class ElidedLabel(QLabel):
    """Single line label that elides instead of resizing the window."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.ElideMiddle, max(10, self.width()))
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.rect(), self.alignment(), elided)


class Banner(QFrame):
    def __init__(
        self,
        text: str,
        action_text: str = "",
        kind: str = "info",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("banner" if kind == "warn" else "bannerInfo")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 12, 10)
        layout.setSpacing(10)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: #d8dee9;" if kind != "warn" else "color: #f0dfae;")
        layout.addWidget(self.label, 1)
        self.button = QPushButton(action_text)
        self.button.setObjectName("chip")
        if not action_text:
            self.button.hide()
        layout.addWidget(self.button)


class ChainLabel(QLabel):
    """Shows the technique chain with arrows between passes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chain")
        self.setWordWrap(True)

    def set_chain(self, steps: list[str]) -> None:
        self.setText("  →  ".join(steps) if steps else "Nenhum passe selecionado")


class ToggleSwitch(QAbstractButton):
    """Compact pill toggle switch matching AniShade's dark theme."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 22)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(42, 22)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        radius = rect.height() / 2.0

        if not self.isEnabled():
            track_color = QColor("#22262e")
            thumb_color = QColor("#616a78")
        elif self.isChecked():
            track_color = QColor(ACCENT_HOVER if self.underMouse() else ACCENT)
            thumb_color = QColor("#ffffff")
        else:
            track_color = QColor("#353c48" if self.underMouse() else "#2a303b")
            thumb_color = QColor("#cfd6e2")

        painter.setPen(Qt.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, radius, radius)

        margin = 3.0
        knob_d = self.height() - margin * 2.0
        knob_x = (self.width() - knob_d - margin) if self.isChecked() else margin
        painter.setBrush(thumb_color)
        painter.drawEllipse(QRectF(knob_x, margin, knob_d, knob_d))
