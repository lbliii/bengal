"""Tests for rendering-side Page content helpers."""

from __future__ import annotations

from pathlib import Path

from bengal.core.page import Page
from bengal.rendering.page_content import (
    extract_links_from_ast_cache,
    extract_text_from_ast_cache,
    get_html,
    get_plain_text,
    strip_html_to_text,
)


def _page(content: str = "", html: str | None = None) -> Page:
    return Page(
        source_path=Path("content/docs/page.md"),
        _raw_content=content,
        _raw_metadata={"title": "Page"},
        html_content=html,
    )


def test_page_content_properties_delegate_to_rendering_helpers() -> None:
    page = _page("raw **markdown**", "<p>Rendered</p>")

    assert page.content == "<p>Rendered</p>"
    assert page.html == "<p>Rendered</p>"
    assert get_html(page) == "<p>Rendered</p>"


def test_plain_text_uses_html_before_raw_source() -> None:
    page = _page("raw **markdown**", "<h1>Title</h1><p>Rendered text</p>")

    assert get_plain_text(page) == "TitleRendered text"
    assert page.plain_text == "TitleRendered text"


def test_plain_text_falls_back_to_raw_source() -> None:
    page = _page("raw markdown")

    assert page.plain_text == "raw markdown"


def test_ast_cache_helpers_handle_document_dict() -> None:
    ast_cache = {
        "type": "document",
        "children": [
            {"type": "paragraph", "children": [{"type": "text", "raw": "Read "}]},
            {"type": "link", "attrs": {"url": "/guide/"}, "children": []},
        ],
    }

    assert extract_text_from_ast_cache(ast_cache) == "Read"
    assert extract_links_from_ast_cache(ast_cache) == ["/guide/"]


def test_page_private_content_shims_delegate_to_rendering_helpers() -> None:
    page = _page()
    page._ast_cache = [{"type": "link", "attrs": {"url": "/guide/"}, "children": []}]

    assert page._extract_links_from_ast() == ["/guide/"]
    assert page._extract_text_from_ast() == ""
    assert page._strip_html_to_text("<p>Hello</p>") == strip_html_to_text("<p>Hello</p>")
