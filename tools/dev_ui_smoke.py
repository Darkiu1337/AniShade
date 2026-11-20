"""Exercise selection/edit handlers headlessly to catch UI regressions."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from anishade import reshade  # noqa: E402
from anishade.store import Store  # noqa: E402
from anishade.ui.main_window import MainWindow  # noqa: E402
from anishade.ui.theme import apply_theme  # noqa: E402

OUT = ROOT / "sandbox" / "screens"


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    store = Store()
    window = MainWindow(store)
    window.resize(1280, 880)
    window.show()
    app.processEvents()

    assert window.game_list.count() >= 3, "fixtures ausentes"
    for row in range(window.game_list.count()):
        window.game_list.setCurrentRow(row)
        app.processEvents()
        window._select_variant("soft_l")
        window.margin_spin.setValue(0)
        window.aspect_spin.setValue(1.5)
        app.processEvents()
        options = window._options()
        assert options.variant == "soft_l", options
        assert abs(options.content_aspect - 1.5) < 0.001, options
        assert window.margin_spin.value() == 0
        assert abs(window.aspect_spin.value() - 1.5) < 0.001
        assert window.install_button.text() in (
            "Instalar ReShade + Anime4K",
            "Aplicar alterações",
            "Reinstalar",
        ), window.install_button.text()

    # empty state
    window.hide()
    empty_store = Store()
    empty_store.games = []
    empty = MainWindow(empty_store)
    empty.resize(1280, 880)
    empty.show()
    app.processEvents()
    empty.grab().save(str(OUT / "empty.png"))

    # first run banner (pretend cache is empty)
    original = reshade.list_cached
    reshade.list_cached = lambda: []
    first = MainWindow(store)
    first.resize(1280, 880)
    first.show()
    app.processEvents()
    first.grab().save(str(OUT / "first_run.png"))
    reshade.list_cached = original

    print("ui smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
