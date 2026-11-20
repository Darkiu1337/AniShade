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

from . import anime4k, detect, engines, installer, nwjs, reshade
from .store import Game, Store, game_id_for


def _print_analysis(analysis: detect.GameAnalysis) -> None:
    print(f"Executavel ....: {analysis.exe}")
    print(f"Nome ..........: {analysis.suggested_name()}")
    print(f"Engine ........: {analysis.engine.name}  ({'; '.join(analysis.engine_evidence) or 'heuristica padrao'})")
    print(f"Arquitetura ...: {analysis.bits or '?'} bits")
    print(f"API ...........: {detect.API_LABELS.get(analysis.api, analysis.api)}  [{analysis.api_source}]")
    print(f"DLL proxy .....: {analysis.dll_name}  (alternativas: {', '.join(analysis.dll_alternatives) or 'nenhuma'})")
    print(f"Conteudo ......: {analysis.content_size or 'nao detectado'}  aspecto {analysis.content_aspect or 0:.3f}")
    print(f"ReShade atual .: {analysis.existing_reshade_version or 'nao instalado'}")
    if analysis.rpgmaker_plugins_js:
        print(f"Plugin RPGM ...: {analysis.rpgmaker_plugins_js} (ocultar caixa de texto com H)")
    if analysis.nwjs_version:
        print(f"NW.js atual ...: {analysis.nwjs_version}")
    if analysis.notes:
        print("Notas:")
        for note in analysis.notes:
            print(f"  - {note}")
    if analysis.warnings:
        print("Avisos:")
        for warning in analysis.warnings:
            print(f"  ! {warning}")


def cmd_info(args: argparse.Namespace) -> int:
    analysis = detect.analyze(args.exe, args.api, args.engine)
    _print_analysis(analysis)
    return 0


def cmd_variants(_: argparse.Namespace) -> int:
    print("Variantes Restore do Anime4K (ReShade FX):")
    for variant in anime4k.VARIANTS:
        print(f"  {variant.key:<10} {variant.label:<32} {variant.resolution:<14} peso {variant.weight}x")
    return 0


