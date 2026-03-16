# md2ti84

Markdown is parsed, converted to LaTeX, compiled with lualatex, and rendered to grayscale 320x240 `.png` files. Exports to [HD Picture Viewer](https://github.com/TheLastMillennial/HD-Picture-Viewer) `.8xv` AppVar files for transfer to TI-84 CE via TI Connect CE.

## Dependencies

Python packages:

```
pip install -e .
```

Or manually:

```
pip install "markdown-it-py[linkify]" mdit-py-plugins jinja2 pdf2image Pillow imagequant zx0
```

System dependencies (must be installed separately):

- **lualatex** — via [MiKTeX](https://miktex.org/) (Windows) or `texlive-full` (Linux/Mac)
- **poppler** — via [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) or `poppler-utils` (Linux/Mac)

## Usage

```bash
md2ti84 notes.md -o output/
```

Common options:

- `--engine pdflatex` — use pdflatex instead of lualatex (faster, less complete Unicode)
- `--font-size 6` — smaller font to fit more content per page
- `--no-grayscale` — keep color output (grayscale is the default)
- `--max-lines 28` — adjust pagination threshold
- `--no-8xv` — skip `.8xv` export, output PNGs only

Output PNGs are named `<stem>_page01.png`, `<stem>_page02.png`, etc. Each page also produces a set of `.8xv` AppVar files (one per 80x80 tile, plus one palette file).

## Viewing on the calculator

1. Install [HD Picture Viewer](https://github.com/TheLastMillennial/HD-Picture-Viewer) (`HDPICV.8xp`) on your calculator via TI Connect CE
2. Transfer all `.8xv` files from the output directory to the calculator (archive memory)
3. Run the `HDPICV` program on the calculator
4. Select an image from the menu and press `[ENTER]` to view it
5. Use arrow keys to pan, `[+]`/`[-]` to zoom, `[Graph]`/`[Y=]` to go to the next/previous image

## Note

This tool is intended for personal reference and studying - not cheating.

## License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
