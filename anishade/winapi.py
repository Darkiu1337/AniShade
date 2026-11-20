"""Thin Windows helpers (no external dependencies)."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import hashlib
import os
import subprocess
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


def long_path(path: str | Path) -> str:
    """Prefix a path so Windows APIs accept more than 260 characters."""
    text = str(path)
    if os.name != "nt" or text.startswith("\\\\?\\"):
        return text
    if len(text) < 240:
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(long_path(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(argv: list[str]) -> bool:
    """Re-launch the current executable elevated. Returns False if the user cancelled."""
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = argv[1:]
    else:
        executable = sys.executable
        params = [str(Path(sys.argv[0]).resolve()), *argv[1:]]
    command = subprocess.list2cmdline(params)
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, command, str(Path.cwd()), 1
        )
        return result > 32
    except Exception:
        return False


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor v2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def open_folder(path: str | Path) -> None:
    os.startfile(long_path(path))  # type: ignore[attr-defined]


def open_file(path: str | Path) -> None:
    os.startfile(long_path(path))  # type: ignore[attr-defined]


def open_in_explorer(path: str | Path) -> None:
    """Open Explorer with the given file selected."""
    subprocess.Popen(
        ["explorer.exe", f"/select,{long_path(path)}"],
        creationflags=CREATE_NO_WINDOW,
    )


def _version_block(path: Path) -> dict[str, str]:
    import struct

    info: dict[str, str] = {}
    size = ctypes.windll.version.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        return info
    buffer = ctypes.create_string_buffer(size)
    if not ctypes.windll.version.GetFileVersionInfoW(str(path), 0, size, buffer):
        return info
    pointer = ctypes.c_void_p()
    length = wintypes.UINT()

    translations: list[tuple[int, int]] = []
    if ctypes.windll.version.VerQueryValueW(
        buffer, "\\VarFileInfo\\Translation", ctypes.byref(pointer), ctypes.byref(length)
    ):
        raw = ctypes.string_at(pointer.value, length.value)
        for index in range(len(raw) // 4):
            translations.append(struct.unpack_from("<HH", raw, index * 4))
    if not translations:
        translations = [(0x0409, 0x04B0), (0x0000, 0x0000)]

    for lang, codepage in translations:
        prefix = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\"
        for key in ("ProductName", "FileDescription", "FileVersion", "CompanyName"):
            if key in info:
                continue
            try:
                ok = ctypes.windll.version.VerQueryValueW(
                    buffer, prefix + key, ctypes.byref(pointer), ctypes.byref(length)
                )
            except Exception:
                ok = False
            if ok and length.value and pointer.value:
                try:
                    info[key] = ctypes.wstring_at(pointer.value)
                except Exception:
                    continue
    return info


def file_version_info(path: str | Path) -> dict[str, str]:
    """(product, description, version) for an exe, tolerant to failures."""
    try:
        return _version_block(Path(path))
    except Exception:
        return {}


def process_running(exe_name: str) -> bool:
    """True when a process with this executable name is running."""
    try:
        output = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=15,
            errors="ignore",
        ).stdout.lower()
    except Exception:
        return False
    return exe_name.lower() in output


def terminate_process(exe_name: str) -> None:
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", exe_name],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=15,
        )
    except Exception:
        pass


def folder_writable(path: str | Path) -> bool:
    probe = Path(path) / ".anishade_write_test"
    try:
        with open(probe, "wb") as handle:
            handle.write(b"ok")
        probe.unlink()
        return True
    except OSError:
        try:
            probe.unlink()
        except OSError:
            pass
        return False


def launch(exe: str | Path, args: list[str] | None = None, env: dict[str, str] | None = None) -> subprocess.Popen:
    exe_path = Path(exe)
    environment = os.environ.copy()
    if env:
        environment.update(env)
    command = [str(exe_path), *(args or [])]
    return subprocess.Popen(
        command,
        cwd=str(exe_path.parent),
        env=environment,
        close_fds=True,
    )


def write_batch_launcher(
    target: Path,
    exe: Path,
    env: dict[str, str] | None = None,
    args: list[str] | None = None,
    title: str | None = None,
) -> Path:
    """Create a small .bat next to the game that applies env fixes and starts it."""
    exe_rel = os.path.relpath(exe, target.parent)
    safe_title = (title or exe.stem).encode("ascii", "replace").decode("ascii")
    lines = [
        "@echo off",
        f"title {safe_title} - AniShade",
        'cd /d "%~dp0"',
    ]
    for key, value in (env or {}).items():
        lines.append(f'set "{key}={value}"')
    argument_text = " ".join(
        f'"{arg}"' if " " in arg else arg for arg in (args or [])
    )
    lines.append(f'start "" "{exe_rel}" {argument_text}'.rstrip())
    target.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    return target
