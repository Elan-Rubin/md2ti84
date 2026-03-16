"""Compile a .tex file to PDF using lualatex or pdflatex."""

from __future__ import annotations

import subprocess
from pathlib import Path


def compile_tex(
    tex_path: Path,
    output_dir: Path,
    engine: str = "lualatex",
) -> Path:
    """Compile *tex_path* with *engine*, writing output into *output_dir*.

    Returns the path to the produced PDF.
    Raises RuntimeError with the last 30 lines of the LaTeX log on failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        engine,
        "-interaction=nonstopmode",
        f"-output-directory={output_dir}",
        str(tex_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    pdf_path = output_dir / tex_path.with_suffix(".pdf").name

    if result.returncode != 0 or not pdf_path.exists():
        # Surface useful part of the LaTeX log
        log_path = output_dir / tex_path.with_suffix(".log").name
        log_tail = ""
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            # Find first error line for context
            error_lines = [l for l in lines if l.startswith("!")]
            relevant = error_lines[:5] if error_lines else lines[-30:]
            log_tail = "\n".join(relevant)
        raise RuntimeError(
            f"{engine} failed for {tex_path.name} (exit {result.returncode}).\n"
            f"Relevant log:\n{log_tail}"
        )

    return pdf_path
