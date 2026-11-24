"""Very small PE (Windows executable) inspector.

Only what AniShade needs:
  * 32 vs 64 bit
  * imported / delay-imported DLL names (to find the graphics API)
  * image base / subsystem
  * whether the image is a DLL

No third-party dependency, tolerant to truncated or exotic files.
"""

from __future__ import annotations

import mmap
import struct
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import tr

IMAGE_FILE_DLL = 0x2000

MACHINES = {
    0x014C: ("x86", 32),
    0x8664: ("x86-64", 64),
    0x01C0: ("ARM", 32),
    0x01C4: ("ARMv7", 32),
    0xAA64: ("ARM64", 64),
}


class PEError(Exception):
    pass


@dataclass
class PEInfo:
    path: Path
    machine: int = 0
    bits: int = 0
    arch: str = "unknown"
    is_dll: bool = False
    subsystem: int = 0
    image_base: int = 0
    imports: set[str] = field(default_factory=set)
    delay_imports: set[str] = field(default_factory=set)

    @property
    def all_imports(self) -> set[str]:
        return self.imports | self.delay_imports


class _Reader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = open(path, "rb")
        try:
            self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        except ValueError as exc:  # empty file
            self._file.close()
            raise PEError(tr("pe.empty_file", path=path)) from exc
        self.size = len(self._map)

    def close(self) -> None:
        try:
            self._map.close()
        finally:
            self._file.close()

    def __enter__(self) -> _Reader:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def u16(self, offset: int) -> int:
        if offset < 0 or offset + 2 > self.size:
            raise PEError(tr("pe.read_oob"))
        return struct.unpack_from("<H", self._map, offset)[0]

    def u32(self, offset: int) -> int:
        if offset < 0 or offset + 4 > self.size:
            raise PEError(tr("pe.read_oob"))
        return struct.unpack_from("<I", self._map, offset)[0]

    def u64(self, offset: int) -> int:
        if offset < 0 or offset + 8 > self.size:
            raise PEError(tr("pe.read_oob"))
        return struct.unpack_from("<Q", self._map, offset)[0]

    def raw(self, offset: int, length: int) -> bytes:
        if offset < 0 or offset + length > self.size:
            raise PEError(tr("pe.read_oob"))
        return self._map[offset : offset + length]

    def cstring(self, offset: int, limit: int = 260) -> str:
        if offset < 0 or offset >= self.size:
            return ""
        end = min(self.size, offset + limit)
        chunk = self._map[offset:end]
        zero = chunk.find(b"\x00")
        if zero >= 0:
            chunk = chunk[:zero]
        return chunk.decode("ascii", "ignore")


@dataclass
class _Section:
    name: str
    virtual_size: int
    virtual_address: int
    raw_size: int
    raw_pointer: int


