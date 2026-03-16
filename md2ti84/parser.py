"""Parse Markdown (with math) into a markdown-it-py token stream."""

from __future__ import annotations

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin


def parse(text: str):
    """Return the token stream for *text*."""
    md = (
        MarkdownIt("commonmark")
        .use(dollarmath_plugin, allow_labels=False, allow_space=False)
        .enable("table")
    )
    return md.parse(text)
