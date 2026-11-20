"""Download the official Anime4K release and extract the .glsl files to vendor/anime4k."""

from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

VERSION = "v4.0.1"
URL = f"https://github.com/bloc97/Anime4K/releases/download/{VERSION}/Anime4K_v4.0.zip"
ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "vendor" / "anime4k"


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    print(f"Baixando {URL} ...")
    request = urllib.request.Request(URL, headers={"User-Agent": "AniShade-build"})
    with urllib.request.urlopen(request, timeout=60) as response:
        blob = response.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        count = 0
        for entry in archive.namelist():
            if not entry.endswith(".glsl"):
                continue
            (TARGET / Path(entry).name).write_bytes(archive.read(entry))
            count += 1
    print(f"{count} shaders extraidos para {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
