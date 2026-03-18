"""Progress bar utilities for md2ti84.

Wraps rich.progress for a consistent look across pipeline stages.
Falls back to plain print() if rich is not installed.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterable, TypeVar

T = TypeVar("T")

try:
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.console import Console

    _RICH = True
except ImportError:
    _RICH = False


def _make_progress() -> "Progress":
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
    )


@contextmanager
def track(
    items: list[T],
    description: str,
) -> Generator[Iterable[tuple[int, T]], None, None]:
    """Context manager that yields ``(index, item)`` pairs with a progress bar.

    Usage::

        with track(pages, "Compiling pages") as bar:
            for i, page in bar:
                ...
    """
    if _RICH:
        with _make_progress() as progress:
            task = progress.add_task(description, total=len(items))

            def _iter():
                for idx, item in enumerate(items):
                    yield idx, item
                    progress.advance(task)

            yield _iter()
    else:
        total = len(items)

        def _iter():
            for idx, item in enumerate(items):
                print(f"[md2ti84] {description} ({idx + 1}/{total}) ...")
                yield idx, item

        yield _iter()


def status(msg: str) -> None:
    """Print a status line, styled if rich is available."""
    if _RICH:
        Console().print(f"[dim][md2ti84][/dim] {msg}")
    else:
        print(f"[md2ti84] {msg}")
