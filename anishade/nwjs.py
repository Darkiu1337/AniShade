"""Official NW.js acquisition, local cache, game runtime updater and compatibility fixer.

NW.js binaries are never redistributed by AniShade: the official Windows build is
downloaded once from nwjs.io / dl.nwjs.io, verified against official SHA-256 sums,
cached locally, and reused for every RPG Maker MV/MZ game going forward.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__, paths, winapi
from .i18n import tr

VERSIONS_URL = "https://nwjs.io/versions.json"
DOWNLOAD_BASE = "https://dl.nwjs.io"
USER_AGENT = f"AniShade/{__version__} (+https://nwjs.io/)"
DEFAULT_ARCH = "win-x64"
COMPAT_SHIM_FILE = "_anishade_nwjs_compat.js"

Progress = Callable[[int, int], None]
Status = Callable[[str], None]


class NwjsError(Exception):
    pass


@dataclass
class NwjsRelease:
    version: str
    arch: str = DEFAULT_ARCH
    flavor: str = "normal"
    url: str = ""
    shasums_url: str = ""
    chromium: str = ""
    node: str = ""

    @property
    def archive_name(self) -> str:
        prefix = "nwjs-sdk" if self.flavor == "sdk" else "nwjs"
        return f"{prefix}-v{self.version}-{self.arch}.zip"


@dataclass
class CachedNwjs:
    version: str
    arch: str
    folder: Path
    runtime_dir: Path
    from_cache: bool = True
    meta: dict | None = None

    @property
    def bits(self) -> int:
        return 32 if "ia32" in self.arch or "32" in self.arch else 64


@dataclass
class NwjsUpdateReport:
    version: str
    arch: str
    previous_version: str = ""
    files_updated: int = 0
    fixes_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    backup_dir: str = ""
    reshade_realigned: bool = False


#: Preload shim injected via `package.json` `"inject_js_start"` (only when the game
#: does not already define its own `inject_js_start`). Polyfills `process.mainModule`
#: for older RPG Maker MV core scripts (`StorageManager.localFileDirectoryPath`) and
#: legacy plugins running on modern Node.js / NW.js.
COMPAT_SHIM_SOURCE = """// Managed by AniShade: compatibility shim for RPG Maker MV/MZ on modern NW.js.
(function() {
    "use strict";
    try {
        if (typeof process !== "undefined" && !process.mainModule) {
            var path = require("path");
            var mainRel = "index.html";
            if (typeof nw !== "undefined" && nw.App && nw.App.manifest && nw.App.manifest.main) {
                mainRel = nw.App.manifest.main;
            }
            var exeDir = process.execPath ? path.dirname(process.execPath) : process.cwd();
            process.mainModule = { filename: path.resolve(exeDir, mainRel) };
        }
    } catch (_err) {
        // Ignore if Node context is unavailable.
    }
})();
"""

#: Strict allowlist of known legacy/modern NW.js runtime files at game root.
#: Only files in this set (or shipped inside the new NW.js runtime) are ever
#: backed up, replaced, or pruned — game content and ReShade files are untouched.
_KNOWN_NWJS_FILES = {
    "nw.exe",
    "nw.dll",
    "nw_elf.dll",
    "node.dll",
    "ffmpeg.dll",
    "ffmpegsumo.dll",
    "libegl.dll",
    "libglesv2.dll",
    "d3dcompiler_47.dll",
    "vk_swiftshader.dll",
    "vk_swiftshader_icd.json",
    "vulkan-1.dll",
    "icudtl.dat",
    "nw.pak",
    "resources.pak",
    "nw_100_percent.pak",
    "nw_200_percent.pak",
    "natives_blob.bin",
    "snapshot_blob.bin",
    "v8_context_snapshot.bin",
    "credits.html",
    "notification_helper.exe",
    "pdf.dll",
    "dbghelp.dll",
    "chrome_100_percent.pak",
    "chrome_200_percent.pak",
    "dxcompiler.dll",
    "dxil.dll",
}

_KNOWN_NWJS_DIRS = {"locales", "swiftshader"}

_OBSOLETE_JS_FLAGS = re.compile(r"^--harmony(?:[_-][a-z0-9_-]+)?$", re.I)
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_GENERIC_APP_NAMES = {
    "",
    "game",
    "game.exe",
    "nw",
    "nwjs",
    "nw.js",
    "nw.exe",
    "node-webkit",
    "application",
    "app",
    "main",
    "index",
    "www",
}


# ---------------------------------------------------------------------------
# version / network helpers
# ---------------------------------------------------------------------------

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


def build_release(
    version: str,
    arch: str = DEFAULT_ARCH,
    flavor: str = "normal",
    chromium: str = "",
    node: str = "",
) -> NwjsRelease:
    clean = _normalize_version(version)
    if not clean:
        raise NwjsError(tr("nwjs.invalid_version"))
    release = NwjsRelease(
        version=clean,
        arch=arch,
        flavor=flavor,
        chromium=chromium,
        node=node,
    )
    release.url = f"{DOWNLOAD_BASE}/v{clean}/{release.archive_name}"
    release.shasums_url = f"{DOWNLOAD_BASE}/v{clean}/SHASUMS256.txt"
    return release


def fetch_latest_release(
    arch: str = DEFAULT_ARCH,
    flavor: str = "normal",
    timeout: int = 30,
) -> NwjsRelease:
    """Resolve the current stable NW.js release from https://nwjs.io/versions.json."""
    try:
        with _request(VERSIONS_URL, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", "ignore"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise NwjsError(tr("nwjs.fetch_failed", error=exc)) from exc

    chosen = _normalize_version(str(data.get("stable") or data.get("latest") or ""))
    entries = data.get("versions") or []
    entry_meta: dict = {}

    for item in entries:
        if not isinstance(item, dict):
            continue
        ver = _normalize_version(str(item.get("version") or ""))
        files = item.get("files") or []
        if ver == chosen and (not files or arch in files):
            entry_meta = item
            break

    if not entry_meta:
        for item in entries:
            if not isinstance(item, dict):
                continue
            files = item.get("files") or []
            if not files or arch in files:
                chosen = _normalize_version(str(item.get("version") or ""))
                entry_meta = item
                break

    if not chosen:
        raise NwjsError(tr("nwjs.no_version"))

    components = entry_meta.get("components") or {}
    return build_release(
        version=chosen,
        arch=arch,
        flavor=flavor,
        chromium=str(components.get("chromium") or ""),
        node=str(components.get("node") or ""),
    )


def fetch_expected_sha256(release: NwjsRelease, timeout: int = 20) -> str:
    """Fetch official SHA-256 for the release archive from dl.nwjs.io (best effort)."""
    if not release.shasums_url:
        return ""
    try:
        with _request(release.shasums_url, timeout=timeout) as response:
            text = response.read().decode("utf-8", "ignore")
    except (urllib.error.URLError, TimeoutError, OSError):
        return ""
    target = release.archive_name.lower()
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].lower().lstrip("*") == target:
            digest = parts[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                return digest
    return ""


# ---------------------------------------------------------------------------
# cache management
# ---------------------------------------------------------------------------

def _meta_path(folder: Path) -> Path:
    return folder / "meta.json"


def _load_meta(folder: Path) -> dict:
    try:
        return json.loads(_meta_path(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _cache_folder_name(version: str, arch: str) -> str:
    return f"{_normalize_version(version)}-{arch}"


def list_cached(arch: str | None = None) -> list[CachedNwjs]:
    paths.ensure_dirs()
    releases: list[CachedNwjs] = []
    if not paths.NWJS_CACHE_DIR.is_dir():
        return releases
    for folder in paths.NWJS_CACHE_DIR.iterdir():
        if not folder.is_dir() or folder.name.endswith(".tmp"):
            continue
        runtime = folder / "runtime"
        if not (runtime / "nw.exe").is_file() or not (runtime / "nw.dll").is_file():
            continue
        meta = _load_meta(folder)
        version = _normalize_version(str(meta.get("version") or folder.name.split("-", 1)[0]))
        entry_arch = str(meta.get("arch") or (folder.name.split("-", 1)[1] if "-" in folder.name else DEFAULT_ARCH))
        if arch and entry_arch != arch:
            continue
        releases.append(
            CachedNwjs(
                version=version,
                arch=entry_arch,
                folder=folder,
                runtime_dir=runtime,
                from_cache=True,
                meta=meta,
            )
        )
    releases.sort(key=lambda item: _version_key(item.version), reverse=True)
    return releases


def newest_cached(arch: str = DEFAULT_ARCH) -> CachedNwjs | None:
    cached = list_cached(arch=arch)
    return cached[0] if cached else None


def _validate_archive(zip_path: Path) -> tuple[str, list[str]]:
    """Verify the zip contains nw.exe and nw.dll, returning (common_prefix, members)."""
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = [info.filename for info in archive.infolist() if not info.is_dir()]
    except (zipfile.BadZipFile, OSError) as exc:
        raise NwjsError(tr("nwjs.invalid_zip", error=exc)) from exc

    if not names:
        raise NwjsError(tr("nwjs.empty_zip"))

    top_parts = {name.split("/", 1)[0] for name in names if "/" in name}
    prefix = ""
    if len(top_parts) == 1 and all(name.startswith(next(iter(top_parts)) + "/") for name in names):
        prefix = next(iter(top_parts)) + "/"

    rel_lower = {name[len(prefix):].lower() for name in names}
    if "nw.exe" not in rel_lower or "nw.dll" not in rel_lower:
        raise NwjsError(tr("nwjs.missing_binaries"))
    return prefix, names


def download_archive(
    release: NwjsRelease,
    progress: Progress | None = None,
    status: Status | None = None,
) -> Path:
    paths.ensure_dirs()
    target = paths.DOWNLOAD_DIR / release.archive_name
    expected_sha = fetch_expected_sha256(release)

    if target.is_file() and target.stat().st_size > 10_000_000:
        if not expected_sha or winapi.sha256_file(target).lower() == expected_sha:
            try:
                _validate_archive(target)
                if status:
                    status(tr("nwjs.archive_cached", version=release.version, arch=release.arch))
                return target
            except NwjsError:
                target.unlink(missing_ok=True)
        else:
            target.unlink(missing_ok=True)

    temporary = target.with_suffix(target.suffix + ".part")
    if status:
        status(tr("nwjs.downloading", version=release.version, arch=release.arch))
    try:
        with _request(release.url, timeout=120) as response, open(temporary, "wb") as handle:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(512 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise NwjsError(tr("nwjs.download_failed", error=exc)) from exc

    if temporary.stat().st_size < 10_000_000:
        temporary.unlink(missing_ok=True)
        raise NwjsError(tr("nwjs.download_incomplete"))

    if expected_sha:
        actual_sha = winapi.sha256_file(temporary).lower()
        if actual_sha != expected_sha:
            temporary.unlink(missing_ok=True)
            raise NwjsError(tr("nwjs.sha_mismatch"))

    try:
        _validate_archive(temporary)
    except NwjsError:
        temporary.unlink(missing_ok=True)
        raise

    temporary.replace(target)
    if status:
        status(tr("nwjs.downloaded", version=release.version, mb=target.stat().st_size / 1048576))
    return target


def cache_from_archive(zip_path: Path, release: NwjsRelease, status: Status | None = None) -> CachedNwjs:
    prefix, _ = _validate_archive(zip_path)
    folder = paths.NWJS_CACHE_DIR / _cache_folder_name(release.version, release.arch)
    temporary = folder.with_name(folder.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary, ignore_errors=True)
    runtime_tmp = temporary / "runtime"
    runtime_tmp.mkdir(parents=True, exist_ok=True)

    if status:
        status(tr("nwjs.extracting", version=release.version))

    extracted_files: list[str] = []
    try:
        runtime_root = runtime_tmp.resolve()
        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                rel = info.filename[len(prefix):] if prefix and info.filename.startswith(prefix) else info.filename
                rel = rel.lstrip("/")
                if not rel or rel.startswith("..") or "/../" in rel or "\\" in rel:
                    continue
                dest = (runtime_tmp / rel).resolve()
                if runtime_root not in dest.parents:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=512 * 1024)
                extracted_files.append(rel)

        if not (runtime_tmp / "nw.exe").is_file() or not (runtime_tmp / "nw.dll").is_file():
            raise NwjsError(tr("nwjs.extract_incomplete"))

        meta = {
            "version": release.version,
            "arch": release.arch,
            "flavor": release.flavor,
            "chromium": release.chromium,
            "node": release.node,
            "source": release.url or DOWNLOAD_BASE,
            "archive_sha256": winapi.sha256_file(zip_path),
            "cached_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "app_version": __version__,
            "files": sorted(extracted_files),
        }
        _meta_path(temporary).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    temporary.replace(folder)
    return CachedNwjs(
        version=release.version,
        arch=release.arch,
        folder=folder,
        runtime_dir=folder / "runtime",
        from_cache=False,
        meta=meta,
    )


def ensure_release(
    preferred_version: str | None = None,
    arch: str = DEFAULT_ARCH,
    progress: Progress | None = None,
    status: Status | None = None,
    allow_network: bool = True,
) -> CachedNwjs:
    """Return a cached NW.js runtime, downloading once from official source when needed."""
    preferred = _normalize_version(preferred_version or "")
    cached = list_cached(arch=arch)
    if preferred:
        for item in cached:
            if item.version == preferred:
                if status:
                    status(tr("nwjs.using_cached", version=item.version, arch=item.arch))
                return item
    elif cached:
        if status:
            status(tr("nwjs.using_cached", version=cached[0].version, arch=cached[0].arch))
        return cached[0]

    if not allow_network:
        if cached:
            return cached[0]
        raise NwjsError(tr("nwjs.no_cache_offline"))

    if preferred:
        release = build_release(preferred, arch=arch)
    else:
        if status:
            status(tr("nwjs.checking_latest"))
        try:
            release = fetch_latest_release(arch=arch)
        except NwjsError:
            if cached:
                if status:
                    status(tr("nwjs.offline_fallback"))
                return cached[0]
            raise

    archive = download_archive(release, progress=progress, status=status)
    return cache_from_archive(archive, release, status=status)


def prune_cache(keep: int = 1, arch: str | None = None) -> list[str]:
    cached = list_cached(arch=arch)
    removed: list[str] = []
    for item in cached[keep:]:
        shutil.rmtree(item.folder, ignore_errors=True)
        removed.append(f"{item.version} ({item.arch})")
    return removed


# ---------------------------------------------------------------------------
# per-game update record & detection
# ---------------------------------------------------------------------------

def update_record_path(game_id: str) -> Path:
    return paths.GAME_DATA_DIR / f"{game_id}.nwjs.json"


def load_update_record(game_id: str) -> dict:
    try:
        return json.loads(update_record_path(game_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_update_record(game_id: str, data: dict) -> None:
    paths.GAME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    update_record_path(game_id).write_text(json.dumps(data, indent=2), encoding="utf-8")


def has_backup(game_id: str) -> bool:
    record = load_update_record(game_id)
    backup_dir = record.get("backup_dir") or ""
    return bool(backup_dir) and Path(backup_dir).is_dir()


def detect_game_nwjs_version(game_dir: Path, exe: Path, game_id: str = "") -> str:
    """Best-effort NW.js version string for an RPG Maker MV/MZ game."""
    if game_id:
        record = load_update_record(game_id)
        if record.get("version"):
            return str(record["version"])

    for candidate in (exe, game_dir / "nw.exe", game_dir / "nw.dll"):
        if not candidate.is_file():
            continue
        info = winapi.file_version_info(candidate)
        version = (info.get("FileVersion") or "").strip()
        product = ((info.get("ProductName") or "") + " " + (info.get("FileDescription") or "")).lower()
        match = re.search(r"0\.\d+\.\d+", version)
        if match:
            return match.group(0)
        if "nwjs" in product or "nw.js" in product or "node-webkit" in product:
            generic = re.search(r"\d+\.\d+\.\d+", version)
            if generic:
                return generic.group(0)
    return ""


# ---------------------------------------------------------------------------
# package.json compatibility fixer
# ---------------------------------------------------------------------------

def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before `}` or `]` outside JSON strings."""
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < length and text[j] in " \t\r\n":
                j += 1
            if j < length and text[j] in "}]":
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _load_package_json(path: Path) -> tuple[dict, bool]:
    """Load package.json tolerating UTF-8 BOM and trailing commas. Returns (data, had_syntax_fix)."""
    raw = path.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data, had_bom
    except ValueError:
        pass
    cleaned = _strip_trailing_commas(text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data, True
    except ValueError as exc:
        raise NwjsError(tr("nwjs.invalid_package_json", name=path.name, error=exc)) from exc
    raise NwjsError(tr("nwjs.invalid_package_root", name=path.name))


def _is_valid_package_name(name: object) -> bool:
    if not isinstance(name, str):
        return False
    stripped = name.strip()
    if not stripped or stripped.lower() in _GENERIC_APP_NAMES:
        return False
    if stripped in (".", "..") or stripped.startswith(".") or stripped.endswith("."):
        return False
    if ".." in stripped:
        return False
    # Allow forward slash only for standard KADOKAWA/RPGMV style names without invalid Win chars
    if re.search(r'[<>:"\\|?*\x00-\x1f]', stripped):
        return False
    return True


def _generate_package_name(game_dir: Path, window_title: str = "") -> str:
    """Create a clean, deterministic, filesystem-safe NW.js `package.json` name."""
    candidates = [window_title, game_dir.name]
    for candidate in candidates:
        text = (candidate or "").strip()
        if not text or text.lower() in _GENERIC_APP_NAMES:
            continue
        cleaned = _INVALID_NAME_CHARS.sub("_", text)
        cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
        if cleaned and cleaned.lower() not in _GENERIC_APP_NAMES:
            return cleaned[:64]
    digest = hashlib.sha1(str(game_dir.resolve()).encode("utf-8", "ignore")).hexdigest()[:8]
    return f"rpgmaker_{digest}"


def _fix_chromium_args(raw_value: object) -> tuple[str, list[str]]:
    fixes: list[str] = []
    if raw_value is None:
        args = ""
    elif isinstance(raw_value, list):
        args = " ".join(str(item).strip() for item in raw_value if str(item).strip())
        fixes.append(tr("nwjs.fix_chromium_args_list"))
    else:
        args = str(raw_value).strip()

    if "--autoplay-policy" not in args.lower():
        flag = "--autoplay-policy=no-user-gesture-required"
        args = f"{args} {flag}".strip() if args else flag
        fixes.append(tr("nwjs.fix_autoplay"))
    return args, fixes


def _fix_js_flags(raw_value: object) -> tuple[str | None, list[str]]:
    fixes: list[str] = []
    if raw_value is None:
        return None, fixes
    if isinstance(raw_value, list):
        tokens = [str(item).strip() for item in raw_value if str(item).strip()]
    else:
        tokens = str(raw_value).split()

    kept: list[str] = []
    removed: list[str] = []
    for token in tokens:
        if _OBSOLETE_JS_FLAGS.match(token):
            removed.append(token)
        else:
            kept.append(token)

    if removed:
        fixes.append(tr("nwjs.fix_js_flags", flags=", ".join(removed)))
    return (" ".join(kept) if kept else None), fixes


def fix_package_json_dict(
    data: dict,
    base_dir: Path,
    game_dir: Path,
    *,
    is_root: bool = True,
    forced_name: str = "",
) -> tuple[dict, list[str]]:
    """Repair common RPG Maker MV/MZ `package.json` issues for modern NW.js."""
    fixed = dict(data)
    fixes: list[str] = []

    window_obj = fixed.get("window")
    window_title = str(window_obj.get("title") or "").strip() if isinstance(window_obj, dict) else ""

    # 1. name (required by modern NW.js; missing/blank breaks startup and profile paths)
    current_name = fixed.get("name")
    if forced_name and not _is_valid_package_name(current_name):
        fixed["name"] = forced_name
        fixes.append(tr("nwjs.fix_set_name", name=forced_name))
    elif not _is_valid_package_name(current_name):
        generated = forced_name or _generate_package_name(game_dir, window_title)
        fixed["name"] = generated
        fixes.append(tr("nwjs.fix_missing_name", name=generated))

    # 2. main entry point
    main_val = str(fixed.get("main") or "").strip()
    if not main_val or not (base_dir / main_val).is_file():
        candidates = ("www/index.html", "index.html") if is_root else ("index.html",)
        for candidate in candidates:
            if (base_dir / candidate).is_file():
                fixed["main"] = candidate
                fixes.append(tr("nwjs.fix_main", main=candidate))
                break

    # 3. chromium-args (autoplay policy + string type)
    if is_root or "chromium-args" in fixed:
        new_args, arg_fixes = _fix_chromium_args(fixed.get("chromium-args"))
        if new_args:
            fixed["chromium-args"] = new_args
        fixes.extend(arg_fixes)

    # 4. js-flags (strip removed legacy V8 --harmony* flags)
    if "js-flags" in fixed:
        new_js_flags, js_fixes = _fix_js_flags(fixed.get("js-flags"))
        if new_js_flags:
            fixed["js-flags"] = new_js_flags
        else:
            fixed.pop("js-flags", None)
        fixes.extend(js_fixes)

    # 5. window fields (integer dimensions & valid icon path)
    if isinstance(window_obj, dict):
        win_copy = dict(window_obj)
        for dim in ("width", "height", "min_width", "min_height", "max_width", "max_height"):
            val = win_copy.get(dim)
            if isinstance(val, str) and val.strip().isdigit():
                win_copy[dim] = int(val.strip())
                fixes.append(tr("nwjs.fix_window_dim", dim=dim))
        icon = win_copy.get("icon")
        if isinstance(icon, str) and icon.strip() and not (base_dir / icon).is_file():
            fallback_icons = ("www/icon/icon.png", "icon/icon.png") if is_root else ("icon/icon.png",)
            replaced = False
            for candidate in fallback_icons:
                if (base_dir / candidate).is_file():
                    win_copy["icon"] = candidate
                    fixes.append(tr("nwjs.fix_window_icon", icon=candidate))
                    replaced = True
                    break
            if not replaced:
                win_copy.pop("icon", None)
                fixes.append(tr("nwjs.fix_remove_icon"))
        fixed["window"] = win_copy

    # 6. inject_js_start for process.mainModule polyfill (root only, non-invasive)
    if is_root and not fixed.get("inject_js_start"):
        fixed["inject_js_start"] = COMPAT_SHIM_FILE
        fixes.append(tr("nwjs.fix_compat_shim"))

    return fixed, fixes


def fix_game_package_jsons(game_dir: Path, write_fn) -> tuple[list[str], list[str]]:
    """Repair root `package.json` (and `www/package.json` if present) + write compat shim.

    Returns (fixes_applied, touched_relative_paths).
    """
    fixes: list[str] = []
    touched: list[str] = []

    root_pkg = game_dir / "package.json"
    www_pkg = game_dir / "www" / "package.json"

    if not root_pkg.is_file() and www_pkg.is_file():
        www_data, syntax_fix = _load_package_json(www_pkg)
        if syntax_fix:
            fixes.append(tr("nwjs.fix_www_bom"))
        root_data = dict(www_data)
        if root_data.get("main") == "index.html" and (game_dir / "www" / "index.html").is_file():
            root_data["main"] = "www/index.html"
        if isinstance(root_data.get("window"), dict):
            win = dict(root_data["window"])
            icon = win.get("icon")
            if isinstance(icon, str) and icon and not icon.startswith("www/") and (game_dir / "www" / icon).is_file():
                win["icon"] = "www/" + icon
            root_data["window"] = win
        fixes.append(tr("nwjs.fix_root_from_www"))
    elif root_pkg.is_file():
        root_data, syntax_fix = _load_package_json(root_pkg)
        if syntax_fix:
            fixes.append(tr("nwjs.fix_root_bom"))
    else:
        root_data = {}
        fixes.append(tr("nwjs.fix_root_default"))

    fixed_root, root_fixes = fix_package_json_dict(root_data, game_dir, game_dir, is_root=True)
    fixes.extend(root_fixes)

    if fixed_root.get("inject_js_start") == COMPAT_SHIM_FILE:
        write_fn(game_dir / COMPAT_SHIM_FILE, COMPAT_SHIM_SOURCE.encode("utf-8"))
        touched.append(COMPAT_SHIM_FILE)

    write_fn(root_pkg, (json.dumps(fixed_root, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    touched.append("package.json")

    if www_pkg.is_file():
        try:
            www_data, www_syntax = _load_package_json(www_pkg)
            if www_syntax:
                fixes.append(tr("nwjs.fix_www_bom"))
            fixed_www, www_fixes = fix_package_json_dict(
                www_data,
                www_pkg.parent,
                game_dir,
                is_root=False,
                forced_name=str(fixed_root.get("name") or ""),
            )
            if www_fixes or www_syntax:
                write_fn(www_pkg, (json.dumps(fixed_www, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
                touched.append("www/package.json")
                fixes.extend(f"www/package.json: {msg}" for msg in www_fixes)
        except NwjsError:
            pass

    return fixes, touched


# ---------------------------------------------------------------------------
# game runtime update & restore
# ---------------------------------------------------------------------------

def _safe_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".anishade.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(temporary, "wb") as handle:
            handle.write(data)
        temporary.replace(path)
    except PermissionError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise PermissionError(tr("installer.no_write_perm", folder=path.parent)) from exc


def _copy_if_missing_in_backup(src: Path, backup_root: Path, rel: str) -> None:
    dest = backup_root / rel
    if dest.exists() or not src.is_file():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _backup_dir_contents(src_dir: Path, backup_root: Path, rel_dir: str) -> None:
    if not src_dir.is_dir():
        return
    for root, _dirs, files in os.walk(src_dir):
        for filename in files:
            src_file = Path(root) / filename
            rel = src_file.relative_to(src_dir.parent).as_posix()
            _copy_if_missing_in_backup(src_file, backup_root, rel)


def _is_reshade_dll_fast(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".dll":
        return False
    info = winapi.file_version_info(path)
    product = (info.get("ProductName") or "") + (info.get("FileDescription") or "")
    if "reshade" in product.lower():
        return True
    try:
        with open(path, "rb") as handle:
            blob = handle.read(2 * 1024 * 1024)
        return b"ReShade.ini" in blob or b"reshade-shaders" in blob
    except OSError:
        return False


def update_game_nwjs(
    game_dir: Path,
    exe: Path,
    game_id: str,
    preferred_version: str | None = None,
    arch: str = DEFAULT_ARCH,
    progress: Progress | None = None,
    status: Status | None = None,
) -> NwjsUpdateReport:
    """Update an RPG Maker MV/MZ game to the cached official NW.js build and apply fixes."""
    def log(message: str) -> None:
        if status:
            status(message)

    if not exe.is_file():
        raise NwjsError(tr("installer.exe_not_found", exe=exe))
    if winapi.process_running(exe.name):
        raise NwjsError(tr("nwjs.game_running_update", exe=exe.name))

    previous_record = load_update_record(game_id)
    previous_version = detect_game_nwjs_version(game_dir, exe, game_id)

    cached = ensure_release(
        preferred_version=preferred_version,
        arch=arch,
        progress=progress,
        status=log,
    )

    backup_root = Path(previous_record.get("backup_dir") or (paths.BACKUP_DIR / game_id / "nwjs_original"))
    first_backup = not previous_record
    if first_backup:
        backup_root.mkdir(parents=True, exist_ok=True)
        log(tr("nwjs.backing_up"))
        _copy_if_missing_in_backup(exe, backup_root, exe.name)
        for pkg_rel in ("package.json", "www/package.json"):
            _copy_if_missing_in_backup(game_dir / pkg_rel, backup_root, pkg_rel)
        for entry in game_dir.iterdir():
            low = entry.name.lower()
            if entry.is_file() and low in _KNOWN_NWJS_FILES and not _is_reshade_dll_fast(entry):
                _copy_if_missing_in_backup(entry, backup_root, entry.name)
            elif entry.is_dir() and low in _KNOWN_NWJS_DIRS:
                _backup_dir_contents(entry, backup_root, entry.name)

    runtime_dir = cached.runtime_dir
    new_runtime_files_lower: set[str] = set()
    new_runtime_dirs_lower: set[str] = set()
    for entry in runtime_dir.iterdir():
        if entry.is_file():
            new_runtime_files_lower.add(entry.name.lower())
        elif entry.is_dir():
            new_runtime_dirs_lower.add(entry.name.lower())

    # Prune obsolete legacy NW.js files that are no longer part of the new runtime
    for entry in list(game_dir.iterdir()):
        low = entry.name.lower()
        if entry.is_file():
            if (
                low in _KNOWN_NWJS_FILES
                and low not in new_runtime_files_lower
                and low != exe.name.lower()
                and not _is_reshade_dll_fast(entry)
            ):
                try:
                    entry.unlink()
                except OSError:
                    pass
        elif entry.is_dir() and low in _KNOWN_NWJS_DIRS and low not in new_runtime_dirs_lower:
            shutil.rmtree(entry, ignore_errors=True)

    # Deploy new NW.js runtime files
    log(tr("nwjs.applying", version=cached.version, arch=cached.arch, folder=game_dir.name))
    installed_files: list[str] = []
    warnings: list[str] = []
    exe_is_nw = exe.name.lower() == "nw.exe"
    has_separate_nw = (not exe_is_nw) and (game_dir / "nw.exe").is_file()

    for root, _dirs, filenames in os.walk(runtime_dir):
        for filename in filenames:
            src_file = Path(root) / filename
            rel = src_file.relative_to(runtime_dir).as_posix()

            if rel.lower() == "nw.exe":
                # Replace the game's actual executable (e.g. Game.exe)
                _safe_write(exe, src_file.read_bytes())
                installed_files.append(exe.name)
                if has_separate_nw:
                    _safe_write(game_dir / "nw.exe", src_file.read_bytes())
                    installed_files.append("nw.exe")
                continue

            dest = game_dir / rel
            if _is_reshade_dll_fast(dest):
                warnings.append(tr("nwjs.reshade_preserved", file=rel))
                continue
            _safe_write(dest, src_file.read_bytes())
            installed_files.append(rel)

    # Fix package.json compatibility issues + write compat shim
    log(tr("nwjs.fixing_package_json"))
    fixes_applied, _touched = fix_game_package_jsons(game_dir, write_fn=_safe_write)

    # Record backup & installed file list for clean restore
    previous_added = set(previous_record.get("installed_files") or [])
    record = {
        "game_id": game_id,
        "version": cached.version,
        "arch": cached.arch,
        "bits": cached.bits,
        "previous_version": previous_record.get("previous_version") or previous_version,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backup_dir": str(backup_root),
        "installed_files": sorted(previous_added | set(installed_files) | {COMPAT_SHIM_FILE}),
        "fixes_applied": fixes_applied,
        "exe_name": exe.name,
    }
    save_update_record(game_id, record)

    log(tr("nwjs.updated_log", version=cached.version, bits=cached.bits))
    return NwjsUpdateReport(
        version=cached.version,
        arch=cached.arch,
        previous_version=previous_version,
        files_updated=len(installed_files),
        fixes_applied=fixes_applied,
        warnings=warnings,
        backup_dir=str(backup_root),
    )


def restore_game_nwjs(
    game_dir: Path,
    exe: Path,
    game_id: str,
    status: Status | None = None,
) -> list[str]:
    """Restore original NW.js files and package.json from backup."""
    def log(message: str) -> None:
        if status:
            status(message)

    record = load_update_record(game_id)
    backup_dir_str = record.get("backup_dir") or ""
    backup_root = Path(backup_dir_str) if backup_dir_str else Path()
    if not record or not backup_dir_str or not backup_root.is_dir():
        raise NwjsError(tr("nwjs.no_backup"))
    if exe.is_file() and winapi.process_running(exe.name):
        raise NwjsError(tr("nwjs.game_running_restore", exe=exe.name))

    restored: list[str] = []
    backup_files: set[str] = set()
    for root, _dirs, filenames in os.walk(backup_root):
        for filename in filenames:
            src = Path(root) / filename
            rel = src.relative_to(backup_root).as_posix()
            backup_files.add(rel.lower())

    # Remove files that were added only by the newer NW.js update
    for rel in record.get("installed_files") or []:
        if rel.lower() in backup_files:
            continue
        target = game_dir / rel
        if target.is_file() and not _is_reshade_dll_fast(target):
            try:
                target.unlink()
            except OSError:
                pass

    # Restore original backed-up files
    for root, _dirs, filenames in os.walk(backup_root):
        for filename in filenames:
            src = Path(root) / filename
            rel = src.relative_to(backup_root).as_posix()
            dest = game_dir / rel
            if _is_reshade_dll_fast(dest):
                continue
            _safe_write(dest, src.read_bytes())
            restored.append(rel)

    # Clean empty NW.js dirs if they were added by the update
    for dirname in _KNOWN_NWJS_DIRS:
        folder = game_dir / dirname
        if folder.is_dir():
            try:
                next(folder.iterdir())
            except StopIteration:
                folder.rmdir()

    shutil.rmtree(backup_root, ignore_errors=True)
    update_record_path(game_id).unlink(missing_ok=True)
    log(tr("nwjs.restored_log", count=len(restored)))
    return restored
