"""Game analysis: architecture, graphics API, ReShade state, engine quirks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import engines, nwjs, rpgmaker, winapi
from .pe import PEError, PEInfo, executable_strings, guess_api, read_pe

API_DLL = {
    "d3d9": "d3d9.dll",
    "dxgi": "dxgi.dll",
    "d3d11": "d3d11.dll",
    "d3d12": "d3d12.dll",
    "opengl": "opengl32.dll",
    "ddraw": "ddraw.dll",
    "vulkan": "vulkan-1.dll",
}

API_LABELS = {
    "d3d9": "Direct3D 9",
    "dxgi": "Direct3D 10/11/12 (DXGI)",
    "d3d11": "Direct3D 11",
    "d3d12": "Direct3D 12",
    "opengl": "OpenGL",
    "ddraw": "DirectDraw",
    "vulkan": "Vulkan",
    "desconhecida": "Desconhecida",
}

#: proxy DLL names ReShade can use for each API family
DLL_CHOICES = {
    "d3d9": ("d3d9.dll",),
    "dxgi": ("dxgi.dll", "d3d11.dll", "d3d12.dll"),
    "d3d11": ("d3d11.dll", "dxgi.dll"),
    "d3d12": ("d3d12.dll", "dxgi.dll"),
    "opengl": ("opengl32.dll",),
    "ddraw": ("ddraw.dll",),
    "vulkan": ("vulkan-1.dll",),
}

LAUNCHER_NAMES = {
    "launcher.exe",
    "launch.exe",
    "config.exe",
    "setup.exe",
    "unins000.exe",
    "unitycrashhandler64.exe",
    "unitycrashhandler32.exe",
    "crashreportclient.exe",
    "start.exe",
    "autorun.exe",
}

_LOG_API_PATTERNS = (
    (re.compile(r"Direct3D\s*9", re.I), "d3d9"),
    (re.compile(r"Direct3D\s*1[0-2]", re.I), "dxgi"),
    (re.compile(r"OpenGL", re.I), "opengl"),
    (re.compile(r"Vulkan", re.I), "vulkan"),
    (re.compile(r"DirectDraw", re.I), "ddraw"),
)


@dataclass
class GameAnalysis:
    exe: Path
    game_dir: Path
    pe: PEInfo | None = None
    engine: engines.Engine = engines.ENGINES["unknown"]
    engine_evidence: list[str] = field(default_factory=list)
    api: str = "dxgi"
    api_source: str = "padrao"
    dll_name: str = "dxgi.dll"
    dll_alternatives: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    args: list[str] = field(default_factory=list)
    display_name: str = ""
    file_description: str = ""
    exe_version: str = ""
    existing_reshade: bool = False
    existing_reshade_version: str = ""
    existing_reshade_dll: str = ""
    conflicting_dlls: list[str] = field(default_factory=list)
    other_executables: list[str] = field(default_factory=list)
    content_aspect: float = 0.0
    content_size: tuple[int, int] | None = None
    rpgmaker_plugins_js: str = ""
    nwjs_version: str = ""

    @property
    def is_64bit(self) -> bool:
        return bool(self.pe and self.pe.bits == 64)

    @property
    def bits(self) -> int:
        return self.pe.bits if self.pe else 0

    @property
    def supported(self) -> bool:
        return self.api != "vulkan"

    def suggested_name(self) -> str:
        if self.display_name:
            return self.display_name
        return self.exe.stem


def _api_from_log(game_dir: Path) -> str | None:
    for pattern in ("ReShade*.log", "reshade*.log"):
        for log in game_dir.glob(pattern):
            try:
                text = log.read_text(encoding="utf-8", errors="ignore")[:8000]
            except OSError:
                continue
            for regex, api in _LOG_API_PATTERNS:
                if regex.search(text):
                    return api
    return None


def is_reshade_dll(path: Path) -> bool:
    if not path.is_file():
        return False
    info = winapi.file_version_info(path)
    product = (info.get("ProductName") or "") + (info.get("FileDescription") or "")
    if "reshade" in product.lower():
        return True
    try:
        with open(path, "rb") as handle:
            blob = handle.read(3 * 1024 * 1024)
    except OSError:
        return False
    return b"ReShade.ini" in blob or b"reshade-shaders" in blob


def reshade_dll_version(path: Path) -> str:
    info = winapi.file_version_info(path)
    version = info.get("FileVersion") or ""
    match = re.search(r"\d+\.\d+\.\d+(?:\.\d+)?", version)
    if match:
        return match.group(0)
    try:
        with open(path, "rb") as handle:
            blob = handle.read(3 * 1024 * 1024)
        match = re.search(rb"(\d+\.\d+\.\d+)\x00", blob)
        if match:
            return match.group(1).decode("ascii", "ignore")
    except OSError:
        pass
    return ""


_GENERIC_NAMES = {
    "game",
    "game32",
    "game64",
    "game_x64",
    "game_x86",
    "game_en",
    "game_jp",
    "nw",
    "nwjs",
    "nw.js",
    "rpg_rt",
    "launcher",
    "launch",
    "start",
    "play",
    "application",
    "app",
    "setup",
    "main",
    "client",
    "player",
    "bin",
    "run",
    "krkr",
    "bgi",
    "advhd",
    "yuris",
    "renpy",
    "ren'py",
    "untitled",
    "project1",
}
_GENERIC_FOLDERS = {
    "bin",
    "binaries",
    "win64",
    "win32",
    "x64",
    "x86",
    "www",
    "game",
    "release",
    "build",
    "dist",
    "app",
}
_BAD_NAME_HINTS = (
    "microsoft",
    "windows",
    "operating system",
    "installer",
    "uninstall",
    "crashhandler",
    "redistributable",
    "todo:",
    "<file description>",
    "<product name>",
    "node-webkit",
    "nwjs",
    "nw.js",
    "chromium",
    "electron",
    "rgss player",
    "rpg maker",
    "rpgmv",
    "rpgmz",
    "unityplayer",
    "godot engine",
    "kirikiri",
    "siglusengine",
    "ethornell",
    "wolf rpg",
)


def _is_usable_name(candidate: str) -> bool:
    text = (candidate or "").strip()
    if not text:
        return False
    low = text.lower()
    stem = low[:-4] if low.endswith(".exe") else low
    if low in _GENERIC_NAMES or stem in _GENERIC_NAMES:
        return False
    if any(hint in low for hint in _BAD_NAME_HINTS):
        return False
    return True


def _folder_display_name(folder: Path) -> str:
    name = folder.name.strip()
    if name and name.lower() in _GENERIC_FOLDERS:
        parent = folder.parent
        if parent != folder and parent.name.strip():
            return parent.name.strip()
    return name


def _pick_display_name(product: str, description: str, exe: Path, folder: Path) -> str:
    """Choose a readable game name from the EXE, falling back to the folder name."""
    for candidate in (product, description):
        text = (candidate or "").strip()
        if _is_usable_name(text):
            return text
    folder_name = _folder_display_name(folder)
    if folder_name:
        return folder_name
    return exe.stem


def _detect_content_size(game_dir: Path) -> tuple[int, int] | None:
    """Best-effort content resolution for NW.js/RPG Maker and Ren'Py games."""
    package = game_dir / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8", errors="ignore"))
            window = data.get("window") or {}
            width = int(window.get("width") or 0)
            height = int(window.get("height") or 0)
            if 200 <= width <= 10000 and 200 <= height <= 10000:
                return width, height
        except (OSError, ValueError, TypeError):
            pass
    for pattern in ("www/js/rmmz_core.js", "www/js/rpg_core.js", "js/rmmz_core.js", "js/rpg_core.js"):
        candidate = game_dir / pattern
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")[:8000]
        except OSError:
            continue
        width_match = re.search(r"Graphics\.width\s*=\s*(\d+)", text)
        height_match = re.search(r"Graphics\.height\s*=\s*(\d+)", text)
        if width_match and height_match:
            return int(width_match.group(1)), int(height_match.group(1))
    return None


