# AniShade

**ReShade + Anime4K Restore manager for visual novels and Japanese games.**

A lightweight desktop manager: point AniShade to a game's `.exe`, and it detects the engine and
graphics API, installs ReShade with **Anime4K Restore**, and generates a ready-to-use preset.
ReShade is downloaded once from the official site and cached locally for all games.

![Main window](docs/screenshot.png)

## Features

- **Add games by executable** (or drag and drop the `.exe` onto the window).
- **Automatic engine & graphics API detection** by inspecting the PE import table and game files
  (Ren'Py, RPG Maker MV/MZ, RGSS, KiriKiri/XP3, SiglusEngine, BGI, YU-RIS, CatSystem2, RealLive,
  LiveMaker, CMVS, Nitroplus, WOLF, NScripter, Artemis, Unity, Unreal, GameMaker, Godot).
- **Download ReShade once** from `reshade.me`, extract `ReShade32.dll`/`ReShade64.dll` from the
  installer, and reuse the local cache across all games (works offline afterward).
- **Correct proxy DLL selection**: `dxgi.dll`, `d3d9.dll`, `opengl32.dll`, or `ddraw.dll`,
  with automatic fallback (`d3d11.dll`/`d3d12.dll`) when another DLL already occupies the name.
- **ReShade FX shaders** (`.fx`) and auto-generated `AniShade.ini` preset with the selected
  technique enabled.
- **Clean uninstall**: only removes files created by AniShade using SHA-256 verification.
  User-modified files and pre-existing `ReShade.ini` files are backed up and restored.
- **Per-engine fixes**: optional `.bat` launcher with recommended environment variables
  (`RENPY_RENDERER`, etc.) and conflict warnings (ENB, Special K, DXVK, wrong launcher, Vulkan,
  non-writable folders).
- **RPG Maker MV/MZ plugins**: instant toggles right on the game panel (and automatic install
  with ReShade) with clean `plugins.js` backup and restore:
  - `AniShade_HideTextbox.js` — press **H** to hide/show the message textbox;
  - `AniShade_NoAltSkip.js` — prevents `Alt` / `Alt+Tab` / `Alt+Enter` from skipping dialogue (keeps `Ctrl`);
  - `AniShade_SaveSlots100.js` — expands the save menu to **100 manual save slots** (MV and MZ).
- **Official NW.js updater**: downloads official NW.js (`nwjs.io` / `dl.nwjs.io`) once to local
  cache, reuses it across RPG Maker MV/MZ games, fixes common `package.json` issues (missing
  `name`, `--autoplay-policy`, obsolete V8 flags, `process.mainModule` compatibility), and lets you
  restore the original backup.
