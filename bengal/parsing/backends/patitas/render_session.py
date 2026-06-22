"""Unified render session state for page parsing and include expansion.

Consolidates markdown engine binding, include stack tracking, nested source
file resolution, and parse-phase content dependency collection.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.parsing.backends.patitas.utils.contextvar import ContextVarManager

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from bengal.parsing.backends.patitas import Markdown

__all__ = [
    "RenderSession",
    "append_content_dependency",
    "get_markdown_engine",
    "get_render_session",
    "included_source_file",
    "page_render_session",
    "push_include_path",
    "try_get_render_session",
]

_manager: ContextVarManager[RenderSession] = ContextVarManager("patitas_render_session")


@dataclass
class RenderSession:
    """Mutable per-page render session shared across nested includes."""

    markdown_engine: Markdown | None = None
    content_dependencies: list[Path] = field(default_factory=list)
    include_stack: list[str] = field(default_factory=list)
    included_source_file: Path | None = None
    page_context: Any | None = None
    site: Any | None = None
    xref_index: dict[str, Any] | None = None
    links_collector: list[str] | None = None


def get_render_session() -> RenderSession:
    """Return the active render session or raise if unset."""
    return _manager.get_or_raise(
        RuntimeError,
        "No render session active. Use page_render_session() during page parse/render.",
    )


def try_get_render_session() -> RenderSession | None:
    """Return the active render session, if any."""
    return _manager.get()


def get_markdown_engine() -> Markdown | None:
    """Return the Markdown engine bound to the current render session."""
    session = try_get_render_session()
    return session.markdown_engine if session is not None else None


def append_content_dependency(path: Path) -> None:
    """Record a resolved include/literalinclude target."""
    session = try_get_render_session()
    if session is None:
        return
    resolved = path.resolve()
    if resolved not in session.content_dependencies:
        session.content_dependencies.append(resolved)


def included_source_file() -> str | None:
    """Active include source path for nested include resolution."""
    session = try_get_render_session()
    if session is None:
        return None
    if session.included_source_file is not None:
        return str(session.included_source_file)
    page_context = session.page_context
    if page_context is not None:
        source_path = getattr(page_context, "source_path", None)
        if source_path:
            return str(source_path)
    return None


@contextmanager
def push_include_path(resolved_path: Path) -> Iterator[None]:
    """Push *resolved_path* onto the include stack for cycle detection."""
    session = get_render_session()
    resolved_key = str(resolved_path.resolve())
    session.include_stack.append(resolved_key)
    previous_source = session.included_source_file
    session.included_source_file = resolved_path.resolve()
    try:
        yield
    finally:
        session.included_source_file = previous_source
        session.include_stack.pop()


@contextmanager
def page_render_session(
    *,
    markdown_engine: Markdown | None = None,
    page_context: Any | None = None,
    site: Any | None = None,
    xref_index: dict[str, Any] | None = None,
    links_collector: list[str] | None = None,
    content_dependencies: list[Path] | None = None,
) -> Iterator[RenderSession]:
    """Bind a render session for one page parse/render."""
    deps = content_dependencies if content_dependencies is not None else []
    session = RenderSession(
        markdown_engine=markdown_engine,
        content_dependencies=deps,
        page_context=page_context,
        site=site,
        xref_index=xref_index,
        links_collector=links_collector,
    )
    with _manager.context(session):
        yield session
