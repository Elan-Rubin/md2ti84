"""Split a flat list of LatexChunks into pages that fit the TI-84 CE screen."""

from __future__ import annotations

from .renderer import LatexChunk


def paginate(
    chunks: list[LatexChunk],
    max_lines: float = 18.0,
) -> list[list[LatexChunk]]:
    """Split *chunks* into pages, each fitting within *max_lines* estimated lines.

    Chunks are treated as atomic — a chunk is never split mid-way. If a single
    chunk exceeds *max_lines* on its own it gets its own page (overflow warning
    is printed; the user should break it up in the source).
    """
    pages: list[list[LatexChunk]] = []
    current_page: list[LatexChunk] = []
    current_lines: float = 0.0

    for chunk in chunks:
        lines = chunk.estimated_lines

        if current_lines + lines > max_lines and current_page:
            # Flush current page and start a new one
            pages.append(current_page)
            current_page = []
            current_lines = 0.0

        if lines > max_lines:
            print(
                f"[md2ti84] Warning: a chunk is too tall ({lines:.1f} estimated lines "
                f"> max {max_lines}). It will overflow the page. Consider breaking it up."
            )

        current_page.append(chunk)
        current_lines += lines

    if current_page:
        pages.append(current_page)

    return pages
