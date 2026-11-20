"""RPG Maker MV/MZ plugin support: hide/show the message textbox with the H key."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import winapi

PLUGIN_NAME = "AniShade_HideTextbox"
PLUGIN_FILE = f"{PLUGIN_NAME}.js"
PLUGIN_DESCRIPTION = "AniShade: Hide/show the message textbox with the H key."

NO_ALT_SKIP_NAME = "AniShade_NoAltSkip"
NO_ALT_SKIP_FILE = f"{NO_ALT_SKIP_NAME}.js"
NO_ALT_SKIP_DESCRIPTION = "AniShade: Prevent Alt / Alt+Tab from skipping message text."

SAVE_SLOTS_100_NAME = "AniShade_SaveSlots100"
SAVE_SLOTS_100_FILE = f"{SAVE_SLOTS_100_NAME}.js"
SAVE_SLOTS_100_DESCRIPTION = "AniShade: Expand the save menu to 100 manual save slots."

SUPPORTED_ENGINES = ("rpgmaker_mv",)

#: Pure ES5 JavaScript so it works on every RPG Maker MV (including NW.js 0.12)
#: and RPG Maker MZ build without transpilation.
PLUGIN_SOURCE = r"""/*:
 * @target MZ
 * @plugindesc [AniShade] Hide/show the message textbox with the H key.
 * @author AniShade
 * @help
 * Press the H key while a message textbox is open to hide it.
 * Press H again to show the textbox and resume reading.
 *
 * Compatible with RPG Maker MV and RPG Maker MZ.
 * Installed and managed automatically by AniShade.
 */

