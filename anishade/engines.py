"""Engine fingerprints, per-engine quirks and recommended fixes.

Everything here is heuristics plus community knowledge about how the engine
talks to the GPU, which is what decides the ReShade proxy DLL name.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Engine:
    key: str
    name: str
    api: str | None = None
    notes: tuple[str, ...] = ()
    env: tuple[tuple[str, str], ...] = ()
    args: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    fix_hint: str = ""


ENGINES: dict[str, Engine] = {
    "renpy": Engine(
        key="renpy",
        name="Ren'Py",
        api="opengl",
        notes=(
            "Ren'Py desenha com OpenGL (renderer gl2) ou ANGLE/Direct3D 9 (renderer angle2).",
            "Se o overlay nao aparecer, troque entre opengl32.dll (gl2) e d3d9.dll (angle2).",
            "A resolucao interna costuma ser baixa: os shaders Restore do Anime4K sao ideais aqui.",
        ),
        env=(("RENPY_RENDERER", "gl2"),),
        alternatives=("d3d9", "opengl"),
        fix_hint="Forcar OpenGL (gl2) ao iniciar pelo AniShade e criar um .bat com a variavel RENPY_RENDERER.",
    ),
    "rpgmaker_mv": Engine(
        key="rpgmaker_mv",
        name="RPG Maker MV/MZ (NW.js)",
        api="dxgi",
        notes=(
            "MV/MZ rodam dentro do NW.js (Chromium) usando ANGLE sobre Direct3D 11.",
            "Use dxgi.dll. Se o overlay nao aparecer, tente d3d11.dll (o Chromium tambem carrega esse nome).",
            "Evite marcar 'Performance Mode' em jogos MV: o overlay precisa do contexto do Chromium.",
        ),
        alternatives=("dxgi", "d3d11"),
        fix_hint="Renomear a DLL do ReShade para d3d11.dll quando dxgi.dll nao for carregada.",
    ),
    "rpgmaker_rgss": Engine(
        key="rpgmaker_rgss",
        name="RPG Maker XP/VX/VX Ace (RGSS)",
        api="d3d9",
        notes=(
            "RGSS usa Direct3D 9; a DLL correta e d3d9.dll.",
            "Alguns jogos trazem um d3d9.dll proprio (ENB/RT). Nesse caso use a alternativa d3d9.",
        ),
        alternatives=("d3d9",),
        fix_hint="Verificar conflito com d3d9.dll de terceiros antes de instalar.",
    ),
    "rpgmaker_2000": Engine(
        key="rpgmaker_2000",
        name="RPG Maker 2000/2003",
        api="ddraw",
        notes=(
            "RPG Maker 2000/2003 desenha com DirectDraw; o ReShade usa ddraw.dll.",
            "Em Windows modernos o jogo pode precisar de compatibilidade; teste sem o ReShade antes.",
        ),
        alternatives=("ddraw", "d3d9"),
    ),
    "yuris": Engine(
        key="yuris",
        name="YU-RIS",
        api="d3d9",
        notes=("YU-RIS usa Direct3D 9. Comum em VNs japonesas com arquivos .ypf.",),
        alternatives=("d3d9",),
    ),
    "catsystem2": Engine(
        key="catsystem2",
        name="CatSystem2",
        api="d3d9",
        notes=("CatSystem2 usa Direct3D 9 (arquivos .cst/.int).",),
        alternatives=("d3d9",),
    ),
    "reallive": Engine(
        key="reallive",
        name="RealLive (Key)",
        api="d3d9",
        notes=("RealLive usa Direct3D 9; jogos antigos costumam ser 32 bits.",),
        alternatives=("d3d9",),
    ),
    "livemaker": Engine(
        key="livemaker",
        name="LiveMaker",
        api="d3d9",
        notes=("LiveMaker usa Direct3D 9.",),
        alternatives=("d3d9",),
    ),
    "cmvs": Engine(
        key="cmvs",
        name="CMVS",
        api="d3d9",
        notes=("CMVS usa Direct3D 9 (arquivos .cpz).",),
        alternatives=("d3d9",),
    ),
    "nitroplus": Engine(
        key="nitroplus",
        name="Nitroplus",
        api="d3d9",
        notes=("Engine Nitroplus usa Direct3D 9 (arquivos .npk).",),
        alternatives=("d3d9",),
    ),
    "kirikiri": Engine(
        key="kirikiri",
        name="KiriKiri / KAG (XP3)",
        api="d3d9",
        notes=(
            "KiriKiri (KAG) usa Direct3D 9 na maioria dos builds.",
            "Se o jogo travar ao abrir com ReShade, tente desativar o overlay de entrada pelo ReShade.ini.",
        ),
        alternatives=("d3d9",),
    ),
    "siglus": Engine(
        key="siglus",
        name="SiglusEngine (Key/Visual Arts)",
        api="d3d9",
        notes=("SiglusEngine usa Direct3D 9. Alguns titulos antigos precisam de d3d9.dll de 32 bits.",),
        alternatives=("d3d9",),
    ),
    "bgi": Engine(
        key="bgi",
        name="BGI / Ethornell",
        api="d3d9",
        notes=("BGI/Ethornell usa Direct3D 9; o motor costuma rodar em 32 bits.",),
        alternatives=("d3d9",),
    ),
    "nscripter": Engine(
        key="nscripter",
        name="NScripter / ONScripter",
        api=None,
        notes=(
            "NScripter antigo usa DirectDraw/Direct3D 9; ONScripter usa SDL (OpenGL ou Direct3D).",
            "A API e detectada pelas importacoes do .exe; confira o campo API antes de instalar.",
        ),
        alternatives=("d3d9", "opengl", "ddraw"),
    ),
    "wolf": Engine(
        key="wolf",
        name="WOLF RPG Editor",
        api="d3d9",
        notes=("WOLF RPG Editor usa Direct3D 9 (d3d9.dll).",),
        alternatives=("d3d9",),
    ),
    "unity": Engine(
        key="unity",
        name="Unity",
        api="dxgi",
        notes=(
            "Unity usa Direct3D 11 por padrao; dxgi.dll e o nome recomendado.",
            "Jogos Unity costumam precisar de 'Copy depth buffer' desligado (ReShade 6 ja cuida disso).",
            "Se o jogo usar Vulkan, o ReShade nao carrega por proxy DLL: inicie com -force-d3d11.",
        ),
        alternatives=("dxgi", "d3d11"),
        fix_hint="Criar launcher com -force-d3d11 quando o jogo abrir em Vulkan.",
    ),
    "unreal": Engine(
        key="unreal",
        name="Unreal Engine",
        api="dxgi",
        notes=(
            "Unreal Engine 4/5 usa Direct3D 11/12 (dxgi.dll).",
            "Em UE5 com Lumen/Nanite o custo do Anime4K pode ficar alto; prefira variantes S/M.",
        ),
        alternatives=("dxgi", "d3d11"),
    ),
    "godot": Engine(
        key="godot",
        name="Godot",
        api=None,
        notes=(
            "Godot 3 usa OpenGL 3 (opengl32.dll); Godot 4 usa Vulkan por padrao.",
            "Para Godot 4 use o launcher com '--rendering-driver opengl3' para permitir o ReShade.",
        ),
        args=(),
        alternatives=("opengl", "dxgi"),
        fix_hint="Iniciar com --rendering-driver opengl3 e instalar opengl32.dll.",
    ),
    "gamemaker": Engine(
        key="gamemaker",
        name="GameMaker Studio",
        api="dxgi",
        notes=("GameMaker moderno usa Direct3D 11 (dxgi.dll).",),
        alternatives=("dxgi", "d3d9"),
    ),
    "artemis": Engine(
        key="artemis",
        name="Artemis Engine",
        api="d3d9",
        notes=("Artemis usa Direct3D 9.",),
        alternatives=("d3d9",),
    ),
    "majiro": Engine(
        key="majiro",
        name="Majiro",
        api="d3d9",
        notes=("Majiro usa Direct3D 9.",),
        alternatives=("d3d9",),
    ),
    "unknown": Engine(
        key="unknown",
        name="Desconhecida",
        api=None,
        notes=("Engine nao reconhecida: a API foi inferida pelas importacoes do executavel.",),
        alternatives=("dxgi", "d3d9", "opengl"),
    ),
}


@dataclass
class EngineContext:
    game_dir: Path
    exe: Path
    top_files: set[str] = field(default_factory=set)
    top_dirs: set[str] = field(default_factory=set)
    shallow_files: list[str] = field(default_factory=list)

    @classmethod
    def build(cls, game_dir: Path, exe: Path) -> EngineContext:
        names: set[str] = set()
        dirs: set[str] = set()
        shallow: list[str] = []
        try:
            with os.scandir(game_dir) as iterator:
                for entry in iterator:
                    if len(shallow) > 6000:
                        break
                    lowered = entry.name.lower()
                    if entry.is_dir(follow_symlinks=False):
                        dirs.add(lowered)
                        try:
                            with os.scandir(entry.path) as sub:
                                for sub_entry in sub:
                                    if sub_entry.is_file(follow_symlinks=False):
                                        shallow.append(sub_entry.name.lower())
                                    if len(shallow) > 6000:
                                        break
                        except OSError:
                            pass
                    else:
                        names.add(lowered)
        except OSError:
            pass
        return cls(game_dir=game_dir, exe=exe, top_files=names, top_dirs=dirs, shallow_files=shallow)

    # -- helpers ---------------------------------------------------------
    def has_file(self, *suffixes: str) -> bool:
        return any(name.endswith(suffix) for name in self.top_files for suffix in suffixes)

    def has_dir(self, *names: str) -> bool:
        return any(name in self.top_dirs for name in names)

    def any_glob(self, *patterns: str) -> str | None:
        for pattern in patterns:
            try:
                for match in self.game_dir.glob(pattern):
                    return match.name
            except (OSError, ValueError):
                pass
        return None


def _match_renpy(ctx: EngineContext) -> str | None:
    if ctx.has_dir("renpy") or ctx.any_glob("renpy/common/*.rpy", "game/*.rpyc", "game/*.rpa"):
        return "pasta renpy/ ou arquivos .rpyc/.rpa"
    if any(name.startswith(("lib/py3-", "lib/python")) for name in ctx.top_dirs):
        return "lib/py3-* (runtime Python do Ren'Py)"
    if ctx.has_file(".rpy", ".rpyc", ".rpa"):
        return "arquivos .rpy/.rpyc/.rpa"
    return None


def _match_rpgmaker_mv(ctx: EngineContext) -> str | None:
    if ctx.any_glob("www/js/rmmz_core.js", "www/js/rpg_core.js", "js/rmmz_core.js", "js/rpg_core.js"):
        return "js/rmmz_core.js (MV/MZ)"
    if ctx.has_dir("www") and (ctx.has_file("nw.dll", "package.json", "nw_elf.dll")):
        return "pasta www/ + NW.js"
    if ctx.has_file("package.json") and ctx.has_file("index.html"):
        return "package.json + index.html (NW.js)"
    return None


def _match_rgss(ctx: EngineContext) -> str | None:
    rgss = next((name for name in ctx.top_files if name.startswith("rgss") and name.endswith(".dll")), None)
    if rgss:
        return f"{rgss} (RGSS)"
    if ctx.has_file("game.ini", "game.rvproj2", "game.rxproj") and ctx.any_glob("data/*.rxdata", "data/*.rvdata", "data/*.rvdata2"):
        return "Game.ini + data/ (RPG Maker)"
    return None


def _match_rpgmaker_2000(ctx: EngineContext) -> str | None:
    if ctx.has_file("rpg_rt.exe", ".ldb"):
        return "RPG_RT.exe / .ldb (RPG Maker 2000/2003)"
    return None


def _match_yuris(ctx: EngineContext) -> str | None:
    if ctx.has_file(".ypf"):
        return "arquivos .ypf (YU-RIS)"
    return None


def _match_catsystem2(ctx: EngineContext) -> str | None:
    if ctx.has_file(".cst", ".noa") and ctx.has_file(".int", ".cst"):
        return "arquivos .cst/.int (CatSystem2)"
    return None


def _match_reallive(ctx: EngineContext) -> str | None:
    if ctx.has_file(".g00", "seen.txt"):
        return "arquivos .g00 (RealLive)"
    return None


def _match_livemaker(ctx: EngineContext) -> str | None:
    if ctx.has_file(".lsb"):
        return "arquivos .lsb (LiveMaker)"
    return None


def _match_cmvs(ctx: EngineContext) -> str | None:
    if ctx.has_file(".cpz"):
        return "arquivos .cpz (CMVS)"
    return None


def _match_nitroplus(ctx: EngineContext) -> str | None:
    if ctx.has_file(".npk"):
        return "arquivos .npk (Nitroplus)"
    return None


def _match_kirikiri(ctx: EngineContext) -> str | None:
    if ctx.has_file(".xp3"):
        return "arquivos .xp3"
    if ctx.has_dir("kirikiri2") or ctx.has_file("krkr.exe", "kirikiri.exe"):
        return "pasta kirikiri2/ ou krkr.exe"
    return None


def _match_siglus(ctx: EngineContext) -> str | None:
    if ctx.has_file("siglusengine.exe", "siglusengine.dll"):
        return "SiglusEngine"
    if ctx.has_file("scene.pck", "siglus.dat"):
        return "Scene.pck/Siglus.dat"
    return None


def _match_bgi(ctx: EngineContext) -> str | None:
    if ctx.has_file("bgi.exe", "bgi.gdb", "ethornell.dll"):
        return "BGI/Ethornell"
    return None


def _match_nscripter(ctx: EngineContext) -> str | None:
    if ctx.has_file("nscript.dat", ".nsa", ".ns2", ".nsc"):
        return "nscript.dat/.nsa"
    if ctx.has_file("onscript.exe", "onscripter.exe"):
        return "ONScripter"
    return None


def _match_wolf(ctx: EngineContext) -> str | None:
    if ctx.has_file("data.wolf") or ctx.has_file(".wolf"):
        return "Data.wolf"
    return None


def _match_unity(ctx: EngineContext) -> str | None:
    if ctx.has_file("unityplayer.dll", "unitycrashhandler64.exe", "unitycrashhandler32.exe"):
        return "UnityPlayer.dll"
    if any(name.endswith("_data") and name not in ("data",) for name in ctx.top_dirs):
        if ctx.any_glob("*_Data/globalgamemanagers", "*_Data/level0"):
            return "pasta *_Data/ (Unity)"
    return None


def _match_unreal(ctx: EngineContext) -> str | None:
    if ctx.has_dir("engine") or ctx.has_dir("binaries"):
        if ctx.any_glob("engine/binaries/*", "*.uproject", "*/*/content/paks/*.pak"):
            return "Engine/ + Content/Paks"
    return None


def _match_godot(ctx: EngineContext) -> str | None:
    if ctx.has_file(".pck") and not ctx.has_file(".xp3"):
        return "arquivo .pck"
    return None


def _match_gamemaker(ctx: EngineContext) -> str | None:
    if ctx.has_file("data.win", "game.unx"):
        return "data.win (GameMaker)"
    return None


def _match_artemis(ctx: EngineContext) -> str | None:
    if ctx.has_file(".pfs", ".arg", ".alf"):
        return "arquivos .pfs/.arg (Artemis)"
    return None


def _match_majiro(ctx: EngineContext) -> str | None:
    if ctx.has_file("mjotf") or ctx.has_file(".arc"):
        if ctx.has_file("mjotf"):
            return "mjotf (Majiro)"
    return None


_MATCHERS: list[tuple[str, object]] = [
    ("unity", _match_unity),
    ("unreal", _match_unreal),
    ("renpy", _match_renpy),
    ("rpgmaker_mv", _match_rpgmaker_mv),
    ("rpgmaker_rgss", _match_rgss),
    ("rpgmaker_2000", _match_rpgmaker_2000),
    ("yuris", _match_yuris),
    ("catsystem2", _match_catsystem2),
    ("reallive", _match_reallive),
    ("livemaker", _match_livemaker),
    ("cmvs", _match_cmvs),
    ("nitroplus", _match_nitroplus),
    ("kirikiri", _match_kirikiri),
    ("siglus", _match_siglus),
    ("bgi", _match_bgi),
    ("wolf", _match_wolf),
    ("artemis", _match_artemis),
    ("gamemaker", _match_gamemaker),
    ("godot", _match_godot),
    ("nscripter", _match_nscripter),
    ("majiro", _match_majiro),
]


def match_engine(ctx: EngineContext) -> tuple[Engine, list[str]]:
    """Return the best engine match plus the evidence used."""
    for key, matcher in _MATCHERS:
        try:
            evidence = matcher(ctx)  # type: ignore[operator]
        except Exception:
            evidence = None
        if evidence:
            return ENGINES[key], [evidence]
    return ENGINES["unknown"], []
