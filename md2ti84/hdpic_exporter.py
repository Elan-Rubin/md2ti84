"""Convert PNG images to HD Picture Viewer .8xv AppVar files.

Implements the format used by HD Picture Viewer by TheLastMillennial:
  https://github.com/TheLastMillennial/HD-Picture-Viewer

Format details reverse-engineered from:
  https://gitlab.com/taricorp/hdpictureconverter-rs

Each image is split into 80×80 pixel tiles. Each tile becomes one .8xv
AppVar. A separate palette AppVar holds the shared 256-colour palette and
the image dimensions in tiles.

AppVar naming convention (var_prefix = 2-char ID, e.g. "A0"):
  Tile at grid (x, y): f"{var_prefix}{x:03d}{y:03d}"   → e.g. "A0000000"
  Palette AppVar:      f"HP{var_prefix}{cols-1:03d}{rows-1:03d}"

.8xv file structure (TI-83+/84+ variable file):
  [8]  magic: "**TI83F*"
  [3]  extra: 0x1A 0x0A 0x00
  [42] comment (null-padded)
  [2]  data_section_length (LE uint16) — length of everything after this
  --- variable entry ---
  [2]  0x0D 0x00  (metadata length, always 13)
  [2]  data_length (LE uint16) — payload length
  [1]  type byte: 0x15  (AppVar)
  [8]  variable name (null-padded)
  [1]  version: 0x00
  [1]  flags: 0x80  (archived)
  [2]  data_length again (LE uint16)
  --- data ---
  [N]  payload bytes
  --- checksum ---
  [2]  sum of all bytes from start of variable entry, LE uint16, mod 65536
"""

from __future__ import annotations

import struct
from pathlib import Path

import imagequant
import zx0
from PIL import Image

TILE_SIZE = 80
PALETTE_SIZE = 256


# ---------------------------------------------------------------------------
# Colour conversion
# ---------------------------------------------------------------------------

def _to_grgb1555(r: int, g: int, b: int) -> int:
    """Convert 8-bit RGB to the GRGB1555 format used by HD Picture Viewer.

    Bit layout (MSB→LSB):
      G0 R4 R3 R2 R1 R0 G5 G4 G3 G2 G1 B4 B3 B2 B1 B0
    """
    r5 = round(r / 255 * 31)
    g6 = round(g / 255 * 63)
    b5 = round(b / 255 * 31)
    return ((g6 & 0x01) << 15) | (r5 << 10) | ((g6 & 0x3E) << 4) | b5


# ---------------------------------------------------------------------------
# TI AppVar file writer
# ---------------------------------------------------------------------------

def _build_appvar(name: str, payload: bytes, comment: str = "HD Picture Viewer image") -> bytes:
    """Wrap *payload* in a TI-83+/84+ AppVar (.8xv) file."""
    # Truncate/pad name to 8 bytes
    name_bytes = name.encode("ascii")[:8].ljust(8, b"\x00")

    data_len = len(payload)

    # Variable entry (everything after the 2-byte data_section_length header)
    var_entry = (
        struct.pack("<H", 13)           # metadata length (always 13)
        + struct.pack("<H", data_len)   # payload length
        + b"\x15"                       # type: AppVar
        + name_bytes                    # variable name
        + b"\x00"                       # version
        + b"\x80"                       # flags: archived
        + struct.pack("<H", data_len)   # payload length again
        + payload
    )

    checksum = sum(var_entry) & 0xFFFF
    var_entry += struct.pack("<H", checksum)

    comment_bytes = comment.encode("ascii")[:42].ljust(42, b"\x00")

    header = (
        b"**TI83F*"
        + b"\x1A\x0A\x00"
        + comment_bytes
        + struct.pack("<H", len(var_entry))
    )

    return header + var_entry


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def _div_ceil(a: int, b: int) -> int:
    return (a + b - 1) // b


