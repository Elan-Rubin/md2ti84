"""Walk a markdown-it-py token stream and emit LaTeX chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator

from markdown_it.token import Token


@dataclass
class LatexChunk:
    """A single block of LaTeX content with a line-height estimate."""
    latex: str
    # Estimated number of text lines this chunk occupies on the page.
    # Used by the paginator; intentionally rough.
    estimated_lines: float = 1.0
    # Whether this chunk must not be split from the previous chunk.
    keep_with_prev: bool = False


# Characters that fit on one line of a 265pt page at 7pt font.
# Empirically derived: ~60 chars at 7pt with 4pt margins on 265pt paper.
_CHARS_PER_LINE = 60
# Extra vertical space multiplier for display math
_MATH_LINES_PER_NEWLINE = 2.5


def _escape(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _inline_latex(tokens: list[Token]) -> str:
    """Render a list of inline tokens to a LaTeX string."""
    parts: list[str] = []
    for tok in tokens:
        if tok.type == "text":
            parts.append(_escape(tok.content))
        elif tok.type == "softbreak":
            parts.append(" ")
        elif tok.type == "hardbreak":
            parts.append(r"\newline ")
        elif tok.type == "code_inline":
            parts.append(r"\texttt{" + _escape(tok.content) + "}")
        elif tok.type == "strong_open":
            parts.append(r"\textbf{")
        elif tok.type == "strong_close":
            parts.append("}")
        elif tok.type == "em_open":
            parts.append(r"\textit{")
        elif tok.type == "em_close":
            parts.append("}")
        elif tok.type == "math_inline":
            parts.append(f"${tok.content}$")
        elif tok.type == "html_inline":
            pass  # skip raw HTML
        elif tok.type in ("link_open", "link_close", "image"):
            pass  # skip links/images
        else:
            if tok.children:
                parts.append(_inline_latex(tok.children))
            elif tok.content:
                parts.append(_escape(tok.content))
    return "".join(parts)


def _estimate_lines(text: str, chars_per_line: int = _CHARS_PER_LINE) -> float:
    """Estimate how many lines *text* takes when word-wrapped."""
    if not text.strip():
        return 0.0
    # Count explicit newlines first
    paragraphs = text.split("\n")
    total = 0.0
    for para in paragraphs:
        total += max(1.0, len(para) / chars_per_line)
    return total


def render(tokens: list[Token]) -> list[LatexChunk]:
    """Convert a markdown-it-py token list to a flat list of LatexChunk objects."""
    chunks: list[LatexChunk] = []
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]

        # --- Headings ---
        if tok.type == "heading_open":
            level = int(tok.tag[1])  # h1 -> 1, h2 -> 2, h3 -> 3
            inline_tok = tokens[i + 1]
            content = _inline_latex(inline_tok.children or [])
            sizes = {1: r"\large\textbf", 2: r"\normalsize\textbf", 3: r"\small\textbf"}
            cmd = sizes.get(level, r"\small\textbf")
            latex = f"{{{cmd}{{{content}}}}}\n\n"
            chunks.append(LatexChunk(latex=latex, estimated_lines=1.8))
            i += 3  # open, inline, close

        # --- Paragraphs ---
        elif tok.type == "paragraph_open":
            inline_tok = tokens[i + 1]
            content = _inline_latex(inline_tok.children or [])
            latex = content + "\n\n"
            chunks.append(LatexChunk(latex=latex, estimated_lines=_estimate_lines(content)))
            i += 3

        # --- Display math ---
        elif tok.type == "math_block":
            body = tok.content.strip()
            latex = f"\\[\n{body}\n\\]\n"
            # Count newlines in math to approximate height
            lines = max(2.0, body.count("\\\\") * _MATH_LINES_PER_NEWLINE + 2)
            chunks.append(LatexChunk(latex=latex, estimated_lines=lines))
            i += 1

        # --- Bullet lists ---
        elif tok.type == "bullet_list_open":
            items, i = _collect_list(tokens, i, ordered=False)
            latex = "\\begin{itemize}\n" + items + "\\end{itemize}\n"
            line_count = latex.count("\n") * 0.9
            chunks.append(LatexChunk(latex=latex, estimated_lines=line_count))

        # --- Ordered lists ---
        elif tok.type == "ordered_list_open":
            items, i = _collect_list(tokens, i, ordered=True)
            latex = "\\begin{enumerate}\n" + items + "\\end{enumerate}\n"
            line_count = latex.count("\n") * 0.9
            chunks.append(LatexChunk(latex=latex, estimated_lines=line_count))

        # --- Code blocks ---
        elif tok.type == "fence" or tok.type == "code_block":
            body = tok.content.rstrip("\n")
            latex = "\\begin{verbatim}\n" + body + "\n\\end{verbatim}\n"
            lines = body.count("\n") + 2.0
            chunks.append(LatexChunk(latex=latex, estimated_lines=lines))
            i += 1

        # --- Horizontal rule ---
        elif tok.type == "hr":
            latex = "\\noindent\\rule{\\linewidth}{0.4pt}\n\n"
            chunks.append(LatexChunk(latex=latex, estimated_lines=0.8))
            i += 1

        else:
            i += 1

    return chunks


def _collect_list(tokens: list[Token], start: int, ordered: bool) -> tuple[str, int]:
    """Collect list items from tokens[start] (the list_open token) and return
    (latex_items_string, next_index)."""
    open_type = "ordered_list_open" if ordered else "bullet_list_open"
    close_type = "ordered_list_close" if ordered else "bullet_list_close"

    items_latex = ""
    i = start + 1
    n = len(tokens)
    depth = 1

    while i < n and depth > 0:
        tok = tokens[i]
        if tok.type == open_type:
            depth += 1
            i += 1
        elif tok.type == close_type:
            depth -= 1
            i += 1
        elif tok.type == "list_item_open":
            # Gather inline content of this item
            i += 1
            item_parts: list[str] = []
            while i < n and tokens[i].type != "list_item_close":
                t = tokens[i]
                if t.type == "paragraph_open":
                    inline = tokens[i + 1]
                    item_parts.append(_inline_latex(inline.children or []))
                    i += 3
                elif t.type == "math_block":
                    item_parts.append(f"\\( {t.content.strip()} \\)")
                    i += 1
                else:
                    i += 1
            items_latex += "  \\item " + " ".join(item_parts) + "\n"
            i += 1  # skip list_item_close
        else:
            i += 1

    return items_latex, i
