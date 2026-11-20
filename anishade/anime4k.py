"""Anime4K Restore catalog, ReShade FX deployment and preset generation.

The official Anime4K release is GLSL for MPV/libplacebo; ReShade only loads its
own FX format. The ``.fx`` files bundled here are generated from the official
GLSL by ``anishade.glsl_to_fx`` (see ``tools/build_fx.py``), preserving the
original MIT license and weights.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import paths

SHADER_SUBDIR = Path("reshade-shaders") / "Shaders" / "AniShade"
MARKER_FILE = "_anishade_shaders.json"
PRESET_NAME = "AniShade.ini"
SHADER_VERSION = 2


@dataclass(frozen=True)
class Variant:
    key: str
    file: str
    label: str
    family: str
    weight: int
    resolution: str
    description: str

    @property
    def technique(self) -> str:
        return Path(self.file).stem


VARIANTS: tuple[Variant, ...] = (
    Variant(
        "cnn_s",
        "Anime4K_Restore_CNN_S.fx",
        "Restore CNN S (leve)",
        "CNN",
        1,
        "480p - 720p",
        "Menor rede neural: reconstroi detalhes com custo baixo. Boa para GPUs integradas e telas pequenas.",
    ),
    Variant(
        "cnn_m",
        "Anime4K_Restore_CNN_M.fx",
        "Restore CNN M (equilibrado)",
        "CNN",
        2,
        "720p - 900p",
        "Equilibrio entre nitidez e desempenho. Recomendado para a maioria das visual novels em 720p/768p.",
    ),
    Variant(
        "cnn_l",
        "Anime4K_Restore_CNN_L.fx",
        "Restore CNN L (nitido)",
        "CNN",
        3,
        "900p - 1080p",
        "Reconstrucao mais forte de linhas e texturas. Indicado para VNs em 1080p.",
    ),
    Variant(
        "cnn_vl",
        "Anime4K_Restore_CNN_VL.fx",
        "Restore CNN VL (muito nitido)",
        "CNN",
        5,
        "1080p - 1440p",
        "Rede maior: mais detalhe em arte de alta resolucao, custo de GPU alto.",
    ),
    Variant(
        "cnn_ul",
        "Anime4K_Restore_CNN_UL.fx",
        "Restore CNN UL (maximo)",
        "CNN",
        8,
        "1440p - 4K",
        "Maior rede disponivel. Qualidade maxima, uso de VRAM/GPU muito alto.",
    ),
    Variant(
        "soft_s",
        "Anime4K_Restore_CNN_Soft_S.fx",
        "Restore CNN Soft S (suave)",
        "Soft",
        1,
        "480p - 720p",
        "Versao suavizada do CNN S: menos ringing/halo em tracos finos e compressao pesada.",
    ),
    Variant(
        "soft_m",
        "Anime4K_Restore_CNN_Soft_M.fx",
        "Restore CNN Soft M (suave)",
        "Soft",
        2,
        "720p - 900p",
        "CNN Soft M: bom para VNs com arte suave, gradientes e fundos desfocados.",
    ),
    Variant(
        "soft_l",
        "Anime4K_Restore_CNN_Soft_L.fx",
        "Restore CNN Soft L (suave)",
        "Soft",
        3,
        "900p - 1080p",
        "CNN Soft L: detalhe alto com transicoes mais naturais. Indicado para 1080p.",
    ),
    Variant(
        "soft_vl",
        "Anime4K_Restore_CNN_Soft_VL.fx",
        "Restore CNN Soft VL (suave)",
        "Soft",
        5,
        "1080p - 1440p",
        "CNN Soft VL: alta resolucao sem exagerar no realce de bordas.",
    ),
    Variant(
        "soft_ul",
        "Anime4K_Restore_CNN_Soft_UL.fx",
        "Restore CNN Soft UL (suave)",
        "Soft",
        8,
        "1440p - 4K",
        "CNN Soft UL: variante mais suave da rede maxima, para 4K sem artefatos agressivos.",
    ),
)

_VARIANT_MAP = {variant.key: variant for variant in VARIANTS}
DEFAULT_VARIANT = "cnn_m"


def variant(key: str) -> Variant:
    return _VARIANT_MAP.get(key, _VARIANT_MAP[DEFAULT_VARIANT])


def variant_family(family: str) -> list[Variant]:
    return [item for item in VARIANTS if item.family == family]


def required_files(variant_key: str) -> list[str]:
    return [variant(variant_key).file]


def techniques(variant_key: str) -> list[str]:
    return [variant(variant_key).technique]


def build_preset(variant_key: str, top_margin: int = 0, content_aspect: float = 0.0) -> str:
    technique = variant(variant_key).technique
    definitions: list[str] = []
    if top_margin > 0:
        definitions.append(f"ANISHADE_TOP_MARGIN={top_margin}")
    if content_aspect > 0:
        definitions.append(f"ANISHADE_CONTENT_ASPECT={content_aspect:.4f}")
    lines: list[str] = []
    if definitions:
        lines.append("PreprocessorDefinitions=" + ",".join(definitions))
    lines.append(f"Techniques={technique}")
    lines.append(f"TechniqueSorting={technique}")
    return "\n".join(lines) + "\n"


def missing_bundled(files: list[str], source: Path | None = None) -> list[str]:
    source = source or paths.anime4k_fx_dir()
    return [name for name in files if not (source / name).is_file()]


def _read_marker(shader_dir: Path) -> dict:
    try:
        return json.loads((shader_dir / MARKER_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def deploy_shaders(
    game_dir: Path,
    files: list[str],
    source: Path | None = None,
) -> list[Path]:
    """Copy the requested ReShade FX shaders, removing only files we own."""
    source = source or paths.anime4k_fx_dir()
    missing = missing_bundled(files, source)
    if missing:
        raise FileNotFoundError(
            "Shaders ReShade FX ausentes no pacote do AniShade: " + ", ".join(missing)
        )

    shader_dir = game_dir / SHADER_SUBDIR
    shader_dir.mkdir(parents=True, exist_ok=True)
    marker = _read_marker(shader_dir)
    previous = set(marker.get("files", []))

    copied: list[Path] = []
    for name in files:
        destination = shader_dir / name
        shutil.copy2(source / name, destination)
        copied.append(destination)

    for name in previous - set(files):
        stale = shader_dir / name
        if stale.is_file():
            stale.unlink(missing_ok=True)
    # This folder belongs to AniShade: drop older GLSL deployments and any
    # variant that is no longer selected (ReShade would load all of them).
    for stale in shader_dir.glob("*.glsl"):
        stale.unlink(missing_ok=True)
    for stale in shader_dir.glob("Anime4K_Restore_*.fx"):
        if stale.name not in files:
            stale.unlink(missing_ok=True)

    marker = {
        "generator": "AniShade",
        "anime4k_version": "4.0.1",
        "shader_version": SHADER_VERSION,
        "format": "reshade-fx",
        "files": sorted(files),
    }
    (shader_dir / MARKER_FILE).write_text(json.dumps(marker, indent=2), encoding="utf-8")
    return copied


def remove_shaders(game_dir: Path) -> list[Path]:
    shader_dir = game_dir / SHADER_SUBDIR
    removed: list[Path] = []
    marker = _read_marker(shader_dir)
    for name in marker.get("files", []):
        target = shader_dir / name
        if target.is_file():
            target.unlink()
            removed.append(target)
    for stale in shader_dir.glob("*.glsl"):
        stale.unlink(missing_ok=True)
        removed.append(stale)
    (shader_dir / MARKER_FILE).unlink(missing_ok=True)
    for folder in (shader_dir, shader_dir.parent, shader_dir.parent.parent):
        try:
            folder.rmdir()
        except OSError:
            break
    return removed
