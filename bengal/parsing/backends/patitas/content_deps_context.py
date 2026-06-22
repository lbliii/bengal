"""Collect markdown include/literalinclude targets during page parsing.

Deprecated: use ``render_session.page_render_session`` directly.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from bengal.parsing.backends.patitas.render_session import (
    page_render_session,
    try_get_render_session,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def get_content_deps_collector() -> list[Path] | None:
    """Return the active parse-phase content dependency collector, if any."""
    session = try_get_render_session()
    return session.content_dependencies if session is not None else None


@contextmanager
def content_deps_collector() -> Iterator[list[Path]]:
    """Bind a collector list for the duration of a page markdown parse."""
    with page_render_session() as session:
        yield session.content_dependencies
