"""Optionally convert PNGs to TI-84 CE .8ca image vars using img2calc."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def export(
    png_paths: list[Path],
    output_dir: Path,
    prefix: str = "img",
) -> list[Path]:
    """Convert each PNG in *png_paths* to a .8ca file in *output_dir*.

    Files are named ``<prefix><N>.8ca`` where N is 1-indexed.

    If img2calc is not on PATH, a warning is printed and an empty list is
    returned (the PNGs are still usable on their own).
    """
    img2calc = shutil.which("img2calc")
    if img2calc is None:
        print(
            "[md2ti84] Warning: img2calc not found on PATH. "
            "Skipping .8ca export. Install it from "
            "https://github.com/commandblockguy/img2calc"
        )
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []

    for idx, png in enumerate(png_paths, start=1):
        out = output_dir / f"{prefix}{idx}.8ca"
        cmd = [img2calc, "--format", "8ca", "--output", str(out), str(png)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"[md2ti84] Warning: img2calc failed for {png.name}: "
                f"{result.stderr.strip()}"
            )
        else:
            results.append(out)

    return results
