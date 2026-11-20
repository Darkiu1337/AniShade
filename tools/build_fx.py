"""Regenerate the ReShade FX shaders shipped by AniShade from the official Anime4K GLSL.

Input : vendor/anime4k/*.glsl   (official bloc97/Anime4K v4.0.1, MIT)
Output: vendor/anime4k_fx/*.fx  (generated, do not edit by hand)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from anishade.glsl_to_fx import convert_file  # noqa: E402

SOURCE = ROOT / "vendor" / "anime4k"
TARGET = ROOT / "vendor" / "anime4k_fx"


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    generated = 0
    for source in sorted(SOURCE.glob("Anime4K_Restore_*.glsl")):
        destination = TARGET / (source.stem + ".fx")
        convert_file(source, destination)
        print(f"  {source.name} -> {destination.name} ({destination.stat().st_size} bytes)")
        generated += 1
    print(f"{generated} shaders gerados em {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
