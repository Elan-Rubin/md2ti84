# md2ti84

Markdown is parsed, converted to LaTeX, compiled with lualatex, and rendered to grayscale 265x165 `.png` files. Exports to `.8ca` image vars for transfer via TI Connect CE.

## Dependencies

Python packages:

```
pip install "markdown-it-py[linkify]" mdit-py-plugins jinja2 pdf2image Pillow
```

System dependencies (must be installed separately):

- **lualatex** — via [MiKTeX](https://miktex.org/) (Windows) or `texlive-full` (Linux/Mac)
- **poppler** — via [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) or `poppler-utils` (Linux/Mac)
- **img2calc** (optional) — for `.8ca` export, from [github.com/commandblockguy/img2calc](https://github.com/commandblockguy/img2calc)

## Usage

```bash
pip install -e .
md2ti84 notes.md -o output/
```

Common options:

- `--engine pdflatex` — use pdflatex instead of lualatex (faster, less complete Unicode)
- `--font-size 6` — smaller font to fit more content per page
- `--no-grayscale` — keep color output (grayscale is the default)
- `--max-lines 20` — adjust pagination threshold
- `--no-8ca` — skip `.8ca` export

Output images are named `<stem>_page01.png`, `<stem>_page02.png`, etc. The TI-84 CE supports up to 9 image vars (Image1-Image9), so plan your notes accordingly.

## Viewing on the calculator

Transfer the `.8ca` files via TI Connect CE, then on the calculator:

1. Press `[VARS]`
2. Choose `4: Picture...`
3. Scroll to a picture and press `[ENTER]`
4. Press `[ENTER]` again to view it

## Note

This tool is intended for personal reference and studying - not cheating.

## License

MIT License

Copyright (c) 2026