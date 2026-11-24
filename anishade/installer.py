"""Install / update / remove ReShade + Anime4K Restore for a single game."""

from __future__ import annotations

import configparser
import io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import anime4k, detect, nwjs, paths, pe, renpy, reshade, rpgmaker, winapi
from .i18n import tr
from .store import Game, Store

PRESET_HEADER = ""
INI_HEADER = ""


class InstallError(Exception):
    pass


class AdminRequired(InstallError):
    pass


class GameRunningError(InstallError):
    pass


class ConflictError(InstallError):
    def __init__(self, message: str, conflicts: list[str]) -> None:
        super().__init__(message)
        self.conflicts = conflicts


@dataclass
class InstallOptions:
    variant: str = anime4k.DEFAULT_VARIANT
    top_margin: int = 0
    content_aspect: float = 0.0
    dll_name: str = ""
    reshade_version: str = ""
    create_launcher: bool = True
    rpgmaker_hide_textbox: bool = True
    rpgmaker_no_alt_skip: bool = True
    rpgmaker_save_slots_100: bool = True
    renpy_urm: bool = False
    urm_version: str = ""
    hide_splash: bool = True


@dataclass
class InstallReport:
    game_id: str
    dll_name: str = ""
    dll_path: str = ""
    preset_path: str = ""
    shader_dir: str = ""
    reshade_version: str = ""
    techniques: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    backup_paths: list[str] = field(default_factory=list)
    launcher: str = ""
    rpgmaker_plugin: str = ""
    rpgmaker_plugins: list[str] = field(default_factory=list)
    renpy_urm: str = ""
    renpy_urm_version: str = ""


# ---------------------------------------------------------------------------
# manifest helpers
# ---------------------------------------------------------------------------

def manifest_path(identifier: str) -> Path:
    return paths.GAME_DATA_DIR / f"{identifier}.json"


