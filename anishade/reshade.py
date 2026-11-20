"""ReShade acquisition: resolve the latest release, download the setup tool once
and extract ReShade32.dll / ReShade64.dll from the ZIP archive appended to it.

The setup executable is never redistributed by AniShade: it is downloaded from
the official site on first use and the extracted modules are cached locally for
every game added later.
"""

from __future__ import annotations

import array
import io
import json
import re
import shutil
import struct
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import __version__, paths
from .winapi import sha256_bytes, sha256_file

SITE_URL = "https://reshade.me/"
USER_AGENT = f"AniShade/{__version__} (+https://reshade.me/)"
_VERSION_RE = re.compile(r"/downloads/ReShade_Setup_([0-9]+(?:\.[0-9]+)+)\.exe")
_ADDON_RE = re.compile(r"/downloads/ReShade_Setup_([0-9]+(?:\.[0-9]+)+)_Addon\.exe")

Progress = Callable[[int, int], None]
Status = Callable[[str], None]


class ReshadeError(Exception):
    pass


@dataclass
class ReleaseInfo:
    version: str
    url: str
    addon_url: str = ""


@dataclass
class CachedReShade:
    version: str
    folder: Path
    dll32: Path
    dll64: Path
    from_cache: bool = True
    meta: dict | None = None

    def dll_for(self, bits: int) -> Path:
        return self.dll64 if bits == 64 else self.dll32


def _request(url: str, timeout: int = 30) -> urllib.request.addinfourl:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        digits = re.sub(r"\D", "", piece)
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def fetch_latest_release(timeout: int = 30) -> ReleaseInfo:
    """Scrape https://reshade.me for the current version and download links."""
    try:
        with _request(SITE_URL, timeout=timeout) as response:
            html = response.read().decode("utf-8", "ignore")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ReshadeError(f"Nao foi possivel acessar reshade.me: {exc}") from exc

    versions = sorted({match for match in _VERSION_RE.findall(html)}, key=_version_key)
    if not versions:
        raise ReshadeError("Nao encontrei um link de download do ReShade na pagina oficial.")
    version = versions[-1]
    addon = _ADDON_RE.search(html)
    return ReleaseInfo(
        version=version,
        url=f"https://reshade.me/downloads/ReShade_Setup_{version}.exe",
        addon_url=f"https://reshade.me/downloads/ReShade_Setup_{version}_Addon.exe" if addon else "",
    )


def download_setup(
    release: ReleaseInfo,
    progress: Progress | None = None,
    status: Status | None = None,
) -> Path:
    paths.ensure_dirs()
    target = paths.DOWNLOAD_DIR / f"ReShade_Setup_{release.version}.exe"
    if target.is_file() and target.stat().st_size > 1_000_000:
        if status:
            status(f"Instalador do ReShade {release.version} ja esta no cache.")
        return target

    temporary = target.with_suffix(target.suffix + ".part")
    if status:
        status(f"Baixando ReShade {release.version} de reshade.me ...")
    try:
        with _request(release.url, timeout=60) as response, open(temporary, "wb") as handle:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise ReshadeError(f"Falha ao baixar o ReShade: {exc}") from exc

    if temporary.stat().st_size < 1_000_000:
        temporary.unlink(missing_ok=True)
        raise ReshadeError("O download do ReShade veio incompleto.")

    # validate that the DLLs can be extracted before keeping the file
    try:
        extract_dlls(temporary)
    except ReshadeError:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(target)
    if status:
        status(f"ReShade {release.version} baixado ({target.stat().st_size / 1048576:.1f} MB).")
    return target


