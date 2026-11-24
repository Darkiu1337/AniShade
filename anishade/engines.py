"""Engine fingerprints, per-engine quirks and recommended fixes.

Everything here is heuristics plus community knowledge about how the engine
talks to the GPU, which is what decides the ReShade proxy DLL name.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import tr


@dataclass(frozen=True)
class Engine:
    key: str
    _name: str
    api: str | None = None
    _note_keys: tuple[str, ...] = ()
    env: tuple[tuple[str, str], ...] = ()
    args: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    _fix_hint_key: str = ""

    @property
    def name(self) -> str:
        if self.key == "unknown":
            return tr("engine.unknown.name")
        return self._name

    @property
    def notes(self) -> tuple[str, ...]:
        return tuple(tr(key) for key in self._note_keys)

    @property
    def fix_hint(self) -> str:
        return tr(self._fix_hint_key) if self._fix_hint_key else ""


ENGINES: dict[str, Engine] = {
    "renpy": Engine(
        key="renpy",
        _name="Ren'Py",
        api="opengl",
        _note_keys=("engine.renpy.note1", "engine.renpy.note2", "engine.renpy.note3"),
        env=(("RENPY_RENDERER", "gl2"),),
        alternatives=("d3d9", "opengl"),
        _fix_hint_key="engine.renpy.fix_hint",
    ),
    "rpgmaker_mv": Engine(
        key="rpgmaker_mv",
        _name="RPG Maker MV/MZ (NW.js)",
        api="dxgi",
        _note_keys=("engine.rpgmaker_mv.note1", "engine.rpgmaker_mv.note2", "engine.rpgmaker_mv.note3"),
        alternatives=("dxgi", "d3d11"),
        _fix_hint_key="engine.rpgmaker_mv.fix_hint",
    ),
    "rpgmaker_rgss": Engine(
        key="rpgmaker_rgss",
        _name="RPG Maker XP/VX/VX Ace (RGSS)",
        api="d3d9",
        _note_keys=("engine.rpgmaker_rgss.note1", "engine.rpgmaker_rgss.note2"),
        alternatives=("d3d9",),
        _fix_hint_key="engine.rpgmaker_rgss.fix_hint",
    ),
    "rpgmaker_2000": Engine(
        key="rpgmaker_2000",
        _name="RPG Maker 2000/2003",
        api="ddraw",
        _note_keys=("engine.rpgmaker_2000.note1", "engine.rpgmaker_2000.note2"),
        alternatives=("ddraw", "d3d9"),
    ),
    "yuris": Engine(
        key="yuris",
        _name="YU-RIS",
        api="d3d9",
        _note_keys=("engine.yuris.note1",),
        alternatives=("d3d9",),
    ),
    "catsystem2": Engine(
        key="catsystem2",
        _name="CatSystem2",
        api="d3d9",
        _note_keys=("engine.catsystem2.note1",),
        alternatives=("d3d9",),
    ),
    "reallive": Engine(
        key="reallive",
        _name="RealLive (Key)",
        api="d3d9",
        _note_keys=("engine.reallive.note1",),
        alternatives=("d3d9",),
    ),
    "livemaker": Engine(
        key="livemaker",
        _name="LiveMaker",
        api="d3d9",
        _note_keys=("engine.livemaker.note1",),
        alternatives=("d3d9",),
    ),
    "cmvs": Engine(
        key="cmvs",
        _name="CMVS",
        api="d3d9",
        _note_keys=("engine.cmvs.note1",),
        alternatives=("d3d9",),
    ),
    "nitroplus": Engine(
        key="nitroplus",
        _name="Nitroplus",
        api="d3d9",
        _note_keys=("engine.nitroplus.note1",),
        alternatives=("d3d9",),
    ),
    "kirikiri": Engine(
        key="kirikiri",
        _name="KiriKiri / KAG (XP3)",
        api="d3d9",
        _note_keys=("engine.kirikiri.note1", "engine.kirikiri.note2"),
        alternatives=("d3d9",),
    ),
    "siglus": Engine(
        key="siglus",
        _name="SiglusEngine (Key/Visual Arts)",
        api="d3d9",
        _note_keys=("engine.siglus.note1",),
        alternatives=("d3d9",),
    ),
    "bgi": Engine(
        key="bgi",
        _name="BGI / Ethornell",
        api="d3d9",
        _note_keys=("engine.bgi.note1",),
        alternatives=("d3d9",),
    ),
    "nscripter": Engine(
        key="nscripter",
        _name="NScripter / ONScripter",
        api=None,
        _note_keys=("engine.nscripter.note1", "engine.nscripter.note2"),
        alternatives=("d3d9", "opengl", "ddraw"),
    ),
    "wolf": Engine(
        key="wolf",
        _name="WOLF RPG Editor",
        api="d3d9",
        _note_keys=("engine.wolf.note1",),
        alternatives=("d3d9",),
    ),
    "unity": Engine(
        key="unity",
        _name="Unity",
        api="dxgi",
        _note_keys=("engine.unity.note1", "engine.unity.note2", "engine.unity.note3"),
        alternatives=("dxgi", "d3d11"),
        _fix_hint_key="engine.unity.fix_hint",
    ),
    "unreal": Engine(
        key="unreal",
        _name="Unreal Engine",
        api="dxgi",
        _note_keys=("engine.unreal.note1", "engine.unreal.note2"),
        alternatives=("dxgi", "d3d11"),
    ),
    "godot": Engine(
        key="godot",
        _name="Godot",
        api=None,
        _note_keys=("engine.godot.note1", "engine.godot.note2"),
        args=(),
        alternatives=("opengl", "dxgi"),
        _fix_hint_key="engine.godot.fix_hint",
    ),
    "gamemaker": Engine(
        key="gamemaker",
        _name="GameMaker Studio",
        api="dxgi",
        _note_keys=("engine.gamemaker.note1",),
        alternatives=("dxgi", "d3d9"),
    ),
    "artemis": Engine(
        key="artemis",
        _name="Artemis Engine",
        api="d3d9",
        _note_keys=("engine.artemis.note1",),
        alternatives=("d3d9",),
    ),
    "majiro": Engine(
        key="majiro",
        _name="Majiro",
        api="d3d9",
        _note_keys=("engine.majiro.note1",),
        alternatives=("d3d9",),
    ),
    "unknown": Engine(
        key="unknown",
        _name="Unknown",
        api=None,
        _note_keys=("engine.unknown.note1",),
        alternatives=("dxgi", "d3d9", "opengl"),
    ),
}


def engine_display_name(engine_key: str, fallback: str = "") -> str:
    """Return the localized display name for an engine key."""
    engine = ENGINES.get(engine_key)
    if engine is not None:
        return engine.name
    return fallback or tr("engine.unknown.name")


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
        return tr("evidence.renpy_dir")
    if any(name.startswith(("lib/py3-", "lib/python")) for name in ctx.top_dirs):
        return tr("evidence.renpy_lib")
    if ctx.has_file(".rpy", ".rpyc", ".rpa"):
        return tr("evidence.renpy_files")
    return None


def _match_rpgmaker_mv(ctx: EngineContext) -> str | None:
    if ctx.any_glob("www/js/rmmz_core.js", "www/js/rpg_core.js", "js/rmmz_core.js", "js/rpg_core.js"):
        return tr("evidence.rpgm_core")
    if ctx.has_dir("www") and (ctx.has_file("nw.dll", "package.json", "nw_elf.dll")):
        return tr("evidence.rpgm_www")
    if ctx.has_file("package.json") and ctx.has_file("index.html"):
        return tr("evidence.rpgm_pkg")
    return None


def _match_rgss(ctx: EngineContext) -> str | None:
    rgss = next((name for name in ctx.top_files if name.startswith("rgss") and name.endswith(".dll")), None)
    if rgss:
        return tr("evidence.rgss_dll", name=rgss)
    if ctx.has_file("game.ini", "game.rvproj2", "game.rxproj") and ctx.any_glob("data/*.rxdata", "data/*.rvdata", "data/*.rvdata2"):
        return tr("evidence.rgss_data")
    return None


def _match_rpgmaker_2000(ctx: EngineContext) -> str | None:
    if ctx.has_file("rpg_rt.exe", ".ldb"):
        return tr("evidence.rpgm2k")
    return None


def _match_yuris(ctx: EngineContext) -> str | None:
    if ctx.has_file(".ypf"):
        return tr("evidence.yuris")
    return None


def _match_catsystem2(ctx: EngineContext) -> str | None:
    if ctx.has_file(".cst", ".noa") and ctx.has_file(".int", ".cst"):
        return tr("evidence.catsystem2")
    return None


def _match_reallive(ctx: EngineContext) -> str | None:
    if ctx.has_file(".g00", "seen.txt"):
        return tr("evidence.reallive")
    return None


def _match_livemaker(ctx: EngineContext) -> str | None:
    if ctx.has_file(".lsb"):
        return tr("evidence.livemaker")
    return None


def _match_cmvs(ctx: EngineContext) -> str | None:
    if ctx.has_file(".cpz"):
        return tr("evidence.cmvs")
    return None


def _match_nitroplus(ctx: EngineContext) -> str | None:
    if ctx.has_file(".npk"):
        return tr("evidence.nitroplus")
    return None


def _match_kirikiri(ctx: EngineContext) -> str | None:
    if ctx.has_file(".xp3"):
        return tr("evidence.kirikiri_xp3")
    if ctx.has_dir("kirikiri2") or ctx.has_file("krkr.exe", "kirikiri.exe"):
        return tr("evidence.kirikiri_dir")
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
            return tr("evidence.unity_data")
    return None


def _match_unreal(ctx: EngineContext) -> str | None:
    if ctx.has_dir("engine") or ctx.has_dir("binaries"):
        if ctx.any_glob("engine/binaries/*", "*.uproject", "*/*/content/paks/*.pak"):
            return "Engine/ + Content/Paks"
    return None


def _match_godot(ctx: EngineContext) -> str | None:
    if ctx.has_file(".pck") and not ctx.has_file(".xp3"):
        return tr("evidence.godot_pck")
    return None


def _match_gamemaker(ctx: EngineContext) -> str | None:
    if ctx.has_file("data.win", "game.unx"):
        return "data.win (GameMaker)"
    return None


def _match_artemis(ctx: EngineContext) -> str | None:
    if ctx.has_file(".pfs", ".arg", ".alf"):
        return tr("evidence.artemis")
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
