"""Tests for rendering-side Page content helpers."""

from __future__ import annotations

from pathlib import Path

from bengal.rendering.page_content import (
    compute_excerpt,
    compute_meta_description,
    extract_links_from_ast_cache,
    extract_text_from_ast_cache,
    get_excerpt,
    get_html,
    get_meta_description,
    get_plain_text,
    strip_html_to_text,
)
from tests._testing.page_records import make_test_page, seed_parsed_page_state


def _page(content: str = "", html: str | None = None):
    return make_test_page(
        source_path=Path("content/docs/page.md"),
        raw_content=content,
        metadata={"title": "Page"},
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


def test_meta_description_prefers_pipeline_value() -> None:
    page = _page("fallback content")
    seed_parsed_page_state(page, meta_description="AST description")

    assert get_meta_description(page, {}) == "AST description"
    assert page.meta_description == "AST description"


def test_meta_description_prefers_explicit_metadata() -> None:
    page = _page("fallback content")

    assert get_meta_description(page, {"description": "Explicit"}) == "Explicit"
    assert compute_meta_description({"description": "Explicit"}, "fallback content") == "Explicit"


def test_meta_description_derives_from_content() -> None:
    page = _page("<p>This is <strong>bold</strong> text.</p>")

    assert get_meta_description(page, {}) == "This is bold text."


def test_excerpt_prefers_pipeline_value() -> None:
    page = _page("fallback content")
    seed_parsed_page_state(page, excerpt="AST excerpt")

    assert get_excerpt(page) == "AST excerpt"
    assert page.excerpt == "AST excerpt"


def test_excerpt_fallback_renders_markdown_without_leading_h1() -> None:
    page = _page("# Title\n\nThis has **bold** text.")

    excerpt = get_excerpt(page)

    assert "This has" in excerpt
    assert "Title" not in excerpt
    assert "<strong>" in excerpt


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


# -----------------------------------------------------------------------
# compute_meta_description
# -----------------------------------------------------------------------


class TestComputeMetaDescription:
    """Direct tests for compute_meta_description (raw-content path)."""

    def test_explicit_description_preferred(self):
        result = compute_meta_description(
            {"description": "Explicit desc"},
            "Some long content",
        )
        assert result == "Explicit desc"

    def test_generated_from_content(self):
        result = compute_meta_description({}, "Short content here.")
        assert result == "Short content here."

    def test_empty_content_no_description(self):
        assert compute_meta_description({}, "") == ""

    def test_max_160_chars(self):
        long = "This is a sentence. " * 30
        result = compute_meta_description({}, long)
        assert len(result) <= 160


# -----------------------------------------------------------------------
# compute_excerpt
# -----------------------------------------------------------------------


class TestComputeExcerpt:
    """Direct tests for compute_excerpt (raw-content path).

    The helper returns rendered HTML, strips a leading h1, and truncates at
    ~250 chars before rendering.
    """

    def test_short_content_renders_markdown(self):
        result = compute_excerpt("Hello world.")
        assert "Hello world" in result
        assert "<" in result  # Rendered to HTML (e.g. <p>)

    def test_empty_string(self):
        assert compute_excerpt("") == ""

    def test_strips_leading_h1(self):
        result = compute_excerpt("# My Title\n\nFirst paragraph here.")
        assert "First paragraph" in result
        assert "My Title" not in result

    def test_renders_markdown(self):
        result = compute_excerpt("This has **bold** and *italic*.")
        assert "bold" in result
        assert "<strong>" in result or "**" not in result  # Rendered

    def test_does_not_cut_mid_markdown(self):
        """Excerpt should not end with orphaned ** or other markdown syntax."""
        content = (
            "Bengal is a powerful static site generator. "
            "Key Features: Fast Builds, Asset Optimization, **SEO** friendly."
        )
        result = compute_excerpt(content)
        from bengal.core.utils.text import strip_html

        plain = strip_html(result)
        assert not plain.endswith("**"), "Should not end with orphaned **"

    def test_headers_in_content(self):
        """Headers in content are rendered and available for card excerpt."""
        content = (
            "Intro paragraph here.\n\n"
            "## Key Features\n\n"
            "### Fast Builds\n"
            "- Parallel processing\n"
            "- Asset Optimization\n"
            "**SEO** friendly."
        )
        result = compute_excerpt(content)
        assert "Key Features" in result or "Intro" in result
