"""Compatibility adapters for immutable parsed page records."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.records import ParsedPage
    from bengal.protocols import PageLike


def apply_parsed_page_to_page(
    page: PageLike,
    parsed_page: ParsedPage,
    *,
    seed_counts: bool = True,
    seed_links: bool = True,
    seed_plain_text: bool = True,
    seed_ast: bool = False,
) -> None:
    """Apply a ``ParsedPage`` record to the remaining mutable page surface."""
    page.html_content = parsed_page.html_content
    page.toc = parsed_page.toc
    page._toc_items_cache = [dict(item) for item in parsed_page.toc_items]
    page._excerpt = parsed_page.excerpt
    page._meta_description = parsed_page.meta_description

    if seed_links:
        page.links = list(parsed_page.links)
    if seed_plain_text:
        page._plain_text_cache = parsed_page.plain_text
    if seed_ast:
        page._ast_cache = parsed_page.ast_cache
    if seed_counts:
        page.__dict__["word_count"] = parsed_page.word_count
        page.__dict__["reading_time"] = parsed_page.reading_time
        if hasattr(page, "_word_count"):
            page._word_count = parsed_page.word_count
        if hasattr(page, "_reading_time"):
            page._reading_time = parsed_page.reading_time


def clear_parsed_page_state(page: PageLike) -> None:
    """Clear parse-derived compatibility fields before reparsing a page."""
    page.html_content = None
    page.toc = ""
    page._toc_items_cache = []
    page.links = []
    page._excerpt = None
    page._meta_description = None
    page._plain_text_cache = None
    page._ast_cache = None


def clear_parsed_page_caches(page: object, *, clear_html_cache: bool = True) -> None:
    """Clear derived parsed caches while preserving parsed page output fields."""
    if hasattr(page, "_ast_cache"):
        page._ast_cache = None  # type: ignore[attr-defined]
    if clear_html_cache and hasattr(page, "_html_cache"):
        page._html_cache = None  # type: ignore[attr-defined]
    if hasattr(page, "_plain_text_cache"):
        page._plain_text_cache = None  # type: ignore[attr-defined]
    if hasattr(page, "_toc_items_cache"):
        page._toc_items_cache = None  # type: ignore[attr-defined]


def with_parsed_html(parsed_page: ParsedPage, html_content: str) -> ParsedPage:
    """Return a ``ParsedPage`` copy with transformed HTML content."""
    return replace(parsed_page, html_content=html_content)


def apply_parsed_links_to_page(page: PageLike, links: list[object] | tuple[object, ...]) -> None:
    """Apply parsed link output to the remaining mutable page surface."""
    page.links = [str(link) for link in links]


def cache_plain_text_on_page(page: object, plain_text: str) -> None:
    """Cache derived plain text on the temporary mutable page surface."""
    page._plain_text_cache = plain_text  # type: ignore[attr-defined]


def cache_toc_items_on_page(page: object, toc_items: list[dict[str, object]]) -> None:
    """Cache derived TOC items on the temporary mutable page surface."""
    page._toc_items_cache = toc_items  # type: ignore[attr-defined]
