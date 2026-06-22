"""Thread-local Markdown engine context for nested fragment rendering.

Deprecated: prefer ``render_session.page_render_session`` / ``get_markdown_engine``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from bengal.parsing.backends.patitas.render_session import (
    get_markdown_engine,
    page_render_session,
    try_get_render_session,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bengal.parsing.backends.patitas import Markdown

__all__ = [
    "get_markdown_engine",
    "markdown_engine_context",
    "reset_markdown_engine",
    "set_markdown_engine",
]


@contextmanager
def markdown_engine_context(engine: Markdown) -> Iterator[Markdown]:
    """Temporarily bind *engine* for nested parse/render calls."""
    session = try_get_render_session()
    if session is not None:
        previous = session.markdown_engine
        session.markdown_engine = engine
        try:
            yield engine
        finally:
            session.markdown_engine = previous
        return

    with page_render_session(markdown_engine=engine) as _session:
        yield engine


def set_markdown_engine(engine: Markdown | None):  # type: ignore[no-untyped-def]
    """Legacy no-op token API retained for compatibility."""
    session = try_get_render_session()
    if session is not None:
        session.markdown_engine = engine
    return


def reset_markdown_engine(_token) -> None:  # type: ignore[no-untyped-def]
    """Legacy no-op token API retained for compatibility."""
    return
