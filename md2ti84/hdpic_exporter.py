"""Convert PNG images to HD Picture Viewer .8xv AppVar files.

Drives convimg.exe (from TheLastMillennial's HD Picture Viewer converter
package) to produce the correct ZX0-compressed AppVar tiles and palette.

convimg is looked up in order:
  1. $CONVIMG_PATH environment variable
  2. Same directory as this file's package root (project root)
  3. PATH
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from .progress import track, status

TILE_SIZE = 80
PALETTE_SIZE = 256


# ---------------------------------------------------------------------------
# convimg discovery
# ---------------------------------------------------------------------------

def _find_convimg() -> str | None:
    # 1. Explicit env override
    env = os.environ.get("CONVIMG_PATH")
    if env and Path(env).exists():
        return env

    # 2. Project root (repo root sits two levels above this file)
    for candidate_name in ("convimg.exe", "convimg"):
        for base in (Path(__file__).parent, Path(__file__).parent.parent):
            p = base / candidate_name
            if p.exists():
                return str(p)

    # 3. PATH
    return shutil.which("convimg") or shutil.which("convimg.exe")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _div_ceil(a: int, b: int) -> int:
    return (a + b - 1) // b


def _calc_name(s: str) -> str:
    """Sanitize into an 8-char calculator-safe name (alphanumeric, alpha-first)."""
    chars = [c for c in s if c.isascii() and c.isalnum()]
    if not chars or not chars[0].isalpha():
        chars.insert(0, 'Z')
    return ("".join(chars)[:8]).ljust(8, '_')


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def convert_image(
    png_path: Path,
    output_dir: Path,
    var_prefix: str,
    convimg_exe: str,
) -> list[Path]:
    """Convert a PNG to HD Picture Viewer AppVar files using convimg.

    Returns a list of all .8xv files written (tiles + palette).
    *var_prefix* must be exactly 2 characters.
    """
    if len(var_prefix) != 2:
        raise ValueError(f"var_prefix must be exactly 2 characters, got {var_prefix!r}")

    image_name = _calc_name(png_path.stem)  # 8-char name used in headers

    img = Image.open(png_path).convert("RGBA")
    cols = _div_ceil(img.width, TILE_SIZE)
    rows = _div_ceil(img.height, TILE_SIZE)
    padded_w = cols * TILE_SIZE
    padded_h = rows * TILE_SIZE

    canvas = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 255))
    canvas.paste(img, (0, 0))

    with tempfile.TemporaryDirectory(prefix="hdpic_") as tmpdir:
        tmp = Path(tmpdir)

        # ---- Slice into 80×80 tile PNGs ----
        tile_names: list[tuple[int, int, str]] = []  # (tx, ty, filename)
        for ty in range(rows):
            for tx in range(cols):
                tile_img = canvas.crop((
                    tx * TILE_SIZE, ty * TILE_SIZE,
                    (tx + 1) * TILE_SIZE, (ty + 1) * TILE_SIZE,
                ))
                # Prefix tile filename with coordinates so it sorts cleanly
                tile_fname = f"{tx:03d}{ty:03d}{image_name.strip('_')}.png"
                tile_img.save(tmp / tile_fname)
                tile_names.append((tx, ty, tile_fname))

        # ---- Build palette image (full padded canvas) ----
        palette_png = f"{image_name.strip('_')}Palette.png"
        canvas.save(tmp / palette_png)

        # ---- Generate convimg YAML ----
        palette_block = f"""\
palettes:
  - name: my_palette
    fixed-entries:
      - color: {{ index: 0,   r: 0,   g: 0,   b: 0}}
      - color: {{ index: 255, r: 255, g: 255, b: 255}}
    images:
      - {palette_png}

converts:
"""
        for tx, ty, fname in tile_names:
            appvar_name = f"{var_prefix}{tx:03d}{ty:03d}"
            palette_block += f"""\
  - name: {appvar_name}
    palette: my_palette
    images:
      - {fname}
    compress: zx0

"""

        palette_block += "outputs:\n\n"

        for tx, ty, fname in tile_names:
            appvar_name = f"{var_prefix}{tx:03d}{ty:03d}"
            palette_block += f"""\
  - type: appvar
    name: {appvar_name}
    source-format: ice
    header-string: HDPICCV4{image_name}
    archived: true
    converts:
      - {appvar_name}

"""

        # Palette AppVar: header = HDPALV10 + name(8) + prefix(2) + max_col(3) + max_row(3)
        pal_appvar_name = f"HP{var_prefix}0000"
        pal_header = f"HDPALV10{image_name}{var_prefix}{cols-1:03d}{rows-1:03d}"
        palette_block += f"""\
  - type: appvar
    name: {pal_appvar_name}
    source-format: ice
    header-string: {pal_header}
    archived: true
    palettes:
      - my_palette
"""

        yaml_path = tmp / "convimg.yaml"
        yaml_path.write_text(palette_block, encoding="utf-8")

        # ---- Run convimg ----
        result = subprocess.run(
            [convimg_exe, "-i", str(yaml_path)],
            cwd=str(tmp),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"convimg failed (exit {result.returncode}):\n"
                f"{result.stdout}\n{result.stderr}"
            )

        # ---- Collect .8xv output files ----
        output_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for f in tmp.glob("*.8xv"):
            dest = output_dir / f.name
            shutil.copy2(f, dest)
            written.append(dest)

    return written


# ---------------------------------------------------------------------------
# Batch export
# ---------------------------------------------------------------------------

def export(
    png_paths: list[Path],
    output_dir: Path,
    prefix_base: str = "A",
) -> list[Path]:
    """Convert a list of PNGs to HD Picture Viewer AppVar sets.

    Each image gets a 2-char prefix: A0, A1, ... A9, B0, ...
    Returns all .8xv files written.
    """
    convimg = _find_convimg()
    if convimg is None:
        status(
            "Warning: convimg not found. "
            "Place convimg.exe in the project root or set CONVIMG_PATH. "
            "Skipping .8xv export."
        )
        return []

    all_files: list[Path] = []

    with track(png_paths, "Exporting .8xv AppVars") as bar:
        for idx, png in bar:
            letter = chr(ord(prefix_base[0]) + idx // 10)
            digit = str(idx % 10)
            var_prefix = letter + digit

            try:
                files = convert_image(png, output_dir, var_prefix, convimg)
                all_files.extend(files)
            except Exception as e:
                status(f"Warning: failed to convert {png.name}: {e}")

    return all_files
