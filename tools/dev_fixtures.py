"""Create fake game folders and library entries for UI development.

Not part of the shipped app; used to render screenshots and smoke-test flows.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from anishade import detect, installer, paths  # noqa: E402
from anishade.store import Game, Store, game_id_for  # noqa: E402

SANDBOX = ROOT / "sandbox"
NOTEPAD = Path(r"C:\Windows\System32\notepad.exe")

FIXTURES = {
    "FakeVN": {
        "name": "Sakura no Uta — Fake Demo",
        "files": {
            "game/script.rpyc": "",
            "renpy/common/00start.rpy": "init python: pass\n",
        },
        "variant": "cnn_l",
    },
    "FakeMV": {
        "name": "RPG Maker MV — Fake Project",
        "files": {
            "www/js/rmmz_core.js": "// fake\n",
            "www/index.html": "<html></html>\n",
            "package.json": '{"name":"fake","main":"www/index.html"}\n',
            "nw.dll": "fake\n",
        },
        "variant": "cnn_s",
    },
    "FakeUnity": {
        "name": "Unity — Fake Visual Novel",
        "files": {
            "UnityPlayer.dll": "fake\n",
            "FakeUnity_Data/globalgamemanagers": "fake\n",
        },
        "variant": "cnn_m",
    },
}


def build_fixtures() -> Store:
    paths.ensure_dirs()
    store = Store()
    store.games = []
    store.save_games()

    for folder, spec in FIXTURES.items():
        directory = SANDBOX / folder
        directory.mkdir(parents=True, exist_ok=True)
        exe = directory / ("Game.exe" if folder == "FakeMV" else f"{folder}.exe")
        shutil.copy2(NOTEPAD, exe)
        for relative, content in spec["files"].items():
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        analysis = detect.analyze(exe)
        game = Game(
            id=game_id_for(exe),
            name=spec["name"],
            exe=str(exe),
            engine_key=analysis.engine.key,
            engine_name=analysis.engine.name,
            api=analysis.api,
            dll_name=analysis.dll_name,
            bits=analysis.bits or 64,
            variant=spec["variant"],
            top_margin=0,
            content_aspect=-1.0,
        )
        store.add_or_update(game)

    installed = next(game for game in store.games if game.name.startswith("Sakura"))
    installer.install(
        store,
        installed,
        installer.InstallOptions(variant="cnn_l", content_aspect=1.5),
        status=print,
    )
    return store


if __name__ == "__main__":
    build_fixtures()
    print("fixtures ready")
