"""Dark theme and shared visual constants."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from .. import paths

ACCENT = "#5b7cfa"
ACCENT_HOVER = "#6b8aff"
BG = "#14161a"
PANEL = "#1b1e24"
CARD = "#1b1e24"
BORDER = "#2a2f39"
TEXT = "#e6e9ef"
MUTED = "#9aa3b2"
SUCCESS = "#3ddc97"
WARNING = "#ffc857"
DANGER = "#ff7b7b"

DARK_QSS = f"""
QWidget {{
    color: {TEXT};
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 9.5pt;
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#banner {{
    background: #23231a;
    border: 1px solid #4a4326;
    border-radius: 10px;
}}
QFrame#bannerInfo {{
    background: #182330;
    border: 1px solid #274157;
    border-radius: 10px;
}}
QFrame#divider {{
    background: {BORDER};
    max-height: 1px;
    border: none;
}}
QLabel#appTitle {{
    font-size: 15pt;
    font-weight: 600;
    color: #ffffff;
}}
QLabel#appSubtitle {{
    color: {MUTED};
    font-size: 8.5pt;
}}
QLabel#gameTitle {{
    font-size: 17pt;
    font-weight: 600;
    color: #ffffff;
}}
QLabel#path {{
    color: {MUTED};
    font-size: 8.5pt;
}}
QLabel#sectionTitle {{
    font-size: 10pt;
    font-weight: 600;
    color: #cfd6e2;
}}
QLabel#muted {{
    color: {MUTED};
}}
QLabel#warning {{
    color: #ffd479;
    background: #26231a;
    border: 1px solid #40391f;
    border-radius: 8px;
    padding: 8px 10px;
}}
QLabel#chain {{
    color: #b9c6ff;
    background: #191d26;
    border: 1px solid #2b3242;
    border-radius: 8px;
    padding: 8px 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 9pt;
}}
QLabel#statusOk {{ color: {SUCCESS}; }}
QLabel#statusWarn {{ color: {WARNING}; }}
QLabel#statusBad {{ color: {DANGER}; }}

QPushButton {{
    background: #262b34;
    border: 1px solid #343b47;
    border-radius: 8px;
    padding: 7px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: #2f3540; border-color: #3f4754; }}
QPushButton:pressed {{ background: #22262e; }}
QPushButton:disabled {{ color: #616a78; background: #1d2127; border-color: #262b34; }}
QPushButton#primary {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #ffffff;
    font-weight: 600;
    padding: 9px 18px;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: #2b3552; border-color: #2b3552; color: #7d8aa8; }}
QPushButton#danger {{
    background: transparent;
    border: 1px solid #4d2c31;
    color: {DANGER};
}}
QPushButton#danger:hover {{ background: #2a1c1f; }}
QPushButton#danger:disabled {{
    color: #5b6472;
    border-color: #2a2f39;
    background: transparent;
}}
QPushButton#ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {MUTED};
    padding: 6px 10px;
}}
QPushButton#ghost:hover {{ color: {TEXT}; background: #23272f; }}
QPushButton#ghost:disabled {{ color: #5b6472; background: transparent; }}
QPushButton#chip {{
    background: transparent;
    border: 1px solid #333a46;
    border-radius: 10px;
    padding: 4px 10px;
    color: {MUTED};
    font-size: 8.5pt;
}}
QPushButton#chip:hover {{ color: {TEXT}; border-color: #49515f; }}

QLineEdit, QComboBox, QSpinBox {{
    background: #11141a;
    border: 1px solid #2d333d;
    border-radius: 7px;
    padding: 6px 9px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {PANEL};
    border: 1px solid #2d333d;
    border-radius: 8px;
    selection-background-color: #2a3550;
    padding: 4px;
    outline: none;
}}
QCheckBox {{ spacing: 8px; color: #cbd2de; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 5px;
    border: 1px solid #3a414d;
    background: #11141a;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:disabled {{ border-color: #2a2f39; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border: none; }}
QListWidget::item:selected {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #333a46; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #414a59; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #333a46; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

QProgressBar {{
    background: #1d2127;
    border: none;
    border-radius: 4px;
    max-height: 6px;
    min-height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QPlainTextEdit {{
    background: #0f1116;
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: #aab6c8;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8.5pt;
    padding: 6px;
}}
QSplitter::handle {{ background: transparent; width: 10px; }}
QMenu {{
    background: {PANEL};
    border: 1px solid #2d333d;
    border-radius: 8px;
    padding: 5px;
}}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: #2a3550; }}
QMessageBox {{ background: {PANEL}; }}
QToolTip {{
    background: #11141a;
    color: {TEXT};
    border: 1px solid #333a46;
    padding: 5px 8px;
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor("#11141a"))
    palette.setColor(QPalette.AlternateBase, QColor(PANEL))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor("#262b34"))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor(PANEL))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#616a78"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#616a78"))
    app.setPalette(palette)
    extra = ""
    check = paths.bundle_dir() / "assets" / "check.svg"
    if check.is_file():
        extra = (
            "QCheckBox::indicator:checked {"
            f" image: url('{check.as_posix()}');"
            "}"
        )
    app.setStyleSheet(DARK_QSS + extra)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
