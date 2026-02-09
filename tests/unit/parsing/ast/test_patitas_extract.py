"""
Unit tests for bengal.parsing.ast.patitas_extract.

Tests Patitas Document AST extraction: plain text, links, TOC, and HTML rendering.
Uses real Patitas parse() to produce genuine ASTs — no hand-built mocks.
"""

from __future__ import annotations

import pytest
from patitas import parse, render

from bengal.parsing.ast.patitas_extract import (
    extract_links_from_document,
    extract_plain_text_from_document,
    extract_toc_from_document,
    render_document_to_html,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_doc():
    """Simple document with heading, paragraph, and link."""
    return parse("## Hello World\n\nThis is a [test](https://example.com) page.\n")


@pytest.fixture
def complex_doc():
    """Document with multiple block types: headings, lists, code, emphasis."""
    source = (
        "## Getting Started\n\n"
        "Welcome to the **documentation**.\n\n"
        "### Installation\n\n"
        "Run `pip install bengal` to install.\n\n"
        "- Step one\n"
        "- Step two\n"
        "- Step three\n\n"
        "```python\nprint('hello')\n```\n\n"
        "Visit [docs](https://docs.example.com) or [repo](https://github.com/example).\n"
    )
    return parse(source)


@pytest.fixture
def headings_doc():
    """Document with multiple heading levels for TOC testing."""
    source = (
        "## Introduction\n\n"
        "Some text.\n\n"
        "## Features\n\n"
        "### Feature One\n\n"
        "Details.\n\n"
        "### Feature Two\n\n"
        "More details.\n\n"
        "## Conclusion\n\n"
        "Final thoughts.\n"
    )
    return parse(source)


@pytest.fixture
def links_doc():
    """Document with various link patterns."""
    source = (
        "See [home](/)\n\n"
        "Also [docs](/docs) and [API](/api/v1).\n\n"
        "External: [GitHub](https://github.com) link.\n"
    )
    return parse(source)


@pytest.fixture
def empty_doc():
    """Empty document."""
    return parse("")


# =============================================================================
# extract_plain_text_from_document Tests
# =============================================================================


class TestExtractPlainText:
    """Tests for extract_plain_text_from_document."""

    def test_simple_text_extraction(self, simple_doc) -> None:
        """Extracts plain text from a simple document."""
        text = extract_plain_text_from_document(simple_doc)

        assert "Hello World" in text
        assert "test" in text
        assert "page" in text

    def test_strips_formatting(self, complex_doc) -> None:
        """Bold/emphasis markers are stripped, text content preserved."""
        text = extract_plain_text_from_document(complex_doc)

        assert "documentation" in text
        assert "**" not in text
        assert "Welcome to the" in text

    def test_includes_code_spans(self, complex_doc) -> None:
        """Inline code content is included in plain text."""
        text = extract_plain_text_from_document(complex_doc)

        assert "pip install bengal" in text

    def test_includes_list_items(self, complex_doc) -> None:
        """List item text is included."""
        text = extract_plain_text_from_document(complex_doc)

        assert "Step one" in text
        assert "Step two" in text
        assert "Step three" in text

    def test_includes_heading_text(self, complex_doc) -> None:
        """Heading text is included."""
        text = extract_plain_text_from_document(complex_doc)

        assert "Getting Started" in text
        assert "Installation" in text

    def test_empty_document_returns_empty(self, empty_doc) -> None:
        """Empty document returns empty string."""
        text = extract_plain_text_from_document(empty_doc)
        assert text == ""

    def test_non_document_returns_empty(self) -> None:
        """Non-Document input returns empty string."""
        assert extract_plain_text_from_document("not a doc") == ""
        assert extract_plain_text_from_document(None) == ""
        assert extract_plain_text_from_document(42) == ""

    def test_no_excessive_newlines(self, complex_doc) -> None:
        """Output has no more than 2 consecutive newlines."""
        text = extract_plain_text_from_document(complex_doc)
        assert "\n\n\n" not in text

    def test_link_text_included(self, links_doc) -> None:
        """Link text (not URL) is included in plain text."""
        text = extract_plain_text_from_document(links_doc)

        assert "home" in text
        assert "docs" in text
        assert "GitHub" in text


# =============================================================================
# extract_links_from_document Tests
# =============================================================================


class TestExtractLinks:
    """Tests for extract_links_from_document."""

    def test_single_link(self, simple_doc) -> None:
        """Extracts a single link URL."""
        links = extract_links_from_document(simple_doc)

        assert "https://example.com" in links

    def test_multiple_links(self, complex_doc) -> None:
        """Extracts multiple link URLs."""
        links = extract_links_from_document(complex_doc)

        assert "https://docs.example.com" in links
        assert "https://github.com/example" in links

    def test_relative_links(self, links_doc) -> None:
        """Extracts relative link URLs."""
        links = extract_links_from_document(links_doc)

        assert "/" in links
        assert "/docs" in links
        assert "/api/v1" in links

    def test_link_count(self, links_doc) -> None:
        """Returns correct number of links."""
        links = extract_links_from_document(links_doc)

        assert len(links) == 4  # /, /docs, /api/v1, https://github.com

    def test_empty_document_no_links(self, empty_doc) -> None:
        """Empty document returns empty list."""
        links = extract_links_from_document(empty_doc)
        assert links == []

    def test_non_document_returns_empty(self) -> None:
        """Non-Document input returns empty list."""
        assert extract_links_from_document("not a doc") == []
        assert extract_links_from_document(None) == []

    def test_document_without_links(self) -> None:
        """Document with no links returns empty list."""
        doc = parse("Just plain text here.\n\nNo links at all.\n")
        links = extract_links_from_document(doc)
        assert links == []


# =============================================================================
# extract_toc_from_document Tests
# =============================================================================


class TestExtractTOC:
    """Tests for extract_toc_from_document."""

    def test_extracts_headings(self, headings_doc) -> None:
        """Extracts all headings from document."""
        toc = extract_toc_from_document(headings_doc)

        titles = [item["title"] for item in toc]
        assert "Introduction" in titles
        assert "Features" in titles
        assert "Feature One" in titles
        assert "Feature Two" in titles
        assert "Conclusion" in titles

    def test_heading_levels(self, headings_doc) -> None:
        """TOC items have correct levels (H2=1, H3=2)."""
        toc = extract_toc_from_document(headings_doc)

        level_map = {item["title"]: item["level"] for item in toc}
        # H2 headings -> level 1
        assert level_map["Introduction"] == 1
        assert level_map["Features"] == 1
        assert level_map["Conclusion"] == 1
        # H3 headings -> level 2
        assert level_map["Feature One"] == 2
        assert level_map["Feature Two"] == 2

    def test_heading_ids_generated(self, headings_doc) -> None:
        """TOC items have slugified IDs."""
        toc = extract_toc_from_document(headings_doc)

        ids = [item["id"] for item in toc]
        # All IDs should be non-empty strings
        for heading_id in ids:
            assert isinstance(heading_id, str)
            assert len(heading_id) > 0

    def test_toc_structure(self, headings_doc) -> None:
        """Each TOC item has id, title, and level keys."""
        toc = extract_toc_from_document(headings_doc)

        for item in toc:
            assert "id" in item
            assert "title" in item
            assert "level" in item

    def test_toc_count(self, headings_doc) -> None:
        """Correct number of TOC items (5 headings in fixture)."""
        toc = extract_toc_from_document(headings_doc)
        assert len(toc) == 5

    def test_empty_document_no_toc(self, empty_doc) -> None:
        """Empty document returns empty TOC."""
        toc = extract_toc_from_document(empty_doc)
        assert toc == []

    def test_non_document_returns_empty(self) -> None:
        """Non-Document input returns empty list."""
        assert extract_toc_from_document("not a doc") == []
        assert extract_toc_from_document(None) == []

    def test_document_without_headings(self) -> None:
        """Document with no headings returns empty TOC."""
        doc = parse("Just a paragraph.\n\nAnother paragraph.\n")
        toc = extract_toc_from_document(doc)
        assert toc == []

    def test_explicit_id_preserved(self) -> None:
        """Explicit {#custom-id} syntax is preserved in TOC."""
        doc = parse("## My Heading {#custom-id}\n\nContent.\n")
        toc = extract_toc_from_document(doc)

        assert len(toc) == 1
        assert toc[0]["id"] == "custom-id"
        assert toc[0]["title"] == "My Heading"

    def test_heading_with_inline_formatting(self) -> None:
        """Headings with bold/italic have clean text in TOC."""
        doc = parse("## **Bold** and *italic* heading\n\nContent.\n")
        toc = extract_toc_from_document(doc)

        assert len(toc) == 1
        assert toc[0]["title"] == "Bold and italic heading"


# =============================================================================
# render_document_to_html Tests
# =============================================================================


class TestRenderDocumentToHTML:
    """Tests for render_document_to_html."""

    def test_renders_paragraph(self) -> None:
        """Simple paragraph renders to HTML."""
        doc = parse("Hello world.\n")
        html = render_document_to_html(doc)

        assert "<p>" in html
        assert "Hello world." in html

    def test_renders_heading(self) -> None:
        """Heading renders to correct HTML tag."""
        doc = parse("## My Heading\n")
        html = render_document_to_html(doc)

        assert "<h2" in html
        assert "My Heading" in html

    def test_renders_link(self, simple_doc) -> None:
        """Links render with href attribute."""
        html = render_document_to_html(simple_doc)

        assert 'href="https://example.com"' in html
        assert "test" in html

    def test_renders_emphasis(self) -> None:
        """Bold and italic render correctly."""
        doc = parse("**bold** and *italic*\n")
        html = render_document_to_html(doc)

        assert "<strong>" in html
        assert "<em>" in html
        assert "bold" in html
        assert "italic" in html

    def test_empty_document_returns_empty(self, empty_doc) -> None:
        """Empty document renders to empty string."""
        html = render_document_to_html(empty_doc)
        # Patitas may return empty or whitespace-only for empty docs
        assert html.strip() == ""

    def test_non_document_returns_empty(self) -> None:
        """Non-Document input returns empty string."""
        assert render_document_to_html("not a doc") == ""
        assert render_document_to_html(None) == ""

    def test_matches_patitas_render(self) -> None:
        """Output matches patitas.render() for same document."""
        source = "## Title\n\nA paragraph with **bold**.\n"
        doc = parse(source)

        our_html = render_document_to_html(doc, source=source)
        patitas_html = render(doc, source=source)

        assert our_html == patitas_html

    def test_source_parameter_used(self) -> None:
        """Source parameter is passed through for zero-copy code extraction."""
        source = "```python\nprint('hello')\n```\n"
        doc = parse(source)

        html = render_document_to_html(doc, source=source)
        assert "print" in html


# =============================================================================
# Guard: _is_patitas_document Tests
# =============================================================================


class TestDocumentGuard:
    """Tests for the _is_patitas_document type guard used by all functions."""

    def test_real_document_passes(self) -> None:
        """Real Patitas Document passes the guard."""
        doc = parse("Hello\n")
        # All functions should work with a real Document
        assert extract_plain_text_from_document(doc) != ""

    def test_dict_fails_guard(self) -> None:
        """Dict objects fail the guard."""
        fake = {"children": [], "location": None}
        assert extract_plain_text_from_document(fake) == ""
        assert extract_links_from_document(fake) == []
        assert extract_toc_from_document(fake) == []
        assert render_document_to_html(fake) == ""

    def test_none_fails_guard(self) -> None:
        """None fails the guard."""
        assert extract_plain_text_from_document(None) == ""
        assert extract_links_from_document(None) == []
        assert extract_toc_from_document(None) == []
        assert render_document_to_html(None) == ""
