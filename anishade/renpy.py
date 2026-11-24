"""Universal Ren'Py Mod (URM) acquisition, cache and per-game installer.

Source: https://0x52.dev/mods/Universal-Ren-Py-Mod-1000

URM is never redistributed by AniShade: the official archive is downloaded once
from 0x52.dev, ``0x52_URM.rpa`` is extracted and cached locally, and then copied
into each Ren'Py game's ``game/`` directory when toggled on.
"""

from __future__ import annotations

import json
import re
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import __version__, paths, winapi

SUPPORTED_ENGINES = ("renpy",)

MOD_ID = 1000
MOD_PAGE_URL = "https://0x52.dev/mods/Universal-Ren-Py-Mod-1000"
API_BASE = "https://api.0x52.dev"
MOD_INFO_URL = f"{API_BASE}/mods/{MOD_ID}"
MOD_VERSIONS_URL = f"{API_BASE}/mods/{MOD_ID}/versions"
URM_FILENAME = "0x52_URM.rpa"
USER_AGENT = f"AniShade/{__version__} (+{MOD_PAGE_URL})"

Progress = Callable[[int, int], None]
Status = Callable[[str], None]


class RenpyModError(Exception):
    pass


@dataclass
class UrmRelease:
    version: str
    version_id: int
    url: str
    filename: str = "0x52_URM.zip"
    size: int = 0
    channel: str = "stable"


@dataclass
class CachedUrm:
    version: str
    folder: Path
    rpa_path: Path
    from_cache: bool = True
    meta: dict | None = None


@dataclass
class UrmInstallResult:
    installed: bool = False
    version: str = ""
    rpa_path: str = ""
    rpa_sha256: str = ""
    backup_path: str = ""
    warning: str = ""

    def to_manifest(self) -> dict:
        return {
            "version": self.version,
            "rpa_path": self.rpa_path,
            "rpa_sha256": self.rpa_sha256,
            "backup_path": self.backup_path,
        }


def is_supported_engine(engine_key: str) -> bool:
    return engine_key in SUPPORTED_ENGINES


