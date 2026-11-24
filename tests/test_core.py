"""Core smoke tests: PE parsing, ReShade extraction, presets, INI merge, install.

Run with:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from anishade import anime4k, detect, engines, installer, nwjs, paths, pe, renpy, reshade, rpgmaker  # noqa: E402
from anishade.installer import InstallOptions  # noqa: E402
from anishade.store import Game, game_id_for  # noqa: E402

NOTEPAD = Path(r"C:\Windows\System32\notepad.exe")
SETUP = ROOT / "vendor" / "ReShade_Setup_6.8.0.exe"
CACHED = reshade.newest_cached()


class StoreStub:
    def __init__(self) -> None:
        self.games: list[Game] = []
        self.saved = 0

    def save_games(self) -> None:
        self.saved += 1


def make_game(directory: Path, name: str = "Test Game", api_override: str = "") -> Game:
    exe = directory / "game.exe"
    if not exe.exists():
        if not NOTEPAD.exists():
            raise unittest.SkipTest("notepad.exe indisponivel para o fixture")
        shutil.copy2(NOTEPAD, exe)
    return Game(
        id=game_id_for(exe),
        name=name,
        exe=str(exe),
        api_override=api_override,
    )


class PETests(unittest.TestCase):
    def test_notepad_is_64bit_exe(self) -> None:
        info = pe.read_pe(NOTEPAD)
        self.assertEqual(info.bits, 64)
        self.assertEqual(info.arch, "x86-64")
        self.assertFalse(info.is_dll)
        self.assertIn("user32.dll", info.all_imports)

    def test_cached_reshade_dlls(self) -> None:
        self.assertIsNotNone(CACHED)
        assert CACHED is not None
        self.assertEqual(pe.read_pe(CACHED.dll32).bits, 32)
        self.assertEqual(pe.read_pe(CACHED.dll64).bits, 64)
        self.assertTrue(detect.is_reshade_dll(CACHED.dll64))
        self.assertTrue(detect.reshade_dll_version(CACHED.dll64).startswith("6."))

    def test_garbage_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bogus = Path(tmp) / "x.exe"
            bogus.write_bytes(b"not a pe file")
            with self.assertRaises(pe.PEError):
                pe.read_pe(bogus)


class ReshadeExtractionTests(unittest.TestCase):
    @unittest.skipUnless(SETUP.is_file(), "instalador do ReShade nao esta em vendor/")
    def test_extracts_both_dlls(self) -> None:
        payload = reshade.extract_dlls(SETUP)
        self.assertEqual(set(payload), {"ReShade32.dll", "ReShade64.dll"})
        self.assertTrue(payload["ReShade32.dll"].startswith(b"MZ"))
        self.assertTrue(payload["ReShade64.dll"].startswith(b"MZ"))
        self.assertGreater(len(payload["ReShade64.dll"]), 1_000_000)

    def test_rejects_tiny_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "setup.exe"
            fake.write_bytes(b"MZ" + b"\x00" * 1000)
            with self.assertRaises(reshade.ReshadeError):
                reshade.extract_dlls(fake)

    @unittest.skipUnless(CACHED is not None, "cache do ReShade vazio")
    def test_patch_hide_splash_patches_both_architectures_with_valid_pe_checksum(self) -> None:
        import ctypes

        assert CACHED is not None
        imagehlp = ctypes.windll.imagehlp
        with tempfile.TemporaryDirectory() as tmp:
            for bits, src in ((64, CACHED.dll64), (32, CACHED.dll32)):
                original = src.read_bytes()
                patched, ok = reshade.patch_hide_splash(original)
                self.assertTrue(ok, f"patch falhou para {bits} bits")
                self.assertNotEqual(patched, original)
                out = Path(tmp) / f"ReShade{bits}.dll"
                out.write_bytes(patched)

                hdr_sum = ctypes.c_ulong(0)
                chk_sum = ctypes.c_ulong(0)
                rc = imagehlp.MapFileAndCheckSumW(str(out), ctypes.byref(hdr_sum), ctypes.byref(chk_sum))
                self.assertEqual(rc, 0)
                self.assertEqual(hdr_sum.value, chk_sum.value)
                self.assertEqual(pe.read_pe(out).bits, bits)
                self.assertTrue(detect.is_reshade_dll(out))
                self.assertTrue(detect.reshade_dll_version(out).startswith(CACHED.version))

                # Already patched -> no-op
                _, ok_again = reshade.patch_hide_splash(patched)
                self.assertFalse(ok_again)


class PresetTests(unittest.TestCase):
    def test_restore_only_preset(self) -> None:
        self.assertEqual(anime4k.techniques("cnn_m"), ["Anime4K_Restore_CNN_M"])
        text = anime4k.build_preset("cnn_m")
        self.assertEqual(
            text,
            "Techniques=Anime4K_Restore_CNN_M\nTechniqueSorting=Anime4K_Restore_CNN_M\n",
        )

    def test_preset_with_margins(self) -> None:
        text = anime4k.build_preset("soft_s", top_margin=31, content_aspect=1.5)
        self.assertIn("PreprocessorDefinitions=ANISHADE_TOP_MARGIN=31,ANISHADE_CONTENT_ASPECT=1.5000", text)
        self.assertIn("Techniques=Anime4K_Restore_CNN_Soft_S", text)

    def test_every_variant_exists_as_fx(self) -> None:
        source = paths.anime4k_fx_dir()
        for variant in anime4k.VARIANTS:
            self.assertTrue((source / variant.file).is_file(), variant.file)
            content = (source / variant.file).read_text(encoding="utf-8")
            self.assertIn(f"technique {variant.technique}", content)
            self.assertIn("pass Copy", content)
            self.assertIn("RenderTarget0 = texInput", content)
            for n in (1, 2, 3, 4):
                self.assertIn(f"texture texPrev{n}", content)
            self.assertIn("pass Shift3", content)
            self.assertIn("pass Shift2", content)
            self.assertIn("pass Shift1", content)
            self.assertIn("RenderTarget0 = texPrev1", content)
            self.assertIn("pass Present", content)
            self.assertIn("anishade_maxdiff", content)
            self.assertNotIn("float4x4", content)


class IniMergeTests(unittest.TestCase):
    def test_preserves_unknown_sections_and_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = Path(tmp)
            original = "[GENERAL]\nPresetPath=.\\User.ini\nPerformanceMode=1\n\n[CUSTOM]\nkeepme=yes\n"
            (game_dir / "ReShade.ini").write_text(original, encoding="utf-8")
            path, payload = installer._merge_reshade_ini(game_dir, "AniShade.ini")  # noqa: SLF001
            text = payload.decode("utf-8")
            self.assertIn("[CUSTOM]", text)
            self.assertIn("keepme=yes", text)
            self.assertIn("PresetPath=.\\AniShade.ini", text)
            self.assertIn("StartupPresetPath=.\\AniShade.ini", text)
            self.assertIn("PerformanceMode=0", text)
            self.assertIn("EffectSearchPaths=.\\reshade-shaders\\Shaders\\**", text)

    def test_appends_missing_shader_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = Path(tmp)
            (game_dir / "ReShade.ini").write_text(
                "[GENERAL]\nEffectSearchPaths=D:\\Shaders\\**\n", encoding="utf-8"
            )
            _, payload = installer._merge_reshade_ini(game_dir, "AniShade.ini")  # noqa: SLF001
            text = payload.decode("utf-8")
            self.assertIn("D:\\Shaders\\**,.\\reshade-shaders\\Shaders\\**", text)


class EngineDetectionTests(unittest.TestCase):
    def _detect(self, files: dict[str, str]) -> detect.GameAnalysis:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        directory = Path(tmp)
        for relative, content in files.items():
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return detect.analyze(make_game(directory).exe_path)

    def test_renpy(self) -> None:
        analysis = self._detect(
            {"game/script.rpyc": "", "renpy/common/00start.rpy": "", "libEGL.dll": "x"}
        )
        self.assertEqual(analysis.engine.key, "renpy")
        self.assertEqual(analysis.api, "d3d9")
        self.assertEqual(analysis.env.get("RENPY_RENDERER"), "angle2")

    def test_renpy_without_angle_uses_opengl(self) -> None:
        analysis = self._detect({"game/script.rpyc": "", "renpy/common/00start.rpy": ""})
        self.assertEqual(analysis.api, "opengl")
        self.assertEqual(analysis.env.get("RENPY_RENDERER"), "gl2")

    def test_rpgmaker_mv(self) -> None:
        analysis = self._detect(
            {
                "www/js/rmmz_core.js": "Graphics.width = 1080; Graphics.height = 720;\n",
                "nw.dll": "",
                "package.json": '{"window":{"width":1080,"height":720}}',
            }
        )
        self.assertEqual(analysis.engine.key, "rpgmaker_mv")
        self.assertEqual(analysis.api, "dxgi")
        self.assertEqual(analysis.dll_name, "dxgi.dll")
        self.assertEqual(analysis.content_size, (1080, 720))
        self.assertEqual(analysis.content_aspect, 0.0)

    def test_rgss(self) -> None:
        analysis = self._detect({"RGSS300.dll": "", "Game.ini": ""})
        self.assertEqual(analysis.engine.key, "rpgmaker_rgss")
        self.assertEqual(analysis.api, "d3d9")

    def test_unity(self) -> None:
        analysis = self._detect(
            {"UnityPlayer.dll": "", "Demo_Data/globalgamemanagers": ""}
        )
        self.assertEqual(analysis.engine.key, "unity")
        self.assertEqual(analysis.api, "dxgi")

    def test_yuris_and_others_are_registered(self) -> None:
        analysis = self._detect({"data.ypf": ""})
        self.assertEqual(analysis.engine.key, "yuris")
        for key in ("yuris", "catsystem2", "reallive", "livemaker", "cmvs", "nitroplus"):
            self.assertIn(key, engines.ENGINES)

    def test_launcher_warning(self) -> None:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        directory = Path(tmp)
        shutil.copy2(NOTEPAD, directory / "launcher.exe")
        analysis = detect.analyze(directory / "launcher.exe")
        self.assertTrue(any("launcher" in warning for warning in analysis.warnings))


class InstallFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        if CACHED is None:
            raise unittest.SkipTest("cache do ReShade vazio")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.game_dir = self.base / "game"
        self.game_dir.mkdir()
        self.game = make_game(self.game_dir)
        self.store = StoreStub()
        self.patches = [
            mock.patch.object(paths, "GAME_DATA_DIR", self.base / "meta"),
            mock.patch.object(paths, "BACKUP_DIR", self.base / "backups"),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_install_and_uninstall_are_clean(self) -> None:
        before = {item.name for item in self.game_dir.iterdir()}
        report = installer.install(
            self.store,
            self.game,
            InstallOptions(variant="cnn_m", content_aspect=1.5),
        )
        self.assertTrue((self.game_dir / report.dll_name).is_file())
        self.assertTrue((self.game_dir / "AniShade.ini").is_file())
        self.assertTrue((self.game_dir / "ReShade.ini").is_file())
        self.assertTrue(
            (self.game_dir / anime4k.SHADER_SUBDIR / "Anime4K_Restore_CNN_M.fx").is_file()
        )
        preset = (self.game_dir / "AniShade.ini").read_text(encoding="utf-8")
        self.assertIn("Anime4K_Restore_CNN_M", preset)
        self.assertIn("ANISHADE_CONTENT_ASPECT=1.5", preset)
        ini = (self.game_dir / "ReShade.ini").read_text(encoding="utf-8")
        self.assertIn("KeyOverlay=36,0,0,0", ini)
        self.assertEqual(self.game.installed, True)
        state = installer.inspect(self.game)
        self.assertTrue(state.dll_ok)
        self.assertTrue(state.preset_ok)
        self.assertTrue(state.shaders_ok)

        removed = installer.uninstall(self.store, self.game)
        self.assertTrue(removed)
        after = {item.name for item in self.game_dir.iterdir()}
        self.assertEqual(after, before, "a desinstalacao deve restaurar o estado original")
        self.assertFalse((self.game_dir / "reshade-shaders").exists())

    def test_variant_switch_removes_stale_shaders(self) -> None:
        installer.install(self.store, self.game, InstallOptions(variant="cnn_l"))
        shader_dir = self.game_dir / anime4k.SHADER_SUBDIR
        self.assertTrue((shader_dir / "Anime4K_Restore_CNN_L.fx").is_file())
        installer.install(self.store, self.game, InstallOptions(variant="cnn_s"))
        self.assertFalse((shader_dir / "Anime4K_Restore_CNN_L.fx").exists())
        self.assertTrue((shader_dir / "Anime4K_Restore_CNN_S.fx").is_file())

    def test_conflicting_dxgi_falls_back(self) -> None:
        (self.game_dir / "dxgi.dll").write_bytes(b"fake third party")
        report = installer.install(self.store, self.game, InstallOptions())
        self.assertEqual(report.dll_name, "d3d11.dll")
        self.assertEqual((self.game_dir / "dxgi.dll").read_bytes(), b"fake third party")

    def test_user_preset_is_backed_up(self) -> None:
        preset = self.game_dir / "AniShade.ini"
        preset.write_text("Techniques=Anime4K_Restore_CNN_S\n", encoding="utf-8")
        report = installer.install(self.store, self.game, InstallOptions(variant="cnn_m"))
        self.assertTrue(report.backup_paths)
        self.assertIn("Anime4K_Restore_CNN_M", preset.read_text(encoding="utf-8"))

    def test_rpgmaker_mv_installs_and_cleanly_uninstalls_hide_textbox_plugin(self) -> None:
        (self.game_dir / "nw.dll").write_bytes(b"")
        (self.game_dir / "package.json").write_text('{"main":"www/index.html"}', encoding="utf-8")
        js_dir = self.game_dir / "www" / "js"
        (js_dir / "plugins").mkdir(parents=True)
        (js_dir / "rpg_core.js").write_text("Graphics.width = 816; Graphics.height = 624;\n", encoding="utf-8")
        original_plugins_js = (
            "// Generated by RPG Maker.\r\n"
            "// Do not edit this file directly.\r\n"
            "var $plugins =\r\n"
            "[\r\n"
            '{"name":"ExistingPlugin","status":true,"description":"ok","parameters":{}}\r\n'
            "];\r\n"
        )
        plugins_js = js_dir / "plugins.js"
        plugins_js.write_bytes(original_plugins_js.encode("utf-8"))

        report = installer.install(self.store, self.game, InstallOptions(variant="cnn_m"))
        self.assertEqual(report.rpgmaker_plugin, "www/js/plugins/AniShade_HideTextbox.js")
        plugin_file = js_dir / "plugins" / rpgmaker.PLUGIN_FILE
        self.assertTrue(plugin_file.is_file())
        updated_text = plugins_js.read_text(encoding="utf-8")
        self.assertTrue(rpgmaker.is_plugin_enabled(updated_text))
        self.assertIn('"name":"ExistingPlugin"', updated_text)

        state = installer.inspect(self.game)
        self.assertTrue(state.plugin_ok)
        self.assertEqual(state.rpgmaker_plugin, "www/js/plugins/AniShade_HideTextbox.js")

        # Reinstalling preserves original backup and stays idempotent
        installer.install(self.store, self.game, InstallOptions(variant="cnn_s"))
        self.assertEqual(plugins_js.read_text(encoding="utf-8").count(rpgmaker.PLUGIN_NAME), 1)

        # Uninstalling removes the plugin file and restores plugins.js byte-for-byte
        installer.uninstall(self.store, self.game)
        self.assertFalse(plugin_file.exists())
        self.assertEqual(plugins_js.read_bytes(), original_plugins_js.encode("utf-8"))

    def test_rpgmaker_mz_uninstall_preserves_user_edits_to_plugins_js(self) -> None:
        js_dir = self.game_dir / "js"
        (js_dir / "plugins").mkdir(parents=True)
        (js_dir / "rmmz_core.js").write_text("Graphics.width = 1280; Graphics.height = 720;\n", encoding="utf-8")
        plugins_js = js_dir / "plugins.js"
        plugins_js.write_text(
            'var $plugins =\n[\n{"name":"First","status":true,"description":"","parameters":{}}\n];\n',
            encoding="utf-8",
        )

        report = installer.install(self.store, self.game, InstallOptions())
        self.assertEqual(report.rpgmaker_plugin, "js/plugins/AniShade_HideTextbox.js")

        # User adds another plugin after AniShade installed
        after_user = rpgmaker.register_plugin_in_text(
            plugins_js.read_text(encoding="utf-8"),
            name="UserAddedLater",
            description="added after",
        )
        plugins_js.write_text(after_user, encoding="utf-8")

        installer.uninstall(self.store, self.game)
        remaining = plugins_js.read_text(encoding="utf-8")
        self.assertFalse(rpgmaker.has_plugin_entry(remaining))
        self.assertIn('"name":"First"', remaining)
        self.assertIn('"name":"UserAddedLater"', remaining)
        self.assertFalse((js_dir / "plugins" / rpgmaker.PLUGIN_FILE).exists())

    def test_rpgmaker_plugin_can_be_disabled_on_reinstall(self) -> None:
        js_dir = self.game_dir / "js"
        (js_dir / "plugins").mkdir(parents=True)
        (js_dir / "rmmz_core.js").write_text("", encoding="utf-8")
        plugins_js = js_dir / "plugins.js"
        original = "var $plugins =\n[\n];\n"
        plugins_js.write_text(original, encoding="utf-8")

        installer.install(
            self.store,
            self.game,
            InstallOptions(
                rpgmaker_hide_textbox=True,
                rpgmaker_no_alt_skip=True,
                rpgmaker_save_slots_100=True,
            ),
        )
        self.assertTrue((js_dir / "plugins" / rpgmaker.PLUGIN_FILE).is_file())
        self.assertTrue((js_dir / "plugins" / rpgmaker.NO_ALT_SKIP_FILE).is_file())
        self.assertTrue((js_dir / "plugins" / rpgmaker.SAVE_SLOTS_100_FILE).is_file())

        report = installer.install(
            self.store,
            self.game,
            InstallOptions(
                rpgmaker_hide_textbox=False,
                rpgmaker_no_alt_skip=False,
                rpgmaker_save_slots_100=False,
            ),
        )
        self.assertEqual(report.rpgmaker_plugin, "")
        self.assertEqual(report.rpgmaker_plugins, [])
        self.assertFalse((js_dir / "plugins" / rpgmaker.PLUGIN_FILE).exists())
        self.assertFalse((js_dir / "plugins" / rpgmaker.NO_ALT_SKIP_FILE).exists())
        self.assertFalse((js_dir / "plugins" / rpgmaker.SAVE_SLOTS_100_FILE).exists())
        self.assertEqual(plugins_js.read_text(encoding="utf-8"), original)

    def test_rpgmaker_without_plugins_js_warns_without_failing(self) -> None:
        (self.game_dir / "package.json").write_text("{}", encoding="utf-8")
        (self.game_dir / "index.html").write_text("<html></html>", encoding="utf-8")
        report = installer.install(self.store, self.game, InstallOptions())
        self.assertEqual(report.rpgmaker_plugin, "")
        self.assertTrue((self.game_dir / report.dll_name).is_file())
        self.assertTrue(any("plugins.js" in warning for warning in report.warnings))

    def test_rpgmaker_inspect_detects_missing_or_disabled_plugin(self) -> None:
        js_dir = self.game_dir / "js"
        (js_dir / "plugins").mkdir(parents=True)
        (js_dir / "rmmz_core.js").write_text("", encoding="utf-8")
        plugins_js = js_dir / "plugins.js"
        plugins_js.write_text("var $plugins = [];\n", encoding="utf-8")

        installer.install(self.store, self.game, InstallOptions())
        (js_dir / "plugins" / rpgmaker.PLUGIN_FILE).unlink()
        state = installer.inspect(self.game)
        self.assertFalse(state.plugin_ok)
        self.assertTrue(any("AniShade_HideTextbox.js" in problem for problem in state.problems))


class RpgMakerPluginTextTests(unittest.TestCase):
    def test_register_and_unregister_empty_array(self) -> None:
        src = "// header\nvar $plugins =\n[\n];\n"
        added = rpgmaker.register_plugin_in_text(src)
        self.assertTrue(rpgmaker.is_plugin_enabled(added))
        removed = rpgmaker.unregister_plugin_in_text(added)
        self.assertEqual(removed, src)

    def test_register_and_unregister_minified(self) -> None:
        src = 'var $plugins=[{"name":"A","status":true,"description":"[brackets]","parameters":{}}];'
        added = rpgmaker.register_plugin_in_text(src)
        self.assertTrue(rpgmaker.is_plugin_enabled(added))
        self.assertIn('"description":"[brackets]"', added)
        removed = rpgmaker.unregister_plugin_in_text(added)
        self.assertEqual(removed, src)

    def test_register_handles_trailing_comma_and_comments(self) -> None:
        src = (
            "/* comment with var $plugins = [] */\n"
            "var $plugins = [\n"
            '{"name":"A","status":true,"description":"AniShade_HideTextbox","parameters":{}},\n'
            "];\n"
        )
        added = rpgmaker.register_plugin_in_text(src)
        self.assertTrue(rpgmaker.is_plugin_enabled(added))
        self.assertNotIn(",,", added)
        removed = rpgmaker.unregister_plugin_in_text(added)
        self.assertFalse(rpgmaker.has_plugin_entry(removed))
        self.assertIn('"name":"A"', removed)

    def test_register_re_enables_disabled_entry_in_place(self) -> None:
        src = (
            "var $plugins =\n[\n"
            '{"name":"AniShade_HideTextbox","status":false,"description":"old","parameters":{}},\n'
            '{"name":"B","status":true,"description":"","parameters":{}}\n'
            "];\n"
        )
        self.assertTrue(rpgmaker.has_plugin_entry(src))
        self.assertFalse(rpgmaker.is_plugin_enabled(src))
        updated = rpgmaker.register_plugin_in_text(src)
        self.assertTrue(rpgmaker.is_plugin_enabled(updated))
        self.assertEqual(updated.count("AniShade_HideTextbox"), 1)
        removed = rpgmaker.unregister_plugin_in_text(updated)
        self.assertFalse(rpgmaker.has_plugin_entry(removed))
        self.assertIn('"name":"B"', removed)

    def test_find_js_dir_supports_custom_package_main(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"main":"app/index.html"}', encoding="utf-8")
            js_dir = root / "app" / "js"
            js_dir.mkdir(parents=True)
            (js_dir / "plugins.js").write_text("var $plugins = [];\n", encoding="utf-8")
            self.assertEqual(rpgmaker.find_js_dir(root), js_dir)

    def test_plugin_js_runtime_hides_and_restores_textbox_on_h_key(self) -> None:
        try:
            from PySide6.QtCore import QCoreApplication
            from PySide6.QtQml import QJSEngine
        except ImportError:
            self.skipTest("PySide6.QtQml indisponivel")

        _app = QCoreApplication.instance() or QCoreApplication([])
        engine = QJSEngine()
        harness = """
        var listeners = [];
        var window = {};
        var document = {
            addEventListener: function(type, fn, capture) {
                listeners.push({type: type, fn: fn, capture: capture});
            }
        };
        function dispatchKey(ev) {
            for (var i = 0; i < listeners.length; i++) {
                if (listeners[i].type === "keydown") listeners[i].fn(ev);
            }
        }
        function Scene_Base() { this._windowLayer = { children: [] }; }
        Scene_Base.prototype.update = function() {
            if (this._messageWindow) this._messageWindow.update();
            if (this._nameBoxWindow) this._nameBoxWindow.update();
            if (this._choiceListWindow) this._choiceListWindow.update();
        };
        function Window_Message() {
            this.visible = true;
            this.openness = 255;
            this._closing = false;
            this.updateCalls = 0;
        }
        Window_Message.prototype.isClosed = function() { return this.openness <= 0; };
        Window_Message.prototype.isClosing = function() { return this._closing; };
        Window_Message.prototype.update = function() { this.updateCalls++; };
        Window_Message.prototype.isTriggered = function() { return true; };
        Window_Message.prototype.terminateMessage = function() { this.openness = 0; };
        var $gameMessage = { _busy: true, isBusy: function() { return this._busy; } };
        var SceneManager = { _scene: null };
        """
        self.assertFalse(engine.evaluate(harness).isError())
        plugin_eval = engine.evaluate(rpgmaker.PLUGIN_SOURCE)
        self.assertFalse(plugin_eval.isError(), plugin_eval.toString())

        scenario = """
        (function() {
            var scene = new Scene_Base();
            var msg = new Window_Message();
            var nameBox = {
                visible: true, openness: 255, active: false,
                isClosed: function() { return this.openness <= 0; },
                update: function() { this.visible = true; }
            };
            var choices = {
                visible: true, openness: 255, active: true,
                isClosed: function() { return this.openness <= 0; },
                update: function() {}
            };
            msg._nameBoxWindow = nameBox;
            msg._choiceListWindow = choices;
            scene._messageWindow = msg;
            scene._nameBoxWindow = nameBox;
            scene._choiceListWindow = choices;
            SceneManager._scene = scene;

            scene.update();
            if (msg.updateCalls !== 1) throw new Error("initial update failed");

            dispatchKey({ key: "h", keyCode: 72, ctrlKey: true });
            scene.update();
            if (!msg.visible) throw new Error("Ctrl+H must be ignored");

            dispatchKey({ key: "h", keyCode: 72 });
            scene.update();
            if (msg.visible || nameBox.visible || choices.visible || choices.active) {
                throw new Error("H must hide message, nameBox, and choices");
            }
            if (msg.isTriggered() !== false) throw new Error("isTriggered must be false while hidden");

            var calls = msg.updateCalls;
            scene.update();
            if (msg.updateCalls !== calls || nameBox.visible) {
                throw new Error("hidden state must pause update and keep nameBox hidden");
            }

            dispatchKey({ key: "H", keyCode: 72 });
            scene.update();
            if (!msg.visible || !nameBox.visible || !choices.visible || !choices.active) {
                throw new Error("second H must restore visibility and active states");
            }
            return "OK";
        })();
        """
        result = engine.evaluate(scenario)
        self.assertFalse(result.isError(), result.toString())
        self.assertEqual(result.toString(), "OK")


class DisplayNameTests(unittest.TestCase):
    def test_falls_back_to_folder_name_when_exe_has_no_usable_name(self) -> None:
        folder = Path(r"C:\Games\Starlight Odyssey")
        exe = folder / "Game.exe"
        self.assertEqual(detect._pick_display_name("", "", exe, folder), "Starlight Odyssey")  # noqa: SLF001
        self.assertEqual(detect._pick_display_name("nwjs", "NW.js", exe, folder), "Starlight Odyssey")  # noqa: SLF001
        self.assertEqual(detect._pick_display_name("Game.exe", "Game", exe, folder), "Starlight Odyssey")  # noqa: SLF001
        self.assertEqual(
            detect._pick_display_name("", "", folder / "custom_bin.exe", folder),  # noqa: SLF001
            "Starlight Odyssey",
        )

    def test_uses_parent_folder_for_generic_subfolders(self) -> None:
        folder = Path(r"C:\Games\Chrono Tale\bin")
        self.assertEqual(
            detect._pick_display_name("", "", folder / "Game.exe", folder),  # noqa: SLF001
            "Chrono Tale",
        )

    def test_prefers_valid_exe_product_name(self) -> None:
        folder = Path(r"C:\Games\RandomDir")
        self.assertEqual(
            detect._pick_display_name("Chrono Tale", "nwjs", folder / "Game.exe", folder),  # noqa: SLF001
            "Chrono Tale",
        )

    def test_analyze_ignores_blank_or_generic_package_json_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = Path(tmp) / "Moonlight RPG"
            game_dir.mkdir()
            shutil.copy2(NOTEPAD, game_dir / "Game.exe")
            (game_dir / "package.json").write_text('{"name":"","window":{"title":"Game"}}', encoding="utf-8")
            with mock.patch.object(detect.winapi, "file_version_info", return_value={"ProductName": "nwjs"}):
                analysis = detect.analyze(game_dir / "Game.exe")
            self.assertEqual(analysis.suggested_name(), "Moonlight RPG")


class StandalonePluginToggleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.game_dir = self.base / "My MV Game"
        self.game_dir.mkdir()
        self.game = make_game(self.game_dir)
        self.store = StoreStub()
        for patch in (
            mock.patch.object(paths, "GAME_DATA_DIR", self.base / "meta"),
            mock.patch.object(paths, "BACKUP_DIR", self.base / "backups"),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_toggle_plugin_without_reshade_installed(self) -> None:
        js_dir = self.game_dir / "www" / "js"
        (js_dir / "plugins").mkdir(parents=True)
        original = "var $plugins =\n[\n];\n"
        (js_dir / "plugins.js").write_text(original, encoding="utf-8")

        self.assertFalse(installer.is_rpgmaker_plugin_active(self.game_dir))
        installed_path = installer.set_rpgmaker_hide_textbox(self.store, self.game, True)
        self.assertEqual(installed_path, "www/js/plugins/AniShade_HideTextbox.js")
        self.assertTrue(installer.is_rpgmaker_plugin_active(self.game_dir))
        self.assertEqual(installer.load_manifest(self.game.id), {})

        installer.set_rpgmaker_hide_textbox(self.store, self.game, False)
        self.assertFalse(installer.is_rpgmaker_plugin_active(self.game_dir))
        self.assertEqual((js_dir / "plugins.js").read_text(encoding="utf-8"), original)

    def test_both_plugins_coexist_and_toggle_independently(self) -> None:
        js_dir = self.game_dir / "www" / "js"
        (js_dir / "plugins").mkdir(parents=True)
        original = (
            "var $plugins =\n[\n"
            '{"name":"GamePlugin","status":true,"description":"","parameters":{}}\n'
            "];\n"
        )
        (js_dir / "plugins.js").write_text(original, encoding="utf-8")

        installer.set_rpgmaker_plugin(self.store, self.game, "hide_textbox", True)
        installer.set_rpgmaker_plugin(self.store, self.game, "no_alt_skip", True)
        installer.set_rpgmaker_plugin(self.store, self.game, "save_slots_100", True)
        self.assertTrue(installer.is_rpgmaker_plugin_active(self.game_dir, "hide_textbox"))
        self.assertTrue(installer.is_rpgmaker_plugin_active(self.game_dir, "no_alt_skip"))
        self.assertTrue(installer.is_rpgmaker_plugin_active(self.game_dir, "save_slots_100"))

        # Disabling hide_textbox must keep no_alt_skip and save_slots_100 intact!
        installer.set_rpgmaker_plugin(self.store, self.game, "hide_textbox", False)
        self.assertFalse(installer.is_rpgmaker_plugin_active(self.game_dir, "hide_textbox"))
        self.assertTrue(installer.is_rpgmaker_plugin_active(self.game_dir, "no_alt_skip"))
        self.assertTrue(installer.is_rpgmaker_plugin_active(self.game_dir, "save_slots_100"))
        self.assertFalse((js_dir / "plugins" / rpgmaker.PLUGIN_FILE).exists())
        self.assertTrue((js_dir / "plugins" / rpgmaker.NO_ALT_SKIP_FILE).is_file())
        self.assertTrue((js_dir / "plugins" / rpgmaker.SAVE_SLOTS_100_FILE).is_file())

        # Disabling no_alt_skip must keep save_slots_100 intact
        installer.set_rpgmaker_plugin(self.store, self.game, "no_alt_skip", False)
        self.assertFalse(installer.is_rpgmaker_plugin_active(self.game_dir, "no_alt_skip"))
        self.assertTrue(installer.is_rpgmaker_plugin_active(self.game_dir, "save_slots_100"))
        self.assertFalse((js_dir / "plugins" / rpgmaker.NO_ALT_SKIP_FILE).exists())
        self.assertTrue((js_dir / "plugins" / rpgmaker.SAVE_SLOTS_100_FILE).is_file())

        # Disabling save_slots_100 too restores plugins.js cleanly without touching GamePlugin
        installer.set_rpgmaker_plugin(self.store, self.game, "save_slots_100", False)
        self.assertFalse(installer.is_rpgmaker_plugin_active(self.game_dir, "save_slots_100"))
        self.assertFalse((js_dir / "plugins" / rpgmaker.SAVE_SLOTS_100_FILE).exists())
        self.assertEqual((js_dir / "plugins.js").read_text(encoding="utf-8"), original)

    def test_no_alt_skip_plugin_runtime_blocks_alt_and_keeps_ctrl(self) -> None:
        try:
            from PySide6.QtCore import QCoreApplication
            from PySide6.QtQml import QJSEngine
        except ImportError:
            self.skipTest("PySide6.QtQml indisponivel")

        _app = QCoreApplication.instance() or QCoreApplication([])
        engine = QJSEngine()
        harness = """
        var winListeners = [];
        var docListeners = [];
        var window = {
            addEventListener: function(type, fn, capture) {
                winListeners.push({type: type, fn: fn, capture: capture});
            }
        };
        var document = {
            hidden: false,
            addEventListener: function(type, fn, capture) {
                docListeners.push({type: type, fn: fn, capture: capture});
            }
        };
        function fireWin(type, ev) {
            for (var i = 0; i < winListeners.length; i++) {
                if (winListeners[i].type === type) winListeners[i].fn(ev);
            }
        }
        var Input = {
            keyMapper: { 9: "tab", 13: "ok", 17: "control", 18: "control" },
            _currentState: {},
            clearCalls: 0,
            clear: function() { this._currentState = {}; this.clearCalls++; },
            _onKeyDown: function(ev) {
                var btn = this.keyMapper[ev.keyCode];
                if (btn) this._currentState[btn] = true;
            },
            _onKeyUp: function(ev) {
                var btn = this.keyMapper[ev.keyCode];
                if (btn) this._currentState[btn] = false;
            },
            isPressed: function(name) { return !!this._currentState[name]; },
            isTriggered: function(name) { return !!this._currentState[name]; },
            isRepeated: function(name) { return !!this._currentState[name]; },
            isLongPressed: function(name) { return !!this._currentState[name]; }
        };
        function Window_Message() { this.fastCalls = 0; }
        Window_Message.prototype.isTriggered = function() { return true; };
        Window_Message.prototype.updateShowFast = function() { this.fastCalls++; };
        """
        self.assertFalse(engine.evaluate(harness).isError())
        load_res = engine.evaluate(rpgmaker.NO_ALT_SKIP_SOURCE)
        self.assertFalse(load_res.isError(), load_res.toString())

        scenario = """
        (function() {
            if (18 in Input.keyMapper) throw new Error("keyCode 18 should be removed from keyMapper");
            var msg = new Window_Message();

            // Press Alt (keyCode 18) -> must NOT trigger control, must block message fast-forward
            var altDown = { keyCode: 18, key: "Alt", altKey: true };
            fireWin("keydown", altDown);
            Input._onKeyDown(altDown);
            if (Input.isPressed("control")) throw new Error("Alt must not press control");
            if (msg.isTriggered() !== false) throw new Error("msg.isTriggered must be false during Alt");
            msg.updateShowFast();
            if (msg.fastCalls !== 0) throw new Error("updateShowFast must be blocked during Alt");

            // Press Alt+Enter -> must NOT trigger ok in RPG Maker Input
            var altEnter = { keyCode: 13, key: "Enter", altKey: true };
            fireWin("keydown", altEnter);
            Input._onKeyDown(altEnter);
            if (Input.isPressed("ok")) throw new Error("Alt+Enter must not trigger ok");

            // Window blur (Alt+Tab switches away) -> clears stuck keys and resets altHeld
            fireWin("blur", {});
            if (Input.clearCalls < 1) throw new Error("blur must call Input.clear()");

            // Normal Enter after returning -> works normally
            var enterDown = { keyCode: 13, key: "Enter", altKey: false, ctrlKey: false };
            fireWin("keydown", enterDown);
            Input._onKeyDown(enterDown);
            if (!Input.isPressed("ok")) throw new Error("Normal Enter must trigger ok");
            if (msg.isTriggered() !== true) throw new Error("Normal msg.isTriggered must work");
            Input._onKeyUp(enterDown);

            // Ctrl (keyCode 17) -> MUST STILL WORK for intentional text skipping!
            var ctrlDown = { keyCode: 17, key: "Control", altKey: false, ctrlKey: true };
            fireWin("keydown", ctrlDown);
            Input._onKeyDown(ctrlDown);
            if (!Input.isPressed("control")) throw new Error("Ctrl must still press control");
            msg.updateShowFast();
            if (msg.fastCalls !== 1) throw new Error("Ctrl must still allow updateShowFast");
            return "NO_ALT_OK";
        })();
        """
        res = engine.evaluate(scenario)
        self.assertFalse(res.isError(), res.toString())
        self.assertEqual(res.toString(), "NO_ALT_OK")

    def test_save_slots_100_plugin_runtime_mv_mz_and_preserves_higher_limit(self) -> None:
        try:
            from PySide6.QtCore import QCoreApplication
            from PySide6.QtQml import QJSEngine
        except ImportError:
            self.skipTest("PySide6.QtQml indisponivel")

        _app = QCoreApplication.instance() or QCoreApplication([])

        # 1. RPG Maker MV (default 20 slots, including hardcoded maxItems)
        mv = QJSEngine()
        self.assertFalse(
            mv.evaluate(
                """
                var window = {};
                var Utils = { RPGMAKER_NAME: "MV" };
                var DataManager = { maxSavefiles: function() { return 20; } };
                function Window_SavefileList() {}
                Window_SavefileList.prototype.maxItems = function() { return 20; };
                """
            ).isError()
        )
        mv_load = mv.evaluate(rpgmaker.SAVE_SLOTS_100_SOURCE)
        self.assertFalse(mv_load.isError(), mv_load.toString())
        mv_res = mv.evaluate(
            """
            (function() {
                if (DataManager.maxSavefiles() !== 100) throw new Error("MV maxSavefiles != 100");
                var win = new Window_SavefileList();
                if (win.maxItems() !== 100) throw new Error("MV maxItems != 100");
                return "MV_OK";
            })();
            """
        )
        self.assertFalse(mv_res.isError(), mv_res.toString())
        self.assertEqual(mv_res.toString(), "MV_OK")

        # 2. RPG Maker MZ (slot 0 Autosave + 100 manual slots = 101 maxSavefiles)
        mz = QJSEngine()
        self.assertFalse(
            mz.evaluate(
                """
                var window = {};
                var Utils = { RPGMAKER_NAME: "MZ" };
                var DataManager = { maxSavefiles: function() { return 20; } };
                function Window_SavefileList(autosave) { this._autosave = autosave; }
                Window_SavefileList.prototype.indexToSavefileId = function(i) {
                    return i + (this._autosave ? 0 : 1);
                };
                Window_SavefileList.prototype.maxItems = function() {
                    return DataManager.maxSavefiles() - (this._autosave ? 0 : 1);
                };
                """
            ).isError()
        )
        mz_load = mz.evaluate(rpgmaker.SAVE_SLOTS_100_SOURCE)
        self.assertFalse(mz_load.isError(), mz_load.toString())
        mz_res = mz.evaluate(
            """
            (function() {
                if (DataManager.maxSavefiles() !== 101) throw new Error("MZ maxSavefiles != 101");
                var loadWin = new Window_SavefileList(true);
                if (loadWin.maxItems() !== 101) throw new Error("MZ autosave maxItems != 101");
                var saveWin = new Window_SavefileList(false);
                if (saveWin.maxItems() !== 100) throw new Error("MZ manual maxItems != 100");
                return "MZ_OK";
            })();
            """
        )
        self.assertFalse(mz_res.isError(), mz_res.toString())
        self.assertEqual(mz_res.toString(), "MZ_OK")

        # 3. Never shrinks games that already allow > 100 slots
        high = QJSEngine()
        self.assertFalse(
            high.evaluate(
                """
                var window = {};
                var Utils = { RPGMAKER_NAME: "MV" };
                var DataManager = { maxSavefiles: function() { return 200; } };
                function Window_SavefileList() {}
                Window_SavefileList.prototype.maxItems = function() { return 200; };
                """
            ).isError()
        )
        self.assertFalse(high.evaluate(rpgmaker.SAVE_SLOTS_100_SOURCE).isError())
        high_res = high.evaluate(
            """
            (function() {
                if (DataManager.maxSavefiles() !== 200) throw new Error("Must preserve 200");
                if (new Window_SavefileList().maxItems() !== 200) throw new Error("Must preserve maxItems 200");
                return "HIGH_OK";
            })();
            """
        )
        self.assertFalse(high_res.isError(), high_res.toString())
        self.assertEqual(high_res.toString(), "HIGH_OK")


class NwjsUpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        for patch in (
            mock.patch.object(paths, "DATA_DIR", self.base / "data"),
            mock.patch.object(paths, "CACHE_DIR", self.base / "data" / "cache"),
            mock.patch.object(paths, "DOWNLOAD_DIR", self.base / "data" / "cache" / "downloads"),
            mock.patch.object(paths, "NWJS_CACHE_DIR", self.base / "data" / "cache" / "nwjs"),
            mock.patch.object(paths, "GAME_DATA_DIR", self.base / "data" / "games"),
            mock.patch.object(paths, "BACKUP_DIR", self.base / "data" / "backups"),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def _make_fake_nwjs_zip(self, version: str = "0.120.0", arch: str = "win-x64") -> Path:
        zip_path = self.base / f"nwjs-v{version}-{arch}.zip"
        prefix = f"nwjs-v{version}-{arch}/"
        exe_bytes = NOTEPAD.read_bytes() if NOTEPAD.is_file() else b"MZ" + b"\x00" * 128
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr(prefix + "nw.exe", exe_bytes)
            archive.writestr(prefix + "nw.dll", b"MZ-NEW-NW-DLL")
            archive.writestr(prefix + "icudtl.dat", b"NEW-ICU")
            archive.writestr(prefix + "v8_context_snapshot.bin", b"NEW-V8")
            archive.writestr(prefix + "locales/en-US.pak", b"NEW-EN-US")
        return zip_path

    def test_fix_package_json_repairs_missing_name_and_legacy_issues(self) -> None:
        game_dir = self.base / "Sakura Quest"
        (game_dir / "www" / "icon").mkdir(parents=True)
        (game_dir / "www" / "index.html").write_text("<html></html>", encoding="utf-8")
        (game_dir / "www" / "icon" / "icon.png").write_bytes(b"PNG")
        # BOM + trailing comma + empty name + broken main + obsolete js-flags + list chromium-args + string width
        broken_pkg = (
            '\ufeff{\n'
            '  "name": "",\n'
            '  "main": "missing.html",\n'
            '  "js-flags": "--harmony --harmony_proxies --expose-gc",\n'
            '  "chromium-args": ["--ignore-gpu-blacklist"],\n'
            '  "window": { "title": "", "width": "816", "height": "624", "icon": "bad/icon.png", },\n'
            '}\n'
        )
        (game_dir / "package.json").write_bytes(broken_pkg.encode("utf-8"))
        (game_dir / "www" / "package.json").write_text('{"name":"","main":"index.html"}', encoding="utf-8")

        fixes, _ = nwjs.fix_game_package_jsons(game_dir, write_fn=nwjs._safe_write)  # noqa: SLF001
        self.assertTrue(fixes)

        root_data = json.loads((game_dir / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(root_data["name"], "Sakura_Quest")
        self.assertEqual(root_data["main"], "www/index.html")
        self.assertEqual(root_data["js-flags"], "--expose-gc")
        self.assertIn("--autoplay-policy=no-user-gesture-required", root_data["chromium-args"])
        self.assertIn("--ignore-gpu-blacklist", root_data["chromium-args"])
        self.assertEqual(root_data["window"]["width"], 816)
        self.assertEqual(root_data["window"]["height"], 624)
        self.assertEqual(root_data["window"]["icon"], "www/icon/icon.png")
        self.assertEqual(root_data["inject_js_start"], nwjs.COMPAT_SHIM_FILE)
        self.assertTrue((game_dir / nwjs.COMPAT_SHIM_FILE).is_file())

        www_data = json.loads((game_dir / "www" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(www_data["name"], "Sakura_Quest")
        self.assertEqual(www_data["main"], "index.html")

    def test_cache_update_reuse_and_restore_game_nwjs(self) -> None:
        zip_path = self._make_fake_nwjs_zip("0.120.0", "win-x64")
        release = nwjs.build_release("0.120.0", "win-x64")
        cached = nwjs.cache_from_archive(zip_path, release)
        self.assertEqual(cached.version, "0.120.0")
        self.assertEqual(len(nwjs.list_cached()), 1)

        game_dir = self.base / "Old MV Game"
        (game_dir / "www").mkdir(parents=True)
        (game_dir / "locales").mkdir()
        exe = game_dir / "Game.exe"
        original_exe = b"MZ-OLD-GAME-EXE"
        exe.write_bytes(original_exe)
        (game_dir / "nw.dll").write_bytes(b"OLD-NW-DLL")
        (game_dir / "nw.pak").write_bytes(b"LEGACY-PAK")
        (game_dir / "locales" / "en-US.pak").write_bytes(b"OLD-EN-US")
        (game_dir / "www" / "index.html").write_text("<html>game</html>", encoding="utf-8")
        original_pkg = '{"name":"","main":"www/index.html"}'
        (game_dir / "package.json").write_text(original_pkg, encoding="utf-8")
        # Simulate an installed ReShade DLL that must NOT be overwritten
        (game_dir / "dxgi.dll").write_bytes(b"MZ-fake-ReShade.ini-payload")

        store = StoreStub()
        game = Game(id=game_id_for(exe), name="Old MV Game", exe=str(exe), engine_key="rpgmaker_mv")

        # Update uses cached build without touching network
        with mock.patch.object(nwjs, "fetch_latest_release", side_effect=AssertionError("should use cache")):
            report = installer.update_nwjs(store, game)

        self.assertEqual(report.version, "0.120.0")
        self.assertEqual((game_dir / "nw.dll").read_bytes(), b"MZ-NEW-NW-DLL")
        self.assertFalse((game_dir / "nw.pak").exists(), "legacy nw.pak should be pruned")
        self.assertTrue((game_dir / "v8_context_snapshot.bin").is_file())
        self.assertEqual((game_dir / "dxgi.dll").read_bytes(), b"MZ-fake-ReShade.ini-payload")
        self.assertEqual((game_dir / "www" / "index.html").read_text(encoding="utf-8"), "<html>game</html>")
        fixed_pkg = json.loads((game_dir / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(fixed_pkg["name"], "Old_MV_Game")
        self.assertTrue(nwjs.has_backup(game.id))

        # Restore reverts Game.exe, nw.dll, legacy nw.pak, and package.json cleanly
        restored = installer.restore_nwjs(store, game)
        self.assertTrue(restored)
        self.assertEqual(exe.read_bytes(), original_exe)
        self.assertEqual((game_dir / "nw.dll").read_bytes(), b"OLD-NW-DLL")
        self.assertEqual((game_dir / "nw.pak").read_bytes(), b"LEGACY-PAK")
        self.assertEqual((game_dir / "package.json").read_text(encoding="utf-8"), original_pkg)
        self.assertFalse((game_dir / "v8_context_snapshot.bin").exists())
        self.assertFalse((game_dir / nwjs.COMPAT_SHIM_FILE).exists())
        self.assertFalse(nwjs.has_backup(game.id))

    def test_compat_shim_js_polyfills_process_main_module(self) -> None:
        try:
            from PySide6.QtCore import QCoreApplication
            from PySide6.QtQml import QJSEngine
        except ImportError:
            self.skipTest("PySide6.QtQml indisponivel")

        _app = QCoreApplication.instance() or QCoreApplication([])
        engine = QJSEngine()
        harness = """
        var process = { execPath: "C:/Games/MyMV/Game.exe", cwd: function() { return "C:/Other"; } };
        var nw = { App: { manifest: { main: "www/index.html" } } };
        function require(name) {
            if (name !== "path") throw new Error("unexpected require");
            return {
                dirname: function(p) { return p.replace(/\\/[^\\/]+$/, ""); },
                resolve: function(a, b) { return a + "/" + b; }
            };
        }
        """
        self.assertFalse(engine.evaluate(harness).isError())
        shim_res = engine.evaluate(nwjs.COMPAT_SHIM_SOURCE)
        self.assertFalse(shim_res.isError(), shim_res.toString())
        filename = engine.evaluate("process.mainModule && process.mainModule.filename").toString()
        self.assertEqual(filename, "C:/Games/MyMV/www/index.html")


class RenpyUrmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        for patch in (
            mock.patch.object(paths, "DATA_DIR", self.base / "data"),
            mock.patch.object(paths, "CACHE_DIR", self.base / "data" / "cache"),
            mock.patch.object(paths, "DOWNLOAD_DIR", self.base / "data" / "cache" / "downloads"),
            mock.patch.object(paths, "URM_CACHE_DIR", self.base / "data" / "cache" / "urm"),
            mock.patch.object(paths, "GAME_DATA_DIR", self.base / "data" / "games"),
            mock.patch.object(paths, "BACKUP_DIR", self.base / "data" / "backups"),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def _make_fake_urm_zip(self, version: str = "2.6.2", payload: bytes | None = None) -> Path:
        zip_path = self.base / f"0x52_URM_{version}.zip"
        rpa_bytes = payload if payload is not None else (b"RPA-2.0 0000000000000100\n" + b"X" * 2048)
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr(renpy.URM_FILENAME, rpa_bytes)
        return zip_path

    def _make_renpy_game(self, folder_name: str = "My RenPy VN") -> tuple[Path, Game]:
        game_dir = self.base / folder_name
        (game_dir / "game").mkdir(parents=True)
        (game_dir / "renpy" / "common").mkdir(parents=True)
        (game_dir / "game" / "script.rpyc").write_bytes(b"RENPY")
        (game_dir / "renpy" / "common" / "00start.rpy").write_text("# renpy\n", encoding="utf-8")
        game = make_game(game_dir, name=folder_name)
        game.engine_key = "renpy"
        return game_dir, game

    def test_extract_and_cache_validates_rpa_header(self) -> None:
        zip_path = self._make_fake_urm_zip("2.6.2")
        release = renpy.UrmRelease(version="2.6.2", version_id=1223, url="https://api.0x52.dev/modversions/1223/download")
        cached = renpy.cache_from_archive(zip_path, release)
        self.assertEqual(cached.version, "2.6.2")
        self.assertTrue(cached.rpa_path.is_file())
        self.assertEqual(len(renpy.list_cached()), 1)
        self.assertEqual(renpy.verified_rpa(cached), cached.rpa_path)

        bad_zip = self.base / "bad.zip"
        with zipfile.ZipFile(bad_zip, "w") as archive:
            archive.writestr(renpy.URM_FILENAME, b"NOT_AN_RPA_FILE" * 200)
        with self.assertRaises(renpy.RenpyModError):
            renpy.extract_rpa(bad_zip)

    def test_pick_latest_stable_release_ignores_beta_and_unpublished(self) -> None:
        entries = [
            {"id": 1200, "versionName": "2.5.0", "channel": "stable", "isPublished": True},
            {"id": 1223, "versionName": "2.6.2", "channel": "stable", "isPublished": True},
            {"id": 1224, "versionName": "2.7.0", "channel": "beta", "isPublished": True},
            {"id": 1225, "versionName": "2.8.0", "channel": "stable", "isPublished": False},
        ]
        picked = renpy._pick_release_from_entries(entries)  # noqa: SLF001
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked.version, "2.6.2")
        self.assertEqual(picked.version_id, 1223)
        self.assertEqual(picked.url, "https://api.0x52.dev/modversions/1223/download")

    def test_detect_finds_renpy_game_dir(self) -> None:
        game_dir, game = self._make_renpy_game()
        analysis = detect.analyze(game.exe_path)
        self.assertEqual(analysis.engine.key, "renpy")
        self.assertEqual(analysis.renpy_game_dir, "game")
        self.assertEqual(renpy.find_game_dir(game_dir), game_dir / "game")

    def test_standalone_toggle_without_reshade_uses_cache_and_cleans_up(self) -> None:
        zip_path = self._make_fake_urm_zip("2.6.2")
        release = renpy.UrmRelease(version="2.6.2", version_id=1223, url="https://api.0x52.dev/modversions/1223/download")
        renpy.cache_from_archive(zip_path, release)

        game_dir, game = self._make_renpy_game()
        store = StoreStub()
        self.assertFalse(installer.is_renpy_urm_active(game_dir))

        with mock.patch.object(renpy, "fetch_latest_release", side_effect=AssertionError("should use cache")):
            rel_path = installer.set_renpy_urm(store, game, True)

        self.assertEqual(rel_path, "game/0x52_URM.rpa")
        self.assertTrue(installer.is_renpy_urm_active(game_dir))
        self.assertTrue(game.renpy_urm)
        self.assertEqual(installer.load_manifest(game.id), {})
        self.assertEqual(installer.load_renpy_meta(game.id).get("version"), "2.6.2")

        installer.set_renpy_urm(store, game, False)
        self.assertFalse(installer.is_renpy_urm_active(game_dir))
        self.assertFalse((game_dir / "game" / renpy.URM_FILENAME).exists())
        self.assertFalse(game.renpy_urm)
        self.assertEqual(installer.load_renpy_meta(game.id), {})

    @unittest.skipUnless(CACHED is not None, "cache do ReShade vazio")
    def test_reshade_install_inspect_and_uninstall_with_renpy_urm(self) -> None:
        zip_path = self._make_fake_urm_zip("2.6.2")
        release = renpy.UrmRelease(version="2.6.2", version_id=1223, url="https://api.0x52.dev/modversions/1223/download")
        renpy.cache_from_archive(zip_path, release)

        game_dir, game = self._make_renpy_game("RenPy With ReShade")
        store = StoreStub()
        report = installer.install(store, game, InstallOptions(variant="cnn_m", renpy_urm=True))
        self.assertEqual(report.renpy_urm, "game/0x52_URM.rpa")
        self.assertEqual(report.renpy_urm_version, "2.6.2")
        self.assertTrue((game_dir / "game" / renpy.URM_FILENAME).is_file())

        state = installer.inspect(game)
        self.assertTrue(state.urm_ok)
        self.assertEqual(state.renpy_urm, "game/0x52_URM.rpa")

        # Removing the rpa manually is flagged by inspect()
        (game_dir / "game" / renpy.URM_FILENAME).unlink()
        missing_state = installer.inspect(game)
        self.assertFalse(missing_state.urm_ok)
        self.assertTrue(any(renpy.URM_FILENAME in problem for problem in missing_state.problems))

        # Reinstall restores it, then uninstall removes both ReShade and URM cleanly
        installer.install(store, game, InstallOptions(variant="cnn_m", renpy_urm=True))
        self.assertTrue((game_dir / "game" / renpy.URM_FILENAME).is_file())
        installer.uninstall(store, game)
        self.assertFalse((game_dir / "game" / renpy.URM_FILENAME).exists())


class I18nTests(unittest.TestCase):
    def tearDown(self) -> None:
        from anishade import i18n

        i18n.set_language(i18n.DEFAULT_LANGUAGE)

    def test_default_language_is_english(self) -> None:
        from anishade import i18n
        from anishade.store import Settings

        self.assertEqual(i18n.DEFAULT_LANGUAGE, "en")
        self.assertEqual(Settings().language, "en")
        self.assertEqual(i18n.normalize_language(""), "en")
        self.assertEqual(i18n.normalize_language("pt-br"), "pt_BR")
        self.assertEqual(i18n.normalize_language("unknown"), "en")

    def test_catalogs_have_matching_keys_and_placeholders(self) -> None:
        import string

        from anishade import i18n

        en_keys = set(i18n._TRANSLATIONS["en"])
        pt_keys = set(i18n._TRANSLATIONS["pt_BR"])
        self.assertEqual(en_keys, pt_keys)

        formatter = string.Formatter()
        for key in en_keys:
            en_fields = {
                field_name
                for _, field_name, _, _ in formatter.parse(i18n._TRANSLATIONS["en"][key])
                if field_name is not None
            }
            pt_fields = {
                field_name
                for _, field_name, _, _ in formatter.parse(i18n._TRANSLATIONS["pt_BR"][key])
                if field_name is not None
            }
            self.assertEqual(en_fields, pt_fields, f"Placeholder mismatch for key {key!r}")

    def test_variants_and_engines_follow_active_language(self) -> None:
        from anishade import anime4k, engines, i18n

        i18n.set_language("en")
        self.assertIn("balanced", anime4k.variant("cnn_m").label)
        self.assertEqual(engines.ENGINES["unknown"].name, "Unknown")

        i18n.set_language("pt_BR")
        self.assertIn("equilibrado", anime4k.variant("cnn_m").label)
        self.assertEqual(engines.ENGINES["unknown"].name, "Desconhecida")

    def test_ui_switches_language_live_via_settings(self) -> None:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from anishade import i18n
        from anishade.store import Settings
        from anishade.ui.main_window import MainWindow
        from anishade.ui.settings_dialog import SettingsDialog

        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)

        store = StoreStub()
        store.settings = Settings()
        store.games = []
        store.sorted_games = lambda: []
        store.save_settings = lambda: None
        store.get = lambda _id: None

        i18n.set_language("en")
        win = MainWindow(store)
        try:
            self.assertEqual(win.add_button.text(), "Add Game")
            self.assertEqual(win.settings_button.text(), "Settings")

            dlg = SettingsDialog(store, win)
            self.assertEqual(dlg.language_combo.currentData(), "en")
            pt_index = dlg.language_combo.findData("pt_BR")
            self.assertGreaterEqual(pt_index, 0)
            dlg.language_combo.setCurrentIndex(pt_index)
            dlg._save()
            self.assertEqual(store.settings.language, "pt_BR")

            win.retranslate_ui()
            self.assertEqual(win.add_button.text(), "Adicionar jogo")
            self.assertEqual(win.settings_button.text(), "Configurações")

            dlg2 = SettingsDialog(store, win)
            self.assertEqual(dlg2.windowTitle(), "Configurações — AniShade")
            en_index = dlg2.language_combo.findData("en")
            dlg2.language_combo.setCurrentIndex(en_index)
            dlg2._save()
            win.retranslate_ui()
            self.assertEqual(win.add_button.text(), "Add Game")
        finally:
            win.close()


if __name__ == "__main__":
    unittest.main()