(function() {
    "use strict";

    if (window.__AniShadeHideTextboxLoaded) {
        return;
    }
    window.__AniShadeHideTextboxLoaded = true;

    var togglePending = false;

    function isHideKey(event) {
        if (!event || event.repeat || event.ctrlKey || event.altKey || event.metaKey) {
            return false;
        }
        var target = event.target;
        if (target && target.tagName) {
            var tag = target.tagName.toUpperCase();
            if (tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable) {
                return false;
            }
        }
        if (typeof event.key === "string" && event.key.toLowerCase() === "h") {
            return true;
        }
        if (event.keyCode === 72 || event.which === 72) {
            return true;
        }
        if (event.code === "KeyH" && (event.key === "Process" || event.key === "Unidentified")) {
            return true;
        }
        return false;
    }

    function getActiveMessageWindow() {
        var scene = typeof SceneManager !== "undefined" ? SceneManager._scene : null;
        if (!scene) {
            return null;
        }
        if (scene._messageWindow) {
            return scene._messageWindow;
        }
        var layer = scene._windowLayer;
        if (layer && Array.isArray(layer.children)) {
            for (var i = 0; i < layer.children.length; i++) {
                if (typeof Window_Message !== "undefined" && layer.children[i] instanceof Window_Message) {
                    return layer.children[i];
                }
            }
        }
        return null;
    }

    function collectRelatedWindows(msgWin) {
        var result = [];
        function add(obj) {
            if (obj && obj !== msgWin && result.indexOf(obj) === -1) {
                result.push(obj);
            }
        }

        if (typeof msgWin.subWindows === "function") {
            var subs = msgWin.subWindows();
            if (Array.isArray(subs)) {
                for (var i = 0; i < subs.length; i++) {
                    add(subs[i]);
                }
            }
        }

        var winProps = [
            "_nameBoxWindow",
            "_nameWindow",
            "_goldWindow",
            "_choiceWindow",
            "_choiceListWindow",
            "_numberWindow",
            "_numberInputWindow",
            "_itemWindow",
            "_eventItemWindow",
            "_galvMsgBg",
            "_msgBackground",
            "_messageBackground"
        ];
        for (var j = 0; j < winProps.length; j++) {
            add(msgWin[winProps[j]]);
        }

        var scene = typeof SceneManager !== "undefined" ? SceneManager._scene : null;
        if (scene) {
            var sceneProps = [
                "_nameBoxWindow",
                "_nameWindow",
                "_choiceListWindow",
                "_numberInputWindow",
                "_eventItemWindow",
                "_goldWindow",
                "_galvMsgBg",
                "_msgBackground",
                "_messageBackground"
            ];
            for (var k = 0; k < sceneProps.length; k++) {
                add(scene[sceneProps[k]]);
            }
        }

        return result;
    }

    function isWindowOpen(win) {
        if (!win || !win.visible) {
            return false;
        }
        if (typeof win.isClosing === "function" && win.isClosing()) {
            return false;
        }
        if (typeof win.isClosed === "function") {
            return !win.isClosed();
        }
        if (typeof win.openness === "number") {
            return win.openness > 0;
        }
        return true;
    }

    function canHideMessage(msgWin) {
        if (!msgWin) {
            return false;
        }
        if (isWindowOpen(msgWin)) {
            return true;
        }
        var related = collectRelatedWindows(msgWin);
        for (var i = 0; i < related.length; i++) {
            if (isWindowOpen(related[i])) {
                return true;
            }
        }
        return false;
    }

    function hideTextbox(msgWin) {
        var saved = [];
        saved.push({
            obj: msgWin,
            visible: msgWin.visible,
            hasActive: "active" in msgWin,
            active: msgWin.active
        });
        msgWin.visible = false;

        var related = collectRelatedWindows(msgWin);
        for (var i = 0; i < related.length; i++) {
            var win = related[i];
            saved.push({
                obj: win,
                visible: win.visible,
                hasActive: "active" in win,
                active: win.active
            });
            win.visible = false;
            if ("active" in win) {
                win.active = false;
            }
        }

        msgWin._aniShadeHidden = true;
        msgWin._aniShadeSaved = saved;
    }

    function enforceHidden(msgWin) {
        if (!msgWin || !msgWin._aniShadeHidden) {
            return;
        }
        msgWin.visible = false;
        var saved = msgWin._aniShadeSaved;
        if (saved) {
            for (var i = 0; i < saved.length; i++) {
                var entry = saved[i];
                if (entry.obj) {
                    entry.obj.visible = false;
                    if (entry.hasActive && entry.obj !== msgWin) {
                        entry.obj.active = false;
                    }
                }
            }
        }
    }

    function showTextbox(msgWin) {
        if (!msgWin || !msgWin._aniShadeHidden) {
            return;
        }
        msgWin._aniShadeHidden = false;
        var saved = msgWin._aniShadeSaved || [];
        msgWin._aniShadeSaved = null;
        for (var i = 0; i < saved.length; i++) {
            var entry = saved[i];
            if (entry.obj) {
                entry.obj.visible = entry.visible;
                if (entry.hasActive && entry.obj !== msgWin) {
                    entry.obj.active = entry.active;
                }
            }
        }
    }

    document.addEventListener("keydown", function(event) {
        if (!isHideKey(event)) {
            return;
        }
        var msgWin = getActiveMessageWindow();
        if (!msgWin) {
            return;
        }
        if (msgWin._aniShadeHidden || canHideMessage(msgWin)) {
            togglePending = true;
            if (typeof event.preventDefault === "function") {
                event.preventDefault();
            }
        }
    }, true);

    if (typeof Window_Message !== "undefined") {
        var _Window_Message_update = Window_Message.prototype.update;
        Window_Message.prototype.update = function() {
            if (this._aniShadeHidden) {
                if (togglePending) {
                    togglePending = false;
                    showTextbox(this);
                    return;
                }
                if (
                    typeof $gameMessage !== "undefined" &&
                    $gameMessage &&
                    !$gameMessage.isBusy() &&
                    typeof this.isClosed === "function" &&
                    this.isClosed()
                ) {
                    showTextbox(this);
                    _Window_Message_update.call(this);
                    return;
                }
                enforceHidden(this);
                return;
            }

            if (togglePending) {
                togglePending = false;
                if (canHideMessage(this)) {
                    hideTextbox(this);
                    return;
                }
            }

            _Window_Message_update.call(this);
        };

        if (typeof Window_Message.prototype.isTriggered === "function") {
            var _Window_Message_isTriggered = Window_Message.prototype.isTriggered;
            Window_Message.prototype.isTriggered = function() {
                if (this._aniShadeHidden) {
                    return false;
                }
                return _Window_Message_isTriggered.call(this);
            };
        }

        if (typeof Window_Message.prototype.terminateMessage === "function") {
            var _Window_Message_terminateMessage = Window_Message.prototype.terminateMessage;
            Window_Message.prototype.terminateMessage = function() {
                if (this._aniShadeHidden) {
                    showTextbox(this);
                }
                _Window_Message_terminateMessage.call(this);
            };
        }
    }

    if (typeof Scene_Base !== "undefined") {
        var _Scene_Base_update = Scene_Base.prototype.update;
        Scene_Base.prototype.update = function() {
            _Scene_Base_update.call(this);
            var msgWin = getActiveMessageWindow();
            if (msgWin && msgWin._aniShadeHidden) {
                enforceHidden(msgWin);
            }
            togglePending = false;
        };
    }
})();
"""

#: Pure ES5 plugin that unbinds Alt from RPG Maker's Input system so Alt / Alt+Tab /
#: Alt+Enter never skip dialogue text (while keeping Ctrl text-skipping intact).
NO_ALT_SKIP_SOURCE = r"""/*:
 * @target MZ
 * @plugindesc [AniShade] Prevent the Alt key (and Alt+Tab / Alt+Enter) from skipping dialogue text.
 * @author AniShade
 * @help
 * In RPG Maker MV and MZ, the Alt key (keyCode 18) is mapped to "control"
 * alongside Ctrl, which causes Alt+Tab and Alt+Enter to skip dialogue text.
 * This plugin unbinds Alt from RPG Maker's Input system and clears stuck
 * keys on window blur while keeping Ctrl text-skipping working normally.
 *
 * Compatible with RPG Maker MV and RPG Maker MZ.
 * Installed and managed automatically by AniShade.
 */

