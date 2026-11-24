"""Internationalization (i18n) support for AniShade.

English (``en``) is the default language; Brazilian Portuguese (``pt_BR``) is
also bundled and can be switched at runtime from the Settings dialog.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("pt_BR", "Português (Brasil)"),
)

_ALIASES: dict[str, str] = {
    "en": "en",
    "en_us": "en",
    "en-us": "en",
    "en_gb": "en",
    "en-gb": "en",
    "english": "en",
    "pt": "pt_BR",
    "pt_br": "pt_BR",
    "pt-br": "pt_BR",
    "portuguese": "pt_BR",
    "portugues": "pt_BR",
}

_current_language: str = DEFAULT_LANGUAGE


def normalize_language(code: str | None) -> str:
    """Normalize a language code to a supported locale, defaulting to English."""
    if not code:
        return DEFAULT_LANGUAGE
    key = str(code).strip().lower()
    return _ALIASES.get(key, DEFAULT_LANGUAGE)


def get_language() -> str:
    """Return the active language code (``en`` or ``pt_BR``)."""
    return _current_language


def set_language(code: str | None) -> str:
    """Set and return the active language code."""
    global _current_language
    _current_language = normalize_language(code)
    return _current_language


def tr(key: str, **kwargs: object) -> str:
    """Translate ``key`` into the active language, with optional format args."""
    catalog = _TRANSLATIONS.get(_current_language, _TRANSLATIONS[DEFAULT_LANGUAGE])
    template = catalog.get(key)
    if template is None:
        template = _TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


_EN: dict[str, str] = {
    # -- app / general ---------------------------------------------------
    "app.tagline": "ReShade + Anime4K Restore for visual novels and Japanese games",
    "app.window_title": "AniShade — ReShade + Anime4K Restore",
    "app.unhandled_error": "Unhandled error:",
    "common.unknown": "Unknown",
    "common.unknown_lower": "unknown",
    "common.none": "none",
    "common.bits": "{bits}-bit",
    "common.bits_unknown": "?-bit",
    "common.cancel": "Cancel",
    "common.save": "Save",
    "common.open": "Open",
    "common.error": "Error",
    # -- widgets ---------------------------------------------------------
    "widget.no_pass_selected": "No pass selected",
    # -- topbar / banners / log ------------------------------------------
    "topbar.add_game": "Add Game",
    "topbar.settings": "Settings",
    "topbar.log": "Log",
    "banner.reshade_missing": (
        "ReShade hasn't been downloaded yet. It will be fetched from the official site (reshade.me) "
        "on your first install — then cached locally for all games."
    ),
    "banner.download_now": "Download now",
    "log.placeholder": "Operation logs appear here (Ctrl+L).",
    # -- left panel / library --------------------------------------------
    "library.search_placeholder": "Search library...",
    "library.empty_hint": (
        "No games yet.\n\nClick “Add Game” and point to the game's .exe, "
        "or drag and drop the executable onto this window."
    ),
    "library.hint": "Double-click to rename · Right-click for options",
    "library.select_placeholder": (
        "Select a game from the list to inspect detection, choose an Anime4K variant, "
        "and install ReShade."
    ),
    "badge.not_installed": "Not installed",
    "badge.incomplete": "Incomplete",
    "badge.pending": "Pending",
    "badge.installed": "Installed",
    "menu.play": "Play",
    "menu.rename": "Rename",
    "menu.open_folder": "Open folder",
    "menu.remove_from_library": "Remove from library",
    # -- game header -----------------------------------------------------
    "header.play": "Play",
    "header.play_tooltip": "Launch the game with engine-specific environment fixes",
    "header.folder": "Folder",
    "header.remove": "Remove",
    # -- detection card --------------------------------------------------
    "detection.title": "Detection",
    "detection.reanalyze": "Re-analyze",
    "detection.engine": "Engine",
    "detection.auto_detect": "Auto-detect",
    "detection.api": "Graphics API",
    "detection.arch": "Architecture",
    "detection.reshade": "ReShade",
    "detection.default_heuristic": "default heuristic",
    "detection.module_tooltip": "Module used: {module}",
    "detection.installed_lower": "installed",
    "detection.not_installed_lower": "not installed",
    "detection.conflict_warning": "Name conflict: {dlls} (will be avoided).",
    # -- rpgmaker card ---------------------------------------------------
    "rpgmaker.title": "RPG Maker MV/MZ",
    "rpgmaker.hide_textbox_title": "Hide textbox with the H key",
    "rpgmaker.hide_textbox_tooltip": (
        "Immediately installs or removes AniShade_HideTextbox.js in js/plugins/ and plugins.js."
    ),
    "rpgmaker.no_alt_title": "Prevent Alt from skipping text (Alt+Tab)",
    "rpgmaker.no_alt_tooltip": (
        "Installs or removes AniShade_NoAltSkip.js so Alt / Alt+Tab / Alt+Enter never skip dialogue "
        "(Ctrl keeps working normally)."
    ),
    "rpgmaker.save_slots_title": "Expand to 100 save slots",
    "rpgmaker.save_slots_tooltip": (
        "Installs or removes AniShade_SaveSlots100.js to unlock 100 manual save slots "
        "(keeps Autosave on MZ and never shrinks if the game already allows more than 100)."
    ),
    "rpgmaker.plugins_js_missing": (
        "plugins.js not found (packed game or non-standard NW.js layout)."
    ),
    "rpgmaker.hide_textbox_active": (
        "Active ({file} registered in {plugins_js}). "
        "Press H in-game to hide/show the message textbox."
    ),
    "rpgmaker.no_alt_active": (
        "Active ({file}). Alt and Alt+Tab will not skip dialogue; Ctrl still works."
    ),
    "rpgmaker.save_slots_active": (
        "Active ({file}). 100 manual save slots unlocked (MV and MZ)."
    ),
    "rpgmaker.not_installed_yet": (
        "Not installed yet — flip the toggle now or it will be installed along with ReShade."
    ),
    "rpgmaker.hide_textbox_disabled": "Disabled — flip the toggle to add it to the game.",
    "rpgmaker.no_alt_disabled": "Disabled — flip the toggle to stop Alt / Alt+Tab from skipping text.",
    "rpgmaker.save_slots_disabled": "Disabled — flip the toggle to expand the limit to 100 save slots.",
    "rpgmaker.nwjs_title": "Update NW.js (official)",
    "rpgmaker.nwjs_restore": "Restore",
    "rpgmaker.nwjs_restore_tooltip": "Restore the original NW.js and package.json from backup",
    "rpgmaker.nwjs_update": "Update NW.js",
    "rpgmaker.nwjs_update_tooltip": (
        "Downloads official NW.js from nwjs.io (once), updates the game's runtime, "
        "and fixes package.json compatibility issues (missing name, autoplay, js-flags, etc.)."
    ),
    "rpgmaker.nwjs_cache_hint_cached": "Local cache: NW.js {version} ({bits}-bit)",
    "rpgmaker.nwjs_cache_hint_empty": "Downloads official NW.js from nwjs.io once and reuses it across all games",
    "rpgmaker.nwjs_updated_tag": " · updated by AniShade",
    "rpgmaker.nwjs_status": (
        "In game: {version} ({bits_text}{updated_tag})\n"
        "{cache_hint} · fixes package.json (missing name, autoplay, js-flags, MV compatibility)."
    ),
    # -- renpy card ------------------------------------------------------
    "renpy.title": "Ren'Py",
    "renpy.mod_link_tooltip": "Open official page: {url}",
    "renpy.urm_title": "Universal Ren'Py Mod (URM)",
    "renpy.urm_tooltip": (
        "Downloads Universal Ren'Py Mod (0x52_URM.rpa) from 0x52.dev once, "
        "caches it locally, and installs or removes it in the game/ folder immediately."
    ),
    "renpy.game_dir_missing": "game/ folder not found next to the executable.",
    "renpy.urm_active": (
        "Active ({ver_tag}{game_dir}/{filename}). "
        "In-game menu for variables, scenes, choices, saves, and customization."
    ),
    "renpy.urm_not_installed_yet": (
        "Not installed yet — flip the toggle now or it will be installed along with ReShade."
    ),
    "renpy.urm_disabled_cached": (
        "Disabled — toggle on to install {filename} into {game_dir}/ "
        "(local cache: v{version})."
    ),
    "renpy.urm_disabled_uncached": (
        "Disabled — downloads {filename} from 0x52.dev once, caches it locally, "
        "and installs into {game_dir}/."
    ),
    # -- shader card -----------------------------------------------------
    "shader.title": "Anime4K Shaders (Restore)",
    "shader.intro": (
        "Restore reconstructs artwork details that the game has already upscaled. Pick the variant "
        "matching the game's internal resolution; larger networks cost more GPU power."
    ),
    "shader.top_margin": "Top margin (title bar)",
    "shader.top_margin_tooltip": (
        "Top pixels excluded from filtering. Some NW.js/Chromium games include the title bar "
        "in the swapchain (e.g. 1080x751 buffer for 1080x720 content). Use 0 in fullscreen/borderless."
    ),
    "shader.top_margin_hint": (
        "Leave at 0 in fullscreen. In windowed mode, if the title bar looks distorted, "
        "set it to the title bar height (e.g. 31 px)."
    ),
    "shader.aspect": "Content aspect ratio (W/H)",
    "shader.aspect_tooltip": (
        "Optional: manually restricts the shader to an aspect ratio (e.g. 1.5). "
        "Leave at 0 (recommended): the shader automatically detects and blocks border feedback."
    ),
    "shader.aspect_hint": (
        "Recommended: 0 (full screen). Protection against noise/feedback on black bars is automatic in the shader."
    ),
    # -- install card ----------------------------------------------------
    "install.title": "Installation",
    "install.refresh": "Refresh status",
    "install.reshade": "ReShade",
    "install.dll_proxy": "Proxy DLL",
    "install.dll_tooltip_auto": (
        "Proxy DLL filename. 'Auto' picks the best available option in the game folder."
    ),
    "install.dll_tooltip_installed": "Installed as {dll_name}",
    "install.dll_auto": "Auto ({name})",
    "install.dll_auto_label": "auto",
    "install.dll_conflict": "name conflict",
    "install.preset": "Preset",
    "install.edit": "Edit",
    "install.edit_tooltip": "Open preset in the default editor (.ini)",
    "install.shaders": "Shaders",
    "install.launcher": "Launcher",
    "install.rpgmaker_plugin": "RPG Maker Plugins",
    "install.renpy_urm": "Ren'Py Mod",
    "install.techniques_installed": "{count} technique(s) in {subdir}",
    "install.techniques_planned": "{count} planned technique(s)",
    "install.create_launcher": "Create .bat launcher with engine fixes",
    "install.create_launcher_tooltip": (
        "The launcher sets recommended environment variables (e.g. RENPY_RENDERER) "
        "before starting the game."
    ),
    "install.open_game_folder": "Open game folder",
    "install.rpgm_hide_short": "Hide textbox (H)",
    "install.rpgm_no_alt_short": "No Alt-skip",
    "install.rpgm_slots_short": "100 save slots",
    "install.will_install_plural": "will be installed with ReShade",
    "install.disabled_plural": "disabled",
    "install.plugins_js_not_found": "plugins.js not found",
    "install.will_install_single": "will be installed with ReShade",
    "install.disabled_single": "disabled",
    "install.game_dir_not_found": "game/ folder not found",
    # -- footer / buttons ------------------------------------------------
    "footer.add_game_start": "Add a game to get started.",
    "footer.uninstall": "Uninstall",
    "footer.install": "Install ReShade + Anime4K",
    "footer.apply_changes": "Apply changes",
    "footer.reinstall": "Reinstall",
    "footer.vulkan_unsupported": "Vulkan unsupported",
    "footer.vulkan_status": (
        "This game uses Vulkan: ReShade cannot load via proxy DLL. "
        "Launch in Direct3D 11/OpenGL or use ReShade global injection."
    ),
    "footer.ready_to_install": "Ready to install. ReShade is only downloaded once.",
    "footer.changes_pending": "Shader or mod changes pending (not applied yet).",
    "footer.installed_status": (
        "Installed. Launch the game and press Home to open the ReShade overlay."
    ),
    "footer.exe_missing": "Executable not found — was the game moved or deleted?",
    # -- dialogs & messages (main window) --------------------------------
    "dialog.analyze_error_title": "Analysis error",
    "dialog.install_success_title": "AniShade",
    "dialog.install_success_header": "Done!",
    "dialog.install_success_dll": "• DLL: {dll}",
    "dialog.install_success_preset": "• Preset: {preset}",
    "dialog.install_success_chain": "• Chain: {chain}",
    "dialog.install_success_plugin_hide": "• RPG Maker plugin: {file} (H key hides textbox)\n",
    "dialog.install_success_plugin_no_alt": "• RPG Maker plugin: {file} (Alt / Alt+Tab won't skip text)\n",
    "dialog.install_success_plugin_slots": "• RPG Maker plugin: {file} (100 save slots)\n",
    "dialog.install_success_plugin_other": "• RPG Maker plugin: {file}\n",
    "dialog.install_success_renpy_urm": "• Ren'Py Mod: Universal Ren'Py Mod{ver} ({file})\n",
    "dialog.install_success_footer": "Launch the game and press Home to open the ReShade overlay.",
    "dialog.install_success_launcher": "\n\nLauncher created: {launcher}",
    "dialog.uninstall_title": "Uninstall",
    "dialog.uninstall_body": (
        "Remove ReShade and Anime4K shaders from “{name}”?\n\n"
        "Only files created by AniShade will be removed."
    ),
    "dialog.nwjs_update_title": "Update NW.js",
    "dialog.nwjs_source_cached": "Will use NW.js {version} (64-bit) from local cache.",
    "dialog.nwjs_source_download": (
        "Official NW.js (64-bit) will be downloaded once from nwjs.io and cached for future games."
    ),
    "dialog.nwjs_update_body": (
        "Update the NW.js runtime for “{name}”?\n\n"
        "{source_note}\n"
        "Original NW.js files and package.json will be backed up "
        "(you can restore them later).\n"
        "Automatic fixes applied: missing 'name' in package.json, "
        "audio autoplay, obsolete V8 flags, and process.mainModule compatibility."
    ),
    "dialog.nwjs_success_title": "NW.js updated",
    "dialog.nwjs_success_header": "NW.js updated successfully!",
    "dialog.nwjs_success_version": "• Version: NW.js {version} ({arch})",
    "dialog.nwjs_success_files": "• Files updated: {count}",
    "dialog.nwjs_success_realigned": "• ReShade DLL automatically updated to 64-bit.",
    "dialog.nwjs_success_fixes": "Fixes applied:",
    "dialog.nwjs_success_warnings": "Warnings:",
    "dialog.nwjs_restore_title": "Restore original NW.js",
    "dialog.nwjs_restore_body": (
        "Restore the original NW.js files and package.json for “{name}”?"
    ),
    "dialog.task_error_title": "Operation failed",
    "dialog.admin_title": "Permission required",
    "dialog.admin_body": "Restart AniShade as administrator to continue?",
    "dialog.pick_game_title": "Choose game executable",
    "dialog.pick_game_filter": "Executables (*.exe);;All files (*.*)",
    "dialog.invalid_file_title": "Invalid file",
    "dialog.invalid_file_body": "Select a valid .exe file.",
    "dialog.analyze_failed_body": "Could not analyze the executable:\n{error}",
    "dialog.rename_title": "Rename",
    "dialog.rename_label": "Display name:",
    "dialog.remove_title": "Remove game",
    "dialog.remove_body": "Remove “{name}” from the library?",
    "dialog.remove_installed_info": (
        "This game has ReShade installed by AniShade. You can uninstall it before removing."
    ),
    "dialog.remove_only": "Remove from list only",
    "dialog.remove_and_uninstall": "Uninstall and remove",
    "dialog.game_missing_title": "Game missing",
    "dialog.game_missing_body": "The executable no longer exists at this path.",
    "dialog.launch_error_title": "Launch error",
    "dialog.folder_missing_title": "Folder missing",
    "dialog.folder_missing_body": "The folder no longer exists:\n{folder}",
    "dialog.preset_missing_title": "Preset missing",
    "dialog.preset_missing_body": "AniShade.ini has not been created yet. Install first.",
    "dialog.open_error_title": "Open error",
    "dialog.busy_close_title": "Operation in progress",
    "dialog.busy_close_body": "Wait for the current operation to finish before closing AniShade.",
    # -- main window logs & progress -------------------------------------
    "log.reshade_cached": "ReShade {version} ready in cache.",
    "log.downloading_reshade": "Downloading ReShade...",
    "log.downloading_urm": "Downloading Universal Ren'Py Mod... {done:.1f} / {total:.1f} MB",
    "log.installing_urm": "Installing Universal Ren'Py Mod...",
    "log.removing_urm": "Removing Universal Ren'Py Mod...",
    "log.installing": "Installing...",
    "log.installed": "Installed: {dll} + {count} pass(es) (ReShade {version}).",
    "log.uninstalling": "Uninstalling...",
    "log.uninstalled": "ReShade removed ({count} file(s)).",
    "log.downloading_nwjs": "Downloading NW.js... {done:.1f} / {total:.1f} MB",
    "log.updating_nwjs": "Updating NW.js...",
    "log.nwjs_updated": "NW.js updated to {version} ({arch}).",
    "log.restoring_nwjs": "Restoring NW.js...",
    "log.nwjs_restored": "Original NW.js restored ({count} file(s)).",
    "log.error": "Error: {message}",
    "log.already_in_library": "“{name}” is already in the library.",
    "log.game_added": "Added: {name} ({engine}).",
    "log.game_uninstalled_removed": "“{name}” uninstalled and removed.",
    "log.game_removed": "Game removed from library.",
    "log.launching": "Launching {exe}{detail}",
    "log.detection_updated": "Detection updated.",
    "log.settings_saved": "Settings saved.",
    # -- settings dialog -------------------------------------------------
    "settings.title": "Settings — AniShade",
    "settings.general_card": "General",
    "settings.language": "Language",
    "settings.language_hint": "Interface language. Changes apply immediately after saving.",
    "settings.reshade_card": "ReShade",
    "settings.nwjs_card": "NW.js (RPG Maker MV/MZ)",
    "settings.urm_card": "Universal Ren'Py Mod (Ren'Py)",
    "settings.defaults_card": "Defaults for new games",
    "settings.version_used": "Version to use",
    "settings.download_now": "Download / update now",
    "settings.prune_old": "Remove old versions",
    "settings.open_cache": "Open cache folder",
    "settings.variant": "Variant",
    "settings.default_top_margin": "Default top margin",
    "settings.default_top_margin_tooltip": (
        "Top pixels to ignore (title bar in NW.js games). Use 0 in fullscreen."
    ),
    "settings.create_launcher": "Create .bat launcher with engine fixes",
    "settings.rpgm_hide_textbox": "Install textbox hide plugin (H key) for RPG Maker MV/MZ",
    "settings.rpgm_no_alt": "Prevent Alt / Alt+Tab from skipping text in RPG Maker MV/MZ",
    "settings.rpgm_save_slots": "Expand to 100 save slots in RPG Maker MV/MZ",
    "settings.renpy_urm": "Install Universal Ren'Py Mod (0x52_URM.rpa) in new Ren'Py games",
    "settings.app_data": "App data: {path}",
    "settings.about": (
        "AniShade does not redistribute binaries. ReShade is downloaded from reshade.me, "
        "NW.js is downloaded from dl.nwjs.io, Universal Ren'Py Mod is downloaded from 0x52.dev "
        "(all reused via local cache), and the Anime4K shaders (bloc97/Anime4K, MIT) "
        "are bundled with the app.\n"
        "Press Home in-game to open the ReShade overlay and tweak the preset."
    ),
    "settings.reshade_cache_present": "Cached versions: {versions}.\nFolder: {folder}",
    "settings.reshade_cache_empty": (
        "No ReShade version downloaded yet. It will be fetched from reshade.me "
        "on the first install (or click 'Download / update now')."
    ),
    "settings.reshade_latest_option": "Latest (downloads if needed)",
    "settings.cached_suffix": "{version} (cached)",
    "settings.preferred_suffix": " — preferred",
    "settings.nwjs_cache_present": "Cached versions: {versions}.\nFolder: {folder}",
    "settings.nwjs_cache_empty": (
        "No NW.js version downloaded yet. It will be fetched once from nwjs.io "
        "and reused across all RPG Maker MV/MZ games."
    ),
    "settings.stable_latest_option": "Latest stable (downloads if needed)",
    "settings.nwjs_cached_item": "{version} ({bits}-bit, cached)",
    "settings.urm_cache_present": "Cached versions: {versions}.\nFolder: {folder}",
    "settings.urm_cache_empty": (
        "No Universal Ren'Py Mod version downloaded yet. It will be fetched once from 0x52.dev "
        "when you enable the toggle on a Ren'Py game."
    ),
    "settings.downloading_progress": "Downloading... {done:.1f} / {total:.1f} MB",
    "settings.reshade_ready": "ReShade {version} ready in {folder}",
    "settings.download_failed": "Failed: {message}",
    "settings.download_failed_title": "Download failed",
    "settings.nwjs_already_latest": "NW.js {version} is already the latest stable version in cache.",
    "settings.nwjs_downloading_progress": "Downloading NW.js... {done:.1f} / {total:.1f} MB",
    "settings.nwjs_ready": "NW.js {version} ({bits}-bit) ready in cache.",
    "settings.nwjs_download_failed_title": "NW.js download failed",
    "settings.urm_already_latest": "Universal Ren'Py Mod {version} is already the latest stable version in cache.",
    "settings.urm_downloading_progress": "Downloading URM... {done:.1f} / {total:.1f} MB",
    "settings.urm_ready": "Universal Ren'Py Mod {version} ready in cache.",
    "settings.urm_download_failed_title": "Universal Ren'Py Mod download failed",
    "settings.pruned": "Removed: {items}",
    "settings.download_in_progress_title": "Download in progress",
    "settings.download_in_progress_body": "Wait for the download to finish before closing.",
    # -- anime4k variants ------------------------------------------------
    "variant.cnn_s.label": "Restore CNN S (light)",
    "variant.cnn_s.desc": "Smallest neural network: restores details at low cost. Great for integrated GPUs and small displays.",
    "variant.cnn_m.label": "Restore CNN M (balanced)",
    "variant.cnn_m.desc": "Balance between sharpness and performance. Recommended for most 720p/768p visual novels.",
    "variant.cnn_l.label": "Restore CNN L (sharp)",
    "variant.cnn_l.desc": "Stronger line and texture reconstruction. Best suited for 1080p visual novels.",
    "variant.cnn_vl.label": "Restore CNN VL (very sharp)",
    "variant.cnn_vl.desc": "Larger network: more detail on high-resolution artwork, higher GPU cost.",
    "variant.cnn_ul.label": "Restore CNN UL (maximum)",
    "variant.cnn_ul.desc": "Largest available network. Maximum quality, very high VRAM/GPU usage.",
    "variant.soft_s.label": "Restore CNN Soft S (soft)",
    "variant.soft_s.desc": "Softer version of CNN S: less ringing/haloing on thin lines and heavy compression.",
    "variant.soft_m.label": "Restore CNN Soft M (soft)",
    "variant.soft_m.desc": "CNN Soft M: great for visual novels with soft art, gradients, and blurred backgrounds.",
    "variant.soft_l.label": "Restore CNN Soft L (soft)",
    "variant.soft_l.desc": "CNN Soft L: high detail with more natural transitions. Great for 1080p.",
    "variant.soft_vl.label": "Restore CNN Soft VL (soft)",
    "variant.soft_vl.desc": "CNN Soft VL: high resolution without over-sharpening edges.",
    "variant.soft_ul.label": "Restore CNN Soft UL (soft)",
    "variant.soft_ul.desc": "CNN Soft UL: softer variant of the maximum network, for 4K without harsh artifacts.",
    "anime4k.missing_fx": "Missing ReShade FX shaders in AniShade bundle: {files}",
    # -- engines ---------------------------------------------------------
    "engine.unknown.name": "Unknown",
    "engine.renpy.note1": "Ren'Py renders with OpenGL (gl2 renderer) or ANGLE/Direct3D 9 (angle2 renderer).",
    "engine.renpy.note2": "If the overlay does not appear, switch between opengl32.dll (gl2) and d3d9.dll (angle2).",
    "engine.renpy.note3": "Internal resolution is usually low: Anime4K Restore shaders shine here.",
    "engine.renpy.fix_hint": "Force OpenGL (gl2) when launching via AniShade and create a .bat with RENPY_RENDERER.",
    "engine.rpgmaker_mv.note1": "MV/MZ run inside NW.js (Chromium) using ANGLE over Direct3D 11.",
    "engine.rpgmaker_mv.note2": "Use dxgi.dll. If the overlay does not appear, try d3d11.dll (Chromium loads that name too).",
    "engine.rpgmaker_mv.note3": "Avoid enabling 'Performance Mode' in MV games: the overlay needs Chromium's context.",
    "engine.rpgmaker_mv.fix_hint": "Rename the ReShade DLL to d3d11.dll when dxgi.dll is not loaded.",
    "engine.rpgmaker_rgss.note1": "RGSS uses Direct3D 9; the right DLL is d3d9.dll.",
    "engine.rpgmaker_rgss.note2": "Some games ship their own d3d9.dll (ENB/RT). Check for conflicts first.",
    "engine.rpgmaker_rgss.fix_hint": "Check for third-party d3d9.dll conflicts before installing.",
    "engine.rpgmaker_2000.note1": "RPG Maker 2000/2003 renders with DirectDraw; ReShade uses ddraw.dll.",
    "engine.rpgmaker_2000.note2": "On modern Windows the game may need compatibility settings; test without ReShade first.",
    "engine.yuris.note1": "YU-RIS uses Direct3D 9. Common in Japanese visual novels with .ypf archives.",
    "engine.catsystem2.note1": "CatSystem2 uses Direct3D 9 (.cst/.int files).",
    "engine.reallive.note1": "RealLive uses Direct3D 9; older titles are usually 32-bit.",
    "engine.livemaker.note1": "LiveMaker uses Direct3D 9.",
    "engine.cmvs.note1": "CMVS uses Direct3D 9 (.cpz files).",
    "engine.nitroplus.note1": "Nitroplus engine uses Direct3D 9 (.npk files).",
    "engine.kirikiri.note1": "KiriKiri (KAG) uses Direct3D 9 in most builds.",
    "engine.kirikiri.note2": "If the game crashes on startup with ReShade, try disabling input hooking in ReShade.ini.",
    "engine.siglus.note1": "SiglusEngine uses Direct3D 9. Some older titles require 32-bit d3d9.dll.",
    "engine.bgi.note1": "BGI/Ethornell uses Direct3D 9; the engine usually runs in 32-bit.",
    "engine.nscripter.note1": "Older NScripter uses DirectDraw/Direct3D 9; ONScripter uses SDL (OpenGL or Direct3D).",
    "engine.nscripter.note2": "The API is detected from the .exe imports; double-check the Graphics API field before installing.",
    "engine.wolf.note1": "WOLF RPG Editor uses Direct3D 9 (d3d9.dll).",
    "engine.unity.note1": "Unity uses Direct3D 11 by default; dxgi.dll is the recommended name.",
    "engine.unity.note2": "Unity games usually need 'Copy depth buffer' off (ReShade 6 handles this automatically).",
    "engine.unity.note3": "If the game uses Vulkan, ReShade won't load via proxy DLL: launch with -force-d3d11.",
    "engine.unity.fix_hint": "Create a launcher with -force-d3d11 when the game launches in Vulkan.",
    "engine.unreal.note1": "Unreal Engine 4/5 uses Direct3D 11/12 (dxgi.dll).",
    "engine.unreal.note2": "In UE5 with Lumen/Nanite, Anime4K GPU cost can be high; prefer S/M variants.",
    "engine.godot.note1": "Godot 3 uses OpenGL 3 (opengl32.dll); Godot 4 uses Vulkan by default.",
    "engine.godot.note2": "For Godot 4, use the launcher with '--rendering-driver opengl3' so ReShade can load.",
    "engine.godot.fix_hint": "Launch with --rendering-driver opengl3 and install opengl32.dll.",
    "engine.gamemaker.note1": "Modern GameMaker uses Direct3D 11 (dxgi.dll).",
    "engine.artemis.note1": "Artemis uses Direct3D 9.",
    "engine.majiro.note1": "Majiro uses Direct3D 9.",
    "engine.unknown.note1": "Unrecognized engine: the API was inferred from the executable's imports.",
    # -- engine match evidence -------------------------------------------
    "evidence.renpy_dir": "renpy/ folder or .rpyc/.rpa files",
    "evidence.renpy_lib": "lib/py3-* (Ren'Py Python runtime)",
    "evidence.renpy_files": ".rpy/.rpyc/.rpa files",
    "evidence.rpgm_core": "js/rmmz_core.js (MV/MZ)",
    "evidence.rpgm_www": "www/ folder + NW.js",
    "evidence.rpgm_pkg": "package.json + index.html (NW.js)",
    "evidence.rgss_dll": "{name} (RGSS)",
    "evidence.rgss_data": "Game.ini + data/ (RPG Maker)",
    "evidence.rpgm2k": "RPG_RT.exe / .ldb (RPG Maker 2000/2003)",
    "evidence.yuris": ".ypf files (YU-RIS)",
    "evidence.catsystem2": ".cst/.int files (CatSystem2)",
    "evidence.reallive": ".g00 files (RealLive)",
    "evidence.livemaker": ".lsb files (LiveMaker)",
    "evidence.cmvs": ".cpz files (CMVS)",
    "evidence.nitroplus": ".npk files (Nitroplus)",
    "evidence.kirikiri_xp3": ".xp3 files",
    "evidence.kirikiri_dir": "kirikiri2/ folder or krkr.exe",
    "evidence.unity_data": "*_Data/ folder (Unity)",
    "evidence.godot_pck": ".pck file",
    "evidence.artemis": ".pfs/.arg files (Artemis)",
    # -- detect ----------------------------------------------------------
    "detect.pe_read_error": "Could not read the executable header ({error}).",
    "detect.manual_engine": "manually set engine: {name}",
    "detect.godot4_note": "Godot 4 detected: launch via the Play button (or the .bat) to force OpenGL 3.",
    "detect.godot4_warn": "Godot 4 uses Vulkan by default. Running the .exe directly may prevent ReShade from loading.",
    "detect.godot3_note": "Godot 3 detected: renders with OpenGL 3 (opengl32.dll).",
    "detect.content_size_note": (
        "Detected internal resolution: {w}x{h}. "
        "The full screen is filtered; border noise/feedback protection is automatic in the shader."
    ),
    "detect.rpgm_plugin_note": "Plugin {name} (H key to hide textbox) available at {path}.",
    "detect.api_source.default": "default",
    "detect.api_source.manual": "manually set",
    "detect.api_source.log": "ReShade log",
    "detect.api_source.imports": "executable imports",
    "detect.api_source.engine": "detected engine",
    "detect.api_source.godot4": "Godot 4 with OpenGL launcher",
    "detect.api_source.fallback": "default (not detected)",
    "detect.api_source.angle": "ANGLE libraries in game folder",
    "detect.warn_vulkan": (
        "Vulkan detected: ReShade does not load via proxy DLL. "
        "Launch the game in Direct3D 11/OpenGL (e.g. -force-d3d11) or use ReShade global injection."
    ),
    "detect.warn_32bit": "32-bit game: ReShade32.dll will be used (process memory limit applies).",
    "detect.warn_is_dll": "The selected file is a DLL, not an executable.",
    "detect.warn_no_arch": "No architecture info available: assuming 64-bit.",
    "detect.warn_launcher": "'{name}' looks like a launcher/config tool. Prefer the actual game executable.",
    "detect.note_many_exes": "There are many .exe files in this folder; make sure the selected one launches the actual game.",
    "detect.warn_conflicts": (
        "A proxy DLL name already exists in the folder ({dlls}). "
        "AniShade uses an alternative name whenever possible and never overwrites without confirmation."
    ),
    "detect.warn_not_writable": "The game folder is not writable without administrator privileges.",
    # -- installer -------------------------------------------------------
    "installer.no_write_perm": (
        "No permission to write to {folder}.\n"
        "Close the game and run AniShade as administrator."
    ),
    "installer.write_failed": "Failed to write {name}: {error}",
    "installer.conflict_forced": "{name} already exists in the game folder and is not ReShade.",
    "installer.no_proxy_dll": "API has no known proxy DLL.",
    "installer.conflict_all": (
        "All proxy DLL names for this API already exist and belong to another program:\n"
        "{list}\n\n"
        "Rename/remove the conflict or pick another DLL name in the 'Proxy DLL' field."
    ),
    "installer.exe_not_found": "Executable not found: {exe}",
    "installer.game_running_install": "{exe} is currently running. Close the game before installing or updating ReShade.",
    "installer.vulkan_unsupported": (
        "Vulkan API detected. ReShade cannot be loaded via proxy DLL in this game.\n"
        "Launch the game in Direct3D 11/OpenGL or use ReShade global injection."
    ),
    "installer.using_reshade_dll": "Using {dll} from ReShade {version}.",
    "installer.proxy_dll": "Proxy DLL: {dll}",
    "installer.splash_hidden": "Startup splash and loading spinner hidden in the ReShade DLL.",
    "installer.splash_hide_warn": "Warning: could not hide the splash screen in this ReShade version.",
    "installer.old_dll_removed": "Old DLL removed: {path}",
    "installer.copying_shaders": "Copying ReShade FX shader: {files}",
    "installer.no_shader_perm": (
        "No permission to write shaders to {folder}.\n"
        "Run AniShade as administrator."
    ),
    "installer.preset_backed_up": "In-game edited preset was backed up.",
    "installer.launcher_warn": "Warning: could not create the .bat launcher ({error}).",
    "installer.rpgm_plugin_installed": "RPG Maker plugin installed: {path}.",
    "installer.warning_prefix": "Warning: {warning}",
    "installer.rpgm_plugin_removed": "RPG Maker plugin removed: {files}.",
    "installer.urm_installed": "Universal Ren'Py Mod {version} installed at {path}.",
    "installer.urm_install_warn": "Could not install Universal Ren'Py Mod: {error}",
    "installer.urm_install_log_warn": "Warning: failed to install Universal Ren'Py Mod ({error}).",
    "installer.urm_removed": "Universal Ren'Py Mod removed: {files}.",
    "installer.done": "Installation complete.",
    "installer.no_manifest": (
        "No AniShade installation record found for this game. "
        "Nothing was removed to avoid deleting third-party files."
    ),
    "installer.game_running_uninstall": "Close the game before uninstalling.",
    "installer.modified_backed_up": "Modified file backed up: {backup}",
    "installer.remove_failed": "Could not remove {path}: {error}",
    "installer.ini_modified_backed_up": "Modified ReShade.ini backed up: {backup}",
    "installer.ini_restored": "Original ReShade.ini restored.",
    "installer.ini_restore_failed": "Failed to restore ReShade.ini: {error}",
    "installer.reshade_removed": "ReShade removed from the game.",
    "installer.problem_dll": "ReShade DLL is missing or modified.",
    "installer.problem_preset_edited": "Preset was edited in-game (normal if you tweaked it manually).",
    "installer.problem_preset_missing": "Preset AniShade.ini is missing.",
    "installer.problem_shaders_missing": "Anime4K shaders are missing; click 'Reinstall'.",
    "installer.unknown_rpgm_plugin": "Unknown RPG Maker plugin: {key}",
    "installer.game_running_plugin": "{exe} is currently running. Close the game before changing plugins.",
    "installer.plugins_js_missing": "plugins.js not found in this game.",
    "installer.plugin_enabled": "Plugin {file} enabled in {path}.",
    "installer.plugin_removed": "Plugin {file} removed from the game.",
    "installer.game_running_urm": "{exe} is currently running. Close the game before changing Universal Ren'Py Mod.",
    "installer.renpy_game_dir_missing": "Ren'Py 'game/' folder not found next to the executable.",
    "installer.renpy_game_dir_missing_short": "Ren'Py 'game/' folder not found.",
    "installer.urm_enabled": "Universal Ren'Py Mod {version} enabled at {path}.",
    "installer.urm_removed_list": "Universal Ren'Py Mod removed ({files}).",
    "installer.urm_disabled": "Universal Ren'Py Mod disabled.",
    "installer.dll_realigned": "ReShade DLL ({dll}) updated to {bits}-bit.",
    "installer.reshade_reinstall_needed": "Installed ReShade needs to be reinstalled ({error}).",
    # -- reshade ---------------------------------------------------------
    "reshade.fetch_failed": "Could not reach reshade.me: {error}",
    "reshade.no_link": "Could not find a ReShade download link on the official page.",
    "reshade.setup_cached": "ReShade {version} installer is already cached.",
    "reshade.downloading": "Downloading ReShade {version} from reshade.me ...",
    "reshade.download_failed": "Failed to download ReShade: {error}",
    "reshade.download_incomplete": "ReShade download was incomplete.",
    "reshade.downloaded": "ReShade {version} downloaded ({mb:.1f} MB).",
    "reshade.setup_too_small": "Installer file is too small to be ReShade Setup.",
    "reshade.invalid_dll": "Extracted {name} does not appear to be a valid DLL.",
    "reshade.dlls_not_found": (
        "Could not find the DLLs inside the ReShade installer. "
        "Download again from https://reshade.me."
    ),
    "reshade.using_cached": "Using ReShade {version} from local cache.",
    "reshade.no_cache_offline": "No ReShade version is cached and networking is disabled.",
    "reshade.checking_latest": "Checking for the latest ReShade version ...",
    "reshade.offline_fallback": "Could not reach reshade.me; using cached version.",
    "reshade.extracting": "Extracting ReShade32.dll and ReShade64.dll from installer ...",
    "reshade.dll_missing_cache": "{name} not found in ReShade cache.",
    "reshade.dll_corrupt_cache": "{name} in cache is corrupted. Delete {folder} and download again.",
    # -- nwjs ------------------------------------------------------------
    "nwjs.invalid_version": "Invalid NW.js version.",
    "nwjs.fetch_failed": "Could not reach nwjs.io: {error}",
    "nwjs.no_version": "Could not find a valid NW.js version in nwjs.io/versions.json.",
    "nwjs.invalid_zip": "Invalid NW.js ZIP archive: {error}",
    "nwjs.empty_zip": "NW.js ZIP archive is empty.",
    "nwjs.missing_binaries": "Downloaded ZIP archive does not contain nw.exe and nw.dll.",
    "nwjs.archive_cached": "NW.js {version} ({arch}) package is already in the download cache.",
    "nwjs.downloading": "Downloading NW.js {version} ({arch}) from dl.nwjs.io ...",
    "nwjs.download_failed": "Failed to download NW.js: {error}",
    "nwjs.download_incomplete": "NW.js download was incomplete.",
    "nwjs.sha_mismatch": (
        "SHA-256 checksum of the NW.js package does not match the official sum on dl.nwjs.io. "
        "Please try downloading again."
    ),
    "nwjs.downloaded": "NW.js {version} downloaded ({mb:.1f} MB).",
    "nwjs.extracting": "Extracting NW.js {version} to local cache ...",
    "nwjs.extract_incomplete": "Incomplete NW.js extraction (nw.exe or nw.dll missing).",
    "nwjs.using_cached": "Using NW.js {version} ({arch}) from local cache.",
    "nwjs.no_cache_offline": "No NW.js version is cached and networking is disabled.",
    "nwjs.checking_latest": "Checking for the latest stable NW.js version on nwjs.io ...",
    "nwjs.offline_fallback": "Could not reach nwjs.io; using cached NW.js.",
    "nwjs.invalid_package_json": "Invalid package.json ({name}): {error}",
    "nwjs.invalid_package_root": "Invalid package.json ({name}): root is not a JSON object.",
    "nwjs.fix_chromium_args_list": "converted chromium-args from array to string",
    "nwjs.fix_autoplay": "added --autoplay-policy=no-user-gesture-required (prevents muted audio)",
    "nwjs.fix_js_flags": "removed obsolete V8 flags from js-flags ({flags})",
    "nwjs.fix_set_name": 'set "name": "{name}" in package.json',
    "nwjs.fix_missing_name": 'fixed missing/invalid "name" to "{name}"',
    "nwjs.fix_main": 'fixed "main" to "{main}"',
    "nwjs.fix_window_dim": "converted window.{dim} to integer",
    "nwjs.fix_window_icon": 'fixed window.icon to "{icon}"',
    "nwjs.fix_remove_icon": "removed window.icon pointing to a non-existent file",
    "nwjs.fix_compat_shim": "added process.mainModule compatibility shim for legacy MV/plugins",
    "nwjs.fix_www_bom": "normalized JSON/BOM in www/package.json",
    "nwjs.fix_root_from_www": "created root package.json from www/package.json",
    "nwjs.fix_root_bom": "normalized JSON/BOM in package.json",
    "nwjs.fix_root_default": "created default root package.json",
    "nwjs.game_running_update": "{exe} is currently running. Close the game before updating NW.js.",
    "nwjs.backing_up": "Backing up original NW.js files ...",
    "nwjs.applying": "Applying NW.js {version} ({arch}) to {folder} ...",
    "nwjs.reshade_preserved": "{file} belongs to ReShade and was preserved.",
    "nwjs.fixing_package_json": "Checking and fixing package.json ...",
    "nwjs.updated_log": "NW.js updated to {version} ({bits}-bit).",
    "nwjs.no_backup": "No original NW.js backup found for this game.",
    "nwjs.game_running_restore": "{exe} is currently running. Close the game before restoring NW.js.",
    "nwjs.restored_log": "Original NW.js restored ({count} file(s)).",
    # -- rpgmaker --------------------------------------------------------
    "rpgmaker_mod.array_not_found": "$plugins array not found in plugins.js.",
    "rpgmaker_mod.plugins_js_not_found": (
        "plugins.js not found (packed game or non-standard NW.js layout): "
        "plugin {file} was not installed."
    ),
    "rpgmaker_mod.decode_failed": (
        "Could not decode plugins.js (unknown encoding): "
        "plugin {file} was not installed."
    ),
    "rpgmaker_mod.plugins_js_restored": "Original plugins.js restored.",
    "rpgmaker_mod.plugins_js_backed_up": "Modified plugins.js backed up: {backup}",
    "rpgmaker_mod.entry_removed": "Entry {name} removed from plugins.js.",
    "rpgmaker_mod.clean_failed": "Could not clean plugins.js: {error}",
    "rpgmaker_mod.plugin_backed_up": "Modified plugin backed up: {backup}",
    "rpgmaker_mod.remove_failed": "Could not remove {path}: {error}",
    "rpgmaker_mod.problem_missing": "RPG Maker plugin ({file}) is missing; click 'Reinstall'.",
    "rpgmaker_mod.problem_inactive": "Plugin {name} is not enabled in plugins.js; click 'Reinstall'.",
    # -- renpy -----------------------------------------------------------
    "renpy_mod.fetch_failed": "Could not reach 0x52.dev: {error}",
    "renpy_mod.unexpected_api": "Unexpected response from the 0x52.dev API.",
    "renpy_mod.no_release": "No available Universal Ren'Py Mod release was found on 0x52.dev.",
    "renpy_mod.rpa_not_found": "{filename} not found inside the ZIP downloaded from 0x52.dev.",
    "renpy_mod.invalid_zip": "Universal Ren'Py Mod ZIP archive is invalid or corrupted: {error}",
    "renpy_mod.invalid_rpa": "Extracted {filename} does not appear to be a valid Ren'Py .rpa archive.",
    "renpy_mod.archive_cached": "Universal Ren'Py Mod {version} package is already in the download cache.",
    "renpy_mod.downloading": "Downloading Universal Ren'Py Mod {version} from 0x52.dev ...",
    "renpy_mod.download_failed": "Failed to download Universal Ren'Py Mod: {error}",
    "renpy_mod.downloaded": "Universal Ren'Py Mod {version} downloaded ({mb:.1f} MB).",
    "renpy_mod.using_cached": "Using Universal Ren'Py Mod {version} from local cache.",
    "renpy_mod.no_cache_offline": "No Universal Ren'Py Mod version is cached and networking is disabled.",
    "renpy_mod.checking_latest": "Checking for the latest Universal Ren'Py Mod version on 0x52.dev ...",
    "renpy_mod.offline_fallback": "Could not reach 0x52.dev; using cached version.",
    "renpy_mod.extracting": "Extracting {filename} ...",
    "renpy_mod.rpa_missing_cache": "{filename} not found in local cache.",
    "renpy_mod.rpa_corrupt_cache": "{filename} in cache is corrupted. Delete {folder} and download again.",
    "renpy_mod.game_dir_missing": "Ren'Py 'game/' folder not found next to the executable.",
    "renpy_mod.modified_backed_up": "Modified {filename} was backed up before removal: {backup}",
    "renpy_mod.remove_failed": "Could not remove {filename}: {error}",
    "renpy_mod.problem_missing": "Universal Ren'Py Mod ({filename}) is missing from the game/ folder.",
    # -- pe --------------------------------------------------------------
    "pe.unknown_arch": "unknown",
    "pe.empty_file": "empty file: {path}",
    "pe.read_oob": "read beyond end of file",
    "pe.too_small": "file is too small to be an executable",
    "pe.no_mz": "missing MZ signature",
    "pe.no_pe": "missing PE signature",
    "pe.unknown_magic": "unknown PE format (magic 0x{magic:x})",
    # -- cli -------------------------------------------------------------
    "cli.info.exe": "Executable ....: {value}",
    "cli.info.name": "Name ..........: {value}",
    "cli.info.engine": "Engine ........: {name}  ({evidence})",
    "cli.info.arch": "Architecture ..: {bits}-bit",
    "cli.info.api": "API ...........: {label}  [{source}]",
    "cli.info.dll": "Proxy DLL .....: {dll}  (alternatives: {alts})",
    "cli.info.content": "Content .......: {size}  aspect {aspect:.3f}",
    "cli.info.content_none": "not detected",
    "cli.info.reshade": "Current ReShade: {value}",
    "cli.info.rpgm_plugin": "RPGM Plugin ...: {path} (hide textbox with H)",
    "cli.info.nwjs": "Current NW.js .: {value}",
    "cli.info.renpy_urm": "Ren'Py Mod ....: {dir}/{file} ({state})",
    "cli.info.active": "active",
    "cli.info.notes": "Notes:",
    "cli.info.warnings": "Warnings:",
    "cli.variants.header": "Anime4K Restore variants (ReShade FX):",
    "cli.variants.weight": "cost {weight}x",
    "cli.cache.ready": "Cache ready: ReShade {version} in {folder}",
    "cli.install.header": "\nInstalled:",
    "cli.install.dll": "  DLL ..........: {value}",
    "cli.install.preset": "  Preset .......: {value}",
    "cli.install.shaders": "  Shaders ......: {value}",
    "cli.install.reshade": "  ReShade ......: {value}",
    "cli.install.techniques": "  Techniques ...: {value}",
    "cli.install.rpgm_plugins": "  RPGM Plugins .: {value}",
    "cli.install.renpy_urm": "  Ren'Py Mod ...: {value}{ver}",
    "cli.install.launcher": "  Launcher .....: {value}",
    "cli.uninstall.not_found": "Game is not in the AniShade library.",
    "cli.uninstall.done": "Removed {count} file(s).",
    "cli.list.empty": "Library is empty.",
    "cli.list.installed": "installed",
    "cli.list.pending": "pending",
    "cli.plugin.enabled": "Plugin enabled: {path}",
    "cli.plugin.disabled": "Plugin disabled.",
    "cli.nwjs.cache_ready": "Cache ready: NW.js {version} ({arch}) in {folder}",
    "cli.nwjs.updated": "\nNW.js updated to {version} ({arch}).",
    "cli.nwjs.restored": "Restored {count} original file(s).",
    "cli.urm.cache_ready": "Cache ready: Universal Ren'Py Mod {version} in {folder}",
    "cli.urm.enabled": "Universal Ren'Py Mod enabled: {path}",
    "cli.urm.disabled": "Universal Ren'Py Mod disabled.",
    "cli.error_prefix": "ERROR: {error}",
    "cli.help.info": "analyze an executable",
    "cli.help.install": "install ReShade + Anime4K",
    "cli.help.top_margin": "top pixels to ignore (title bar)",
    "cli.help.aspect": "content aspect ratio (e.g. 1.5); 0 disables",
    "cli.help.no_hide_textbox": "do not install the hide-textbox (H key) plugin on RPG Maker MV/MZ games",
    "cli.help.no_alt_skip": "do not install the no-Alt-skip plugin on RPG Maker MV/MZ games",
    "cli.help.no_save_slots": "do not install the 100 save slots plugin on RPG Maker MV/MZ games",
    "cli.help.renpy_urm": "install or remove Universal Ren'Py Mod (0x52_URM.rpa) on Ren'Py games",
    "cli.help.uninstall": "remove ReShade installed by AniShade",
    "cli.help.variants": "list available shader variants",
    "cli.help.cache": "manage the ReShade cache",
    "cli.help.list": "list games in the library",
    "cli.help.engines": "list recognized engines",
    "cli.help.plugin": "enable or remove AniShade RPG Maker MV/MZ plugins",
    "cli.help.plugin_choice": "which plugin to toggle (default: hide_textbox)",
    "cli.help.plugin_disable": "remove the plugin from the game",
    "cli.help.nwjs": "manage and update NW.js on RPG Maker MV/MZ games",
    "cli.help.nwjs_update": "update the game's NW.js runtime and fix package.json",
    "cli.help.nwjs_restore": "restore the original NW.js from backup",
    "cli.help.nwjs_cache": "list or download official NW.js into the cache",
    "cli.help.urm": "manage Universal Ren'Py Mod (0x52.dev) on Ren'Py games",
    "cli.help.urm_enable": "install 0x52_URM.rpa into the Ren'Py game/ folder",
    "cli.help.urm_disable": "remove 0x52_URM.rpa from the Ren'Py game",
    "cli.help.urm_cache": "list or download Universal Ren'Py Mod into the cache",
}


_PT_BR: dict[str, str] = {
    # -- app / general ---------------------------------------------------
    "app.tagline": "ReShade + Anime4K Restore para visual novels e jogos japoneses",
    "app.window_title": "AniShade — ReShade + Anime4K Restore",
    "app.unhandled_error": "Erro não tratado:",
    "common.unknown": "Desconhecida",
    "common.unknown_lower": "desconhecida",
    "common.none": "nenhuma",
    "common.bits": "{bits} bits",
    "common.bits_unknown": "? bits",
    "common.cancel": "Cancelar",
    "common.save": "Salvar",
    "common.open": "Abrir",
    "common.error": "Erro",
    # -- widgets ---------------------------------------------------------
    "widget.no_pass_selected": "Nenhum passe selecionado",
    # -- topbar / banners / log ------------------------------------------
    "topbar.add_game": "Adicionar jogo",
    "topbar.settings": "Configurações",
    "topbar.log": "Registro",
    "banner.reshade_missing": (
        "O ReShade ainda não foi baixado. Ele será obtido do site oficial (reshade.me) "
        "na primeira instalação — depois fica em cache para todos os jogos."
    ),
    "banner.download_now": "Baixar agora",
    "log.placeholder": "O registro das operações aparece aqui (Ctrl+L).",
    # -- left panel / library --------------------------------------------
    "library.search_placeholder": "Buscar na biblioteca...",
    "library.empty_hint": (
        "Nenhum jogo ainda.\n\nClique em “Adicionar jogo” e aponte para o .exe do jogo, "
        "ou arraste o executável para esta janela."
    ),
    "library.hint": "Duplo clique renomeia · Botão direito abre opções",
    "library.select_placeholder": (
        "Selecione um jogo na lista para ver a detecção, escolher a variante do Anime4K "
        "e instalar o ReShade."
    ),
    "badge.not_installed": "Não instalado",
    "badge.incomplete": "Incompleto",
    "badge.pending": "Pendente",
    "badge.installed": "Instalado",
    "menu.play": "Jogar",
    "menu.rename": "Renomear",
    "menu.open_folder": "Abrir pasta",
    "menu.remove_from_library": "Remover da biblioteca",
    # -- game header -----------------------------------------------------
    "header.play": "Jogar",
    "header.play_tooltip": "Inicia o jogo com as correções de ambiente do engine",
    "header.folder": "Pasta",
    "header.remove": "Remover",
    # -- detection card --------------------------------------------------
    "detection.title": "Detecção",
    "detection.reanalyze": "Reanalisar",
    "detection.engine": "Engine",
    "detection.auto_detect": "Detectar automaticamente",
    "detection.api": "API gráfica",
    "detection.arch": "Arquitetura",
    "detection.reshade": "ReShade",
    "detection.default_heuristic": "heurística padrão",
    "detection.module_tooltip": "Módulo usado: {module}",
    "detection.installed_lower": "instalado",
    "detection.not_installed_lower": "não instalado",
    "detection.conflict_warning": "Conflito de nome: {dlls} (será evitado).",
    # -- rpgmaker card ---------------------------------------------------
    "rpgmaker.title": "RPG Maker MV/MZ",
    "rpgmaker.hide_textbox_title": "Ocultar caixa de texto com a tecla H",
    "rpgmaker.hide_textbox_tooltip": (
        "Ativa ou remove AniShade_HideTextbox.js em js/plugins/ e plugins.js imediatamente."
    ),
    "rpgmaker.no_alt_title": "Impedir Alt de pular texto (Alt+Tab)",
    "rpgmaker.no_alt_tooltip": (
        "Ativa ou remove AniShade_NoAltSkip.js para que Alt / Alt+Tab / Alt+Enter nunca pulem diálogos "
        "(Ctrl continua funcionando normalmente)."
    ),
    "rpgmaker.save_slots_title": "Expandir para 100 slots de save",
    "rpgmaker.save_slots_tooltip": (
        "Ativa ou remove AniShade_SaveSlots100.js para liberar 100 slots manuais de save "
        "(mantém o Autosave no MZ e nunca reduz se o jogo já tiver mais de 100)."
    ),
    "rpgmaker.plugins_js_missing": (
        "plugins.js não encontrado (jogo compactado ou estrutura NW.js não padrão)."
    ),
    "rpgmaker.hide_textbox_active": (
        "Ativo ({file} registrado em {plugins_js}). "
        "Pressione H no jogo para ocultar/exibir a caixa de texto."
    ),
    "rpgmaker.no_alt_active": (
        "Ativo ({file}). Alt e Alt+Tab não pulam diálogos; Ctrl continua funcionando."
    ),
    "rpgmaker.save_slots_active": (
        "Ativo ({file}). 100 slots manuais de save liberados (MV e MZ)."
    ),
    "rpgmaker.not_installed_yet": (
        "Não instalado ainda — ative o interruptor agora ou ele será instalado junto com o ReShade."
    ),
    "rpgmaker.hide_textbox_disabled": "Desativado — ative o interruptor para adicionar ao jogo.",
    "rpgmaker.no_alt_disabled": "Desativado — ative o interruptor para impedir que Alt / Alt+Tab pule texto.",
    "rpgmaker.save_slots_disabled": "Desativado — ative o interruptor para expandir o limite para 100 slots de save.",
    "rpgmaker.nwjs_title": "Atualizar NW.js (oficial)",
    "rpgmaker.nwjs_restore": "Restaurar",
    "rpgmaker.nwjs_restore_tooltip": "Restaura o NW.js e o package.json originais do backup",
    "rpgmaker.nwjs_update": "Atualizar NW.js",
    "rpgmaker.nwjs_update_tooltip": (
        "Baixa o NW.js oficial de nwjs.io (uma única vez), atualiza o runtime do jogo "
        "e corrige problemas de compatibilidade no package.json (name ausente, autoplay, js-flags, etc.)."
    ),
    "rpgmaker.nwjs_cache_hint_cached": "Cache local: NW.js {version} ({bits} bits)",
    "rpgmaker.nwjs_cache_hint_empty": "Baixa o NW.js oficial de nwjs.io 1x e reutiliza em todos os jogos",
    "rpgmaker.nwjs_updated_tag": " · atualizado pelo AniShade",
    "rpgmaker.nwjs_status": (
        "No jogo: {version} ({bits_text}{updated_tag})\n"
        "{cache_hint} · corrige package.json (name ausente, autoplay, js-flags, compatibilidade MV)."
    ),
    # -- renpy card ------------------------------------------------------
    "renpy.title": "Ren'Py",
    "renpy.mod_link_tooltip": "Abrir página oficial: {url}",
    "renpy.urm_title": "Universal Ren'Py Mod (URM)",
    "renpy.urm_tooltip": (
        "Baixa o Universal Ren'Py Mod (0x52_URM.rpa) de 0x52.dev uma única vez, "
        "salva em cache e instala ou remove na pasta game/ imediatamente."
    ),
    "renpy.game_dir_missing": "Pasta game/ não encontrada ao lado do executável.",
    "renpy.urm_active": (
        "Ativo ({ver_tag}{game_dir}/{filename}). "
        "Menu de variáveis, cenas, escolhas, saves e customização dentro do jogo."
    ),
    "renpy.urm_not_installed_yet": (
        "Não instalado ainda — ative o interruptor agora ou ele será instalado junto com o ReShade."
    ),
    "renpy.urm_disabled_cached": (
        "Desativado — ative para instalar {filename} em {game_dir}/ "
        "(cache local: v{version})."
    ),
    "renpy.urm_disabled_uncached": (
        "Desativado — baixa {filename} de 0x52.dev uma única vez, salva em cache "
        "e instala em {game_dir}/."
    ),
    # -- shader card -----------------------------------------------------
    "shader.title": "Shaders Anime4K (Restore)",
    "shader.intro": (
        "Restore reconstrói detalhes da arte que o jogo já ampliou. Escolha a variante pela "
        "resolução interna do jogo; quanto maior a rede, maior o custo de GPU."
    ),
    "shader.top_margin": "Margem superior (barra de título)",
    "shader.top_margin_tooltip": (
        "Pixels do topo que não devem ser filtrados. Alguns jogos NW.js/Chromium "
        "incluem a barra de título no swapchain (ex.: buffer 1080x751 para conteúdo "
        "1080x720). Use 0 em fullscreen/borderless."
    ),
    "shader.top_margin_hint": (
        "Deixe 0 em fullscreen. Em janela, se a barra de título ficar distorcida, "
        "ajuste para a altura da barra (ex.: 31 px)."
    ),
    "shader.aspect": "Proporção do conteúdo (L/A)",
    "shader.aspect_tooltip": (
        "Opcional: limita manualmente o shader a uma proporção (ex.: 1.5). "
        "Deixe 0 (recomendado): o shader já detecta e bloqueia feedback nas bordas automaticamente."
    ),
    "shader.aspect_hint": (
        "Recomendado: 0 (tela inteira). A proteção contra ruído/feedback nas bordas pretas é automática no shader."
    ),
    # -- install card ----------------------------------------------------
    "install.title": "Instalação",
    "install.refresh": "Atualizar status",
    "install.reshade": "ReShade",
    "install.dll_proxy": "DLL proxy",
    "install.dll_tooltip_auto": (
        "Nome da DLL proxy. 'Automático' escolhe a melhor opção livre na pasta do jogo."
    ),
    "install.dll_tooltip_installed": "Instalado como {dll_name}",
    "install.dll_auto": "Automático ({name})",
    "install.dll_auto_label": "automático",
    "install.dll_conflict": "conflito de nomes",
    "install.preset": "Preset",
    "install.edit": "Editar",
    "install.edit_tooltip": "Abrir o preset no editor padrão (.ini)",
    "install.shaders": "Shaders",
    "install.launcher": "Launcher",
    "install.rpgmaker_plugin": "Plugin RPG Maker",
    "install.renpy_urm": "Mod Ren'Py",
    "install.techniques_installed": "{count} técnicas em {subdir}",
    "install.techniques_planned": "{count} técnicas planejadas",
    "install.create_launcher": "Criar launcher .bat com correções do engine",
    "install.create_launcher_tooltip": (
        "O launcher aplica variáveis de ambiente recomendadas (ex.: RENPY_RENDERER) "
        "antes de abrir o jogo."
    ),
    "install.open_game_folder": "Abrir pasta do jogo",
    "install.rpgm_hide_short": "Ocultar texto (H)",
    "install.rpgm_no_alt_short": "Sem pular com Alt",
    "install.rpgm_slots_short": "100 slots de save",
    "install.will_install_plural": "serão instalados com o ReShade",
    "install.disabled_plural": "desativados",
    "install.plugins_js_not_found": "plugins.js não encontrado",
    "install.will_install_single": "será instalado com o ReShade",
    "install.disabled_single": "desativado",
    "install.game_dir_not_found": "pasta game/ não encontrada",
    # -- footer / buttons ------------------------------------------------
    "footer.add_game_start": "Adicione um jogo para começar.",
    "footer.uninstall": "Desinstalar",
    "footer.install": "Instalar ReShade + Anime4K",
    "footer.apply_changes": "Aplicar alterações",
    "footer.reinstall": "Reinstalar",
    "footer.vulkan_unsupported": "Vulkan não suportado",
    "footer.vulkan_status": (
        "Este jogo usa Vulkan: o ReShade não carrega por proxy DLL. "
        "Inicie em Direct3D 11/OpenGL ou use a injeção global."
    ),
    "footer.ready_to_install": "Pronto para instalar. O ReShade é baixado apenas uma vez.",
    "footer.changes_pending": "Alterações de shader pendentes (não instaladas ainda).",
    "footer.installed_status": (
        "Instalado. Abra o jogo e pressione Home para abrir o overlay do ReShade."
    ),
    "footer.exe_missing": "Executável não encontrado — o jogo foi movido ou removido?",
    # -- dialogs & messages (main window) --------------------------------
    "dialog.analyze_error_title": "Erro ao analisar",
    "dialog.install_success_title": "AniShade",
    "dialog.install_success_header": "Pronto!",
    "dialog.install_success_dll": "• DLL: {dll}",
    "dialog.install_success_preset": "• Preset: {preset}",
    "dialog.install_success_chain": "• Cadeia: {chain}",
    "dialog.install_success_plugin_hide": "• Plugin RPG Maker: {file} (tecla H oculta a caixa de texto)\n",
    "dialog.install_success_plugin_no_alt": "• Plugin RPG Maker: {file} (Alt / Alt+Tab não pula texto)\n",
    "dialog.install_success_plugin_slots": "• Plugin RPG Maker: {file} (100 slots de save)\n",
    "dialog.install_success_plugin_other": "• Plugin RPG Maker: {file}\n",
    "dialog.install_success_renpy_urm": "• Mod Ren'Py: Universal Ren'Py Mod{ver} ({file})\n",
    "dialog.install_success_footer": "Abra o jogo e pressione Home para abrir o overlay do ReShade.",
    "dialog.install_success_launcher": "\n\nLauncher criado: {launcher}",
    "dialog.uninstall_title": "Desinstalar",
    "dialog.uninstall_body": (
        "Remover o ReShade e os shaders Anime4K de “{name}”?\n\n"
        "Somente arquivos criados pelo AniShade são removidos."
    ),
    "dialog.nwjs_update_title": "Atualizar NW.js",
    "dialog.nwjs_source_cached": "Usará o NW.js {version} (64 bits) do cache local.",
    "dialog.nwjs_source_download": (
        "O NW.js oficial (64 bits) será baixado de nwjs.io uma única vez e salvo em cache para os próximos jogos."
    ),
    "dialog.nwjs_update_body": (
        "Atualizar o runtime NW.js de “{name}”?\n\n"
        "{source_note}\n"
        "Os arquivos originais do NW.js e o package.json serão salvos em backup "
        "(você pode restaurar depois).\n"
        "Correções automáticas aplicadas: campo 'name' ausente no package.json, "
        "autoplay de áudio, flags V8 obsoletas e compatibilidade process.mainModule."
    ),
    "dialog.nwjs_success_title": "NW.js atualizado",
    "dialog.nwjs_success_header": "NW.js atualizado com sucesso!",
    "dialog.nwjs_success_version": "• Versão: NW.js {version} ({arch})",
    "dialog.nwjs_success_files": "• Arquivos atualizados: {count}",
    "dialog.nwjs_success_realigned": "• DLL do ReShade atualizada automaticamente para 64 bits.",
    "dialog.nwjs_success_fixes": "Correções aplicadas:",
    "dialog.nwjs_success_warnings": "Avisos:",
    "dialog.nwjs_restore_title": "Restaurar NW.js original",
    "dialog.nwjs_restore_body": (
        "Restaurar os arquivos originais do NW.js e o package.json de “{name}”?"
    ),
    "dialog.task_error_title": "Falha na operação",
    "dialog.admin_title": "Permissão necessária",
    "dialog.admin_body": "Reiniciar o AniShade como administrador para continuar?",
    "dialog.pick_game_title": "Escolha o executável do jogo",
    "dialog.pick_game_filter": "Executáveis (*.exe);;Todos os arquivos (*.*)",
    "dialog.invalid_file_title": "Arquivo inválido",
    "dialog.invalid_file_body": "Selecione um arquivo .exe válido.",
    "dialog.analyze_failed_body": "Não foi possível analisar o executável:\n{error}",
    "dialog.rename_title": "Renomear",
    "dialog.rename_label": "Nome exibido:",
    "dialog.remove_title": "Remover jogo",
    "dialog.remove_body": "Remover “{name}” da biblioteca?",
    "dialog.remove_installed_info": (
        "O jogo tem o ReShade instalado pelo AniShade. Você pode desinstalar antes de remover."
    ),
    "dialog.remove_only": "Só remover da lista",
    "dialog.remove_and_uninstall": "Desinstalar e remover",
    "dialog.game_missing_title": "Jogo ausente",
    "dialog.game_missing_body": "O executável não existe mais neste caminho.",
    "dialog.launch_error_title": "Erro ao iniciar",
    "dialog.folder_missing_title": "Pasta ausente",
    "dialog.folder_missing_body": "A pasta não existe mais:\n{folder}",
    "dialog.preset_missing_title": "Preset ausente",
    "dialog.preset_missing_body": "O preset AniShade.ini ainda não foi criado. Instale primeiro.",
    "dialog.open_error_title": "Erro ao abrir",
    "dialog.busy_close_title": "Operação em andamento",
    "dialog.busy_close_body": "Aguarde a operação atual terminar antes de fechar o AniShade.",
    # -- main window logs & progress -------------------------------------
    "log.reshade_cached": "ReShade {version} pronto no cache.",
    "log.downloading_reshade": "Baixando ReShade...",
    "log.downloading_urm": "Baixando Universal Ren'Py Mod... {done:.1f} / {total:.1f} MB",
    "log.installing_urm": "Instalando Universal Ren'Py Mod...",
    "log.removing_urm": "Removendo Universal Ren'Py Mod...",
    "log.installing": "Instalando...",
    "log.installed": "Instalado: {dll} + {count} passes (ReShade {version}).",
    "log.uninstalling": "Desinstalando...",
    "log.uninstalled": "ReShade removido ({count} arquivos).",
    "log.downloading_nwjs": "Baixando NW.js... {done:.1f} / {total:.1f} MB",
    "log.updating_nwjs": "Atualizando NW.js...",
    "log.nwjs_updated": "NW.js atualizado para {version} ({arch}).",
    "log.restoring_nwjs": "Restaurando NW.js...",
    "log.nwjs_restored": "NW.js original restaurado ({count} arquivos).",
    "log.error": "Erro: {message}",
    "log.already_in_library": "“{name}” já está na biblioteca.",
    "log.game_added": "Adicionado: {name} ({engine}).",
    "log.game_uninstalled_removed": "“{name}” desinstalado e removido.",
    "log.game_removed": "Jogo removido da biblioteca.",
    "log.launching": "Iniciando {exe}{detail}",
    "log.detection_updated": "Detecção atualizada.",
    "log.settings_saved": "Configurações salvas.",
    # -- settings dialog -------------------------------------------------
    "settings.title": "Configurações — AniShade",
    "settings.general_card": "Geral",
    "settings.language": "Idioma",
    "settings.language_hint": "Idioma da interface. As alterações são aplicadas imediatamente ao salvar.",
    "settings.reshade_card": "ReShade",
    "settings.nwjs_card": "NW.js (RPG Maker MV/MZ)",
    "settings.urm_card": "Universal Ren'Py Mod (Ren'Py)",
    "settings.defaults_card": "Padrões para novos jogos",
    "settings.version_used": "Versão usada",
    "settings.download_now": "Baixar / atualizar agora",
    "settings.prune_old": "Remover versões antigas",
    "settings.open_cache": "Abrir pasta de cache",
    "settings.variant": "Variante",
    "settings.default_top_margin": "Margem superior padrão",
    "settings.default_top_margin_tooltip": (
        "Pixels do topo ignorados (barra de título em jogos NW.js). 0 em fullscreen."
    ),
    "settings.create_launcher": "Criar launcher .bat com correções do engine",
    "settings.rpgm_hide_textbox": "Instalar plugin para ocultar caixa de texto (tecla H) no RPG Maker MV/MZ",
    "settings.rpgm_no_alt": "Impedir tecla Alt / Alt+Tab de pular texto no RPG Maker MV/MZ",
    "settings.rpgm_save_slots": "Expandir para 100 slots de save no RPG Maker MV/MZ",
    "settings.renpy_urm": "Instalar Universal Ren'Py Mod (0x52_URM.rpa) em novos jogos Ren'Py",
    "settings.app_data": "Dados do app: {path}",
    "settings.about": (
        "AniShade não redistribui binários. O ReShade é baixado de reshade.me, "
        "o NW.js é baixado de dl.nwjs.io, o Universal Ren'Py Mod é baixado de 0x52.dev "
        "(todos reutilizados via cache local), e os shaders Anime4K (bloc97/Anime4K, MIT) "
        "acompanham o aplicativo.\n"
        "Pressione Home no jogo para abrir o overlay do ReShade e ajustar o preset."
    ),
    "settings.reshade_cache_present": "Versões no cache local: {versions}.\nPasta: {folder}",
    "settings.reshade_cache_empty": (
        "Nenhuma versão do ReShade baixada ainda. Ela será obtida em reshade.me "
        "na primeira instalação (ou clique em 'Baixar / atualizar agora')."
    ),
    "settings.reshade_latest_option": "Mais recente (baixa se necessário)",
    "settings.cached_suffix": "{version} (em cache)",
    "settings.preferred_suffix": " — preferida",
    "settings.nwjs_cache_present": "Versões no cache local: {versions}.\nPasta: {folder}",
    "settings.nwjs_cache_empty": (
        "Nenhuma versão do NW.js baixada ainda. Ele será baixado de nwjs.io uma única vez "
        "e reutilizado em todos os jogos RPG Maker MV/MZ."
    ),
    "settings.stable_latest_option": "Mais recente estável (baixa se necessário)",
    "settings.nwjs_cached_item": "{version} ({bits} bits, em cache)",
    "settings.urm_cache_present": "Versões no cache local: {versions}.\nPasta: {folder}",
    "settings.urm_cache_empty": (
        "Nenhuma versão do Universal Ren'Py Mod baixada ainda. Ele será obtido em 0x52.dev "
        "uma única vez ao ativar o interruptor em um jogo Ren'Py."
    ),
    "settings.downloading_progress": "Baixando... {done:.1f} / {total:.1f} MB",
    "settings.reshade_ready": "ReShade {version} pronto em {folder}",
    "settings.download_failed": "Falha: {message}",
    "settings.download_failed_title": "Falha no download",
    "settings.nwjs_already_latest": "NW.js {version} já é a versão estável mais recente em cache.",
    "settings.nwjs_downloading_progress": "Baixando NW.js... {done:.1f} / {total:.1f} MB",
    "settings.nwjs_ready": "NW.js {version} ({bits} bits) pronto no cache.",
    "settings.nwjs_download_failed_title": "Falha no download do NW.js",
    "settings.urm_already_latest": "Universal Ren'Py Mod {version} já é a versão estável mais recente em cache.",
    "settings.urm_downloading_progress": "Baixando URM... {done:.1f} / {total:.1f} MB",
    "settings.urm_ready": "Universal Ren'Py Mod {version} pronto no cache.",
    "settings.urm_download_failed_title": "Falha no download do Universal Ren'Py Mod",
    "settings.pruned": "Removidas: {items}",
    "settings.download_in_progress_title": "Download em andamento",
    "settings.download_in_progress_body": "Aguarde o download terminar antes de fechar.",
    # -- anime4k variants ------------------------------------------------
    "variant.cnn_s.label": "Restore CNN S (leve)",
    "variant.cnn_s.desc": "Menor rede neural: reconstrói detalhes com custo baixo. Boa para GPUs integradas e telas pequenas.",
    "variant.cnn_m.label": "Restore CNN M (equilibrado)",
    "variant.cnn_m.desc": "Equilíbrio entre nitidez e desempenho. Recomendado para a maioria das visual novels em 720p/768p.",
    "variant.cnn_l.label": "Restore CNN L (nítido)",
    "variant.cnn_l.desc": "Reconstrução mais forte de linhas e texturas. Indicado para VNs em 1080p.",
    "variant.cnn_vl.label": "Restore CNN VL (muito nítido)",
    "variant.cnn_vl.desc": "Rede maior: mais detalhe em arte de alta resolução, custo de GPU alto.",
    "variant.cnn_ul.label": "Restore CNN UL (máximo)",
    "variant.cnn_ul.desc": "Maior rede disponível. Qualidade máxima, uso de VRAM/GPU muito alto.",
    "variant.soft_s.label": "Restore CNN Soft S (suave)",
    "variant.soft_s.desc": "Versão suavizada do CNN S: menos ringing/halo em traços finos e compressão pesada.",
    "variant.soft_m.label": "Restore CNN Soft M (suave)",
    "variant.soft_m.desc": "CNN Soft M: bom para VNs com arte suave, gradientes e fundos desfocados.",
    "variant.soft_l.label": "Restore CNN Soft L (suave)",
    "variant.soft_l.desc": "CNN Soft L: detalhe alto com transições mais naturais. Indicado para 1080p.",
    "variant.soft_vl.label": "Restore CNN Soft VL (suave)",
    "variant.soft_vl.desc": "CNN Soft VL: alta resolução sem exagerar no realce de bordas.",
    "variant.soft_ul.label": "Restore CNN Soft UL (suave)",
    "variant.soft_ul.desc": "CNN Soft UL: variante mais suave da rede máxima, para 4K sem artefatos agressivos.",
    "anime4k.missing_fx": "Shaders ReShade FX ausentes no pacote do AniShade: {files}",
    # -- engines ---------------------------------------------------------
    "engine.unknown.name": "Desconhecida",
    "engine.renpy.note1": "Ren'Py desenha com OpenGL (renderer gl2) ou ANGLE/Direct3D 9 (renderer angle2).",
    "engine.renpy.note2": "Se o overlay não aparecer, troque entre opengl32.dll (gl2) e d3d9.dll (angle2).",
    "engine.renpy.note3": "A resolução interna costuma ser baixa: os shaders Restore do Anime4K são ideais aqui.",
    "engine.renpy.fix_hint": "Forçar OpenGL (gl2) ao iniciar pelo AniShade e criar um .bat com a variável RENPY_RENDERER.",
    "engine.rpgmaker_mv.note1": "MV/MZ rodam dentro do NW.js (Chromium) usando ANGLE sobre Direct3D 11.",
    "engine.rpgmaker_mv.note2": "Use dxgi.dll. Se o overlay não aparecer, tente d3d11.dll (o Chromium também carrega esse nome).",
    "engine.rpgmaker_mv.note3": "Evite marcar 'Performance Mode' em jogos MV: o overlay precisa do contexto do Chromium.",
    "engine.rpgmaker_mv.fix_hint": "Renomear a DLL do ReShade para d3d11.dll quando dxgi.dll não for carregada.",
    "engine.rpgmaker_rgss.note1": "RGSS usa Direct3D 9; a DLL correta é d3d9.dll.",
    "engine.rpgmaker_rgss.note2": "Alguns jogos trazem um d3d9.dll próprio (ENB/RT). Nesse caso verifique conflitos primeiro.",
    "engine.rpgmaker_rgss.fix_hint": "Verificar conflito com d3d9.dll de terceiros antes de instalar.",
    "engine.rpgmaker_2000.note1": "RPG Maker 2000/2003 desenha com DirectDraw; o ReShade usa ddraw.dll.",
    "engine.rpgmaker_2000.note2": "Em Windows modernos o jogo pode precisar de compatibilidade; teste sem o ReShade antes.",
    "engine.yuris.note1": "YU-RIS usa Direct3D 9. Comum em VNs japonesas com arquivos .ypf.",
    "engine.catsystem2.note1": "CatSystem2 usa Direct3D 9 (arquivos .cst/.int).",
    "engine.reallive.note1": "RealLive usa Direct3D 9; jogos antigos costumam ser 32 bits.",
    "engine.livemaker.note1": "LiveMaker usa Direct3D 9.",
    "engine.cmvs.note1": "CMVS usa Direct3D 9 (arquivos .cpz).",
    "engine.nitroplus.note1": "Engine Nitroplus usa Direct3D 9 (arquivos .npk).",
    "engine.kirikiri.note1": "KiriKiri (KAG) usa Direct3D 9 na maioria dos builds.",
    "engine.kirikiri.note2": "Se o jogo travar ao abrir com ReShade, tente desativar o overlay de entrada pelo ReShade.ini.",
    "engine.siglus.note1": "SiglusEngine usa Direct3D 9. Alguns títulos antigos precisam de d3d9.dll de 32 bits.",
    "engine.bgi.note1": "BGI/Ethornell usa Direct3D 9; o motor costuma rodar em 32 bits.",
    "engine.nscripter.note1": "NScripter antigo usa DirectDraw/Direct3D 9; ONScripter usa SDL (OpenGL ou Direct3D).",
    "engine.nscripter.note2": "A API é detectada pelas importações do .exe; confira o campo API antes de instalar.",
    "engine.wolf.note1": "WOLF RPG Editor usa Direct3D 9 (d3d9.dll).",
    "engine.unity.note1": "Unity usa Direct3D 11 por padrão; dxgi.dll é o nome recomendado.",
    "engine.unity.note2": "Jogos Unity costumam precisar de 'Copy depth buffer' desligado (ReShade 6 já cuida disso).",
    "engine.unity.note3": "Se o jogo usar Vulkan, o ReShade não carrega por proxy DLL: inicie com -force-d3d11.",
    "engine.unity.fix_hint": "Criar launcher com -force-d3d11 quando o jogo abrir em Vulkan.",
    "engine.unreal.note1": "Unreal Engine 4/5 usa Direct3D 11/12 (dxgi.dll).",
    "engine.unreal.note2": "Em UE5 com Lumen/Nanite o custo do Anime4K pode ficar alto; prefira variantes S/M.",
    "engine.godot.note1": "Godot 3 usa OpenGL 3 (opengl32.dll); Godot 4 usa Vulkan por padrão.",
    "engine.godot.note2": "Para Godot 4 use o launcher com '--rendering-driver opengl3' para permitir o ReShade.",
    "engine.godot.fix_hint": "Iniciar com --rendering-driver opengl3 e instalar opengl32.dll.",
    "engine.gamemaker.note1": "GameMaker moderno usa Direct3D 11 (dxgi.dll).",
    "engine.artemis.note1": "Artemis usa Direct3D 9.",
    "engine.majiro.note1": "Majiro usa Direct3D 9.",
    "engine.unknown.note1": "Engine não reconhecida: a API foi inferida pelas importações do executável.",
    # -- engine match evidence -------------------------------------------
    "evidence.renpy_dir": "pasta renpy/ ou arquivos .rpyc/.rpa",
    "evidence.renpy_lib": "lib/py3-* (runtime Python do Ren'Py)",
    "evidence.renpy_files": "arquivos .rpy/.rpyc/.rpa",
    "evidence.rpgm_core": "js/rmmz_core.js (MV/MZ)",
    "evidence.rpgm_www": "pasta www/ + NW.js",
    "evidence.rpgm_pkg": "package.json + index.html (NW.js)",
    "evidence.rgss_dll": "{name} (RGSS)",
    "evidence.rgss_data": "Game.ini + data/ (RPG Maker)",
    "evidence.rpgm2k": "RPG_RT.exe / .ldb (RPG Maker 2000/2003)",
    "evidence.yuris": "arquivos .ypf (YU-RIS)",
    "evidence.catsystem2": "arquivos .cst/.int (CatSystem2)",
    "evidence.reallive": "arquivos .g00 (RealLive)",
    "evidence.livemaker": "arquivos .lsb (LiveMaker)",
    "evidence.cmvs": "arquivos .cpz (CMVS)",
    "evidence.nitroplus": "arquivos .npk (Nitroplus)",
    "evidence.kirikiri_xp3": "arquivos .xp3",
    "evidence.kirikiri_dir": "pasta kirikiri2/ ou krkr.exe",
    "evidence.unity_data": "pasta *_Data/ (Unity)",
    "evidence.godot_pck": "arquivo .pck",
    "evidence.artemis": "arquivos .pfs/.arg (Artemis)",
    # -- detect ----------------------------------------------------------
    "detect.pe_read_error": "Não foi possível ler o cabeçalho do executável ({error}).",
    "detect.manual_engine": "engine definida manualmente: {name}",
    "detect.godot4_note": "Godot 4 detectado: abra pelo botão Jogar (ou pelo .bat) para forçar OpenGL 3.",
    "detect.godot4_warn": "Godot 4 usa Vulkan por padrão. Abrir o .exe direto pode impedir o ReShade de carregar.",
    "detect.godot3_note": "Godot 3 detectado: renderiza em OpenGL 3 (opengl32.dll).",
    "detect.content_size_note": (
        "Resolução interna detectada: {w}x{h}. "
        "A tela inteira é filtrada; a proteção contra ruído/feedback nas bordas é automática no shader."
    ),
    "detect.rpgm_plugin_note": "Plugin {name} (tecla H para ocultar caixa de texto) disponível em {path}.",
    "detect.api_source.default": "padrão",
    "detect.api_source.manual": "definida manualmente",
    "detect.api_source.log": "log do ReShade",
    "detect.api_source.imports": "importações do executável",
    "detect.api_source.engine": "engine detectada",
    "detect.api_source.godot4": "Godot 4 com launcher OpenGL",
    "detect.api_source.fallback": "padrão (não detectada)",
    "detect.api_source.angle": "bibliotecas ANGLE na pasta do jogo",
    "detect.warn_vulkan": (
        "Vulkan detectado: ReShade não carrega por proxy DLL. "
        "Inicie o jogo em Direct3D 11/OpenGL (ex.: -force-d3d11) ou use a injeção global do ReShade."
    ),
    "detect.warn_32bit": "Jogo de 32 bits: o ReShade32.dll será usado (limitação de memória do processo).",
    "detect.warn_is_dll": "O arquivo selecionado é uma DLL, não um executável.",
    "detect.warn_no_arch": "Sem informações de arquitetura: será assumido 64 bits.",
    "detect.warn_launcher": "'{name}' parece um launcher/configurador. Prefira o executável real do jogo.",
    "detect.note_many_exes": "Existem muitos .exe nessa pasta; confirme que o escolhido é o que abre o jogo de fato.",
    "detect.warn_conflicts": (
        "Já existe DLL com nome de proxy na pasta ({dlls}). "
        "O AniShade usa outro nome quando possível e nunca sobrescreve sem confirmação."
    ),
    "detect.warn_not_writable": "A pasta do jogo não permite escrita sem privilégios de administrador.",
    # -- installer -------------------------------------------------------
    "installer.no_write_perm": (
        "Sem permissão para escrever em {folder}.\n"
        "Feche o jogo e execute o AniShade como administrador."
    ),
    "installer.write_failed": "Falha ao gravar {name}: {error}",
    "installer.conflict_forced": "{name} já existe na pasta do jogo e não é o ReShade.",
    "installer.no_proxy_dll": "API sem DLL de proxy conhecida.",
    "installer.conflict_all": (
        "Todas as DLLs de proxy para esta API já existem e pertencem a outro programa:\n"
        "{list}\n\n"
        "Renomeie/remova o conflito ou escolha outro nome de DLL no campo 'DLL proxy'."
    ),
    "installer.exe_not_found": "Executável não encontrado: {exe}",
    "installer.game_running_install": "{exe} está em execução. Feche o jogo antes de instalar ou atualizar o ReShade.",
    "installer.vulkan_unsupported": (
        "API Vulkan detectada. O ReShade não pode ser carregado por proxy DLL neste jogo.\n"
        "Inicie o jogo em Direct3D 11/OpenGL ou use a injeção global do ReShade."
    ),
    "installer.using_reshade_dll": "Usando {dll} do ReShade {version}.",
    "installer.proxy_dll": "DLL de proxy: {dll}",
    "installer.splash_hidden": "Splash inicial e spinner de carregamento ocultados na DLL do ReShade.",
    "installer.splash_hide_warn": "Aviso: não foi possível ocultar o splash nesta versão do ReShade.",
    "installer.old_dll_removed": "DLL antiga removida: {path}",
    "installer.copying_shaders": "Copiando shader ReShade FX: {files}",
    "installer.no_shader_perm": (
        "Sem permissão para escrever os shaders em {folder}.\n"
        "Execute o AniShade como administrador."
    ),
    "installer.preset_backed_up": "Preset editado no jogo foi salvo em backup.",
    "installer.launcher_warn": "Aviso: não foi possível criar o launcher .bat ({error}).",
    "installer.rpgm_plugin_installed": "Plugin RPG Maker instalado: {path}.",
    "installer.warning_prefix": "Aviso: {warning}",
    "installer.rpgm_plugin_removed": "Plugin RPG Maker removido: {files}.",
    "installer.urm_installed": "Universal Ren'Py Mod {version} instalado em {path}.",
    "installer.urm_install_warn": "Não foi possível instalar o Universal Ren'Py Mod: {error}",
    "installer.urm_install_log_warn": "Aviso: falha ao instalar Universal Ren'Py Mod ({error}).",
    "installer.urm_removed": "Universal Ren'Py Mod removido: {files}.",
    "installer.done": "Instalação concluída.",
    "installer.no_manifest": (
        "Não há registro de instalação do AniShade para este jogo. "
        "Nada foi removido para não apagar arquivos de terceiros."
    ),
    "installer.game_running_uninstall": "Feche o jogo antes de desinstalar.",
    "installer.modified_backed_up": "Arquivo modificado preservado em backup: {backup}",
    "installer.remove_failed": "Não foi possível remover {path}: {error}",
    "installer.ini_modified_backed_up": "ReShade.ini modificado preservado em backup: {backup}",
    "installer.ini_restored": "ReShade.ini original restaurado.",
    "installer.ini_restore_failed": "Falha ao restaurar ReShade.ini: {error}",
    "installer.reshade_removed": "ReShade removido do jogo.",
    "installer.problem_dll": "DLL do ReShade ausente ou modificada.",
    "installer.problem_preset_edited": "Preset foi editado dentro do jogo (normal se você ajustou na mão).",
    "installer.problem_preset_missing": "Preset AniShade.ini ausente.",
    "installer.problem_shaders_missing": "Shaders Anime4K ausentes; use 'Reinstalar'.",
    "installer.unknown_rpgm_plugin": "Plugin RPG Maker desconhecido: {key}",
    "installer.game_running_plugin": "{exe} está em execução. Feche o jogo antes de alterar o plugin.",
    "installer.plugins_js_missing": "Arquivo plugins.js não encontrado neste jogo.",
    "installer.plugin_enabled": "Plugin {file} ativado em {path}.",
    "installer.plugin_removed": "Plugin {file} removido do jogo.",
    "installer.game_running_urm": "{exe} está em execução. Feche o jogo antes de alterar o Universal Ren'Py Mod.",
    "installer.renpy_game_dir_missing": "Pasta 'game/' do Ren'Py não encontrada ao lado do executável.",
    "installer.renpy_game_dir_missing_short": "Pasta 'game/' do Ren'Py não encontrada.",
    "installer.urm_enabled": "Universal Ren'Py Mod {version} ativado em {path}.",
    "installer.urm_removed_list": "Universal Ren'Py Mod removido ({files}).",
    "installer.urm_disabled": "Universal Ren'Py Mod desativado.",
    "installer.dll_realigned": "DLL do ReShade ({dll}) atualizada para {bits} bits.",
    "installer.reshade_reinstall_needed": "ReShade instalado precisa ser reinstalado ({error}).",
    # -- reshade ---------------------------------------------------------
    "reshade.fetch_failed": "Não foi possível acessar reshade.me: {error}",
    "reshade.no_link": "Não encontrei um link de download do ReShade na página oficial.",
    "reshade.setup_cached": "Instalador do ReShade {version} já está no cache.",
    "reshade.downloading": "Baixando ReShade {version} de reshade.me ...",
    "reshade.download_failed": "Falha ao baixar o ReShade: {error}",
    "reshade.download_incomplete": "O download do ReShade veio incompleto.",
    "reshade.downloaded": "ReShade {version} baixado ({mb:.1f} MB).",
    "reshade.setup_too_small": "Arquivo do instalador muito pequeno para ser o ReShade Setup.",
    "reshade.invalid_dll": "{name} extraído não parece uma DLL válida.",
    "reshade.dlls_not_found": (
        "Não encontrei as DLLs dentro do instalador do ReShade. "
        "Baixe novamente em https://reshade.me."
    ),
    "reshade.using_cached": "Usando ReShade {version} do cache local.",
    "reshade.no_cache_offline": "Nenhuma versão do ReShade está no cache e a rede está desativada.",
    "reshade.checking_latest": "Consultando a versão mais recente do ReShade ...",
    "reshade.offline_fallback": "Sem conexão com reshade.me; usando a versão em cache.",
    "reshade.extracting": "Extraindo ReShade32.dll e ReShade64.dll do instalador ...",
    "reshade.dll_missing_cache": "{name} não encontrado no cache do ReShade.",
    "reshade.dll_corrupt_cache": "{name} no cache está corrompido. Remova {folder} e baixe novamente.",
    # -- nwjs ------------------------------------------------------------
    "nwjs.invalid_version": "Versão do NW.js inválida.",
    "nwjs.fetch_failed": "Não foi possível consultar nwjs.io: {error}",
    "nwjs.no_version": "Não encontrei uma versão válida do NW.js em nwjs.io/versions.json.",
    "nwjs.invalid_zip": "Arquivo ZIP do NW.js inválido: {error}",
    "nwjs.empty_zip": "Arquivo ZIP do NW.js está vazio.",
    "nwjs.missing_binaries": "O arquivo ZIP baixado não contém nw.exe e nw.dll.",
    "nwjs.archive_cached": "Pacote NW.js {version} ({arch}) já está no cache de downloads.",
    "nwjs.downloading": "Baixando NW.js {version} ({arch}) de dl.nwjs.io ...",
    "nwjs.download_failed": "Falha ao baixar o NW.js: {error}",
    "nwjs.download_incomplete": "O download do NW.js veio incompleto.",
    "nwjs.sha_mismatch": (
        "Checksum SHA-256 do pacote NW.js não confere com o oficial em dl.nwjs.io. "
        "Tente baixar novamente."
    ),
    "nwjs.downloaded": "NW.js {version} baixado ({mb:.1f} MB).",
    "nwjs.extracting": "Extraindo NW.js {version} para o cache local ...",
    "nwjs.extract_incomplete": "Extração do NW.js incompleta (nw.exe ou nw.dll ausente).",
    "nwjs.using_cached": "Usando NW.js {version} ({arch}) do cache local.",
    "nwjs.no_cache_offline": "Nenhuma versão do NW.js está no cache e a rede está desativada.",
    "nwjs.checking_latest": "Consultando a versão estável mais recente do NW.js em nwjs.io ...",
    "nwjs.offline_fallback": "Sem conexão com nwjs.io; usando o NW.js em cache.",
    "nwjs.invalid_package_json": "package.json inválido ({name}): {error}",
    "nwjs.invalid_package_root": "package.json inválido ({name}): raiz não é um objeto JSON.",
    "nwjs.fix_chromium_args_list": "chromium-args convertido de lista para string",
    "nwjs.fix_autoplay": "adicionado --autoplay-policy=no-user-gesture-required (evita áudio mudo)",
    "nwjs.fix_js_flags": "removidas flags V8 obsoletas de js-flags ({flags})",
    "nwjs.fix_set_name": 'definido "name": "{name}" em package.json',
    "nwjs.fix_missing_name": 'corrigido "name" ausente/inválido para "{name}"',
    "nwjs.fix_main": 'corrigido "main" para "{main}"',
    "nwjs.fix_window_dim": "convertido window.{dim} para inteiro",
    "nwjs.fix_window_icon": 'corrigido window.icon para "{icon}"',
    "nwjs.fix_remove_icon": "removido window.icon apontando para arquivo inexistente",
    "nwjs.fix_compat_shim": "adicionado shim de compatibilidade process.mainModule para MV/plugins antigos",
    "nwjs.fix_www_bom": "normalizado JSON/BOM em www/package.json",
    "nwjs.fix_root_from_www": "criado package.json na raiz a partir de www/package.json",
    "nwjs.fix_root_bom": "normalizado JSON/BOM em package.json",
    "nwjs.fix_root_default": "criado package.json padrão na raiz",
    "nwjs.game_running_update": "{exe} está em execução. Feche o jogo antes de atualizar o NW.js.",
    "nwjs.backing_up": "Fazendo backup dos arquivos originais do NW.js ...",
    "nwjs.applying": "Aplicando NW.js {version} ({arch}) em {folder} ...",
    "nwjs.reshade_preserved": "{file} pertence ao ReShade e foi preservada.",
    "nwjs.fixing_package_json": "Verificando e corrigindo package.json ...",
    "nwjs.updated_log": "NW.js atualizado para {version} ({bits} bits).",
    "nwjs.no_backup": "Não há backup do NW.js original para este jogo.",
    "nwjs.game_running_restore": "{exe} está em execução. Feche o jogo antes de restaurar o NW.js.",
    "nwjs.restored_log": "NW.js original restaurado ({count} arquivos).",
    # -- rpgmaker --------------------------------------------------------
    "rpgmaker_mod.array_not_found": "Array $plugins não encontrado em plugins.js.",
    "rpgmaker_mod.plugins_js_not_found": (
        "Arquivo plugins.js não encontrado (jogo compactado ou estrutura NW.js não padrão): "
        "plugin {file} não foi instalado."
    ),
    "rpgmaker_mod.decode_failed": (
        "Não foi possível decodificar plugins.js (codificação desconhecida): "
        "plugin {file} não foi instalado."
    ),
    "rpgmaker_mod.plugins_js_restored": "plugins.js original restaurado.",
    "rpgmaker_mod.plugins_js_backed_up": "plugins.js modificado preservado em backup: {backup}",
    "rpgmaker_mod.entry_removed": "Entrada {name} removida de plugins.js.",
    "rpgmaker_mod.clean_failed": "Não foi possível limpar plugins.js: {error}",
    "rpgmaker_mod.plugin_backed_up": "Plugin modificado preservado em backup: {backup}",
    "rpgmaker_mod.remove_failed": "Não foi possível remover {path}: {error}",
    "rpgmaker_mod.problem_missing": "Plugin RPG Maker ({file}) ausente; use 'Reinstalar'.",
    "rpgmaker_mod.problem_inactive": "Plugin {name} não está ativo em plugins.js; use 'Reinstalar'.",
    # -- renpy -----------------------------------------------------------
    "renpy_mod.fetch_failed": "Não foi possível consultar 0x52.dev: {error}",
    "renpy_mod.unexpected_api": "Resposta inesperada da API do 0x52.dev.",
    "renpy_mod.no_release": "Nenhuma versão disponível do Universal Ren'Py Mod foi encontrada em 0x52.dev.",
    "renpy_mod.rpa_not_found": "Arquivo {filename} não encontrado dentro do ZIP baixado de 0x52.dev.",
    "renpy_mod.invalid_zip": "Arquivo ZIP do Universal Ren'Py Mod inválido ou corrompido: {error}",
    "renpy_mod.invalid_rpa": "{filename} extraído não parece um arquivo .rpa válido do Ren'Py.",
    "renpy_mod.archive_cached": "Pacote Universal Ren'Py Mod {version} já está no cache de downloads.",
    "renpy_mod.downloading": "Baixando Universal Ren'Py Mod {version} de 0x52.dev ...",
    "renpy_mod.download_failed": "Falha ao baixar o Universal Ren'Py Mod: {error}",
    "renpy_mod.downloaded": "Universal Ren'Py Mod {version} baixado ({mb:.1f} MB).",
    "renpy_mod.using_cached": "Usando Universal Ren'Py Mod {version} do cache local.",
    "renpy_mod.no_cache_offline": "Nenhuma versão do Universal Ren'Py Mod está no cache e a rede está desativada.",
    "renpy_mod.checking_latest": "Consultando a versão mais recente do Universal Ren'Py Mod em 0x52.dev ...",
    "renpy_mod.offline_fallback": "Sem conexão com 0x52.dev; usando a versão em cache.",
    "renpy_mod.extracting": "Extraindo {filename} ...",
    "renpy_mod.rpa_missing_cache": "{filename} não encontrado no cache local.",
    "renpy_mod.rpa_corrupt_cache": "{filename} no cache está corrompido. Remova {folder} e baixe novamente.",
    "renpy_mod.game_dir_missing": "Pasta 'game/' do Ren'Py não encontrada ao lado do executável.",
    "renpy_mod.modified_backed_up": "{filename} modificado foi salvo em backup antes de remover: {backup}",
    "renpy_mod.remove_failed": "Não foi possível remover {filename}: {error}",
    "renpy_mod.problem_missing": "Mod Universal Ren'Py Mod ({filename}) ausente na pasta game/.",
    # -- pe --------------------------------------------------------------
    "pe.unknown_arch": "desconhecido",
    "pe.empty_file": "arquivo vazio: {path}",
    "pe.read_oob": "leitura fora do arquivo",
    "pe.too_small": "arquivo pequeno demais para ser um executável",
    "pe.no_mz": "assinatura MZ ausente",
    "pe.no_pe": "assinatura PE ausente",
    "pe.unknown_magic": "formato PE desconhecido (magic 0x{magic:x})",
    # -- cli -------------------------------------------------------------
    "cli.info.exe": "Executável ....: {value}",
    "cli.info.name": "Nome ..........: {value}",
    "cli.info.engine": "Engine ........: {name}  ({evidence})",
    "cli.info.arch": "Arquitetura ...: {bits} bits",
    "cli.info.api": "API ...........: {label}  [{source}]",
    "cli.info.dll": "DLL proxy .....: {dll}  (alternativas: {alts})",
    "cli.info.content": "Conteúdo ......: {size}  aspecto {aspect:.3f}",
    "cli.info.content_none": "não detectado",
    "cli.info.reshade": "ReShade atual .: {value}",
    "cli.info.rpgm_plugin": "Plugin RPGM ...: {path} (ocultar caixa de texto com H)",
    "cli.info.nwjs": "NW.js atual ...: {value}",
    "cli.info.renpy_urm": "Mod Ren'Py ....: {dir}/{file} ({state})",
    "cli.info.active": "ativo",
    "cli.info.notes": "Notas:",
    "cli.info.warnings": "Avisos:",
    "cli.variants.header": "Variantes Restore do Anime4K (ReShade FX):",
    "cli.variants.weight": "peso {weight}x",
    "cli.cache.ready": "Cache pronto: ReShade {version} em {folder}",
    "cli.install.header": "\nInstalado:",
    "cli.install.dll": "  DLL ..........: {value}",
    "cli.install.preset": "  Preset .......: {value}",
    "cli.install.shaders": "  Shaders ......: {value}",
    "cli.install.reshade": "  ReShade ......: {value}",
    "cli.install.techniques": "  Técnicas .....: {value}",
    "cli.install.rpgm_plugins": "  Plugins RPGM .: {value}",
    "cli.install.renpy_urm": "  Mod Ren'Py ...: {value}{ver}",
    "cli.install.launcher": "  Launcher .....: {value}",
    "cli.uninstall.not_found": "Jogo não está na biblioteca do AniShade.",
    "cli.uninstall.done": "Removidos {count} arquivos.",
    "cli.list.empty": "Biblioteca vazia.",
    "cli.list.installed": "instalado",
    "cli.list.pending": "pendente",
    "cli.plugin.enabled": "Plugin ativado: {path}",
    "cli.plugin.disabled": "Plugin desativado.",
    "cli.nwjs.cache_ready": "Cache pronto: NW.js {version} ({arch}) em {folder}",
    "cli.nwjs.updated": "\nNW.js atualizado para {version} ({arch}).",
    "cli.nwjs.restored": "Restaurados {count} arquivos originais.",
    "cli.urm.cache_ready": "Cache pronto: Universal Ren'Py Mod {version} em {folder}",
    "cli.urm.enabled": "Universal Ren'Py Mod ativado: {path}",
    "cli.urm.disabled": "Universal Ren'Py Mod desativado.",
    "cli.error_prefix": "ERRO: {error}",
    "cli.help.info": "analisa um executável",
    "cli.help.install": "instala ReShade + Anime4K",
    "cli.help.top_margin": "pixels do topo a ignorar (barra de título)",
    "cli.help.aspect": "proporção do conteúdo (ex.: 1.5); 0 desativa",
    "cli.help.no_hide_textbox": "não instala o plugin de ocultar caixa de texto (tecla H) em jogos RPG Maker MV/MZ",
    "cli.help.no_alt_skip": "não instala o plugin que impede Alt/Alt+Tab de pular texto em jogos RPG Maker MV/MZ",
    "cli.help.no_save_slots": "não instala o plugin que expande para 100 slots de save em jogos RPG Maker MV/MZ",
    "cli.help.renpy_urm": "instala ou remove o Universal Ren'Py Mod (0x52_URM.rpa) em jogos Ren'Py",
    "cli.help.uninstall": "remove o ReShade instalado pelo AniShade",
    "cli.help.variants": "lista as variantes disponíveis",
    "cli.help.cache": "gerencia o cache do ReShade",
    "cli.help.list": "lista os jogos da biblioteca",
    "cli.help.engines": "lista engines reconhecidas",
    "cli.help.plugin": "ativa ou remove plugins RPG Maker MV/MZ do AniShade",
    "cli.help.plugin_choice": "qual plugin alternar (padrão: hide_textbox)",
    "cli.help.plugin_disable": "remove o plugin do jogo",
    "cli.help.nwjs": "gerencia e atualiza o NW.js em jogos RPG Maker MV/MZ",
    "cli.help.nwjs_update": "atualiza o NW.js do jogo e corrige package.json",
    "cli.help.nwjs_restore": "restaura o NW.js original do backup",
    "cli.help.nwjs_cache": "lista ou baixa o NW.js oficial para o cache",
    "cli.help.urm": "gerencia o Universal Ren'Py Mod (0x52.dev) em jogos Ren'Py",
    "cli.help.urm_enable": "instala 0x52_URM.rpa na pasta game/ do jogo Ren'Py",
    "cli.help.urm_disable": "remove 0x52_URM.rpa do jogo Ren'Py",
    "cli.help.urm_cache": "lista ou baixa o Universal Ren'Py Mod para o cache",
}


_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": _EN,
    "pt_BR": _PT_BR,
}