def _normalize_version(version: str) -> str:
    return (version or "").strip().lstrip("vV")


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in _normalize_version(version).split("."):
        digits = re.sub(r"\D", "", piece)
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _request(url: str, timeout: int = 30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def _download_url(version_id: int) -> str:
    return f"{API_BASE}/modversions/{version_id}/download"


def _pick_release_from_entries(entries: list[dict], preferred_version: str | None = None) -> UrmRelease | None:
    published = [
        item
        for item in entries
        if isinstance(item, dict)
        and item.get("id") is not None
        and item.get("versionName")
        and item.get("isPublished", True)
    ]
    if not published:
        return None

    if preferred_version:
        wanted = _normalize_version(preferred_version)
        for item in published:
            if _normalize_version(str(item.get("versionName") or "")) == wanted:
                return _entry_to_release(item)

    stables = [item for item in published if str(item.get("channel") or "stable").lower() == "stable"]
    pool = stables or published
    pool.sort(
        key=lambda item: (
            _version_key(str(item.get("versionName") or "")),
            int(item.get("id") or 0),
        )
    )
    return _entry_to_release(pool[-1])


def _entry_to_release(entry: dict) -> UrmRelease:
    version_id = int(entry["id"])
    version_name = _normalize_version(str(entry.get("versionName") or ""))
    file_info = entry.get("file") if isinstance(entry.get("file"), dict) else {}
    return UrmRelease(
        version=version_name,
        version_id=version_id,
        url=_download_url(version_id),
        filename=str(file_info.get("filename") or "0x52_URM.zip"),
        size=int(file_info.get("size") or 0),
        channel=str(entry.get("channel") or "stable"),
    )


def fetch_latest_release(preferred_version: str | None = None, timeout: int = 30) -> UrmRelease:
    """Resolve the latest stable Universal Ren'Py Mod release from api.0x52.dev."""
    if not preferred_version:
        try:
            with _request(MOD_INFO_URL, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8", "ignore"))
            latest_stable = data.get("latestStable") if isinstance(data, dict) else None
            if isinstance(latest_stable, list):
                picked = _pick_release_from_entries(latest_stable)
                if picked is not None:
                    return picked
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            pass

    try:
        with _request(MOD_VERSIONS_URL, timeout=timeout) as response:
            entries = json.loads(response.read().decode("utf-8", "ignore"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RenpyModError(f"Nao foi possivel consultar 0x52.dev: {exc}") from exc

    if not isinstance(entries, list):
        raise RenpyModError("Resposta inesperada da API do 0x52.dev.")

    picked = _pick_release_from_entries(entries, preferred_version=preferred_version)
    if picked is None:
        raise RenpyModError("Nenhuma versao disponivel do Universal Ren'Py Mod foi encontrada em 0x52.dev.")
    return picked


def extract_rpa(archive_path: str | Path) -> bytes:
    """Extract 0x52_URM.rpa from the downloaded ZIP archive and verify its RPA header."""
    path = Path(archive_path)
    try:
        with zipfile.ZipFile(path, "r") as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            chosen = None
            for info in members:
                if Path(info.filename).name.lower() == URM_FILENAME.lower():
                    chosen = info
                    break
            if chosen is None:
                for info in members:
                    if info.filename.lower().endswith(".rpa"):
                        chosen = info
                        break
            if chosen is None:
                raise RenpyModError(
                    f"Arquivo {URM_FILENAME} nao encontrado dentro do ZIP baixado de 0x52.dev."
                )
            data = archive.read(chosen)
    except (zipfile.BadZipFile, OSError, KeyError) as exc:
        raise RenpyModError(f"Arquivo ZIP do Universal Ren'Py Mod invalido ou corrompido: {exc}") from exc

    if len(data) < 1024 or not data.startswith(b"RPA-"):
        raise RenpyModError(f"{URM_FILENAME} extraido nao parece um arquivo .rpa valido do Ren'Py.")
    return data


def download_archive(
    release: UrmRelease,
    progress: Progress | None = None,
    status: Status | None = None,
) -> Path:
    paths.ensure_dirs()
    safe_ver = re.sub(r"[^0-9A-Za-z._-]+", "_", release.version) or str(release.version_id)
    target = paths.DOWNLOAD_DIR / f"0x52_URM_{safe_ver}.zip"
    if target.is_file() and target.stat().st_size > 10_000:
        try:
            extract_rpa(target)
            if status:
                status(f"Pacote Universal Ren'Py Mod {release.version} ja esta no cache de downloads.")
            return target
        except RenpyModError:
            target.unlink(missing_ok=True)

    temporary = target.with_suffix(target.suffix + ".part")
    if status:
        status(f"Baixando Universal Ren'Py Mod {release.version} de 0x52.dev ...")
    try:
        with _request(release.url, timeout=60) as response, open(temporary, "wb") as handle:
            total = int(response.headers.get("Content-Length") or release.size or 0)
            downloaded = 0
            while True:
                chunk = response.read(128 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise RenpyModError(f"Falha ao baixar o Universal Ren'Py Mod: {exc}") from exc

    try:
        extract_rpa(temporary)
    except RenpyModError:
        temporary.unlink(missing_ok=True)
        raise

    temporary.replace(target)
    if status:
        status(
            f"Universal Ren'Py Mod {release.version} baixado "
            f"({target.stat().st_size / 1048576:.1f} MB)."
        )
    return target


def _meta_path(folder: Path) -> Path:
    return folder / "meta.json"


def _load_meta(folder: Path) -> dict:
    try:
        return json.loads(_meta_path(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def list_cached() -> list[CachedUrm]:
    paths.ensure_dirs()
    releases: list[CachedUrm] = []
    for folder in paths.URM_CACHE_DIR.iterdir():
        if not folder.is_dir() or folder.name.endswith(".tmp"):
            continue
        rpa = folder / URM_FILENAME
        if rpa.is_file():
            releases.append(
                CachedUrm(
                    version=folder.name,
                    folder=folder,
                    rpa_path=rpa,
                    meta=_load_meta(folder),
                )
            )
    releases.sort(key=lambda item: _version_key(item.version), reverse=True)
    return releases


def newest_cached() -> CachedUrm | None:
    cached = list_cached()
    return cached[0] if cached else None


def cache_from_archive(archive_path: Path, release: UrmRelease) -> CachedUrm:
    payload = extract_rpa(archive_path)
    folder = paths.URM_CACHE_DIR / release.version
    temporary = folder.with_name(folder.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True, exist_ok=True)
    try:
        (temporary / URM_FILENAME).write_bytes(payload)
        meta = {
            "version": release.version,
            "version_id": release.version_id,
            "source": release.url or MOD_PAGE_URL,
            "page": MOD_PAGE_URL,
            "sha256": winapi.sha256_bytes(payload),
            "archive_sha256": winapi.sha256_file(archive_path) if archive_path.is_file() else "",
            "cached_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "app_version": __version__,
        }
        _meta_path(temporary).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    temporary.replace(folder)
    return CachedUrm(
        version=release.version,
        folder=folder,
        rpa_path=folder / URM_FILENAME,
        from_cache=False,
        meta=meta,
    )


def ensure_release(
    preferred_version: str | None = None,
    progress: Progress | None = None,
    status: Status | None = None,
    allow_network: bool = True,
) -> CachedUrm:
    """Return a cached Universal Ren'Py Mod build, downloading it only when needed."""
    cached = list_cached()
    if preferred_version:
        wanted = _normalize_version(preferred_version)
        for item in cached:
            if _normalize_version(item.version) == wanted:
                if status:
                    status(f"Usando Universal Ren'Py Mod {item.version} do cache local.")
                return item
    elif cached:
        if status:
            status(f"Usando Universal Ren'Py Mod {cached[0].version} do cache local.")
        return cached[0]

    if not allow_network:
        if cached:
            return cached[0]
        raise RenpyModError(
            "Nenhuma versao do Universal Ren'Py Mod esta no cache e a rede esta desativada."
        )

    if status:
        status("Consultando a versao mais recente do Universal Ren'Py Mod em 0x52.dev ...")
    try:
        release = fetch_latest_release(preferred_version=preferred_version)
    except RenpyModError:
        if cached:
            if status:
                status("Sem conexao com 0x52.dev; usando a versao em cache.")
            return cached[0]
        raise

    archive = download_archive(release, progress=progress, status=status)
    if status:
        status(f"Extraindo {URM_FILENAME} ...")
    return cache_from_archive(archive, release)


def prune_cache(keep: int = 1) -> list[str]:
    """Delete old cached URM builds, returning removed version labels."""
    cached = list_cached()
    removed: list[str] = []
    for item in cached[keep:]:
        shutil.rmtree(item.folder, ignore_errors=True)
        removed.append(item.version)
    return removed


def verified_rpa(cached: CachedUrm) -> Path:
    rpa = cached.rpa_path
    if not rpa.is_file():
        raise RenpyModError(f"{URM_FILENAME} nao encontrado no cache local.")
    meta = cached.meta or {}
    expected = meta.get("sha256")
    if expected and winapi.sha256_file(rpa) != expected:
        raise RenpyModError(
            f"{URM_FILENAME} no cache esta corrompido. Remova {cached.folder} e baixe novamente."
        )
    return rpa


# ---------------------------------------------------------------------------
# Per-game detection and install / uninstall / inspect
# ---------------------------------------------------------------------------

def find_game_dir(game_dir: Path) -> Path | None:
    """Locate the Ren'Py ``game/`` directory for a game root."""
    direct = game_dir / "game"
    if direct.is_dir():
        return direct
    # Some users point to an exe inside lib/<platform>/ (e.g. lib/py3-windows-x86_64/pythonw.exe)
    parent = game_dir.parent
    if parent.name.lower() == "lib":
        root = parent.parent
        nested = root / "game"
        if nested.is_dir() and (root / "renpy").is_dir():
            return nested
    return None


def is_urm_active(game_dir: Path) -> bool:
    """True when ``0x52_URM.rpa`` is currently present inside the game's ``game/`` folder."""
    renpy_game = find_game_dir(game_dir)
    if renpy_game is None:
        return False
    return (renpy_game / URM_FILENAME).is_file()


def _rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def _default_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".anishade.tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def install_urm(
    game_dir: Path,
    rpa_source: Path,
    version: str = "",
    write_fn=None,
    backup_fn=None,
    existing_meta: dict | None = None,
) -> UrmInstallResult:
    """Copy ``0x52_URM.rpa`` into the Ren'Py game's ``game/`` directory."""
    renpy_game = find_game_dir(game_dir)
    if renpy_game is None:
        return UrmInstallResult(
            installed=False,
            warning="Pasta 'game/' do Ren'Py nao encontrada ao lado do executavel.",
        )

    writer = write_fn or _default_write
    target = renpy_game / URM_FILENAME
    payload = rpa_source.read_bytes()
    payload_sha = winapi.sha256_bytes(payload)

    backup_path = str((existing_meta or {}).get("backup_path") or "")
    expected_prev = str((existing_meta or {}).get("rpa_sha256") or "")
    if target.is_file():
        current_sha = winapi.sha256_file(target)
        if current_sha != payload_sha and current_sha != expected_prev and backup_fn:
            saved = backup_fn(target, URM_FILENAME)
            if saved:
                backup_path = saved

    writer(target, payload)
    return UrmInstallResult(
        installed=True,
        version=version,
        rpa_path=_rel(target, game_dir),
        rpa_sha256=payload_sha,
        backup_path=backup_path,
    )


def uninstall_urm(
    game_dir: Path,
    meta: dict | None,
    backup_fn=None,
    log: Status | None = None,
) -> list[str]:
    """Remove ``0x52_URM.rpa`` from the Ren'Py game's ``game/`` directory."""
    removed: list[str] = []
    meta = meta or {}
    rel_path = str(meta.get("rpa_path") or "")
    target = (game_dir / rel_path) if rel_path else None
    if target is None or not target.is_file():
        renpy_game = find_game_dir(game_dir)
        if renpy_game is not None:
            candidate = renpy_game / URM_FILENAME
            if candidate.is_file():
                target = candidate
                rel_path = _rel(candidate, game_dir)
    if target is None or not target.is_file():
        return removed

    expected = str(meta.get("rpa_sha256") or "")
    if expected and winapi.sha256_file(target) != expected and backup_fn:
        saved = backup_fn(target, URM_FILENAME)
        if saved and log:
            log(f"{URM_FILENAME} modificado foi salvo em backup antes de remover: {saved}")

    try:
        target.unlink()
        removed.append(rel_path or URM_FILENAME)
    except OSError as exc:
        if log:
            log(f"Nao foi possivel remover {URM_FILENAME}: {exc}")
    return removed


def inspect_urm(game_dir: Path, meta: dict | None) -> tuple[bool, list[str]]:
    """Verify that the installed Universal Ren'Py Mod archive is present."""
    if not meta:
        return True, []
    rel_path = str(meta.get("rpa_path") or "")
    target = (game_dir / rel_path) if rel_path else None
    if target is None:
        renpy_game = find_game_dir(game_dir)
        target = (renpy_game / URM_FILENAME) if renpy_game is not None else None
    if target is None or not target.is_file():
        return False, [f"Mod Universal Ren'Py Mod ({URM_FILENAME}) ausente na pasta game/."]
    return True, []
