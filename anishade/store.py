"""Persistent state: game library, per-game settings and app preferences."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import anime4k, paths


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=path.parent, encoding="utf-8", newline="\n", suffix=".tmp"
    )
    try:
        with handle:
            handle.write(text)
        os.replace(handle.name, path)
    except Exception:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


def game_id_for(exe: str | Path) -> str:
    normalized = os.path.normcase(str(Path(exe).resolve()))
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


@dataclass
class Game:
    id: str
    name: str
    exe: str
    engine_key: str = "unknown"
    engine_name: str = "Desconhecida"
    api: str = "dxgi"
    dll_name: str = "dxgi.dll"
    bits: int = 64
    variant: str = anime4k.DEFAULT_VARIANT
    top_margin: int = 0
    content_aspect: float = -1.0
    installed: bool = False
    reshade_version: str = ""
    added_at: str = ""
    last_played: str = ""
    engine_override: str = ""
    api_override: str = ""
    dll_override: str = ""
    rpgmaker_hide_textbox: bool = True
    rpgmaker_no_alt_skip: bool = True
    nwjs_version: str = ""
    user_notes: str = ""
    detected: dict = field(default_factory=dict)

    @property
    def exe_path(self) -> Path:
        return Path(self.exe)

    @property
    def game_dir(self) -> Path:
        return Path(self.exe).parent

    @property
    def preset_path(self) -> Path:
        return self.game_dir / anime4k.PRESET_NAME

    @property
    def shader_dir(self) -> Path:
        return self.game_dir / anime4k.SHADER_SUBDIR

    def techniques(self) -> list[str]:
        return anime4k.techniques(self.variant)


class Settings:
    def __init__(self, data: dict | None = None) -> None:
        data = data or {}
        self.reshade_version: str = data.get("reshade_version", "")
        self.nwjs_version: str = data.get("nwjs_version", "")
        self.auto_check_reshade: bool = bool(data.get("auto_check_reshade", True))
        self.default_variant: str = data.get("default_variant", anime4k.DEFAULT_VARIANT)
        self.default_top_margin: int = int(data.get("default_top_margin", 0))
        self.create_launcher: bool = bool(data.get("create_launcher", True))
        self.rpgmaker_hide_textbox: bool = bool(data.get("rpgmaker_hide_textbox", True))
        self.rpgmaker_no_alt_skip: bool = bool(data.get("rpgmaker_no_alt_skip", True))
        self.theme: str = data.get("theme", "dark")
        self.last_dir: str = data.get("last_dir", "")
        self.confirm_before_overwrite: bool = bool(data.get("confirm_before_overwrite", True))
        self.window_width: int = int(data.get("window_width", 1180))
        self.window_height: int = int(data.get("window_height", 760))

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class Store:
    def __init__(self) -> None:
        paths.ensure_dirs()
        self.settings = self._load_settings()
        self.games: list[Game] = self._load_games()

    # -- io --------------------------------------------------------------
    def _load_settings(self) -> Settings:
        try:
            return Settings(json.loads(paths.SETTINGS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return Settings()

    def _load_games(self) -> list[Game]:
        try:
            raw = json.loads(paths.GAMES_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        games: list[Game] = []
        known = set(Game.__dataclass_fields__)
        for entry in raw.get("games", []):
            if not isinstance(entry, dict):
                continue
            filtered = {key: value for key, value in entry.items() if key in known}
            try:
                games.append(Game(**filtered))
            except TypeError:
                continue
        return games

    def save_settings(self) -> None:
        _atomic_write(paths.SETTINGS_FILE, json.dumps(self.settings.to_dict(), indent=2))

    def save_games(self) -> None:
        payload = {"version": 1, "games": [asdict(game) for game in self.games]}
        _atomic_write(paths.GAMES_FILE, json.dumps(payload, indent=2, ensure_ascii=False))

    # -- queries ---------------------------------------------------------
    def get(self, game_id: str) -> Game | None:
        for game in self.games:
            if game.id == game_id:
                return game
        return None

    def find_by_exe(self, exe: str | Path) -> Game | None:
        identifier = game_id_for(exe)
        return self.get(identifier)

    def sorted_games(self) -> list[Game]:
        return sorted(self.games, key=lambda game: (game.name.casefold(), game.exe.casefold()))

    # -- mutations -------------------------------------------------------
    def add_or_update(self, game: Game) -> Game:
        existing = self.get(game.id)
        if existing:
            for key in Game.__dataclass_fields__:
                if key in ("added_at", "last_played"):
                    continue
                setattr(existing, key, getattr(game, key))
            self.save_games()
            return existing
        if not game.added_at:
            game.added_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.games.append(game)
        self.save_games()
        return game

    def remove(self, game_id: str) -> None:
        self.games = [game for game in self.games if game.id != game_id]
        self.save_games()

    def touch_played(self, game: Game) -> None:
        game.last_played = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save_games()