def load_manifest(identifier: str) -> dict:
    try:
        return json.loads(manifest_path(identifier).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_manifest(identifier: str, manifest: dict) -> None:
    paths.GAME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path(identifier).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def plugin_meta_path(identifier: str) -> Path:
    return paths.GAME_DATA_DIR / f"{identifier}.rpgmaker.json"


def load_plugin_meta(identifier: str) -> dict:
    """Load per-game RPG Maker plugin metadata (normalizes legacy single-plugin format)."""
    try:
        raw = json.loads(plugin_meta_path(identifier).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    if "plugins" in raw and isinstance(raw["plugins"], dict):
        return raw
    # Legacy single-plugin format -> normalize
    if raw.get("plugin_path"):
        return {
            "plugins": {"hide_textbox": raw},
            "plugins_js_backup": str(raw.get("plugins_js_backup") or ""),
            "plugins_js_sha256": str(raw.get("plugins_js_sha256") or ""),
            "plugins_js_path": str(raw.get("plugins_js_path") or ""),
        }
    return {}


def save_plugin_meta(identifier: str, data: dict) -> None:
    if not data.get("plugins"):
        plugin_meta_path(identifier).unlink(missing_ok=True)
        return
    paths.GAME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    plugin_meta_path(identifier).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _extract_manifest_plugins(manifest: dict, identifier: str) -> dict:
    """Merge RPG Maker plugin state from manifest and standalone metadata."""
    stored = load_plugin_meta(identifier)
    plugins: dict[str, dict] = dict(stored.get("plugins") or {})
    if isinstance(manifest.get("rpgmaker_plugins"), dict):
        for key, value in manifest["rpgmaker_plugins"].items():
            if isinstance(value, dict) and value:
                plugins.setdefault(key, value)
    legacy = manifest.get("rpgmaker_plugin")
    if isinstance(legacy, dict) and legacy.get("plugin_path"):
        plugins.setdefault("hide_textbox", legacy)
    backup = str(stored.get("plugins_js_backup") or "")
    if not backup:
        for meta in plugins.values():
            if meta.get("plugins_js_backup"):
                backup = str(meta["plugins_js_backup"])
                break
    return {
        "plugins": plugins,
        "plugins_js_backup": backup,
        "plugins_js_sha256": str(stored.get("plugins_js_sha256") or ""),
        "plugins_js_path": str(stored.get("plugins_js_path") or ""),
    }


def is_rpgmaker_plugin_active(game_dir: Path, plugin_key: str = "hide_textbox") -> bool:
    """True when the specified managed RPG Maker plugin is present and enabled."""
    return rpgmaker.is_plugin_active(game_dir, plugin_key=plugin_key)


def renpy_meta_path(identifier: str) -> Path:
    return paths.GAME_DATA_DIR / f"{identifier}.renpy.json"


def load_renpy_meta(identifier: str) -> dict:
    """Load per-game Ren'Py Universal Ren'Py Mod metadata."""
    try:
        raw = json.loads(renpy_meta_path(identifier).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_renpy_meta(identifier: str, data: dict) -> None:
    if not data or not data.get("rpa_path"):
        renpy_meta_path(identifier).unlink(missing_ok=True)
        return
    paths.GAME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    renpy_meta_path(identifier).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _extract_manifest_renpy_urm(manifest: dict, identifier: str) -> dict:
    stored = load_renpy_meta(identifier)
    if stored.get("rpa_path"):
        return stored
    raw = manifest.get("renpy_urm_meta")
    if isinstance(raw, dict) and raw.get("rpa_path"):
        return raw
    return {}


def is_renpy_urm_active(game_dir: Path) -> bool:
    """True when 0x52_URM.rpa is currently present in the game's Ren'Py game/ folder."""
    return renpy.is_urm_active(game_dir)


def _rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


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
        raise AdminRequired(tr("installer.no_write_perm", folder=path.parent)) from exc
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise InstallError(tr("installer.write_failed", name=path.name, error=exc)) from exc


def _backup(identifier: str, source: Path, label: str) -> str:
    folder = paths.BACKUP_DIR / identifier
    folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    suffix = source.suffix or ".bak"
    target = folder / f"{label}.{stamp}{suffix}"
    try:
        target.write_bytes(source.read_bytes())
    except OSError:
        return ""
    # keep the folder small
    for old in sorted(folder.glob(f"{label}.*"), key=lambda item: item.stat().st_mtime, reverse=True)[5:]:
        old.unlink(missing_ok=True)
    return str(target)


def _choose_dll_name(game_dir: Path, analysis: detect.GameAnalysis, forced: str) -> str:
    if forced:
        existing = game_dir / forced
        if existing.is_file() and not detect.is_reshade_dll(existing):
            raise ConflictError(tr("installer.conflict_forced", name=forced), [forced])
        return forced

    choices: list[str] = []
    for name in (analysis.dll_name, *analysis.dll_alternatives):
        if name and name not in choices:
            choices.append(name)
    for name in detect.DLL_CHOICES.get(analysis.api, ()):
        if name not in choices:
            choices.append(name)
    if not choices:
        raise InstallError(tr("installer.no_proxy_dll"))

    conflicts: list[str] = []
    for name in choices:
        candidate = game_dir / name
        if not candidate.is_file():
            return name
        if detect.is_reshade_dll(candidate):
            return name
        conflicts.append(name)

    raise ConflictError(
        tr("installer.conflict_all", list="\n".join(f"  - {name}" for name in conflicts)),
        conflicts,
    )


def resolve_dll_name(
    game_dir: Path, analysis: detect.GameAnalysis, forced: str = ""
) -> str:
    """Public wrapper used by the UI to preview the DLL that will be used."""
    return _choose_dll_name(game_dir, analysis, forced)


# ---------------------------------------------------------------------------
# ReShade.ini / preset
# ---------------------------------------------------------------------------

def _merge_reshade_ini(game_dir: Path, preset_name: str) -> tuple[Path, bytes]:
    ini_path = game_dir / "ReShade.ini"
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str  # keep key casing
    if ini_path.is_file():
        try:
            config.read_string(ini_path.read_text(encoding="utf-8", errors="ignore"))
        except configparser.Error:
            config = configparser.ConfigParser(interpolation=None, strict=False)
            config.optionxform = str
    if not config.has_section("GENERAL"):
        config.add_section("GENERAL")
    general = config["GENERAL"]

    if "TextureSearchPaths" not in general:
        general["TextureSearchPaths"] = ".\\reshade-shaders\\Textures\\**"
    needed = ".\\reshade-shaders\\Shaders\\**"
    existing = (general.get("EffectSearchPaths") or "").strip()
    if needed.lower() not in existing.lower():
        general["EffectSearchPaths"] = f"{existing},{needed}" if existing else needed
    general["PresetPath"] = f".\\{preset_name}"
    general["StartupPresetPath"] = f".\\{preset_name}"
    general["CurrentPreset"] = f".\\{preset_name}"
    general["PerformanceMode"] = "0"
    if "PreprocessorDefinitions" not in general:
        general["PreprocessorDefinitions"] = ""

    # 36 is VK_HOME: guarantee the ReShade overlay opens with the Home key.
    if not config.has_section("INPUT"):
        config.add_section("INPUT")
    config["INPUT"]["KeyOverlay"] = "36,0,0,0"

    # Keep the game view clean: no preset transition banner, no screenshot
    # toast, no first-run tutorial splash. (The small loading spinner shown
    # while ReShade recompiles effects on a resize is internal to ReShade.)
    if not config.has_section("OVERLAY"):
        config.add_section("OVERLAY")
    overlay = config["OVERLAY"]
    overlay["ShowPresetTransitionMessage"] = "0"
    overlay["ShowPresetName"] = "0"
    overlay["ShowScreenshotMessage"] = "0"
    overlay["TutorialProgress"] = "999"
    general["PresetTransitionDuration"] = "0"

    buffer = io.StringIO()
    config.write(buffer, space_around_delimiters=False)
    payload = (INI_HEADER + buffer.getvalue()).encode("utf-8")
    return ini_path, payload


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

def install(
    store: Store,
    game: Game,
    options: InstallOptions,
    status=None,
    progress=None,
    analysis: detect.GameAnalysis | None = None,
) -> InstallReport:
    def log(message: str) -> None:
        if status:
            status(message)

    exe = game.exe_path
    if not exe.is_file():
        raise InstallError(tr("installer.exe_not_found", exe=exe))
    game_dir = exe.parent

    if winapi.process_running(exe.name):
        raise GameRunningError(tr("installer.game_running_install", exe=exe.name))

    analysis = analysis or detect.analyze(exe, game.api_override or None, game.engine_override or None)
    if analysis.api == "vulkan":
        raise InstallError(tr("installer.vulkan_unsupported"))

    bits = analysis.bits or game.bits or 64
    release = reshade.ensure_release(
        options.reshade_version or None,
        progress=progress,
        status=log,
    )
    dll_source = reshade.verified_dll(release, bits)
    log(tr("installer.using_reshade_dll", dll=dll_source.name, version=release.version))

    dll_name = _choose_dll_name(game_dir, analysis, options.dll_name)
    log(tr("installer.proxy_dll", dll=dll_name))

    previous_manifest = load_manifest(game.id)
    files: list[dict] = []
    backups: list[str] = []

    # 1. proxy DLL (remove a previous different name if it is ours)
    dll_bytes = dll_source.read_bytes()
    splash_hidden = False
    if options.hide_splash:
        dll_bytes, splash_hidden = reshade.patch_hide_splash(dll_bytes)
        if splash_hidden:
            log(tr("installer.splash_hidden"))
        else:
            log(tr("installer.splash_hide_warn"))
    for entry in previous_manifest.get("files", []):
        if entry.get("kind") != "reshade":
            continue
        old_path = game_dir / entry.get("path", "")
        if entry.get("path") == dll_name or not old_path.is_file():
            continue
        if winapi.sha256_file(old_path) == entry.get("sha256"):
            old_path.unlink(missing_ok=True)
            log(tr("installer.old_dll_removed", path=entry.get("path")))

    dll_target = game_dir / dll_name
    _safe_write(dll_target, dll_bytes)
    files.append({"path": dll_name, "kind": "reshade", "sha256": winapi.sha256_bytes(dll_bytes)})

    # 2. Anime4K Restore shader (ReShade FX)
    shader_files = anime4k.required_files(options.variant)
    log(tr("installer.copying_shaders", files=", ".join(shader_files)))
    try:
        copied = anime4k.deploy_shaders(game_dir, shader_files)
    except PermissionError as exc:
        raise AdminRequired(tr("installer.no_shader_perm", folder=game_dir)) from exc
    for path in copied:
        files.append(
            {
                "path": _rel(path, game_dir),
                "kind": "shader",
                "sha256": winapi.sha256_bytes(path.read_bytes()),
            }
        )

    # 3. preset
    preset_path = game_dir / anime4k.PRESET_NAME
    if preset_path.is_file():
        current_hash = winapi.sha256_file(preset_path)
        if current_hash != previous_manifest.get("preset_sha256"):
            backup = _backup(game.id, preset_path, "AniShade.ini")
            if backup:
                backups.append(backup)
                log(tr("installer.preset_backed_up"))
    preset_text = anime4k.build_preset(options.variant, options.top_margin, options.content_aspect)
    preset_bytes = (PRESET_HEADER + preset_text).encode("utf-8")
    _safe_write(preset_path, preset_bytes)
    files.append(
        {
            "path": anime4k.PRESET_NAME,
            "kind": "preset",
            "sha256": winapi.sha256_bytes(preset_bytes),
        }
    )

    # 4. ReShade.ini
    ini_path = game_dir / "ReShade.ini"
    if previous_manifest:
        ini_created = bool(previous_manifest.get("ini_created", not ini_path.is_file()))
        ini_backup = previous_manifest.get("ini_backup", "")
    else:
        ini_created = not ini_path.is_file()
        ini_backup = ""
        if not ini_created:
            ini_backup = _backup(game.id, ini_path, "ReShade.ini")
            if ini_backup:
                backups.append(ini_backup)
    ini_target, ini_bytes = _merge_reshade_ini(game_dir, anime4k.PRESET_NAME)
    _safe_write(ini_target, ini_bytes)
    files.append(
        {
            "path": "ReShade.ini",
            "kind": "ini",
            "sha256": winapi.sha256_bytes(ini_bytes),
        }
    )

    # 5. optional launcher with engine-specific environment fixes
    launcher = ""
    launcher_path = game_dir / "AniShade-Launch.bat"
    legacy_launcher = game_dir / "AniShade-Iniciar.bat"
    if options.create_launcher and (analysis.env or analysis.args):
        try:
            winapi.write_batch_launcher(
                launcher_path,
                exe,
                env=analysis.env,
                args=list(analysis.args),
                title=game.name,
            )
            legacy_launcher.unlink(missing_ok=True)
            launcher = launcher_path.name
            files.append(
                {
                    "path": launcher_path.name,
                    "kind": "launcher",
                    "sha256": winapi.sha256_file(launcher_path),
                }
            )
        except OSError as exc:
            if status:
                status(tr("installer.launcher_warn", error=exc))
    else:
        launcher_path.unlink(missing_ok=True)
        legacy_launcher.unlink(missing_ok=True)

    # 6. RPG Maker MV/MZ plugins (hide-textbox H key + no-Alt-skip)
    warnings = list(analysis.warnings)
    prev_state = _extract_manifest_plugins(previous_manifest, game.id)
    prev_plugins: dict[str, dict] = dict(prev_state.get("plugins") or {})
    shared_backup = str(prev_state.get("plugins_js_backup") or "")
    last_plugins_js_sha = str(prev_state.get("plugins_js_sha256") or "")
    last_plugins_js_path = str(prev_state.get("plugins_js_path") or "")

    desired_plugins = {
        "hide_textbox": bool(options.rpgmaker_hide_textbox and rpgmaker.is_supported_engine(analysis.engine.key)),
        "no_alt_skip": bool(options.rpgmaker_no_alt_skip and rpgmaker.is_supported_engine(analysis.engine.key)),
        "save_slots_100": bool(options.rpgmaker_save_slots_100 and rpgmaker.is_supported_engine(analysis.engine.key)),
    }
    active_plugins: dict[str, dict] = {}
    installed_plugin_paths: list[str] = []
    plugins_js_missing_warned = False

    for plugin_key, want in desired_plugins.items():
        if want:
            result = rpgmaker.install_plugin(
                game_dir,
                plugin_key,
                write_fn=_safe_write,
                backup_fn=lambda src, label: _backup(game.id, src, label),
                existing_backup=shared_backup,
            )
            if result.installed:
                if result.plugins_js_backup and result.plugins_js_backup != shared_backup:
                    shared_backup = result.plugins_js_backup
                    backups.append(shared_backup)
                meta = result.to_manifest()
                meta["plugins_js_backup"] = shared_backup
                active_plugins[plugin_key] = meta
                last_plugins_js_sha = result.plugins_js_sha256
                last_plugins_js_path = result.plugins_js_path
                installed_plugin_paths.append(result.plugin_path)
                log(tr("installer.rpgm_plugin_installed", path=result.plugin_path))
            elif result.warning and not plugins_js_missing_warned:
                plugins_js_missing_warned = True
                warnings.append(result.warning)
                log(tr("installer.warning_prefix", warning=result.warning))
        elif plugin_key in prev_plugins:
            old_meta = dict(prev_plugins[plugin_key])
            if shared_backup:
                old_meta["plugins_js_backup"] = shared_backup
            if last_plugins_js_sha:
                old_meta["plugins_js_sha256"] = last_plugins_js_sha
            removed_plugin = rpgmaker.uninstall_plugin(
                game_dir,
                old_meta,
                write_fn=_safe_write,
                backup_fn=lambda src, label: _backup(game.id, src, label),
                log=log,
            )
            if removed_plugin:
                log(tr("installer.rpgm_plugin_removed", files=", ".join(removed_plugin)))
            if last_plugins_js_path and (game_dir / last_plugins_js_path).is_file():
                last_plugins_js_sha = winapi.sha256_file(game_dir / last_plugins_js_path)

    for meta in active_plugins.values():
        meta["plugins_js_sha256"] = last_plugins_js_sha
        meta["plugins_js_backup"] = shared_backup

    save_plugin_meta(
        game.id,
        {
            "plugins": active_plugins,
            "plugins_js_backup": shared_backup,
            "plugins_js_sha256": last_plugins_js_sha,
            "plugins_js_path": last_plugins_js_path,
        },
    )
    hide_meta = active_plugins.get("hide_textbox") or {}
    rpgmaker_plugin_path = str(hide_meta.get("plugin_path") or "")

    # 7. Ren'Py Universal Ren'Py Mod (0x52_URM.rpa)
    prev_urm = _extract_manifest_renpy_urm(previous_manifest, game.id)
    want_urm = bool(options.renpy_urm and renpy.is_supported_engine(analysis.engine.key))
    active_urm: dict = {}
    renpy_urm_path = ""
    renpy_urm_version = ""
    if want_urm:
        try:
            urm_release = renpy.ensure_release(
                options.urm_version or None,
                progress=progress,
                status=log,
            )
            rpa_source = renpy.verified_rpa(urm_release)
            urm_result = renpy.install_urm(
                game_dir,
                rpa_source,
                version=urm_release.version,
                write_fn=_safe_write,
                backup_fn=lambda src, label: _backup(game.id, src, label),
                existing_meta=prev_urm,
            )
            if urm_result.installed:
                active_urm = urm_result.to_manifest()
                renpy_urm_path = urm_result.rpa_path
                renpy_urm_version = urm_result.version
                if urm_result.backup_path and urm_result.backup_path != prev_urm.get("backup_path"):
                    backups.append(urm_result.backup_path)
                log(tr("installer.urm_installed", version=urm_result.version, path=urm_result.rpa_path))
            elif urm_result.warning:
                warnings.append(urm_result.warning)
                log(tr("installer.warning_prefix", warning=urm_result.warning))
        except renpy.RenpyModError as exc:
            warnings.append(tr("installer.urm_install_warn", error=exc))
            log(tr("installer.urm_install_log_warn", error=exc))
            if prev_urm and renpy.is_urm_active(game_dir):
                active_urm = dict(prev_urm)
                renpy_urm_path = str(active_urm.get("rpa_path") or "")
                renpy_urm_version = str(active_urm.get("version") or "")
    elif prev_urm:
        removed_urm = renpy.uninstall_urm(
            game_dir,
            prev_urm,
            backup_fn=lambda src, label: _backup(game.id, src, label),
            log=log,
        )
        if removed_urm:
            log(tr("installer.urm_removed", files=", ".join(removed_urm)))
    save_renpy_meta(game.id, active_urm)

    manifest = {
        "game_id": game.id,
        "exe": str(exe),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "reshade_version": release.version,
        "api": analysis.api,
        "dll_name": dll_name,
        "bits": bits,
        "variant": options.variant,
        "top_margin": options.top_margin,
        "content_aspect": options.content_aspect,
        "techniques": anime4k.techniques(options.variant),
        "preset_sha256": winapi.sha256_bytes(preset_bytes),
        "ini_backup": ini_backup,
        "ini_created": ini_created,
        "launcher": launcher,
        "files": files,
        "engine": analysis.engine.key,
        "shader_version": anime4k.SHADER_VERSION,
        "splash_hidden": splash_hidden,
        "rpgmaker_hide_textbox": "hide_textbox" in active_plugins,
        "rpgmaker_no_alt_skip": "no_alt_skip" in active_plugins,
        "rpgmaker_save_slots_100": "save_slots_100" in active_plugins,
        "rpgmaker_plugin": hide_meta,
        "rpgmaker_plugins": active_plugins,
        "renpy_urm": bool(active_urm),
        "renpy_urm_meta": active_urm,
    }
    save_manifest(game.id, manifest)

    game.installed = True
    game.reshade_version = release.version
    game.dll_name = dll_name
    game.bits = bits
    game.variant = options.variant
    game.top_margin = options.top_margin
    game.content_aspect = options.content_aspect
    game.api = analysis.api
    game.engine_key = analysis.engine.key
    game.engine_name = analysis.engine.name
    game.rpgmaker_hide_textbox = options.rpgmaker_hide_textbox
    game.rpgmaker_no_alt_skip = options.rpgmaker_no_alt_skip
    game.rpgmaker_save_slots_100 = options.rpgmaker_save_slots_100
    game.renpy_urm = options.renpy_urm
    store.save_games()

    log(tr("installer.done"))
    return InstallReport(
        game_id=game.id,
        dll_name=dll_name,
        dll_path=str(dll_target),
        preset_path=str(preset_path),
        shader_dir=str(game_dir / anime4k.SHADER_SUBDIR),
        reshade_version=release.version,
        techniques=manifest["techniques"],
        warnings=warnings,
        backup_paths=backups,
        launcher=launcher,
        rpgmaker_plugin=rpgmaker_plugin_path,
        rpgmaker_plugins=installed_plugin_paths,
        renpy_urm=renpy_urm_path,
        renpy_urm_version=renpy_urm_version,
    )


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------

def uninstall(store: Store, game: Game, status=None) -> list[str]:
    def log(message: str) -> None:
        if status:
            status(message)

    exe = game.exe_path
    game_dir = exe.parent
    manifest = load_manifest(game.id)
    if not manifest:
        raise InstallError(tr("installer.no_manifest"))
    if exe.is_file() and winapi.process_running(exe.name):
        raise GameRunningError(tr("installer.game_running_uninstall"))

    removed: list[str] = []
    for entry in manifest.get("files", []):
        if entry.get("kind") == "ini":
            continue
        rel_path = entry.get("path", "")
        target = game_dir / rel_path
        if not target.is_file() or not rel_path:
            continue
        expected = entry.get("sha256", "")
        if expected and winapi.sha256_file(target) != expected:
            backup = _backup(game.id, target, Path(rel_path).name)
            if backup:
                log(tr("installer.modified_backed_up", backup=backup))
            continue
        try:
            target.unlink()
            removed.append(rel_path)
        except OSError as exc:
            log(tr("installer.remove_failed", path=rel_path, error=exc))

    # shader folder only loses files registered in its own marker
    anime4k.remove_shaders(game_dir)

    ini_backup = manifest.get("ini_backup") or ""
    ini_path = game_dir / "ReShade.ini"
    ini_entry = next((item for item in manifest.get("files", []) if item.get("kind") == "ini"), None)
    if manifest.get("ini_created", False):
        if ini_path.is_file():
            expected = (ini_entry or {}).get("sha256", "")
            if expected and winapi.sha256_file(ini_path) != expected:
                backup = _backup(game.id, ini_path, "ReShade.ini")
                if backup:
                    log(tr("installer.ini_modified_backed_up", backup=backup))
            ini_path.unlink(missing_ok=True)
            removed.append("ReShade.ini")
    elif ini_backup and Path(ini_backup).is_file():
        try:
            ini_path.write_bytes(Path(ini_backup).read_bytes())
            log(tr("installer.ini_restored"))
        except OSError as exc:
            log(tr("installer.ini_restore_failed", error=exc))

    plugin_state = _extract_manifest_plugins(manifest, game.id)
    installed_plugins = plugin_state.get("plugins") or {}
    if installed_plugins:
        shared_backup = str(plugin_state.get("plugins_js_backup") or "")
        shared_sha = str(plugin_state.get("plugins_js_sha256") or "")
        items = list(installed_plugins.items())
        first_pjs_rel = next(
            (str(meta.get("plugins_js_path") or "") for _k, meta in items if meta.get("plugins_js_path")),
            "",
        )
        file_unmodified = bool(
            shared_sha
            and first_pjs_rel
            and (game_dir / first_pjs_rel).is_file()
            and winapi.sha256_file(game_dir / first_pjs_rel) == shared_sha
        )
        for idx, (_key, meta) in enumerate(items):
            is_last = idx == len(items) - 1
            meta_copy = dict(meta)
            if shared_backup:
                meta_copy["plugins_js_backup"] = shared_backup
            meta_copy["plugins_js_sha256"] = shared_sha if file_unmodified else ""
            removed.extend(
                rpgmaker.uninstall_plugin(
                    game_dir,
                    meta_copy,
                    write_fn=_safe_write,
                    backup_fn=lambda src, label: _backup(game.id, src, label),
                    log=log,
                    allow_restore_backup=is_last and file_unmodified,
                )
            )
            if not is_last and file_unmodified and first_pjs_rel and (game_dir / first_pjs_rel).is_file():
                shared_sha = winapi.sha256_file(game_dir / first_pjs_rel)
        plugin_meta_path(game.id).unlink(missing_ok=True)

    urm_meta = _extract_manifest_renpy_urm(manifest, game.id)
    if urm_meta:
        removed.extend(
            renpy.uninstall_urm(
                game_dir,
                urm_meta,
                backup_fn=lambda src, label: _backup(game.id, src, label),
                log=log,
            )
        )
        renpy_meta_path(game.id).unlink(missing_ok=True)

    for name in (anime4k.PRESET_NAME, "AniShade-Launch.bat", "AniShade-Iniciar.bat"):
        leftover = game_dir / name
        if leftover.is_file():
            leftover.unlink(missing_ok=True)

    manifest_path(game.id).unlink(missing_ok=True)
    game.installed = False
    store.save_games()
    log(tr("installer.reshade_removed"))
    return removed


# ---------------------------------------------------------------------------
# health check
# ---------------------------------------------------------------------------

@dataclass
class InstallState:
    installed: bool = False
    dll_ok: bool = False
    preset_ok: bool = False
    shaders_ok: bool = False
    plugin_ok: bool = True
    urm_ok: bool = True
    dll_name: str = ""
    reshade_version: str = ""
    rpgmaker_plugin: str = ""
    renpy_urm: str = ""
    techniques: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def inspect(game: Game) -> InstallState:
    manifest = load_manifest(game.id)
    state = InstallState(dll_name=game.dll_name, reshade_version=game.reshade_version)
    if not manifest:
        return state

    game_dir = game.exe_path.parent
    state.installed = True
    dll_entry = next((item for item in manifest.get("files", []) if item.get("kind") == "reshade"), None)
    if dll_entry:
        dll_path = game_dir / dll_entry["path"]
        state.dll_name = dll_entry["path"]
        state.dll_ok = dll_path.is_file() and winapi.sha256_file(dll_path) == dll_entry.get("sha256")
        if not state.dll_ok:
            state.problems.append(tr("installer.problem_dll"))

    preset_entry = next((item for item in manifest.get("files", []) if item.get("kind") == "preset"), None)
    preset_path = game_dir / anime4k.PRESET_NAME
    if preset_path.is_file():
        state.preset_ok = True
        if preset_entry and winapi.sha256_file(preset_path) != preset_entry.get("sha256"):
            state.problems.append(tr("installer.problem_preset_edited"))
    else:
        state.problems.append(tr("installer.problem_preset_missing"))

    expected = anime4k.required_files(manifest.get("variant", game.variant))
    shader_dir = game_dir / anime4k.SHADER_SUBDIR
    state.shaders_ok = all((shader_dir / name).is_file() for name in expected)
    if not state.shaders_ok:
        state.problems.append(tr("installer.problem_shaders_missing"))

    plugin_state = _extract_manifest_plugins(manifest, game.id)
    installed_plugins = plugin_state.get("plugins") or {}
    if installed_plugins:
        hide_meta = installed_plugins.get("hide_textbox") or {}
        state.rpgmaker_plugin = str(hide_meta.get("plugin_path") or "")
        all_ok = True
        for meta in installed_plugins.values():
            ok, plugin_problems = rpgmaker.inspect_plugin(game_dir, meta)
            all_ok = all_ok and ok
            state.problems.extend(plugin_problems)
        state.plugin_ok = all_ok

    urm_meta = _extract_manifest_renpy_urm(manifest, game.id)
    if urm_meta:
        state.renpy_urm = str(urm_meta.get("rpa_path") or "")
        urm_ok, urm_problems = renpy.inspect_urm(game_dir, urm_meta)
        state.urm_ok = urm_ok
        state.problems.extend(urm_problems)

    try:
        text = preset_path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("Techniques="):
                state.techniques = [part for part in line.split("=", 1)[1].split(",") if part]
    except OSError:
        pass
    return state


# ---------------------------------------------------------------------------
# standalone RPG Maker plugin toggle & NW.js update / restore
# ---------------------------------------------------------------------------

def set_rpgmaker_plugin(
    store: Store,
    game: Game,
    plugin_key: str,
    enabled: bool,
    status=None,
) -> str:
    """Immediately add or remove a managed RPG Maker MV/MZ plugin (`hide_textbox` or `no_alt_skip`)."""
    def log(message: str) -> None:
        if status:
            status(message)

    if plugin_key not in rpgmaker.PLUGINS:
        raise InstallError(tr("installer.unknown_rpgm_plugin", key=plugin_key))

    spec = rpgmaker.PLUGINS[plugin_key]
    exe = game.exe_path
    if not exe.is_file():
        raise InstallError(tr("installer.exe_not_found", exe=exe))
    if winapi.process_running(exe.name):
        raise GameRunningError(tr("installer.game_running_plugin", exe=exe.name))

    game_dir = exe.parent
    manifest = load_manifest(game.id)
    state = _extract_manifest_plugins(manifest, game.id)
    plugins: dict[str, dict] = dict(state.get("plugins") or {})
    shared_backup = str(state.get("plugins_js_backup") or "")
    shared_sha = str(state.get("plugins_js_sha256") or "")
    shared_pjs_path = str(state.get("plugins_js_path") or "")

    attr_map = {
        "hide_textbox": "rpgmaker_hide_textbox",
        "no_alt_skip": "rpgmaker_no_alt_skip",
        "save_slots_100": "rpgmaker_save_slots_100",
    }
    attr_name = attr_map[plugin_key]

    if enabled:
        result = rpgmaker.install_plugin(
            game_dir,
            plugin_key,
            write_fn=_safe_write,
            backup_fn=lambda src, label: _backup(game.id, src, label),
            existing_backup=shared_backup,
        )
        if not result.installed:
            raise InstallError(result.warning or tr("installer.plugins_js_missing"))
        if result.plugins_js_backup:
            shared_backup = result.plugins_js_backup
        shared_sha = result.plugins_js_sha256
        shared_pjs_path = result.plugins_js_path
        meta = result.to_manifest()
        meta["plugins_js_backup"] = shared_backup
        plugins[plugin_key] = meta
        for item in plugins.values():
            item["plugins_js_sha256"] = shared_sha
            item["plugins_js_backup"] = shared_backup

        save_plugin_meta(
            game.id,
            {
                "plugins": plugins,
                "plugins_js_backup": shared_backup,
                "plugins_js_sha256": shared_sha,
                "plugins_js_path": shared_pjs_path,
            },
        )
        if manifest:
            manifest[attr_name] = True
            manifest["rpgmaker_plugins"] = plugins
            manifest["rpgmaker_plugin"] = plugins.get("hide_textbox") or {}
            save_manifest(game.id, manifest)
        setattr(game, attr_name, True)
        store.save_games()
        log(tr("installer.plugin_enabled", file=spec.filename, path=result.plugins_js_path))
        return result.plugin_path

    # Disable / remove plugin
    target_meta = dict(plugins.get(plugin_key) or {})
    if not target_meta:
        js_dir = rpgmaker.find_js_dir(game_dir)
        if js_dir is not None:
            target_meta = {
                "name": spec.name,
                "plugin_path": _rel(js_dir / "plugins" / spec.filename, game_dir),
                "plugins_js_path": _rel(js_dir / "plugins.js", game_dir),
            }
    if shared_backup:
        target_meta["plugins_js_backup"] = shared_backup
    if shared_sha:
        target_meta["plugins_js_sha256"] = shared_sha

    if target_meta:
        rpgmaker.uninstall_plugin(
            game_dir,
            target_meta,
            write_fn=_safe_write,
            backup_fn=lambda src, label: _backup(game.id, src, label),
            log=log,
        )
    plugins.pop(plugin_key, None)

    pjs_rel = target_meta.get("plugins_js_path") or shared_pjs_path
    if plugins and pjs_rel and (game_dir / pjs_rel).is_file():
        shared_sha = winapi.sha256_file(game_dir / pjs_rel)
        for item in plugins.values():
            item["plugins_js_sha256"] = shared_sha

    save_plugin_meta(
        game.id,
        {
            "plugins": plugins,
            "plugins_js_backup": shared_backup if plugins else "",
            "plugins_js_sha256": shared_sha if plugins else "",
            "plugins_js_path": pjs_rel if plugins else "",
        },
    )
    if manifest:
        manifest[attr_name] = False
        manifest["rpgmaker_plugins"] = plugins
        manifest["rpgmaker_plugin"] = plugins.get("hide_textbox") or {}
        save_manifest(game.id, manifest)
    setattr(game, attr_name, False)
    store.save_games()
    log(tr("installer.plugin_removed", file=spec.filename))
    return ""


def set_rpgmaker_hide_textbox(
    store: Store,
    game: Game,
    enabled: bool,
    status=None,
) -> str:
    """Immediately add or remove the RPG Maker MV/MZ hide-textbox plugin (H key)."""
    return set_rpgmaker_plugin(store, game, "hide_textbox", enabled, status=status)


def set_renpy_urm(
    store: Store,
    game: Game,
    enabled: bool,
    preferred_version: str = "",
    status=None,
    progress=None,
) -> str:
    """Immediately install or remove Universal Ren'Py Mod (0x52_URM.rpa) in a Ren'Py game."""
    def log(message: str) -> None:
        if status:
            status(message)

    exe = game.exe_path
    if not exe.is_file():
        raise InstallError(tr("installer.exe_not_found", exe=exe))
    if winapi.process_running(exe.name):
        raise GameRunningError(tr("installer.game_running_urm", exe=exe.name))

    game_dir = exe.parent
    manifest = load_manifest(game.id)
    prev_urm = _extract_manifest_renpy_urm(manifest, game.id)

    if enabled:
        if renpy.find_game_dir(game_dir) is None:
            raise InstallError(tr("installer.renpy_game_dir_missing"))
        release = renpy.ensure_release(
            preferred_version or None,
            progress=progress,
            status=log,
        )
        rpa_source = renpy.verified_rpa(release)
        result = renpy.install_urm(
            game_dir,
            rpa_source,
            version=release.version,
            write_fn=_safe_write,
            backup_fn=lambda src, label: _backup(game.id, src, label),
            existing_meta=prev_urm,
        )
        if not result.installed:
            raise InstallError(result.warning or tr("installer.renpy_game_dir_missing_short"))
        meta = result.to_manifest()
        save_renpy_meta(game.id, meta)
        if manifest:
            manifest["renpy_urm"] = True
            manifest["renpy_urm_meta"] = meta
            save_manifest(game.id, manifest)
        game.renpy_urm = True
        store.save_games()
        log(tr("installer.urm_enabled", version=result.version, path=result.rpa_path))
        return result.rpa_path

    removed = renpy.uninstall_urm(
        game_dir,
        prev_urm,
        backup_fn=lambda src, label: _backup(game.id, src, label),
        log=log,
    )
    save_renpy_meta(game.id, {})
    if manifest:
        manifest["renpy_urm"] = False
        manifest["renpy_urm_meta"] = {}
        save_manifest(game.id, manifest)
    game.renpy_urm = False
    store.save_games()
    if removed:
        log(tr("installer.urm_removed_list", files=", ".join(removed)))
    else:
        log(tr("installer.urm_disabled"))
    return ""


def realign_reshade_bits(store: Store, game: Game, status=None) -> bool:
    """If ReShade is installed and the game's PE bitness changed, swap to the matching DLL."""
    def log(message: str) -> None:
        if status:
            status(message)

    manifest = load_manifest(game.id)
    if not manifest:
        return False
    exe = game.exe_path
    if not exe.is_file():
        return False
    try:
        new_bits = pe.read_pe(exe).bits
    except (pe.PEError, OSError):
        return False
    if not new_bits or new_bits == int(manifest.get("bits") or 0):
        return False

    dll_name = manifest.get("dll_name") or ""
    if not dll_name:
        return False
    release = reshade.ensure_release(
        manifest.get("reshade_version") or None,
        status=log,
        allow_network=False,
    )
    dll_source = reshade.verified_dll(release, new_bits)
    dll_bytes = dll_source.read_bytes()
    if manifest.get("splash_hidden", True):
        dll_bytes, patched = reshade.patch_hide_splash(dll_bytes)
        manifest["splash_hidden"] = patched
    _safe_write(exe.parent / dll_name, dll_bytes)

    new_hash = winapi.sha256_bytes(dll_bytes)
    for entry in manifest.get("files", []):
        if entry.get("kind") == "reshade" and entry.get("path") == dll_name:
            entry["sha256"] = new_hash
    manifest["bits"] = new_bits
    save_manifest(game.id, manifest)

    game.bits = new_bits
    store.save_games()
    log(tr("installer.dll_realigned", dll=dll_name, bits=new_bits))
    return True


def update_nwjs(
    store: Store,
    game: Game,
    preferred_version: str = "",
    arch: str = nwjs.DEFAULT_ARCH,
    status=None,
    progress=None,
) -> nwjs.NwjsUpdateReport:
    """Update an RPG Maker MV/MZ game's NW.js runtime from the official cached build."""
    def log(message: str) -> None:
        if status:
            status(message)

    exe = game.exe_path
    try:
        report = nwjs.update_game_nwjs(
            exe.parent,
            exe,
            game.id,
            preferred_version=preferred_version or None,
            arch=arch,
            progress=progress,
            status=log,
        )
    except PermissionError as exc:
        raise AdminRequired(str(exc)) from exc

    try:
        game.bits = pe.read_pe(exe).bits or game.bits
    except (pe.PEError, OSError):
        game.bits = 32 if "32" in arch else 64
    game.nwjs_version = report.version
    store.save_games()

    try:
        report.reshade_realigned = realign_reshade_bits(store, game, status=log)
    except (InstallError, reshade.ReshadeError) as exc:
        report.warnings.append(tr("installer.reshade_reinstall_needed", error=exc))
    return report


def restore_nwjs(store: Store, game: Game, status=None) -> list[str]:
    """Restore a game's original NW.js runtime and package.json from backup."""
    def log(message: str) -> None:
        if status:
            status(message)

    exe = game.exe_path
    try:
        restored = nwjs.restore_game_nwjs(exe.parent, exe, game.id, status=log)
    except PermissionError as exc:
        raise AdminRequired(str(exc)) from exc

    try:
        game.bits = pe.read_pe(exe).bits or game.bits
    except (pe.PEError, OSError):
        pass
    game.nwjs_version = nwjs.detect_game_nwjs_version(exe.parent, exe, game.id)
    store.save_games()

    try:
        realign_reshade_bits(store, game, status=log)
    except (InstallError, reshade.ReshadeError):
        pass
    return restored