def extract_dlls(setup_path: str | Path) -> dict[str, bytes]:
    """Pull ReShade32.dll/ReShade64.dll out of the archive appended to setup.exe."""
    data = Path(setup_path).read_bytes()
    if len(data) < 1_000_000:
        raise ReshadeError("Arquivo do instalador muito pequeno para ser o ReShade Setup.")

    signature = b"PK\x03\x04"
    offset = data.find(signature)
    attempts = 0
    while offset >= 0 and attempts < 8:
        attempts += 1
        try:
            archive = zipfile.ZipFile(io.BytesIO(data[offset:]))
            names = set(archive.namelist())
            wanted = {"ReShade32.dll", "ReShade64.dll"}
            if wanted <= names:
                payload = {name: archive.read(name) for name in wanted}
                archive.close()
                for name, blob in payload.items():
                    if not blob.startswith(b"MZ"):
                        raise ReshadeError(f"{name} extraido nao parece uma DLL valida.")
                return payload
        except (zipfile.BadZipFile, OSError, KeyError):
            pass
        offset = data.find(signature, offset + 1)

    raise ReshadeError(
        "Nao encontrei as DLLs dentro do instalador do ReShade. "
        "Baixe novamente em https://reshade.me."
    )


def _meta_path(folder: Path) -> Path:
    return folder / "meta.json"