def read_pe(path: str | Path) -> PEInfo:
    path = Path(path)
    with _Reader(path) as reader:
        if reader.size < 0x40:
            raise PEError(tr("pe.too_small"))
        if reader.u16(0) != 0x5A4D:
            raise PEError(tr("pe.no_mz"))
        pe_offset = reader.u32(0x3C)
        if reader.u32(pe_offset) != 0x00004550:
            raise PEError(tr("pe.no_pe"))

        coff = pe_offset + 4
        machine = reader.u16(coff)
        number_of_sections = reader.u16(coff + 2)
        size_of_optional = reader.u16(coff + 16)
        characteristics = reader.u16(coff + 18)

        optional = coff + 20
        magic = reader.u16(optional)
        if magic == 0x10B:
            is_64 = False
            image_base = reader.u32(optional + 28)
            data_dir_offset = optional + 96
        elif magic == 0x20B:
            is_64 = True
            image_base = reader.u64(optional + 24)
            data_dir_offset = optional + 112
        else:
            raise PEError(tr("pe.unknown_magic", magic=magic))

        subsystem = reader.u16(optional + 68)
        number_of_dirs = reader.u32(data_dir_offset - 4)
        section_table = optional + size_of_optional

        sections: list[_Section] = []
        for index in range(number_of_sections):
            base = section_table + index * 40
            name = reader.raw(base, 8).split(b"\x00")[0].decode("ascii", "ignore")
            sections.append(
                _Section(
                    name=name,
                    virtual_size=reader.u32(base + 8),
                    virtual_address=reader.u32(base + 12),
                    raw_size=reader.u32(base + 16),
                    raw_pointer=reader.u32(base + 20),
                )
            )

        def rva_to_offset(rva: int) -> int | None:
            for section in sections:
                span = max(section.virtual_size, section.raw_size)
                if section.virtual_address <= rva < section.virtual_address + span:
                    delta = rva - section.virtual_address
                    if delta >= section.raw_size:
                        return None
                    return section.raw_pointer + delta
            # headers are mapped 1:1 at the beginning of the file
            if rva < section_table:
                return rva
            return None

        def read_dll_names(directory_index: int, descriptor_size: int, name_field: int, delay: bool) -> set[str]:
            names: set[str] = set()
            if directory_index >= number_of_dirs:
                return names
            directory_rva = reader.u32(data_dir_offset + directory_index * 8)
            if directory_rva == 0:
                return names
            offset = rva_to_offset(directory_rva)
            if offset is None:
                return names
            for index in range(4096):  # hard stop, malformed files
                base = offset + index * descriptor_size
                try:
                    descriptor = reader.raw(base, descriptor_size)
                except PEError:
                    break
                if descriptor.count(0) == descriptor_size:
                    break
                attributes = struct.unpack_from("<I", descriptor, 0)[0]
                name_rva = struct.unpack_from("<I", descriptor, name_field)[0]
                if delay and not (attributes & 1):
                    if image_base and name_rva >= image_base:
                        name_rva -= image_base
                name_offset = rva_to_offset(name_rva)
                if name_offset is None:
                    continue
                name = reader.cstring(name_offset).strip().lower()
                if name:
                    names.add(name)
            return names

        imports = read_dll_names(1, 20, 12, delay=False)
        delay_imports = read_dll_names(13, 32, 4, delay=True)

        arch, bits = MACHINES.get(machine, (tr("pe.unknown_arch"), 64 if is_64 else 32))
        if bits == 0:
            bits = 64 if is_64 else 32

        return PEInfo(
            path=path,
            machine=machine,
            bits=bits,
            arch=arch,
            is_dll=bool(characteristics & IMAGE_FILE_DLL),
            subsystem=subsystem,
            image_base=image_base,
            imports=imports,
            delay_imports=delay_imports,
        )


# ---------------------------------------------------------------------------
# Lightweight heuristics used to guess the graphics API from imports
# ---------------------------------------------------------------------------

_DX9 = {"d3d9.dll", "d3dx9_43.dll", "d3dx9_42.dll", "d3dx9_41.dll", "d3dx9_40.dll"}
_DXGI = {"dxgi.dll", "d3d11.dll", "d3d12.dll", "d3d10.dll", "d3d10_1.dll", "d3dcompiler_47.dll"}
_OPENGL = {"opengl32.dll", "libegl.dll", "libglesv2.dll", "glut32.dll"}
_VULKAN = {"vulkan-1.dll"}
_DDRAW = {"ddraw.dll"}


def guess_api(pe: PEInfo) -> str | None:
    """Best guess of the main graphics API, based on the import table."""
    imports = pe.all_imports
    if imports & _VULKAN:
        return "vulkan"
    if imports & _DDRAW:
        return "ddraw"
    if imports & _DX9:
        return "d3d9"
    if imports & _DXGI:
        return "dxgi"
    if imports & _OPENGL:
        return "opengl"
    return None


def executable_strings(path: str | Path, needles: list[str], limit: int = 12 * 1024 * 1024) -> set[str]:
    """Scan the first ``limit`` bytes for ASCII markers (engine fingerprints)."""
    found: set[str] = set()
    lowercase = [needle.lower() for needle in needles]
    try:
        with open(path, "rb") as handle:
            blob = handle.read(limit).lower()
    except OSError:
        return found
    for needle in lowercase:
        if needle.encode("ascii", "ignore") in blob:
            found.add(needle)
    return found
