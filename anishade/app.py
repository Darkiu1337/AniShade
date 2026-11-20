"""Application entry point."""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__, paths, winapi
from .store import Store


def _setup_logging() -> None:
    paths.ensure_dirs()
    log_file = paths.LOG_DIR / "anishade.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _install_excepthook() -> None:
    def handler(exc_type, exc_value, exc_tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.error("Erro não tratado:\n%s", text)
        if QApplication.instance() is not None:
            box = QMessageBox(QMessageBox.Critical, "AniShade", str(exc_value))
            box.setDetailedText(text)
            box.exec()

    sys.excepthook = handler


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    winapi.set_dpi_awareness()

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("AniShade")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("AniShade")
    app.setDesktopFileName("AniShade")

    from .ui.icons import app_icon
    from .ui.main_window import MainWindow
    from .ui.theme import apply_theme

    app.setWindowIcon(app_icon())
    apply_theme(app)
    _install_excepthook()

    paths.ensure_dirs()
    store = Store()
    window = MainWindow(store)
    window.show()

    # Optional: open a game passed on the command line (drag & drop on the exe)
    arguments = [arg for arg in (argv or sys.argv)[1:] if arg.lower().endswith(".exe")]
    if arguments and Path(arguments[0]).is_file():
        window._add_game(arguments[0])  # noqa: SLF001 - deliberate entry helper

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
