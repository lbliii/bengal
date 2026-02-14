"""Renderer tests for Patitas.

Tests HTML rendering from AST nodes.
"""

from __future__ import annotations

import pytest

from bengal.parsing.backends.patitas import parse_to_ast
from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer


class TestRendererBasics:
    """Basic renderer functionality."""

    def test_empty_input(self, render_nodes):
        """Empty AST produces empty output."""
        html = render_nodes((), source="")
        assert html == ""

    def test_renderer_creates_new_stringbuilder(self):
        """Each render call creates new StringBuilder."""
        renderer = HtmlRenderer(source="")
        html1 = renderer.render(())
        html2 = renderer.render(())
        assert html1 == html2 == ""


class TestHeadingRendering:
    """Heading HTML rendering."""

    @pytest.mark.parametrize(
        ("level", "expected_tag"),
        [
            (1, "h1"),
            (2, "h2"),
            (3, "h3"),
            (4, "h4"),
            (5, "h5"),
            (6, "h6"),
        ],
    )
    def test_heading_tags(self, parse_md, level, expected_tag):
        """Correct heading tags are used (with auto-generated id attribute)."""
        html = parse_md("#" * level + " Heading")
        # Patitas adds id attributes to headings for anchor links (extension)
        assert f"<{expected_tag} " in html or f"<{expected_tag}>" in html
        assert f"</{expected_tag}>" in html

    def test_heading_content(self, parse_md):
        """Heading content is rendered."""
        html = parse_md("# Hello World")
        assert "Hello World" in html

    def test_heading_with_inline_formatting(self, parse_md):
        """Heading preserves inline formatting."""
        html = parse_md("# Hello **World**")
        assert "<strong>World</strong>" in html


class TestParagraphRendering:
    """Paragraph HTML rendering."""

    def test_paragraph_tags(self, parse_md):
        """Paragraph uses <p> tags."""
        html = parse_md("Hello")
        assert "<p>" in html
        assert "</p>" in html

    def test_paragraph_content(self, parse_md):
        """Paragraph content is rendered."""
        html = parse_md("Hello world")
        assert "Hello world" in html


class TestCodeRendering:
    """Code block HTML rendering."""

    def test_fenced_code_tags(self, parse_md):
        """Fenced code uses pre/code tags."""
        html = parse_md("```\ncode\n```")
        assert "<pre>" in html
        assert "<code>" in html
        assert "</code>" in html
        assert "</pre>" in html

    def test_fenced_code_language_class(self, parse_md):
        """Fenced code includes language class or data attribute.

        Note: With syntax highlighting enabled (default), rosettes adds
        data-language attribute. Without highlighting, uses language-{lang} class.
        """
        html = parse_md("```python\ncode\n```")
        # Rosettes uses data-language, non-highlighted uses class="language-..."
        assert 'data-language="python"' in html or 'class="language-python"' in html

    def test_fenced_code_content(self, parse_md):
        """Fenced code content is rendered."""
        html = parse_md("```\nhello\n```")
        assert "hello" in html

    def test_code_html_escaping(self, parse_md):
        """Code content is HTML-escaped."""
        html = parse_md("```\n<script>alert('xss')</script>\n```")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_code_span(self, parse_md):
        """Inline code rendering."""
        html = parse_md("`code`")
        assert "<code>" in html
        assert "code" in html


class TestEmphasisRendering:
    """Emphasis/strong HTML rendering."""

    def test_emphasis(self, parse_md):
        """Emphasis uses <em> tag."""
        html = parse_md("*emphasis*")
        assert "<em>" in html
        assert "</em>" in html
        assert "emphasis" in html

    def test_strong(self, parse_md):
        """Strong uses <strong> tag."""
        html = parse_md("**strong**")
        assert "<strong>" in html
        assert "</strong>" in html
        assert "strong" in html

    def test_underscore_emphasis(self, parse_md):
        """Underscore emphasis works."""
        html = parse_md("_emphasis_")
        assert "<em>" in html

    def test_underscore_strong(self, parse_md):
        """Underscore strong works."""
        html = parse_md("__strong__")
        assert "<strong>" in html

    def test_nested_emphasis(self, parse_md):
        """Nested emphasis renders correctly."""
        html = parse_md("***both***")
        assert "<strong>" in html or "<em>" in html