def convert_image(
    png_path: Path,
    output_dir: Path,
    var_prefix: str,
) -> list[Path]:
    """Convert a PNG to HD Picture Viewer AppVar files.

    Returns a list of all .8xv files written (tiles + palette).
    *var_prefix* must be exactly 2 characters (letter + letter/digit).
    """
    if len(var_prefix) != 2:
        raise ValueError(f"var_prefix must be exactly 2 characters, got {var_prefix!r}")

    output_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(png_path).convert("RGBA")

    # Pad image dimensions to multiples of TILE_SIZE
    cols = _div_ceil(img.width, TILE_SIZE)
    rows = _div_ceil(img.height, TILE_SIZE)
    padded_w = cols * TILE_SIZE
    padded_h = rows * TILE_SIZE

    canvas = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 255))
    canvas.paste(img, (0, 0))

    # Quantize to 256 colours across the whole image
    iq_image = imagequant.image_create_rgba(
        list(canvas.tobytes()),
        padded_w,
        padded_h,
        gamma=0,
    )
    iq_attrs = imagequant.Attributes()
    iq_attrs.set_max_colors(PALETTE_SIZE)
    iq_result = imagequant.quantize_image(iq_attrs, iq_image)
    iq_result.set_dithering_level(1.0)
    remapped, palette = imagequant.remap_image(iq_result, iq_image)
    # palette is a flat list of (r,g,b,a) tuples, length 256

    # Build GRGB1555 palette bytes
    palette_bytes = b""
    for entry in palette:
        r, g, b, _a = entry
        val = _to_grgb1555(r, g, b)
        palette_bytes += struct.pack("<H", val)
    # Pad palette to exactly 256 entries
    palette_bytes = palette_bytes.ljust(PALETTE_SIZE * 2, b"\x00")

    # remapped is a flat list of palette indices, row-major
    pixel_indices = bytes(remapped)

    written: list[Path] = []

    # Write tile AppVars
    for ty in range(rows):
        for tx in range(cols):
            # Extract 80×80 tile pixel indices
            tile_pixels = bytearray()
            for row in range(TILE_SIZE):
                y = ty * TILE_SIZE + row
                row_start = y * padded_w + tx * TILE_SIZE
                tile_pixels.extend(pixel_indices[row_start: row_start + TILE_SIZE])

            # Build tile payload: header + dimensions + ZX0-compressed pixels
            uncompressed = (
                struct.pack("<H", TILE_SIZE)   # width = 80
                + struct.pack("<H", TILE_SIZE) # height = 80
                + bytes(tile_pixels)
            )
            compressed = zx0.compress(bytes(uncompressed))
            payload = b"HDPICCV4" + var_prefix.encode("ascii").ljust(8, b" ") + compressed

            appvar_name = f"{var_prefix}{tx:03d}{ty:03d}"
            out_path = output_dir / f"{appvar_name}.8xv"
            out_path.write_bytes(_build_appvar(appvar_name, payload))
            written.append(out_path)

    # Write palette AppVar
    palette_header = (
        f"HDPALV10"
        f"{var_prefix.ljust(8)}"   # wait — spec says: name(8) then prefix(2) then tile dims
    )
    # Correct header per spec: "HDPALV10" + name(8 spaces) + var_prefix(2) + cols-1(3) + rows-1(3)
    palette_payload_header = (
        b"HDPALV10"
        + b" " * 8                          # image name field (unused, spaces)
        + var_prefix.encode("ascii")         # 2-char prefix
        + f"{cols-1:03d}".encode("ascii")   # max tile x index
        + f"{rows-1:03d}".encode("ascii")   # max tile y index
    )
    palette_payload = palette_payload_header + palette_bytes
    palette_name = f"HP{var_prefix}{cols-1:03d}{rows-1:03d}"
    pal_path = output_dir / f"{palette_name}.8xv"
    pal_path.write_bytes(_build_appvar(palette_name, palette_payload))
    written.append(pal_path)

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
    all_files: list[Path] = []

    for idx, png in enumerate(png_paths):
        # Generate prefix: A0–A9, B0–B9, etc.
        letter = chr(ord(prefix_base[0]) + idx // 10)
        digit = str(idx % 10)
        var_prefix = letter + digit

        print(f"[md2ti84] Converting {png.name} → HD Picture Viewer (prefix {var_prefix}) ...")
        try:
            files = convert_image(png, output_dir, var_prefix)
            all_files.extend(files)
            print(f"[md2ti84]   {len(files)} AppVar file(s) written.")
        except Exception as e:
            print(f"[md2ti84] Warning: failed to convert {png.name}: {e}")

    return all_files
