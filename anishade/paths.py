"""Filesystem locations used by AniShade."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "AniShade"


def _local_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Local"


DATA_DIR = _local_appdata() / APP_DIR_NAME
CACHE_DIR = DATA_DIR / "cache"
DOWNLOAD_DIR = CACHE_DIR / "downloads"
RESHADE_CACHE_DIR = CACHE_DIR / "reshade"
NWJS_CACHE_DIR = CACHE_DIR / "nwjs"
GAME_DATA_DIR = DATA_DIR / "games"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = DATA_DIR / "logs"
SETTINGS_FILE = DATA_DIR / "settings.json"
GAMES_FILE = DATA_DIR / "games.json"


def ensure_dirs() -> None:
    for path in (
        DATA_DIR,
        CACHE_DIR,
        DOWNLOAD_DIR,
        RESHADE_CACHE_DIR,
        NWJS_CACHE_DIR,
        GAME_DATA_DIR,
        BACKUP_DIR,
        LOG_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def bundle_dir() -> Path:
    """Directory that contains bundled resources (works frozen and from source)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def anime4k_source_dir() -> Path:
    """Folder with the official Anime4K .glsl sources (reference/regeneration)."""
    candidates = [
        bundle_dir() / "vendor" / "anime4k",
        bundle_dir() / "anime4k",
    ]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.glsl")):
            return candidate
    return candidates[0]


def anime4k_fx_dir() -> Path:
    """Folder with the ReShade FX shaders generated from the GLSL sources."""
    candidates = [
        bundle_dir() / "vendor" / "anime4k_fx",
        bundle_dir() / "anime4k_fx",
    ]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.fx")):
            return candidate
    return candidates[0]


def app_icon_path() -> Path | None:
    for name in ("anishade.ico", "anishade.png"):
        candidate = bundle_dir() / "assets" / name
        if candidate.is_file():
            return candidate
    return None
