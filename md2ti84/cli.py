"""CLI entry point for md2ti84."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import parser as md_parser
from . import renderer, paginator, latex_builder, compiler, image_converter, hdpic_exporter


def _load_defaults() -> dict:
    """Try to read [tool.md2ti84] from pyproject.toml in the project root."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # fallback
        except ImportError:
            return {}

    here = Path(__file__).parent
    for parent in [here, here.parent, here.parent.parent]:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
            return data.get("tool", {}).get("md2ti84", {})
    return {}


def main(argv: list[str] | None = None) -> int:
    defaults = _load_defaults()

    ap = argparse.ArgumentParser(
        prog="md2ti84",
        description="Convert Markdown notes to HD Picture Viewer .8xv AppVars for TI-84 CE",
    )
    ap.add_argument("input", type=Path, help="Input Markdown file")
    ap.add_argument(
        "-o", "--output-dir", type=Path, default=None,
        help="Output directory (default: same directory as input file)",
    )
    ap.add_argument(
        "--font-size", type=int, default=defaults.get("font_size", 8),
        help="LaTeX font size in pt (default: 8)",
    )
    ap.add_argument(
        "--margin", type=int, default=defaults.get("margin", 6),
        help="Page margin in pt (default: 6)",
    )
    ap.add_argument(
        "--dpi", type=int, default=defaults.get("render_dpi", 300),
        help="DPI for PDF rendering before downscaling (default: 300)",
    )
    ap.add_argument(
        "--engine", default=defaults.get("latex_engine", "lualatex"),
        choices=["lualatex", "pdflatex"],
        help="LaTeX engine (default: lualatex)",
    )
    ap.add_argument(
        "--max-lines", type=float, default=defaults.get("max_lines_per_page", 24.0),
        help="Estimated max lines per page for pagination (default: 24)",
    )
    ap.add_argument(
        "--no-grayscale", action="store_true",
        help="Keep color output instead of the default grayscale",
    )
    ap.add_argument(
        "--no-8xv", action="store_true",
        help="Skip HD Picture Viewer .8xv export, output PNGs only",
    )
    ap.add_argument(
        "--width", type=int, default=defaults.get("image_width", 320),
        help="Output image width in pixels (default: 320)",
    )
    ap.add_argument(
        "--height", type=int, default=defaults.get("image_height", 240),
        help="Output image height in pixels (default: 240)",
    )

    args = ap.parse_args(argv)

    md_file: Path = args.input.resolve()
    if not md_file.exists():
        print(f"[md2ti84] Error: file not found: {md_file}", file=sys.stderr)
        return 1

    output_dir: Path = (args.output_dir or md_file.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = md_file.stem

    print(f"[md2ti84] Parsing {md_file.name} ...")
    text = md_file.read_text(encoding="utf-8")
    tokens = md_parser.parse(text)

    print("[md2ti84] Rendering to LaTeX chunks ...")
    chunks = renderer.render(tokens)

    print(f"[md2ti84] Paginating (max {args.max_lines} lines/page) ...")
    pages = paginator.paginate(chunks, max_lines=args.max_lines)
    print(f"[md2ti84] {len(pages)} page(s) to render.")

    png_paths: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="md2ti84_") as tmpdir:
        tmp = Path(tmpdir)

        for page_num, page_chunks in enumerate(pages, start=1):
            print(f"[md2ti84] Compiling page {page_num}/{len(pages)} ...")

            tex_content = latex_builder.build(
                page_chunks,
                font_size=args.font_size,
                image_width=args.width,
                image_height=args.height,
                margin=args.margin,
                use_lualatex=(args.engine == "lualatex"),
            )
            tex_path = tmp / f"{stem}_page{page_num:02d}.tex"
            tex_path.write_text(tex_content, encoding="utf-8")

            try:
                pdf_path = compiler.compile_tex(tex_path, tmp, engine=args.engine)
            except RuntimeError as e:
                print(f"[md2ti84] Error on page {page_num}:\n{e}", file=sys.stderr)
                return 1

            png_path = output_dir / f"{stem}_page{page_num:02d}.png"
            image_converter.convert(
                pdf_path,
                png_path,
                target_width=args.width,
                target_height=args.height,
                render_dpi=args.dpi,
                grayscale=not args.no_grayscale,
            )
            png_paths.append(png_path)
            print(f"[md2ti84]   → {png_path.name}")

    if not args.no_8xv:
        appvar_files = hdpic_exporter.export(png_paths, output_dir, prefix_base=stem[0].upper())
        if appvar_files:
            print(f"[md2ti84] Exported {len(appvar_files)} .8xv AppVar file(s).")

    print(f"[md2ti84] Done. {len(png_paths)} PNG(s) written to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
