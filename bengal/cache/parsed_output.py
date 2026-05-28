"""Compatibility adapters for immutable parsed page records."""

from __future__ import annotations

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