(function() {
    "use strict";

    if (window.__AniShadeNoAltSkipLoaded) {
        return;
    }
    window.__AniShadeNoAltSkipLoaded = true;

    var altHeld = false;
    var ctrlHeld = false;

    function isAltEvent(event) {
        if (!event) {
            return false;
        }
        return (
            event.keyCode === 18 ||
            event.which === 18 ||
            event.key === "Alt" ||
            event.code === "AltLeft" ||
            event.code === "AltRight"
        );
    }

    function isCtrlEvent(event) {
        if (!event) {
            return false;
        }
        return (
            event.keyCode === 17 ||
            event.which === 17 ||
            event.key === "Control" ||
            event.code === "ControlLeft" ||
            event.code === "ControlRight"
        );
    }

    function unbindAltKeyMapper() {
        if (typeof Input !== "undefined" && Input && Input.keyMapper) {
            if (18 in Input.keyMapper) {
                delete Input.keyMapper[18];
            }
            if ("18" in Input.keyMapper) {
                delete Input.keyMapper["18"];
            }
        }
    }

    function resetModifierState() {
        altHeld = false;
        ctrlHeld = false;
        if (typeof Input !== "undefined" && Input && typeof Input.clear === "function") {
            Input.clear();
        }
    }

    unbindAltKeyMapper();

    window.addEventListener("keydown", function(event) {
        if (isAltEvent(event) || (event && event.altKey)) {
            altHeld = true;
        } else if (event && !event.altKey) {
            altHeld = false;
        }
        if (isCtrlEvent(event) || (event && event.ctrlKey)) {
            ctrlHeld = true;
        } else if (event && !event.ctrlKey) {
            ctrlHeld = false;
        }
    }, true);

    window.addEventListener("keyup", function(event) {
        if (isAltEvent(event)) {
            altHeld = false;
        }
        if (isCtrlEvent(event)) {
            ctrlHeld = false;
        }
    }, true);

    window.addEventListener("blur", resetModifierState);
    if (typeof document !== "undefined" && document.addEventListener) {
        document.addEventListener("visibilitychange", function() {
            if (document.hidden) {
                resetModifierState();
            }
        });
    }

    if (typeof Input !== "undefined" && Input) {
        if (typeof Input._onKeyDown === "function") {
            var _Input_onKeyDown = Input._onKeyDown;
            Input._onKeyDown = function(event) {
                if (isAltEvent(event) || (event && event.altKey)) {
                    return;
                }
                _Input_onKeyDown.call(this, event);
            };
        }

        if (typeof Input._onKeyUp === "function") {
            var _Input_onKeyUp = Input._onKeyUp;
            Input._onKeyUp = function(event) {
                if (isAltEvent(event)) {
                    return;
                }
                _Input_onKeyUp.call(this, event);
            };
        }

        var blockedDuringAlt = ["control", "skip", "ok", "tab"];
        function shouldBlockAction(keyName) {
            if (!altHeld || ctrlHeld) {
                return false;
            }
            return blockedDuringAlt.indexOf(keyName) !== -1;
        }

        ["isPressed", "isTriggered", "isRepeated", "isLongPressed"].forEach(function(fnName) {
            if (typeof Input[fnName] === "function") {
                var original = Input[fnName];
                Input[fnName] = function(keyName) {
                    if (shouldBlockAction(keyName)) {
                        return false;
                    }
                    return original.call(this, keyName);
                };
            }
        });
    }

    if (typeof Scene_Boot !== "undefined" && Scene_Boot.prototype && typeof Scene_Boot.prototype.start === "function") {
        var _Scene_Boot_start = Scene_Boot.prototype.start;
        Scene_Boot.prototype.start = function() {
            unbindAltKeyMapper();
            _Scene_Boot_start.call(this);
        };
    }

    if (typeof Window_Message !== "undefined" && Window_Message.prototype) {
        if (typeof Window_Message.prototype.isTriggered === "function") {
            var _Window_Message_isTriggered = Window_Message.prototype.isTriggered;
            Window_Message.prototype.isTriggered = function() {
                if (altHeld && !ctrlHeld) {
                    return false;
                }
                return _Window_Message_isTriggered.call(this);
            };
        }
        if (typeof Window_Message.prototype.updateShowFast === "function") {
            var _Window_Message_updateShowFast = Window_Message.prototype.updateShowFast;
            Window_Message.prototype.updateShowFast = function() {
                if (altHeld && !ctrlHeld) {
                    return;
                }
                _Window_Message_updateShowFast.call(this);
            };
        }
    }
})();
"""

#: Pure ES5 plugin that expands RPG Maker MV and MZ save screens to 100 manual
#: save slots (101 total on MZ so Autosave slot 0 + manual slots 1..100 all fit).
SAVE_SLOTS_100_SOURCE = r"""/*:
 * @target MZ
 * @plugindesc [AniShade] Expand save slots to 100 manual slots (MV and MZ).
 * @author AniShade
 * @help
 * Expands the maximum number of save slots to 100 manual slots
 * (100 in RPG Maker MV; Autosave + 100 manual slots in RPG Maker MZ).
 * Never shrinks the limit if the game already allows more than 100 slots.
 *
 * Compatible with RPG Maker MV and RPG Maker MZ.
 * Installed and managed automatically by AniShade.
 */