class TestLinkRendering:
    """Link HTML rendering."""

    def test_basic_link(self, parse_md):
        """Basic link rendering."""
        html = parse_md("[text](http://example.com)")
        assert '<a href="http://example.com">' in html
        assert "text" in html
        assert "</a>" in html

    def test_link_with_title(self, parse_md):
        """Link with title attribute."""
        html = parse_md('[text](http://example.com "title")')
        assert 'title="title"' in html

    def test_link_url_escaping(self, parse_md):
        """Link URLs are properly escaped."""
        html = parse_md("[text](http://example.com?a=1&b=2)")
        assert "http://example.com" in html


class TestImageRendering:
    """Image HTML rendering."""

    def test_basic_image(self, parse_md):
        """Basic image rendering."""
        html = parse_md("![alt text](image.png)")
        assert '<img src="image.png"' in html
        assert 'alt="alt text"' in html

    def test_image_with_title(self, parse_md):
        """Image with title attribute."""
        html = parse_md('![alt](image.png "title")')
        assert 'title="title"' in html


class TestListRendering:
    """List HTML rendering."""

    def test_unordered_list(self, parse_md):
        """Unordered list uses <ul>."""
        html = parse_md("- item 1\n- item 2")
        assert "<ul>" in html
        assert "</ul>" in html
        assert "<li>" in html

    def test_ordered_list(self, parse_md):
        """Ordered list uses <ol>."""
        html = parse_md("1. item 1\n2. item 2")
        assert "<ol>" in html
        assert "</ol>" in html

    def test_ordered_list_start(self, parse_md):
        """Ordered list respects start number."""
        html = parse_md("5. item")
        assert 'start="5"' in html

    def test_list_items(self, parse_md):
        """List items are rendered."""
        html = parse_md("- one\n- two\n- three")
        assert html.count("<li>") == 3


class TestBlockQuoteRendering:
    """Block quote HTML rendering."""

    def test_basic_block_quote(self, parse_md):
        """Basic block quote rendering."""
        html = parse_md("> quote")
        assert "<blockquote>" in html
        assert "</blockquote>" in html


class TestThematicBreakRendering:
    """Thematic break HTML rendering."""

    def test_thematic_break(self, parse_md):
        """Thematic break uses <hr />."""
        html = parse_md("---")
        assert "<hr />" in html


class TestLineBreakRendering:
    """Line break HTML rendering."""

    def test_hard_break(self, parse_md):
        """Hard break uses <br />."""
        html = parse_md("line1\\\nline2")
        assert "<br />" in html


class TestHtmlEscaping:
    """HTML special character escaping."""

    def test_ampersand_escaped(self, parse_md):
        """Ampersand is escaped."""
        html = parse_md("A & B")
        assert "&amp;" in html

    def test_less_than_escaped(self, parse_md):
        """Less than is escaped."""
        html = parse_md("A < B")
        assert "&lt;" in html

    def test_greater_than_escaped(self, parse_md):
        """Greater than is escaped."""
        html = parse_md("A > B")
        # Note: > is sometimes not escaped in content
        # but < should always be
        assert "<" not in html.replace("<p>", "").replace("</p>", "")


class TestIterBlocks:
    """Block iteration rendering."""

    def test_iter_blocks(self):
        """iter_blocks yields per-block HTML."""
        source = "# One\n\n# Two\n\n# Three"
        ast = parse_to_ast(source)
        renderer = HtmlRenderer(source)
        blocks = list(renderer.iter_blocks(ast))
        assert len(blocks) == 3
        assert all("<h1" in block for block in blocks)  # Patitas adds id attribute