- **Universal Ren'Py Mod (URM) for Ren'Py games**: one-click toggle on Ren'Py games that downloads
  official `0x52_URM.rpa` from [0x52.dev](https://0x52.dev/mods/Universal-Ren-Py-Mod-1000) once to
  local cache and installs or removes `game/0x52_URM.rpa`.
- **Home opens the ReShade overlay** (configured in `ReShade.ini`).
- **No startup splash or resize spinner**: ReShade's startup banner ("ReShade 6.x...") and
  top-left loading spinner (when switching windowed/fullscreen) are hidden in the deployed DLL,
  and preset/tutorial/toast banners are disabled in `ReShade.ini`. Press **Home** anytime to open
  the overlay normally.
- **Localization**: English (default) and Brazilian Portuguese (`Português (Brasil)`), switchable
  instantly in **Settings → General → Language**.

## About the shaders (GLSL → ReShade FX)

The official Anime4K package is written in **GLSL for MPV/libplacebo**. ReShade **does not load
`.glsl`** — it only compiles its own ReShade FX (`.fx`) format. AniShade **converts the official
shaders** (`//!DESC`/`//!HOOK`/`//!SAVE` blocks + CNN weights) to `.fx`, adding:

- a **Copy** pass that snapshots the frame before filtering (preventing frame-to-frame feedback);
- `anishade_mul` instead of `float4x4` matrix multiplies (avoiding layout ambiguity);
- alpha forced to 1 on filtered pixels;
- **letterbox/pillarbox masking** by content aspect ratio, preserving black bars;
- configurable top margin for NW.js games whose swapchain includes the window title bar.

Shaders are regenerated from `vendor/anime4k/*.glsl` via `tools/build_fx.py`.
No third-party shader ports are downloaded: only the official `.glsl` sources (MIT, bloc97) are used.

## Requirements

- Windows 10/11 (64-bit).
- Python 3.10+ to run from source (or use the standalone `AniShade.exe` release).
- GPU with Direct3D 9/11 or OpenGL. For Vulkan, see [Limitations](#limitations).

## Run from source

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Also works via `python -m anishade`.

## Build the executable

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
# outputs dist\AniShade.exe (single-file, windowed)
```

For a portable folder (faster startup): `build_exe.ps1 -OneDir`.

## Usage

1. Click **Add Game** → select the `.exe` that launches the game (not a launcher/config tool).
2. Check **Engine**, **Graphics API**, and **Architecture**. If anything looks wrong, override it
   in the dropdowns (AniShade re-analyzes immediately).
3. Choose an **Anime4K Restore variant** matching the game's internal resolution.
4. Leave **Proxy DLL** on `Auto` in most cases; if another mod already uses `dxgi.dll`
   (Special K, DXVK, ENB), AniShade automatically selects `d3d11.dll`/`d3d12.dll` and shows the
   resolved name. You can also override it manually.
5. Click **Install ReShade + Anime4K**.
6. Launch the game and press **Home** to open the ReShade overlay.
7. To switch variants later, pick another one and click **Apply changes**
   (any manually edited preset is backed up first).

### Restore variants

Restore is the core Anime4K shader — it reconstructs lines and textures that the game upscaled
with bilinear/nearest filtering. **It does not upscale**; it runs at the final resolution and the
effect is subtle by design. To compare, open the overlay (Home) and toggle the technique on/off.

| Variant | Target internal resolution | GPU cost |
|---|---|---|
| Restore CNN S | 480p – 720p | 1x |
| Restore CNN M (default) | 720p – 900p | 2x |
| Restore CNN L | 900p – 1080p | 3x |
| Restore CNN VL | 1080p – 1440p | 5x |
| Restore CNN UL | 1440p – 4K | 8x |
| Restore CNN **Soft** S/M/L/VL/UL | same ranges | same |

**Soft** variants are less aggressive: ideal for soft artwork, gradients, and blurred backgrounds,
or when standard CNN accentuates ringing.

### Black bars and border feedback protection

NW.js/Chromium games (and other partial-swapchain compositors) often do not redraw letterbox/pillarbox
black bars (or the windowed title bar) every frame. Without protection, Anime4K's CNN would re-filter
its own output 60 times per second in those regions and create growing colored noise along the edges.

AniShade's `.fx` shaders include an **automatic 4-buffer temporal guard** (`texPrev1..4`): any pixel
whose backbuffer value still matches a previous shader output is passed through untouched, while
100% of the active game area receives full Anime4K restoration — without needing manual aspect cropping.

- **Content aspect ratio**: default `0` (full screen). Only change it if you want to manually
  restrict the shader region.
- **Top margin** (px): default `0`. Optional in windowed mode if you want to skip the title bar.

## Files created in the game folder

| File | Purpose |
|---|---|
| `dxgi.dll` / `d3d9.dll` / `opengl32.dll` / `ddraw.dll` | ReShade proxy DLL |
| `ReShade.ini` | ReShade configuration (merged without deleting existing keys) |
| `AniShade.ini` | Preset with the active technique and mask definitions |
| `reshade-shaders\Shaders\AniShade\*.fx` | Selected ReShade FX shader |
| `reshade-shaders\Shaders\AniShade\_anishade_shaders.json` | Installed shader manifest |
| `AniShade-Launch.bat` | Optional launcher with engine environment fixes |
| `(www\)js\plugins\AniShade_HideTextbox.js` | RPG Maker MV/MZ plugin to hide textbox with `H` |
| `(www\)js\plugins\AniShade_NoAltSkip.js` | RPG Maker MV/MZ plugin to stop `Alt` / `Alt+Tab` from skipping text |
| `(www\)js\plugins\AniShade_SaveSlots100.js` | RPG Maker MV/MZ plugin expanding to 100 manual save slots |
| `game\0x52_URM.rpa` | Universal Ren'Py Mod (optional, toggled per Ren'Py game) |

Each game's manifest is stored in `%LOCALAPPDATA%\AniShade\games\<id>.json` with file hashes,
allowing safe uninstallation without touching third-party files.

![Installation](docs/screenshot-install.png)

## Cache and data folders

- ReShade: `%LOCALAPPDATA%\AniShade\cache\reshade\<version>\`
- NW.js: `%LOCALAPPDATA%\AniShade\cache\nwjs\<version>-<arch>\`
- Universal Ren'Py Mod: `%LOCALAPPDATA%\AniShade\cache\urm\<version>\`
- Downloads: `%LOCALAPPDATA%\AniShade\cache\downloads\`
- Backups: `%LOCALAPPDATA%\AniShade\backups\<game>\`
- Logs: `%LOCALAPPDATA%\AniShade\logs\anishade.log` and `ReShade.log` in the game folder

## Troubleshooting

**The overlay doesn't open with Home**
- Check `ReShade.ini` → `[INPUT] KeyOverlay=36,0,0,0` (36 = Home).
- Some games capture keyboard input aggressively; check `InputProcessing=2` in `ReShade.ini`.

**Colored noise on the sides or title bar**
- Set **Content aspect ratio** to the actual aspect ratio (e.g. `1.5`) and/or **Top margin** to
  the title bar height (e.g. `31` in windowed mode).
- In fullscreen, keep Top margin at `0`. For 4:3 games, the aspect ratio is `1.3333`.

**The game opens, but nothing looks filtered**
- Restore is subtle; compare by toggling the technique on/off in the overlay (Home).
- Try a larger variant (L/VL) or check `ReShade.log` for
  `Successfully compiled ... Anime4K_Restore_...fx`.

**Vulkan**
- ReShade cannot load via proxy DLL on Vulkan. Launch the game in Direct3D 11/OpenGL
  (e.g. `-force-d3d11`) or use ReShade's global Vulkan injection.

## CLI (headless)

```powershell
python -m anishade.cli info "C:\Games\VN\game.exe"
python -m anishade.cli install "C:\Games\VN\game.exe" --variant cnn_m --aspect 1.5
python -m anishade.cli uninstall "C:\Games\VN\game.exe"
python -m anishade.cli variants
python -m anishade.cli cache --download
python -m anishade.cli list
```

## Limitations

- **Restore** shaders only (by design). Anime4K Denoise/Clamp/Upscalers are not included.
- **Vulkan** cannot be injected via proxy DLL.
- Does not manage ReShade add-ons (depth buffer, textures).
- Games with **anti-cheat** (EAC/BattlEye) may block or ban accounts with ReShade installed.
- If the selected `.exe` is only a launcher, ReShade won't be loaded by the actual game process.
- The preset is rewritten when switching variants; manual edits from the overlay are backed up first.

## Project layout

```
anishade/
  i18n.py          localization catalogs (English default + Brazilian Portuguese)
  pe.py            PE inspector (bitness, imports, delay imports)
  engines.py       engine fingerprints and recommended fixes
  detect.py        game analysis, API, content size, conflicts, existing ReShade
  glsl_to_fx.py    Anime4K GLSL -> ReShade FX translator (copy pass, guards)
  reshade.py       official ReShade download, DLL extraction & cache
  nwjs.py          official NW.js download, cache, runtime updater & package.json fixer
  rpgmaker.py      RPG Maker MV/MZ plugins & plugins.js patcher
  renpy.py         Universal Ren'Py Mod (0x52.dev) download, cache & installer
  anime4k.py       variant catalog, .fx deployment & preset builder
  installer.py     install/uninstall with manifest & backups
  store.py         game library and settings (atomic JSON)
  cli.py           headless CLI
  ui/              main window, theme, delegates, settings dialog
vendor/anime4k/     official GLSL sources v4.0.1 (MIT, bloc97)
vendor/anime4k_fx/  ReShade FX shaders generated by tools/build_fx.py
tests/              unit tests for PE, shaders, presets, INI, install, plugins, i18n
tools/              .fx builder, icon generator, fixtures & screenshots
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Credits and licenses

- **ReShade** — © crosire, BSD-3 license. AniShade **does not redistribute** binaries: it downloads
  the official installer from `reshade.me` and extracts the DLLs locally.
- **Anime4K** — © bloc97, MIT license. Official `.glsl` files are bundled (`vendor/anime4k`, v4.0.1)
  and `.fx` files are generated from them.
- **PySide6 / Qt** — LGPLv3.

AniShade's source code is MIT-licensed. Respect each game's terms of use and do not use ReShade in
anti-cheat protected games.