(function() {
    "use strict";

    if (window.__AniShadeSaveSlots100Loaded) {
        return;
    }
    window.__AniShadeSaveSlots100Loaded = true;

    var MANUAL_SLOTS = 100;

    function isMzEngine() {
        if (typeof Utils !== "undefined" && Utils && Utils.RPGMAKER_NAME === "MZ") {
            return true;
        }
        if (
            typeof Window_SavefileList !== "undefined" &&
            Window_SavefileList.prototype &&
            typeof Window_SavefileList.prototype.indexToSavefileId === "function"
        ) {
            return true;
        }
        return false;
    }

    var targetMaxFiles = isMzEngine() ? MANUAL_SLOTS + 1 : MANUAL_SLOTS;

    if (typeof DataManager !== "undefined" && DataManager) {
        var _DataManager_maxSavefiles = DataManager.maxSavefiles;
        DataManager.maxSavefiles = function() {
            var base = typeof _DataManager_maxSavefiles === "function"
                ? Number(_DataManager_maxSavefiles.call(this)) || 0
                : 0;
            return Math.max(base, targetMaxFiles);
        };
    }

    if (typeof Window_SavefileList !== "undefined" && Window_SavefileList.prototype) {
        var _Window_SavefileList_maxItems = Window_SavefileList.prototype.maxItems;
        Window_SavefileList.prototype.maxItems = function() {
            var base = typeof _Window_SavefileList_maxItems === "function"
                ? Number(_Window_SavefileList_maxItems.call(this)) || 0
                : 0;
            var minimum = isMzEngine()
                ? (this._autosave ? MANUAL_SLOTS + 1 : MANUAL_SLOTS)
                : MANUAL_SLOTS;
            return Math.max(base, minimum);
        };
    }
})();
"""


@dataclass(frozen=True)
class PluginSpec:
    key: str
    name: str
    description: str
    source: str

    @property
    def filename(self) -> str:
        return f"{self.name}.js"


PLUGINS: dict[str, PluginSpec] = {
    "hide_textbox": PluginSpec(
        key="hide_textbox",
        name=PLUGIN_NAME,
        description=PLUGIN_DESCRIPTION,
        source=PLUGIN_SOURCE,
    ),
    "no_alt_skip": PluginSpec(
        key="no_alt_skip",
        name=NO_ALT_SKIP_NAME,
        description=NO_ALT_SKIP_DESCRIPTION,
        source=NO_ALT_SKIP_SOURCE,
    ),
    "save_slots_100": PluginSpec(
        key="save_slots_100",
        name=SAVE_SLOTS_100_NAME,
        description=SAVE_SLOTS_100_DESCRIPTION,
        source=SAVE_SLOTS_100_SOURCE,
    ),
}
ALL_MANAGED_NAMES: tuple[str, ...] = tuple(spec.name for spec in PLUGINS.values())


@dataclass
class PluginInstallResult:
    installed: bool = False
    name: str = PLUGIN_NAME
    plugin_path: str = ""
    plugin_sha256: str = ""
    plugins_js_path: str = ""
    plugins_js_sha256: str = ""
    plugins_js_backup: str = ""
    warning: str = ""

    def to_manifest(self) -> dict:
        return {
            "name": self.name,
            "plugin_path": self.plugin_path,
            "plugin_sha256": self.plugin_sha256,
            "plugins_js_path": self.plugins_js_path,
            "plugins_js_sha256": self.plugins_js_sha256,
            "plugins_js_backup": self.plugins_js_backup,
        }


def is_supported_engine(engine_key: str) -> bool:
    return engine_key in SUPPORTED_ENGINES


# ---------------------------------------------------------------------------
# plugins.js JS-aware scanner
# ---------------------------------------------------------------------------

def _is_ident(ch: str) -> bool:
    return ch.isalnum() or ch in ("_", "$")


def _skip_string(text: str, pos: int, limit: int) -> int:
    quote = text[pos]
    pos += 1
    while pos < limit:
        ch = text[pos]
        if ch == "\\":
            pos += 2
            continue
        if ch == quote:
            return pos + 1
        pos += 1
    return limit


def _skip_ws_and_comments(text: str, pos: int, limit: int) -> int:
    while pos < limit:
        ch = text[pos]
        if ch.isspace():
            pos += 1
        elif ch == "/" and pos + 1 < limit and text[pos + 1] == "/":
            newline = text.find("\n", pos + 2, limit)
            pos = limit if newline < 0 else newline + 1
        elif ch == "/" and pos + 1 < limit and text[pos + 1] == "*":
            end = text.find("*/", pos + 2, limit)
            pos = limit if end < 0 else end + 2
        else:
            break
    return pos


def _find_plugins_array(text: str) -> tuple[int, int] | None:
    """Return (open_bracket_idx, close_bracket_idx) for the `$plugins = [...]` array."""
    length = len(text)
    pos = 0
    open_idx = -1

    while pos < length:
        pos = _skip_ws_and_comments(text, pos, length)
        if pos >= length:
            break
        ch = text[pos]
        if ch in ('"', "'", "`"):
            pos = _skip_string(text, pos, length)
            continue
        if text.startswith("$plugins", pos):
            before_ok = pos == 0 or not _is_ident(text[pos - 1])
            after = pos + len("$plugins")
            after_ok = after >= length or not _is_ident(text[after])
            if before_ok and after_ok:
                scan = _skip_ws_and_comments(text, after, length)
                if scan < length and text[scan] == "=" and (scan + 1 >= length or text[scan + 1] != "="):
                    scan = _skip_ws_and_comments(text, scan + 1, length)
                    if scan < length and text[scan] == "[":
                        open_idx = scan
                        break
        pos += 1

    if open_idx < 0:
        return None

    depth = 0
    pos = open_idx
    while pos < length:
        ch = text[pos]
        if ch in ('"', "'", "`"):
            pos = _skip_string(text, pos, length)
            continue
        if ch == "/" and pos + 1 < length and text[pos + 1] in ("/", "*"):
            pos = _skip_ws_and_comments(text, pos, length)
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return open_idx, pos
        pos += 1
    return None


def _scan_array_elements(text: str, open_idx: int, close_idx: int) -> list[tuple[int, int]]:
    """Return [(start, end), ...] for each top-level element inside `$plugins`."""
    elements: list[tuple[int, int]] = []
    pos = open_idx + 1
    while pos < close_idx:
        pos = _skip_ws_and_comments(text, pos, close_idx)
        if pos >= close_idx:
            break
        if text[pos] == ",":
            pos += 1
            continue

        start = pos
        depth = 0
        last_non_ws = pos
        while pos < close_idx:
            ch = text[pos]
            if ch in ('"', "'", "`"):
                pos = _skip_string(text, pos, close_idx)
                last_non_ws = pos
                continue
            if ch == "/" and pos + 1 < close_idx and text[pos + 1] in ("/", "*"):
                pos = _skip_ws_and_comments(text, pos, close_idx)
                continue
            if ch in ("{", "[", "("):
                depth += 1
                pos += 1
                last_non_ws = pos
                continue
            if ch in ("}", "]", ")"):
                depth = max(0, depth - 1)
                pos += 1
                last_non_ws = pos
                continue
            if ch == "," and depth == 0:
                break
            if not ch.isspace():
                last_non_ws = pos + 1
            pos += 1

        if last_non_ws > start:
            elements.append((start, last_non_ws))
        if pos < close_idx and text[pos] == ",":
            pos += 1
    return elements


def _find_comma_between(text: str, start: int, end: int) -> int:
    """Return index of first top-level comma in text[start:end], or -1."""
    pos = start
    while pos < end:
        pos = _skip_ws_and_comments(text, pos, end)
        if pos >= end:
            break
        if text[pos] == ",":
            return pos
        pos += 1
    return -1


_NAME_RE = re.compile(r'["\']?name["\']?\s*:\s*(["\'])((?:\\.|(?!\1).)*)\1')
_STATUS_RE = re.compile(r'["\']?status["\']?\s*:\s*(true|false)\b', re.I)


def _element_meta(element_text: str) -> tuple[str | None, bool]:
    try:
        parsed = json.loads(element_text)
        if isinstance(parsed, dict):
            name = parsed.get("name")
            return (str(name) if name is not None else None, bool(parsed.get("status", False)))
    except ValueError:
        pass
    name_match = _NAME_RE.search(element_text)
    if not name_match:
        return None, False
    status_match = _STATUS_RE.search(element_text)
    status = status_match.group(1).lower() == "true" if status_match else False
    return name_match.group(2), status


def _detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _entry_json(name: str = PLUGIN_NAME, description: str = PLUGIN_DESCRIPTION) -> str:
    return json.dumps(
        {
            "name": name,
            "status": True,
            "description": description,
            "parameters": {},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def has_plugin_entry(text: str, name: str = PLUGIN_NAME) -> bool:
    span = _find_plugins_array(text)
    if span is None:
        return False
    for start, end in _scan_array_elements(text, *span):
        entry_name, _ = _element_meta(text[start:end])
        if entry_name == name:
            return True
    return False


def is_plugin_enabled(text: str, name: str = PLUGIN_NAME) -> bool:
    span = _find_plugins_array(text)
    if span is None:
        return False
    for start, end in _scan_array_elements(text, *span):
        entry_name, status = _element_meta(text[start:end])
        if entry_name == name and status:
            return True
    return False


def register_plugin_in_text(
    text: str,
    name: str = PLUGIN_NAME,
    description: str = PLUGIN_DESCRIPTION,
) -> str:
    """Return `plugins.js` text with the plugin enabled (idempotent)."""
    span = _find_plugins_array(text)
    if span is None:
        raise ValueError("Array $plugins nao encontrado em plugins.js.")

    open_idx, close_idx = span
    elements = _scan_array_elements(text, open_idx, close_idx)
    entry = _entry_json(name, description)
    nl = _detect_newline(text)

    # Update in place if already registered
    for start, end in elements:
        entry_name, _ = _element_meta(text[start:end])
        if entry_name == name:
            return text[:start] + entry + text[end:]

    if not elements:
        inner = text[open_idx + 1 : close_idx]
        if "\n" in inner or "\n" in text:
            return text[: open_idx + 1] + f"{nl}{entry}{nl}" + text[close_idx:]
        return text[: open_idx + 1] + entry + text[close_idx:]

    last_start, last_end = elements[-1]
    trailing_comma = _find_comma_between(text, last_end, close_idx)
    if trailing_comma >= 0:
        return text[: trailing_comma + 1] + f"{nl}{entry}" + text[trailing_comma + 1 :]
    return text[:last_end] + f",{nl}{entry}" + text[last_end:]


def unregister_plugin_in_text(text: str, name: str = PLUGIN_NAME) -> str:
    """Return `plugins.js` text with all entries matching `name` cleanly removed."""
    while True:
        span = _find_plugins_array(text)
        if span is None:
            return text
        open_idx, close_idx = span
        elements = _scan_array_elements(text, open_idx, close_idx)
        match_index = -1
        for idx, (start, end) in enumerate(elements):
            entry_name, _ = _element_meta(text[start:end])
            if entry_name == name:
                match_index = idx
                break
        if match_index < 0:
            return text

        start, end = elements[match_index]
        if len(elements) == 1:
            trailing_comma = _find_comma_between(text, end, close_idx)
            remove_end = trailing_comma + 1 if trailing_comma >= 0 else end
            # Clean empty array preserving multiline vs single-line style
            before = text[open_idx + 1 : start]
            after = text[remove_end:close_idx]
            if not before.strip() and not after.strip():
                nl = _detect_newline(text)
                replacement = nl if ("\n" in before or "\n" in after) else ""
                text = text[: open_idx + 1] + replacement + text[close_idx:]
            else:
                text = text[:start] + text[remove_end:]
        elif match_index == len(elements) - 1:
            prev_end = elements[match_index - 1][1]
            comma = _find_comma_between(text, prev_end, start)
            remove_start = comma if comma >= 0 else start
            trailing_comma = _find_comma_between(text, end, close_idx)
            remove_end = trailing_comma + 1 if trailing_comma >= 0 else end
            text = text[:remove_start] + text[remove_end:]
        else:
            next_start = elements[match_index + 1][0]
            comma = _find_comma_between(text, end, next_start)
            if comma >= 0:
                # Consume comma and any whitespace/newline right up to the next element
                between = text[comma + 1 : next_start]
                remove_end = next_start if not between.strip() else comma + 1
            else:
                remove_end = end
            text = text[:start] + text[remove_end:]


# ---------------------------------------------------------------------------
# directory discovery
# ---------------------------------------------------------------------------

def _candidate_js_dirs(game_dir: Path) -> list[Path]:
    candidates: list[Path] = [
        game_dir / "www" / "js",
        game_dir / "js",
    ]
    package = game_dir / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8", errors="ignore"))
            main = str(data.get("main") or "").strip()
            if main:
                main_path = (game_dir / main).resolve()
                resolved_root = game_dir.resolve()
                if resolved_root in main_path.parents or main_path.parent == resolved_root:
                    candidates.append(main_path.parent / "js")
        except (OSError, ValueError, TypeError):
            pass

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            key = candidate.resolve()
        except OSError:
            key = candidate
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def find_js_dir(game_dir: Path) -> Path | None:
    """Locate the RPG Maker MV/MZ `js/` directory containing a valid `plugins.js`."""
    for js_dir in _candidate_js_dirs(game_dir):
        plugins_js = js_dir / "plugins.js"
        if not plugins_js.is_file():
            continue
        try:
            text = plugins_js.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        if _find_plugins_array(text) is not None:
            return js_dir
    return None


# ---------------------------------------------------------------------------
# install / uninstall / inspect
# ---------------------------------------------------------------------------

def _rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def is_plugin_active(game_dir: Path, plugin_key: str = "hide_textbox") -> bool:
    """True when the given managed plugin `.js` exists and is enabled in `plugins.js`."""
    spec = PLUGINS[plugin_key]
    js_dir = find_js_dir(game_dir)
    if js_dir is None:
        return False
    if not (js_dir / "plugins" / spec.filename).is_file():
        return False
    try:
        text = (js_dir / "plugins.js").read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return False
    return is_plugin_enabled(text, name=spec.name)


def install_plugin(
    game_dir: Path,
    plugin_key: str,
    write_fn,
    backup_fn=None,
    existing_backup: str = "",
) -> PluginInstallResult:
    """Install a managed RPG Maker MV/MZ plugin and register it in `plugins.js`."""
    spec = PLUGINS[plugin_key]
    js_dir = find_js_dir(game_dir)
    if js_dir is None:
        return PluginInstallResult(
            installed=False,
            name=spec.name,
            warning=(
                "Arquivo plugins.js nao encontrado (jogo compactado ou estrutura NW.js nao padrao): "
                f"plugin {spec.filename} nao foi instalado."
            ),
        )

    plugins_js = js_dir / "plugins.js"
    plugin_target = js_dir / "plugins" / spec.filename

    raw_bytes = plugins_js.read_bytes()
    has_bom = raw_bytes.startswith(b"\xef\xbb\xbf")
    try:
        text = raw_bytes.decode("utf-8-sig", errors="strict")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("cp932", errors="strict")
            encoding = "cp932"
        except UnicodeDecodeError:
            return PluginInstallResult(
                installed=False,
                name=spec.name,
                warning=(
                    "Nao foi possivel decodificar plugins.js (codificacao desconhecida): "
                    f"plugin {spec.filename} nao foi instalado."
                ),
            )

    any_managed_present = any(has_plugin_entry(text, name=name) for name in ALL_MANAGED_NAMES)
    plugins_js_backup = existing_backup
    if not plugins_js_backup and not any_managed_present and backup_fn is not None:
        plugins_js_backup = backup_fn(plugins_js, "plugins.js") or ""

    updated_text = register_plugin_in_text(text, name=spec.name, description=spec.description)
    updated_bytes = (b"\xef\xbb\xbf" if has_bom and encoding == "utf-8" else b"") + updated_text.encode(encoding)

    plugin_bytes = spec.source.encode("utf-8")
    write_fn(plugin_target, plugin_bytes)
    write_fn(plugins_js, updated_bytes)

    return PluginInstallResult(
        installed=True,
        name=spec.name,
        plugin_path=_rel(plugin_target, game_dir),
        plugin_sha256=winapi.sha256_bytes(plugin_bytes),
        plugins_js_path=_rel(plugins_js, game_dir),
        plugins_js_sha256=winapi.sha256_bytes(updated_bytes),
        plugins_js_backup=plugins_js_backup,
    )


def uninstall_plugin(
    game_dir: Path,
    plugin_meta: dict,
    write_fn,
    backup_fn=None,
    log=None,
    *,
    allow_restore_backup: bool = True,
) -> list[str]:
    """Remove a managed RPG Maker plugin and cleanly remove/restore its `plugins.js` entry."""
    removed: list[str] = []
    plugin_name = str(plugin_meta.get("name") or PLUGIN_NAME)

    def emit(message: str) -> None:
        if log:
            log(message)

    plugins_js_rel = plugin_meta.get("plugins_js_path") or ""
    if plugins_js_rel:
        plugins_js = game_dir / plugins_js_rel
        backup_path = plugin_meta.get("plugins_js_backup") or ""
        expected_hash = plugin_meta.get("plugins_js_sha256") or ""
        if plugins_js.is_file():
            try:
                raw_bytes = plugins_js.read_bytes()
                has_bom = raw_bytes.startswith(b"\xef\xbb\xbf")
                try:
                    text = raw_bytes.decode("utf-8-sig", errors="strict")
                    encoding = "utf-8"
                except UnicodeDecodeError:
                    text = raw_bytes.decode("cp932", errors="strict")
                    encoding = "cp932"

                other_managed_present = any(
                    name != plugin_name and has_plugin_entry(text, name=name)
                    for name in ALL_MANAGED_NAMES
                )
                current_hash = winapi.sha256_bytes(raw_bytes)
                if (
                    allow_restore_backup
                    and not other_managed_present
                    and expected_hash
                    and current_hash == expected_hash
                    and backup_path
                    and Path(backup_path).is_file()
                ):
                    write_fn(plugins_js, Path(backup_path).read_bytes())
                    emit("plugins.js original restaurado.")
                elif has_plugin_entry(text, name=plugin_name):
                    if not other_managed_present and backup_fn is not None and expected_hash and current_hash != expected_hash:
                        backup = backup_fn(plugins_js, "plugins.js")
                        if backup:
                            emit(f"plugins.js modificado preservado em backup: {backup}")
                    cleaned = unregister_plugin_in_text(text, name=plugin_name)
                    cleaned_bytes = (
                        (b"\xef\xbb\xbf" if has_bom and encoding == "utf-8" else b"")
                        + cleaned.encode(encoding)
                    )
                    write_fn(plugins_js, cleaned_bytes)
                    emit(f"Entrada {plugin_name} removida de plugins.js.")
            except (OSError, UnicodeDecodeError) as exc:
                emit(f"Nao foi possivel limpar plugins.js: {exc}")

    plugin_rel = plugin_meta.get("plugin_path") or ""
    if plugin_rel:
        plugin_file = game_dir / plugin_rel
        if plugin_file.is_file():
            expected_hash = plugin_meta.get("plugin_sha256") or ""
            if expected_hash and winapi.sha256_file(plugin_file) != expected_hash and backup_fn is not None:
                backup = backup_fn(plugin_file, plugin_file.name)
                if backup:
                    emit(f"Plugin modificado preservado em backup: {backup}")
            try:
                plugin_file.unlink()
                removed.append(plugin_rel)
            except OSError as exc:
                emit(f"Nao foi possivel remover {plugin_rel}: {exc}")

    return removed


def inspect_plugin(game_dir: Path, plugin_meta: dict) -> tuple[bool, list[str]]:
    """Verify an installed managed RPG Maker plugin file and its `plugins.js` registration."""
    problems: list[str] = []
    plugin_name = str(plugin_meta.get("name") or PLUGIN_NAME)
    plugin_file = f"{plugin_name}.js"
    plugin_rel = plugin_meta.get("plugin_path") or ""
    plugins_js_rel = plugin_meta.get("plugins_js_path") or ""

    file_ok = bool(plugin_rel) and (game_dir / plugin_rel).is_file()
    if not file_ok:
        problems.append(f"Plugin RPG Maker ({plugin_file}) ausente; use 'Reinstalar'.")

    reg_ok = False
    if plugins_js_rel:
        plugins_js = game_dir / plugins_js_rel
        if plugins_js.is_file():
            try:
                text = plugins_js.read_text(encoding="utf-8-sig", errors="ignore")
                reg_ok = is_plugin_enabled(text, name=plugin_name)
            except OSError:
                reg_ok = False
    if not reg_ok:
        problems.append(f"Plugin {plugin_name} nao esta ativo em plugins.js; use 'Reinstalar'.")

    return file_ok and reg_ok, problems


# Backward-compatible wrappers for HideTextbox
def install_hide_textbox(
    game_dir: Path,
    write_fn,
    backup_fn=None,
    existing_backup: str = "",
) -> PluginInstallResult:
    return install_plugin(game_dir, "hide_textbox", write_fn, backup_fn=backup_fn, existing_backup=existing_backup)


def uninstall_hide_textbox(
    game_dir: Path,
    plugin_meta: dict,
    write_fn,
    backup_fn=None,
    log=None,
) -> list[str]:
    return uninstall_plugin(game_dir, plugin_meta, write_fn, backup_fn=backup_fn, log=log)


def inspect_hide_textbox(game_dir: Path, plugin_meta: dict) -> tuple[bool, list[str]]:
    return inspect_plugin(game_dir, plugin_meta)
