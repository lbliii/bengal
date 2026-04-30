"""Rendering-side helpers for Page content views.

``Page`` keeps template-facing properties such as ``content``, ``html``, and
``plain_text`` for compatibility. The content processing behind those properties
belongs in rendering, where AST and HTML extraction decisions can evolve without
adding inheritance behavior to core.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.utils.text import strip_html_and_normalize

if TYPE_CHECKING:
    from bengal.parsing.ast.types import ASTNode


class PageContentTarget(Protocol):
    """Structural page surface needed by content rendering helpers."""

    _raw_content: str
    html_content: str | None
    toc: str | None
    _ast_cache: list[ASTNode] | dict[str, Any] | None
    _html_cache: str | None
    _plain_text_cache: str | None
    _toc_items_cache: list[dict[str, Any]] | None
    _init_lock: Any


def get_content(page: PageContentTarget) -> str:
    """Return template-ready rendered HTML content."""
    return get_html(page)


def get_ast(page: PageContentTarget) -> list[ASTNode] | dict[str, Any] | None:
    """Return the parser AST cache when available."""
    if hasattr(page, "_ast_cache"):
        return page._ast_cache
    return None


def get_html(page: PageContentTarget) -> str:
    """Return rendered HTML content, rendering from AST cache when present."""
    if hasattr(page, "_html_cache") and page._html_cache is not None:
        return page._html_cache

    if hasattr(page, "_ast_cache") and page._ast_cache is not None:
        with page._init_lock:
            if page._html_cache is not None:
                return page._html_cache
            html = render_ast_to_html(page)
            page._html_cache = html
        return html

    return page.html_content if page.html_content else ""


def get_plain_text(page: PageContentTarget) -> str:
    """Return plain text extracted from AST, HTML, or raw source."""
    if hasattr(page, "_plain_text_cache") and page._plain_text_cache is not None:
        return page._plain_text_cache

    with page._init_lock:
        if page._plain_text_cache is not None:
            return page._plain_text_cache

        if hasattr(page, "_ast_cache") and page._ast_cache:
            text = extract_text_from_ast_cache(page._ast_cache)
        else:
            html_content = getattr(page, "html_content", None) or ""
            text = strip_html_to_text(html_content) if html_content else page._raw_content or ""

        page._plain_text_cache = text
    return text


def get_toc_items(page: PageContentTarget) -> list[dict[str, Any]]:
    """
    Return structured TOC data.

    Empty results are not cached because toc may be populated later during
    parsing after early xref indexing has already touched this helper.
    """
    if page._toc_items_cache is None and page.toc:
        with page._init_lock:
            if page._toc_items_cache is None and page.toc:
                from bengal.rendering.pipeline import extract_toc_structure

                page._toc_items_cache = extract_toc_structure(page.toc)

    return page._toc_items_cache if page._toc_items_cache is not None else []


def render_ast_to_html(page: PageContentTarget) -> str:
    """
    Render AST tokens to HTML.

    Patitas currently renders directly to HTML and does not use this fallback.
    Keeping it centralized makes the future AST-to-HTML path a rendering concern
    instead of Page behavior.
    """
    if not hasattr(page, "_ast_cache") or not page._ast_cache:
        return ""

    emit_diagnostic(
        page,
        "debug",
        "page_ast_to_html_not_implemented",
        action="returning_empty_string",
    )
    return ""


def extract_text_from_ast_cache(ast_cache: list[ASTNode] | dict[str, Any] | None) -> str:
    """Extract plain text from a Page AST cache."""
    ast_list = _ast_children(ast_cache)
    if ast_list is None:
        return ""

    from bengal.parsing.ast.utils import extract_plain_text

    return extract_plain_text(ast_list)


def extract_links_from_ast_cache(ast_cache: list[ASTNode] | dict[str, Any] | None) -> list[str]:
    """Extract link URLs from a Page AST cache."""
    ast_list = _ast_children(ast_cache)
    if ast_list is None:
        return []

    from bengal.parsing.ast.utils import extract_links_from_ast

    return extract_links_from_ast(ast_list)


def strip_html_to_text(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    return strip_html_and_normalize(html)


def _ast_children(ast_cache: list[ASTNode] | dict[str, Any] | None) -> list[ASTNode] | None:
    """Normalize supported AST cache shapes to a list of nodes."""
    if not ast_cache:
        return None
    ast_list = (
        ast_cache["children"]
        if isinstance(ast_cache, dict) and "children" in ast_cache
        else ast_cache
    )
    return ast_list if isinstance(ast_list, list) else None