def cmd_cache(args: argparse.Namespace) -> int:
    if args.download or not reshade.list_cached():
        release = reshade.ensure_release(
            args.version or None,
            progress=lambda done, total: None,
            status=lambda message: print(f"* {message}"),
        )
        print(f"Cache pronto: ReShade {release.version} em {release.folder}")
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
    )
    report = installer.install(
        store,
        game,
        options,
        status=lambda message: print(f"* {message}"),
    )
    print("\nInstalado:")
    print(f"  DLL ..........: {report.dll_path}")
    print(f"  Preset .......: {report.preset_path}")
    print(f"  Shaders ......: {report.shader_dir}")
    print(f"  ReShade ......: {report.reshade_version}")
    print(f"  Tecnicas .....: {', '.join(report.techniques)}")
    if report.rpgmaker_plugins:
        print(f"  Plugins RPGM .: {', '.join(report.rpgmaker_plugins)}")
    if report.launcher:
        print(f"  Launcher .....: {report.launcher}")
    for warning in report.warnings:
        print(f"  ! {warning}")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    exe = Path(args.exe).resolve()
    store = Store()
    game = store.find_by_exe(exe)
    if not game:
        print("Jogo nao esta na biblioteca do AniShade.")
        return 2
    removed = installer.uninstall(store, game, status=lambda message: print(f"* {message}"))
    print(f"Removidos {len(removed)} arquivos.")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    store = Store()
    if not store.games:
        print("Biblioteca vazia.")
        return 0
    for game in store.sorted_games():
        flag = "instalado" if game.installed else "pendente"
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
        print(f"Plugin ativado: {result}")
    else:
        print("Plugin desativado.")
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
            print(f"Cache pronto: NW.js {cached.version} ({cached.arch}) em {cached.folder}")
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
        print(f"\nNW.js atualizado para {report.version} ({report.arch}).")
        for fix in report.fixes_applied:
            print(f"  - {fix}")
        for warning in report.warnings:
            print(f"  ! {warning}")
        return 0

    if args.nwjs_cmd == "restore":
        restored = installer.restore_nwjs(store, game, status=lambda message: print(f"* {message}"))
        print(f"Restaurados {len(restored)} arquivos originais.")
        return 0
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anishade", description="AniShade - ReShade + Anime4K Restore")
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="analisa um executavel")
    info.add_argument("exe")
    info.add_argument("--api", choices=list(detect.API_DLL), default=None)
    info.add_argument("--engine", choices=list(engines.ENGINES), default=None)
    info.set_defaults(func=cmd_info)

    install = sub.add_parser("install", help="instala ReShade + Anime4K")
    install.add_argument("exe")
    install.add_argument("--variant", choices=[item.key for item in anime4k.VARIANTS], default=None)
    install.add_argument("--top-margin", type=int, default=0, help="pixels do topo a ignorar (barra de titulo)")
    install.add_argument("--aspect", type=float, default=None, help="proporcao do conteudo (ex.: 1.5); 0 desativa")
    install.add_argument("--api", choices=list(detect.API_DLL), default=None)
    install.add_argument("--engine", choices=list(engines.ENGINES), default=None)
    install.add_argument("--dll", default="")
    install.add_argument("--reshade", default="")
    install.add_argument("--no-launcher", action="store_true")
    install.add_argument(
        "--no-hide-textbox",
        action="store_true",
        help="nao instala o plugin de ocultar caixa de texto (tecla H) em jogos RPG Maker MV/MZ",
    )
    install.add_argument(
        "--no-alt-skip-plugin",
        action="store_true",
        help="nao instala o plugin que impede Alt/Alt+Tab de pular texto em jogos RPG Maker MV/MZ",
    )
    install.add_argument(
        "--no-save-slots-plugin",
        action="store_true",
        help="nao instala o plugin que expande para 100 slots de save em jogos RPG Maker MV/MZ",
    )
    install.set_defaults(func=cmd_install)

    uninstall = sub.add_parser("uninstall", help="remove o ReShade instalado pelo AniShade")
    uninstall.add_argument("exe")
    uninstall.set_defaults(func=cmd_uninstall)

    variants = sub.add_parser("variants", help="lista as variantes disponiveis")
    variants.set_defaults(func=cmd_variants)

    cache = sub.add_parser("cache", help="gerencia o cache do ReShade")
    cache.add_argument("--download", action="store_true")
    cache.add_argument("--version", default="")
    cache.set_defaults(func=cmd_cache)

    listing = sub.add_parser("list", help="lista os jogos da biblioteca")
    listing.set_defaults(func=cmd_list)

    engine_cmd = sub.add_parser("engines", help="lista engines reconhecidas")
    engine_cmd.set_defaults(func=cmd_engines)

    plugin_cmd = sub.add_parser("plugin", help="ativa ou remove plugins RPG Maker MV/MZ do AniShade")
    plugin_cmd.add_argument("exe")
    plugin_cmd.add_argument(
        "--plugin",
        choices=["hide_textbox", "no_alt_skip", "save_slots_100"],
        default="hide_textbox",
        help="qual plugin alternar (padrao: hide_textbox)",
    )
    plugin_cmd.add_argument("--disable", action="store_true", help="remove o plugin do jogo")
    plugin_cmd.set_defaults(func=cmd_plugin)

    nwjs_cmd = sub.add_parser("nwjs", help="gerencia e atualiza o NW.js em jogos RPG Maker MV/MZ")
    nwjs_sub = nwjs_cmd.add_subparsers(dest="nwjs_cmd", required=True)

    nwjs_update = nwjs_sub.add_parser("update", help="atualiza o NW.js do jogo e corrige package.json")
    nwjs_update.add_argument("exe")
    nwjs_update.add_argument("--version", default="")
    nwjs_update.add_argument("--arch", default=nwjs.DEFAULT_ARCH, choices=["win-x64", "win-ia32"])
    nwjs_update.set_defaults(func=cmd_nwjs)

    nwjs_restore = nwjs_sub.add_parser("restore", help="restaura o NW.js original do backup")
    nwjs_restore.add_argument("exe")
    nwjs_restore.set_defaults(func=cmd_nwjs)

    nwjs_cache = nwjs_sub.add_parser("cache", help="lista ou baixa o NW.js oficial para o cache")
    nwjs_cache.add_argument("--download", action="store_true")
    nwjs_cache.add_argument("--version", default="")
    nwjs_cache.add_argument("--arch", default=nwjs.DEFAULT_ARCH, choices=["win-x64", "win-ia32"])
    nwjs_cache.set_defaults(func=cmd_nwjs)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (installer.InstallError, reshade.ReshadeError, nwjs.NwjsError, FileNotFoundError, PermissionError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
