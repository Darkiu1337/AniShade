"""Headless interface, useful for testing and for power users.

Examples:
    python -m anishade.cli info "C:\\Games\\VN\\game.exe"
    python -m anishade.cli install "C:\\Games\\VN\\game.exe" --variant cnn_m
    python -m anishade.cli uninstall "C:\\Games\\VN\\game.exe"
    python -m anishade.cli cache
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import anime4k, detect, engines, i18n, installer, nwjs, renpy, reshade
from .i18n import tr
from .store import Game, Store, game_id_for


def _print_analysis(analysis: detect.GameAnalysis) -> None:
    print(tr("cli.info.exe", value=analysis.exe))
    print(tr("cli.info.name", value=analysis.suggested_name()))
    evidence = "; ".join(analysis.engine_evidence) or tr("detection.default_heuristic")
    print(tr("cli.info.engine", name=analysis.engine.name, evidence=evidence))
    print(tr("cli.info.arch", bits=analysis.bits or "?"))
    print(tr("cli.info.api", label=detect.api_label(analysis.api), source=analysis.api_source))
    alts = ", ".join(analysis.dll_alternatives) or tr("common.none")
    print(tr("cli.info.dll", dll=analysis.dll_name, alts=alts))
    size_text = analysis.content_size or tr("cli.info.content_none")
    print(tr("cli.info.content", size=size_text, aspect=analysis.content_aspect or 0))
    reshade_val = analysis.existing_reshade_version or tr("detection.not_installed_lower")
    print(tr("cli.info.reshade", value=reshade_val))
    if analysis.rpgmaker_plugins_js:
        print(tr("cli.info.rpgm_plugin", path=analysis.rpgmaker_plugins_js))
    if analysis.nwjs_version:
        print(tr("cli.info.nwjs", value=analysis.nwjs_version))
    if analysis.renpy_game_dir:
        urm_state = tr("cli.info.active") if renpy.is_urm_active(analysis.game_dir) else tr("detection.not_installed_lower")
        print(tr("cli.info.renpy_urm", dir=analysis.renpy_game_dir, file=renpy.URM_FILENAME, state=urm_state))
    if analysis.notes:
        print(tr("cli.info.notes"))
        for note in analysis.notes:
            print(f"  - {note}")
    if analysis.warnings:
        print(tr("cli.info.warnings"))
        for warning in analysis.warnings:
            print(f"  ! {warning}")


def cmd_info(args: argparse.Namespace) -> int:
    analysis = detect.analyze(args.exe, args.api, args.engine)
    _print_analysis(analysis)
    return 0


def cmd_variants(_: argparse.Namespace) -> int:
    print(tr("cli.variants.header"))
    for variant in anime4k.VARIANTS:
        cost = tr("cli.variants.weight", weight=variant.weight)
        print(f"  {variant.key:<10} {variant.label:<32} {variant.resolution:<14} {cost}")
    return 0


def cmd_cache(args: argparse.Namespace) -> int:
    if args.download or not reshade.list_cached():
        release = reshade.ensure_release(
            args.version or None,
            progress=lambda done, total: None,
            status=lambda message: print(f"* {message}"),
        )
        print(tr("cli.cache.ready", version=release.version, folder=release.folder))
    for item in reshade.list_cached():
        print(f"  {item.version:<10} {item.folder}")
    return 0


def _game_from_store(store: Store, exe: Path, args: argparse.Namespace) -> Game:
    analysis = detect.analyze(exe, getattr(args, "api", None), getattr(args, "engine", None))
    game = store.find_by_exe(exe)
    if game is None:
        game = Game(
            id=game_id_for(exe),
            name=analysis.suggested_name(),
            exe=str(exe),
            variant=args.variant or store.settings.default_variant,
            top_margin=args.top_margin or store.settings.default_top_margin,
            content_aspect=args.aspect if args.aspect is not None else -1.0,
        )
    game.engine_key = analysis.engine.key
    game.engine_name = analysis.engine.name
    game.api = analysis.api
    game.dll_name = analysis.dll_name
    game.bits = analysis.bits or 64
    game.engine_override = args.engine or ""
    game.api_override = args.api or ""
    game.detected = {
        "evidence": analysis.engine_evidence,
        "warnings": analysis.warnings,
        "notes": analysis.notes,
    }
    store.add_or_update(game)
    return game


def cmd_install(args: argparse.Namespace) -> int:
    exe = Path(args.exe).resolve()
    store = Store()
    game = _game_from_store(store, exe, args)
    analysis = detect.analyze(exe, args.api, args.engine)
    aspect = args.aspect if args.aspect is not None else (
        game.content_aspect if game.content_aspect >= 0 else analysis.content_aspect
    )
    options = installer.InstallOptions(
        variant=args.variant or game.variant,
        top_margin=args.top_margin or game.top_margin,
        content_aspect=aspect,
        dll_name=args.dll or "",
        reshade_version=args.reshade or "",
        create_launcher=not args.no_launcher,
        rpgmaker_hide_textbox=not args.no_hide_textbox,
        rpgmaker_no_alt_skip=not args.no_alt_skip_plugin,
        rpgmaker_save_slots_100=not args.no_save_slots_plugin,
        renpy_urm=game.renpy_urm if args.renpy_urm is None else bool(args.renpy_urm),
        urm_version=store.settings.urm_version,
    )
    report = installer.install(
        store,
        game,
        options,
        status=lambda message: print(f"* {message}"),
    )
    print(tr("cli.install.header"))
    print(tr("cli.install.dll", value=report.dll_path))
    print(tr("cli.install.preset", value=report.preset_path))
    print(tr("cli.install.shaders", value=report.shader_dir))
    print(tr("cli.install.reshade", value=report.reshade_version))
    print(tr("cli.install.techniques", value=", ".join(report.techniques)))
    if report.rpgmaker_plugins:
        print(tr("cli.install.rpgm_plugins", value=", ".join(report.rpgmaker_plugins)))
    if report.renpy_urm:
        ver_suffix = f" (v{report.renpy_urm_version})" if report.renpy_urm_version else ""
        print(tr("cli.install.renpy_urm", value=report.renpy_urm, ver=ver_suffix))
    if report.launcher:
        print(tr("cli.install.launcher", value=report.launcher))
    for warning in report.warnings:
        print(f"  ! {warning}")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    exe = Path(args.exe).resolve()
    store = Store()
    game = store.find_by_exe(exe)
    if not game:
        print(tr("cli.uninstall.not_found"))
        return 2
    removed = installer.uninstall(store, game, status=lambda message: print(f"* {message}"))
    print(tr("cli.uninstall.done", count=len(removed)))
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    store = Store()
    if not store.games:
        print(tr("cli.list.empty"))
        return 0
    for game in store.sorted_games():
        flag = tr("cli.list.installed") if game.installed else tr("cli.list.pending")
        print(f"  {game.name:<40} {flag:<10} {game.variant:<9} {game.exe}")
    return 0


def cmd_engines(_: argparse.Namespace) -> int:
    for key, engine in engines.ENGINES.items():
        print(f"  {key:<15} {engine.name}")
    return 0


def cmd_plugin(args: argparse.Namespace) -> int:
    exe = Path(args.exe).resolve()
    store = Store()
    game = store.find_by_exe(exe)
    if game is None:
        game = _game_from_store(
            store,
            exe,
            argparse.Namespace(variant=None, top_margin=0, aspect=None, api=None, engine=None),
        )
    enabled = not args.disable
    result = installer.set_rpgmaker_plugin(
        store,
        game,
        args.plugin,
        enabled,
        status=lambda message: print(f"* {message}"),
    )
    if enabled:
        print(tr("cli.plugin.enabled", path=result))
    else:
        print(tr("cli.plugin.disabled"))
    return 0


def cmd_nwjs(args: argparse.Namespace) -> int:
    if args.nwjs_cmd == "cache":
        if args.download or not nwjs.list_cached():
            cached = nwjs.ensure_release(
                args.version or None,
                arch=args.arch,
                progress=lambda done, total: None,
                status=lambda message: print(f"* {message}"),
            )
            print(tr("cli.nwjs.cache_ready", version=cached.version, arch=cached.arch, folder=cached.folder))
        for item in nwjs.list_cached():
            print(f"  {item.version:<10} {item.arch:<10} {item.folder}")
        return 0

    exe = Path(args.exe).resolve()
    store = Store()
    game = store.find_by_exe(exe)
    if game is None:
        game = _game_from_store(
            store,
            exe,
            argparse.Namespace(variant=None, top_margin=0, aspect=None, api=None, engine=None),
        )
    if args.nwjs_cmd == "update":
        report = installer.update_nwjs(
            store,
            game,
            preferred_version=args.version or "",
            arch=args.arch,
            status=lambda message: print(f"* {message}"),
        )
        print(tr("cli.nwjs.updated", version=report.version, arch=report.arch))
        for fix in report.fixes_applied:
            print(f"  - {fix}")
        for warning in report.warnings:
            print(f"  ! {warning}")
        return 0

    if args.nwjs_cmd == "restore":
        restored = installer.restore_nwjs(store, game, status=lambda message: print(f"* {message}"))
        print(tr("cli.nwjs.restored", count=len(restored)))
        return 0
    return 1


def cmd_urm(args: argparse.Namespace) -> int:
    if args.urm_cmd == "cache":
        if args.download or not renpy.list_cached():
            cached = renpy.ensure_release(
                args.version or None,
                progress=lambda done, total: None,
                status=lambda message: print(f"* {message}"),
            )
            print(tr("cli.urm.cache_ready", version=cached.version, folder=cached.folder))
        for item in renpy.list_cached():
            print(f"  {item.version:<10} {item.folder}")
        return 0

    exe = Path(args.exe).resolve()
    store = Store()
    game = store.find_by_exe(exe)
    if game is None:
        game = _game_from_store(
            store,
            exe,
            argparse.Namespace(variant=None, top_margin=0, aspect=None, api=None, engine=None),
        )
    if args.urm_cmd == "enable":
        result = installer.set_renpy_urm(
            store,
            game,
            True,
            preferred_version=args.version or store.settings.urm_version,
            status=lambda message: print(f"* {message}"),
        )
        print(tr("cli.urm.enabled", path=result))
        return 0
    if args.urm_cmd == "disable":
        installer.set_renpy_urm(
            store,
            game,
            False,
            status=lambda message: print(f"* {message}"),
        )
        print(tr("cli.urm.disabled"))
        return 0
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anishade", description="AniShade - ReShade + Anime4K Restore")
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help=tr("cli.help.info"))
    info.add_argument("exe")
    info.add_argument("--api", choices=list(detect.API_DLL), default=None)
    info.add_argument("--engine", choices=list(engines.ENGINES), default=None)
    info.set_defaults(func=cmd_info)

    install = sub.add_parser("install", help=tr("cli.help.install"))
    install.add_argument("exe")
    install.add_argument("--variant", choices=[item.key for item in anime4k.VARIANTS], default=None)
    install.add_argument("--top-margin", type=int, default=0, help=tr("cli.help.top_margin"))
    install.add_argument("--aspect", type=float, default=None, help=tr("cli.help.aspect"))
    install.add_argument("--api", choices=list(detect.API_DLL), default=None)
    install.add_argument("--engine", choices=list(engines.ENGINES), default=None)
    install.add_argument("--dll", default="")
    install.add_argument("--reshade", default="")
    install.add_argument("--no-launcher", action="store_true")
    install.add_argument("--no-hide-textbox", action="store_true", help=tr("cli.help.no_hide_textbox"))
    install.add_argument("--no-alt-skip-plugin", action="store_true", help=tr("cli.help.no_alt_skip"))
    install.add_argument("--no-save-slots-plugin", action="store_true", help=tr("cli.help.no_save_slots"))
    install.add_argument(
        "--renpy-urm",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=tr("cli.help.renpy_urm"),
    )
    install.set_defaults(func=cmd_install)

    uninstall = sub.add_parser("uninstall", help=tr("cli.help.uninstall"))
    uninstall.add_argument("exe")
    uninstall.set_defaults(func=cmd_uninstall)

    variants = sub.add_parser("variants", help=tr("cli.help.variants"))
    variants.set_defaults(func=cmd_variants)

    cache = sub.add_parser("cache", help=tr("cli.help.cache"))
    cache.add_argument("--download", action="store_true")
    cache.add_argument("--version", default="")
    cache.set_defaults(func=cmd_cache)

    listing = sub.add_parser("list", help=tr("cli.help.list"))
    listing.set_defaults(func=cmd_list)

    engine_cmd = sub.add_parser("engines", help=tr("cli.help.engines"))
    engine_cmd.set_defaults(func=cmd_engines)

    plugin_cmd = sub.add_parser("plugin", help=tr("cli.help.plugin"))
    plugin_cmd.add_argument("exe")
    plugin_cmd.add_argument(
        "--plugin",
        choices=["hide_textbox", "no_alt_skip", "save_slots_100"],
        default="hide_textbox",
        help=tr("cli.help.plugin_choice"),
    )
    plugin_cmd.add_argument("--disable", action="store_true", help=tr("cli.help.plugin_disable"))
    plugin_cmd.set_defaults(func=cmd_plugin)

    nwjs_cmd = sub.add_parser("nwjs", help=tr("cli.help.nwjs"))
    nwjs_sub = nwjs_cmd.add_subparsers(dest="nwjs_cmd", required=True)

    nwjs_update = nwjs_sub.add_parser("update", help=tr("cli.help.nwjs_update"))
    nwjs_update.add_argument("exe")
    nwjs_update.add_argument("--version", default="")
    nwjs_update.add_argument("--arch", default=nwjs.DEFAULT_ARCH, choices=["win-x64", "win-ia32"])
    nwjs_update.set_defaults(func=cmd_nwjs)

    nwjs_restore = nwjs_sub.add_parser("restore", help=tr("cli.help.nwjs_restore"))
    nwjs_restore.add_argument("exe")
    nwjs_restore.set_defaults(func=cmd_nwjs)

    nwjs_cache = nwjs_sub.add_parser("cache", help=tr("cli.help.nwjs_cache"))
    nwjs_cache.add_argument("--download", action="store_true")
    nwjs_cache.add_argument("--version", default="")
    nwjs_cache.add_argument("--arch", default=nwjs.DEFAULT_ARCH, choices=["win-x64", "win-ia32"])
    nwjs_cache.set_defaults(func=cmd_nwjs)

    urm_cmd = sub.add_parser("urm", help=tr("cli.help.urm"))
    urm_sub = urm_cmd.add_subparsers(dest="urm_cmd", required=True)

    urm_enable = urm_sub.add_parser("enable", help=tr("cli.help.urm_enable"))
    urm_enable.add_argument("exe")
    urm_enable.add_argument("--version", default="")
    urm_enable.set_defaults(func=cmd_urm)

    urm_disable = urm_sub.add_parser("disable", help=tr("cli.help.urm_disable"))
    urm_disable.add_argument("exe")
    urm_disable.set_defaults(func=cmd_urm)

    urm_cache = urm_sub.add_parser("cache", help=tr("cli.help.urm_cache"))
    urm_cache.add_argument("--download", action="store_true")
    urm_cache.add_argument("--version", default="")
    urm_cache.set_defaults(func=cmd_urm)
    return parser


def main(argv: list[str] | None = None) -> int:
    store = Store()
    i18n.set_language(store.settings.language)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (
        installer.InstallError,
        reshade.ReshadeError,
        nwjs.NwjsError,
        renpy.RenpyModError,
        FileNotFoundError,
        PermissionError,
    ) as exc:
        print(tr("cli.error_prefix", error=exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
