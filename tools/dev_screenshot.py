"""Render the main window to PNG without a display (for layout review)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from anishade.store import Store  # noqa: E402

OUT = ROOT / "sandbox" / "screens"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)

    from anishade.ui.main_window import MainWindow
    from anishade.ui.theme import apply_theme

    apply_theme(app)
    store = Store()
    window = MainWindow(store)
    window.resize(1280, 880)
    window.show()
    app.processEvents()

    from anishade.ui.delegates import ROLE_TITLE

    for row in range(window.game_list.count()):
        item = window.game_list.item(row)
        if str(item.data(ROLE_TITLE)).startswith("Sakura"):
            window.game_list.setCurrentRow(row)
            break
    app.processEvents()
    app.processEvents()

    window.grab().save(str(OUT / "main.png"))
    window.log_button.setChecked(True)
    app.processEvents()
    window.grab().save(str(OUT / "main_log.png"))
    window.log_button.setChecked(False)
    app.processEvents()

    window.content_scroll.verticalScrollBar().setValue(9999)
    app.processEvents()
    window.grab().save(str(OUT / "main_bottom.png"))
    window.content_scroll.verticalScrollBar().setValue(0)
    app.processEvents()

    from anishade.ui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(store, window)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(OUT / "settings.png"))
    print("saved:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