def _load_meta(folder: Path) -> dict:
    try:
        return json.loads(_meta_path(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def list_cached() -> list[CachedReShade]:
    paths.ensure_dirs()
    releases: list[CachedReShade] = []
    for folder in paths.RESHADE_CACHE_DIR.iterdir():
        if not folder.is_dir() or folder.name.endswith(".tmp"):
            continue
        dll32 = folder / "ReShade32.dll"
        dll64 = folder / "ReShade64.dll"
        if dll32.is_file() and dll64.is_file():
            releases.append(
                CachedReShade(
                    version=folder.name,
                    folder=folder,
                    dll32=dll32,
                    dll64=dll64,
                    meta=_load_meta(folder),
                )
            )
    releases.sort(key=lambda item: _version_key(item.version), reverse=True)
    return releases


def newest_cached() -> CachedReShade | None:
    cached = list_cached()
    return cached[0] if cached else None


def cache_from_setup(setup_path: Path, version: str, url: str = "") -> CachedReShade:
    payload = extract_dlls(setup_path)
    folder = paths.RESHADE_CACHE_DIR / version
    temporary = folder.with_name(folder.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True, exist_ok=True)
    try:
        (temporary / "ReShade32.dll").write_bytes(payload["ReShade32.dll"])
        (temporary / "ReShade64.dll").write_bytes(payload["ReShade64.dll"])
        meta = {
            "version": version,
            "source": url or "https://reshade.me",
            "sha256_32": sha256_bytes(payload["ReShade32.dll"]),
            "sha256_64": sha256_bytes(payload["ReShade64.dll"]),
            "setup_sha256": sha256_file(setup_path) if setup_path.is_file() else "",
            "cached_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "app_version": __version__,
        }
        _meta_path(temporary).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    temporary.replace(folder)
    return CachedReShade(
        version=version,
        folder=folder,
        dll32=folder / "ReShade32.dll",
        dll64=folder / "ReShade64.dll",
        from_cache=False,
        meta=meta,
    )


def ensure_release(
    preferred_version: str | None = None,
    progress: Progress | None = None,
    status: Status | None = None,
    allow_network: bool = True,
) -> CachedReShade:
    """Return a usable cached ReShade build, downloading it only when needed."""
    cached = list_cached()
    if preferred_version:
        for item in cached:
            if item.version == preferred_version:
                if status:
                    status(f"Usando ReShade {item.version} do cache local.")
                return item
    elif cached:
        if status:
            status(f"Usando ReShade {cached[0].version} do cache local.")
        return cached[0]

    if not allow_network:
        if cached:
            return cached[0]
        raise ReshadeError("Nenhuma versao do ReShade esta no cache e a rede esta desativada.")

    if status:
        status("Consultando a versao mais recente do ReShade ...")
    try:
        release = fetch_latest_release()
    except ReshadeError:
        if cached:
            if status:
                status("Sem conexao com reshade.me; usando a versao em cache.")
            return cached[0]
        raise

    if preferred_version and release.version != preferred_version:
        release = ReleaseInfo(
            version=preferred_version,
            url=f"https://reshade.me/downloads/ReShade_Setup_{preferred_version}.exe",
        )

    setup = download_setup(release, progress=progress, status=status)
    if status:
        status("Extraindo ReShade32.dll e ReShade64.dll do instalador ...")
    return cache_from_setup(setup, release.version, release.url)


def prune_cache(keep: int = 1) -> list[str]:
    """Delete old cached builds, returning the removed versions."""
    cached = list_cached()
    removed: list[str] = []
    for item in cached[keep:]:
        shutil.rmtree(item.folder, ignore_errors=True)
        removed.append(item.version)
    return removed


def verified_dll(release: CachedReShade, bits: int) -> Path:
    dll = release.dll_for(bits)
    if not dll.is_file():
        raise ReshadeError(f"{dll.name} nao encontrado no cache do ReShade.")
    meta = release.meta or {}
    expected = meta.get("sha256_64" if bits == 64 else "sha256_32")
    if expected and sha256_file(dll) != expected:
        raise ReshadeError(
            f"{dll.name} no cache esta corrompido. Remova {release.folder} e baixe novamente."
        )
    return dll


# ---------------------------------------------------------------------------
# Splash / resize-spinner suppression (in-memory PE patch on deployed DLL)
# ---------------------------------------------------------------------------

def _pe_checksum(data: bytes | bytearray, checksum_offset: int) -> int:
    """Compute the standard Windows PE optional-header checksum."""
    length = len(data)
    end_even = length & ~1
    words = array.array("H")
    words.frombytes(data[:end_even])
    if sys.byteorder != "little":
        words.byteswap()
    total = sum(words)
    if checksum_offset + 4 <= end_even:
        idx = checksum_offset >> 1
        total -= words[idx] + words[idx + 1]
    if length & 1:
        total += data[length - 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (total + length) & 0xFFFFFFFF


def patch_hide_splash(dll_bytes: bytes) -> tuple[bytes, bool]:
    """Patch a deployed ReShade DLL to skip the 'Splash Window' block.

    In ReShade (runtime_gui.cpp), both the startup splash banner ("ReShade 6.x...")
    and the top-left loading spinner circle shown on fullscreen/windowed resize are
    rendered inside a single `if (show_splash_window && !(show_spinner && show_overlay))`
    block that begins `ImGui::Begin("Splash Window", ...)`.

    This locates that exact branch via multiple structural fingerprints (unique
    `"Splash Window"` reference, splash background color `0.117647f`, ImGui flags
    `0x000b132f`, and paired `je`/`jne` jumps targeting the identical end-of-block
    RVA) and converts the leading `je` into an unconditional `jmp + nop`.
    The Home overlay and shader compilation remain completely intact.
    """
    if len(dll_bytes) < 0x200 or dll_bytes[:2] != b"MZ":
        return dll_bytes, False

    pe_off = struct.unpack_from("<I", dll_bytes, 0x3C)[0]
    if pe_off + 0x80 > len(dll_bytes) or dll_bytes[pe_off : pe_off + 4] != b"PE\x00\x00":
        return dll_bytes, False

    coff = pe_off + 4
    nsec = struct.unpack_from("<H", dll_bytes, coff + 2)[0]
    opt_sz = struct.unpack_from("<H", dll_bytes, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from("<H", dll_bytes, opt)[0]
    if magic == 0x20B:
        is64 = True
        img_base = struct.unpack_from("<Q", dll_bytes, opt + 24)[0]
        dd_off = opt + 112
    elif magic == 0x10B:
        is64 = False
        img_base = struct.unpack_from("<I", dll_bytes, opt + 28)[0]
        dd_off = opt + 96
    else:
        return dll_bytes, False

    sec_tbl = opt + opt_sz
    sections: list[tuple[str, int, int, int, int]] = []
    for index in range(nsec):
        base = sec_tbl + index * 40
        if base + 40 > len(dll_bytes):
            break
        name = dll_bytes[base : base + 8].split(b"\x00")[0].decode("ascii", "ignore")
        vsize, va, rsize, rptr = struct.unpack_from("<IIII", dll_bytes, base + 8)
        sections.append((name, va, vsize, rptr, rsize))

    text_sec = next((sec for sec in sections if sec[0] == ".text"), None)
    if text_sec is None:
        return dll_bytes, False

    str_off = dll_bytes.find(b"Splash Window\x00")
    if str_off < 0:
        return dll_bytes, False

    str_rva = None
    for _name, va, _vs, rptr, rsize in sections:
        if rptr <= str_off < rptr + rsize:
            str_rva = va + (str_off - rptr)
            break
    if str_rva is None:
        return dll_bytes, False

    _, t_va, _t_vs, t_rp, t_rs = text_sec
    text = dll_bytes[t_rp : t_rp + t_rs]

    refs: list[int] = []
    if is64:
        for i in range(len(text) - 7):
            if text[i] in (0x48, 0x4C) and text[i + 1] == 0x8D and (text[i + 2] & 0xC7) == 0x05:
                disp = struct.unpack_from("<i", text, i + 3)[0]
                if (t_va + i + 7) + disp == str_rva:
                    refs.append(i)
    else:
        needle = struct.pack("<BI", 0x68, (img_base + str_rva) & 0xFFFFFFFF)
        pos = 0
        while True:
            idx = text.find(needle, pos)
            if idx < 0:
                break
            refs.append(idx)
            pos = idx + 1

    if len(refs) != 1:
        return dll_bytes, False

    ref = refs[0]
    ref_rva = t_va + ref

    # Verify ImGui splash color 0.117647f (0x3df0f0e9) and splash window flags (0x000b132f)
    before_window = text[max(0, ref - 80) : ref]
    after_window = text[max(0, ref - 16) : min(len(text), ref + 32)]
    if b"\xe9\xf0\xf0\x3d" not in before_window or b"\x2f\x13\x0b\x00" not in after_window:
        return dll_bytes, False

    # Locate the paired `je target` + `jne target` guard for `if (show_splash_window && !(show_spinner && show_overlay))`
    scan_start = max(0, ref - 280)
    scan_end = max(0, ref - 48)
    matches: list[tuple[int, int]] = []
    for pos1 in range(scan_start, scan_end):
        if text[pos1] == 0x0F and text[pos1 + 1] == 0x84:
            disp1 = struct.unpack_from("<i", text, pos1 + 2)[0]
            target1 = (t_va + pos1 + 6) + disp1
            if disp1 < 0x200 or target1 <= ref_rva + 0x100:
                continue
            for pos2 in range(pos1 + 6, min(len(text) - 6, pos1 + 32)):
                if text[pos2] == 0x0F and text[pos2 + 1] == 0x85:
                    disp2 = struct.unpack_from("<i", text, pos2 + 2)[0]
                    target2 = (t_va + pos2 + 6) + disp2
                    if target2 == target1:
                        matches.append((pos1, disp1))
                        break

    if len(matches) != 1:
        return dll_bytes, False

    pos1, disp1 = matches[0]
    file_patch_off = t_rp + pos1
    buf = bytearray(dll_bytes)
    # Replace `0F 84 <disp1>` (je target) with `E9 <disp1 + 1> 90` (jmp target; nop)
    buf[file_patch_off : file_patch_off + 6] = struct.pack("<BiB", 0xE9, disp1 + 1, 0x90)

    # Clear now-invalid Authenticode Certificate Table entry and update PE CheckSum
    num_dirs = struct.unpack_from("<I", buf, dd_off - 4)[0]
    if num_dirs > 4 and dd_off + 40 <= len(buf):
        struct.pack_into("<II", buf, dd_off + 4 * 8, 0, 0)
    checksum_off = opt + 64
    struct.pack_into("<I", buf, checksum_off, _pe_checksum(buf, checksum_off))
    return bytes(buf), True