def analyze(exe: str | Path, api_override: str | None = None, engine_override: str | None = None) -> GameAnalysis:
    exe = Path(exe).resolve()
    game_dir = exe.parent
    analysis = GameAnalysis(exe=exe, game_dir=game_dir)

    try:
        analysis.pe = read_pe(exe)
    except (PEError, OSError) as exc:
        analysis.warnings.append(f"Nao foi possivel ler o cabecalho do executavel ({exc}).")

    version = winapi.file_version_info(exe)
    analysis.file_description = version.get("FileDescription", "") or ""
    analysis.exe_version = version.get("FileVersion", "") or ""
    analysis.display_name = _pick_display_name(
        version.get("ProductName", "") or "",
        analysis.file_description,
        exe,
        game_dir,
    )
    for marker in ("package.json",):
        candidate = game_dir / marker
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8", errors="ignore"))
            title = str((data.get("window") or {}).get("title") or "").strip()
        except (OSError, ValueError, TypeError):
            title = ""
        if _is_usable_name(title):
            analysis.display_name = title
        break

    ctx = engines.EngineContext.build(game_dir, exe)
    engine, evidence = engines.match_engine(ctx)
    if engine_override and engine_override in engines.ENGINES:
        engine = engines.ENGINES[engine_override]
        evidence = [f"engine definida manualmente: {engine.name}"]
    analysis.engine = engine
    analysis.engine_evidence = evidence
    analysis.notes = list(engine.notes)
    analysis.env = dict(engine.env)
    analysis.args = list(engine.args)

    if engine.key == "godot" and not engine_override:
        markers = executable_strings(exe, ["godot engine v4", "godot engine v3"])
        if "godot engine v4" in markers:
            analysis.args = ["--rendering-driver", "opengl3"]
            analysis.notes.append(
                "Godot 4 detectado: abra pelo botão Jogar (ou pelo .bat) para forçar OpenGL 3."
            )
            analysis.warnings.append(
                "Godot 4 usa Vulkan por padrão. Abrir o .exe direto pode impedir o ReShade de carregar."
            )
        elif "godot engine v3" in markers:
            analysis.notes.append("Godot 3 detectado: renderiza em OpenGL 3 (opengl32.dll).")

    size = _detect_content_size(game_dir)
    if size:
        analysis.content_size = size
        analysis.notes.append(
            f"Resolução interna detectada: {size[0]}x{size[1]}. "
            "A tela inteira é filtrada; a proteção contra ruído/feedback nas bordas é automática no shader."
        )

    if rpgmaker.is_supported_engine(engine.key):
        analysis.nwjs_version = nwjs.detect_game_nwjs_version(game_dir, exe)
        js_dir = rpgmaker.find_js_dir(game_dir)
        if js_dir is not None:
            try:
                analysis.rpgmaker_plugins_js = (js_dir / "plugins.js").relative_to(game_dir).as_posix()
            except ValueError:
                analysis.rpgmaker_plugins_js = str(js_dir / "plugins.js")
            analysis.notes.append(
                f"Plugin {rpgmaker.PLUGIN_NAME} (tecla H para ocultar caixa de texto) disponível em {analysis.rpgmaker_plugins_js}."
            )

    pe_api = guess_api(analysis.pe) if analysis.pe else None
    log_api = _api_from_log(game_dir)

    api = None
    if api_override:
        api = api_override
        analysis.api_source = "definida manualmente"
    elif log_api and log_api != "vulkan":
        api = log_api
        analysis.api_source = "log do ReShade"
    elif pe_api:
        api = pe_api
        analysis.api_source = "importacoes do executavel"
    elif engine.api:
        api = engine.api
        analysis.api_source = "engine detectada"
    elif engine.key == "godot" and analysis.args:
        api = "opengl"
        analysis.api_source = "Godot 4 com launcher OpenGL"
    else:
        api = "dxgi"
        analysis.api_source = "padrao (nao detectada)"

    # Ren'Py picks its renderer at runtime: ANGLE libs next to the exe mean D3D9.
    if engine.key == "renpy" and not api_override:
        has_angle = (game_dir / "libEGL.dll").is_file() or (game_dir / "libGLESv2.dll").is_file()
        if has_angle and api in ("opengl", "dxgi") and not pe_api:
            api = "d3d9"
            analysis.api_source = "bibliotecas ANGLE na pasta do jogo"
            analysis.env["RENPY_RENDERER"] = "angle2"
        elif not has_angle:
            analysis.env["RENPY_RENDERER"] = "gl2"

    if api == "d3d11" and not api_override:
        api = "dxgi"
    analysis.api = api

    choices = DLL_CHOICES.get(api, ("dxgi.dll",))
    analysis.dll_name = choices[0]
    analysis.dll_alternatives = list(choices[1:])

    if analysis.api == "vulkan":
        analysis.warnings.append(
            "Vulkan detectado: ReShade nao carrega por proxy DLL. "
            "Inicie o jogo em Direct3D 11/OpenGL (ex.: -force-d3d11) ou use a injecao global do ReShade."
        )

    if analysis.pe:
        if analysis.pe.bits == 32:
            analysis.warnings.append("Jogo de 32 bits: o ReShade32.dll sera usado (limitacao de memoria do processo).")
        if analysis.pe.is_dll:
            analysis.warnings.append("O arquivo selecionado e uma DLL, nao um executavel.")
    else:
        analysis.warnings.append("Sem informacoes de arquitetura: sera assumido 64 bits.")

    if exe.name.lower() in LAUNCHER_NAMES:
        analysis.warnings.append(
            f"'{exe.name}' parece um launcher/configurador. Prefira o executavel real do jogo."
        )

    try:
        executables = sorted(
            entry.name
            for entry in game_dir.iterdir()
            if entry.is_file() and entry.suffix.lower() == ".exe"
        )
    except OSError:
        executables = []
    analysis.other_executables = [name for name in executables if name.lower() != exe.name.lower()]
    if len(analysis.other_executables) > 6:
        analysis.notes.append(
            "Existem muitos .exe nessa pasta; confirme que o escolhido e o que abre o jogo de fato."
        )

    # Existing ReShade install / name conflicts
    for candidate in (*choices, "ReShade64.dll", "ReShade32.dll"):
        path = game_dir / candidate
        if not path.is_file():
            continue
        if is_reshade_dll(path):
            analysis.existing_reshade = True
            analysis.existing_reshade_version = analysis.existing_reshade_version or reshade_dll_version(path)
            analysis.existing_reshade_dll = analysis.existing_reshade_dll or candidate
        else:
            analysis.conflicting_dlls.append(candidate)

    if analysis.conflicting_dlls:
        analysis.warnings.append(
            "Ja existe DLL com nome de proxy na pasta ("
            + ", ".join(analysis.conflicting_dlls)
            + "). O AniShade usa outro nome quando possivel e nunca sobrescreve sem confirmacao."
        )

    if not winapi.folder_writable(game_dir):
        analysis.warnings.append(
            "A pasta do jogo nao permite escrita sem privilegios de administrador."
        )

    return analysis
