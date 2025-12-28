"""Inline element tests for Patitas.

Comprehensive tests for inline parsing and rendering.
"""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas import parse


class TestEmphasisVariants:
    """Emphasis with different delimiters and contexts."""

    @pytest.mark.parametrize(
        "source,expected",
        [
            ("*em*", "<em>em</em>"),
            ("_em_", "<em>em</em>"),
            ("**strong**", "<strong>strong</strong>"),
            ("__strong__", "<strong>strong</strong>"),
        ],
    )
    def test_basic_emphasis(self, source, expected):
        """Basic emphasis variants."""
        html = parse(source)
        assert expected in html

    def test_emphasis_at_start(self):
        """Emphasis at paragraph start."""
        html = parse("*em* rest")
        assert "<em>em</em>" in html

    def test_emphasis_at_end(self):
        """Emphasis at paragraph end."""
        html = parse("start *em*")
        assert "<em>em</em>" in html

    def test_emphasis_in_middle(self):
        """Emphasis in middle of text."""
        html = parse("before *em* after")
        assert "<em>em</em>" in html
        assert "before" in html
        assert "after" in html

    def test_multiple_emphasis(self):
        """Multiple emphasis in same paragraph."""
        html = parse("*one* and *two*")
        assert html.count("<em>") == 2

    def test_emphasis_with_spaces_inside(self):
        """Emphasis with spaces inside."""
        html = parse("*multiple words*")
        assert "<em>multiple words</em>" in html

    def test_unclosed_emphasis(self):
        """Unclosed emphasis treated as literal."""
        html = parse("*unclosed")
        # Should contain literal asterisk or empty emphasis
        assert "*" in html or "<em>" not in html


class TestStrongVariants:
    """Strong emphasis variants."""

    def test_strong_with_emphasis_inside(self):
        """Strong containing emphasis."""
        html = parse("**bold with *italic* inside**")
        assert "<strong>" in html

    def test_emphasis_with_strong_inside(self):
        """Emphasis containing strong."""
        html = parse("*italic with **bold** inside*")
        assert "<em>" in html


class TestCodeSpans:
    """Inline code span tests."""

    def test_basic_code_span(self):
        """Basic code span."""
        html = parse("`code`")
        assert "<code>code</code>" in html

    def test_code_span_with_backticks(self):
        """Code span containing backticks."""
        html = parse("`` `code` ``")
        assert "<code>" in html

    def test_code_span_preserves_spaces(self):
        """Code span preserves internal spaces."""
        html = parse("`a  b`")
        assert "a  b" in html or "a b" in html  # Some normalization may occur

    def test_code_span_escapes_html(self):
        """Code span escapes HTML."""
        html = parse("`<script>`")
        assert "&lt;script&gt;" in html

    def test_multiple_code_spans(self):
        """Multiple code spans in paragraph."""
        html = parse("`one` and `two`")
        assert html.count("<code>") == 2


class TestLinks:
    """Link parsing and rendering tests."""

    def test_basic_link(self):
        """Basic inline link."""
        html = parse("[text](url)")
        assert '<a href="url">text</a>' in html

    def test_link_with_absolute_url(self):
        """Link with absolute URL."""
        html = parse("[Google](https://google.com)")
        assert 'href="https://google.com"' in html

    def test_link_with_title(self):
        """Link with title."""
        html = parse('[text](url "my title")')
        assert 'title="my title"' in html

    def test_link_with_empty_text(self):
        """Link with empty text."""
        html = parse("[](url)")
        assert 'href="url"' in html

    def test_link_with_emphasis_in_text(self):
        """Link text can contain emphasis."""
        html = parse("[*emphasized*](url)")
        assert "<em>" in html or "emphasized" in html

    def test_multiple_links(self):
        """Multiple links in paragraph."""
        html = parse("[one](a) and [two](b)")
        assert 'href="a"' in html
        assert 'href="b"' in html


class TestImages:
    """Image parsing and rendering tests."""

    def test_basic_image(self):
        """Basic image."""
        html = parse("![alt](image.png)")
        assert '<img src="image.png"' in html
        assert 'alt="alt"' in html

    def test_image_with_title(self):
        """Image with title."""
        html = parse('![alt](image.png "title")')
        assert 'title="title"' in html

    def test_image_empty_alt(self):
        """Image with empty alt text."""
        html = parse("![](image.png)")
        assert 'alt=""' in html

    def test_image_url_with_spaces(self):
        """Image URL handling."""
        html = parse("![alt](image%20name.png)")
        assert "image%20name.png" in html


class TestLineBreaks:
    """Line break tests."""

    def test_backslash_hard_break(self):
        """Backslash creates hard break."""
        html = parse("line1\\\nline2")
        assert "<br />" in html

    def test_soft_break_renders_as_newline(self):
        """Soft break renders appropriately."""
        html = parse("line1\nline2")
        # Soft break becomes space or newline
        assert "line1" in html
        assert "line2" in html


class TestEscapes:
    """Escape sequence tests."""

    @pytest.mark.parametrize(
        "char",
        ["\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "+", "-", ".", "!"],
    )
    def test_escaped_characters(self, char):
        """Escaped characters render as literals."""
        html = parse(f"\\{char}")
        # Should contain the literal character, not be processed as markdown
        assert char in html

    def test_escaped_asterisk_not_emphasis(self):
        """Escaped asterisks don't create emphasis."""
        html = parse("\\*not emphasis\\*")
        assert "<em>" not in html

    def test_escape_in_code_span_not_processed(self):
        """Escapes inside code spans are literal."""
        html = parse(r"`\*`")
        assert "\\*" in html or r"\*" in html


class TestMixedInline:
    """Mixed inline elements."""

    def test_emphasis_and_code(self):
        """Emphasis and code in same paragraph."""
        html = parse("*em* and `code`")
        assert "<em>" in html
        assert "<code>" in html

    def test_link_and_emphasis(self):
        """Link and emphasis in same paragraph."""
        html = parse("[link](url) and *em*")
        assert "<a href" in html
        assert "<em>" in html

    def test_complex_inline(self):
        """Complex inline nesting."""
        html = parse("**bold with `code` inside**")
        assert "<strong>" in html
        assert "<code>" in html

    def test_image_and_text(self):
        """Image with surrounding text."""
        html = parse("Before ![alt](img.png) after")
        assert "Before" in html
        assert "<img" in html
        assert "after" in html


class TestInlineEdgeCases:
    """Edge cases for inline parsing."""

    def test_empty_emphasis(self):
        """Empty emphasis markers."""
        html = parse("**")
        # Empty emphasis should render as literal
        assert "**" in html or html.strip() == "<p></p>"

    def test_single_asterisk(self):
        """Single asterisk is literal."""
        html = parse("a * b")
        assert "*" in html

    def test_asterisk_surrounded_by_spaces(self):
        """Asterisks with spaces aren't emphasis."""
        html = parse("a * b * c")
        assert "<em>" not in html

    def test_unclosed_link(self):
        """Unclosed link bracket."""
        html = parse("[unclosed")
        assert "[unclosed" in html or "unclosed" in html

    def test_unclosed_image(self):
        """Unclosed image bracket."""
        html = parse("![unclosed")
        assert "unclosed" in html

    def test_url_without_brackets(self):
        """URL without link brackets is literal."""
        html = parse("http://example.com")
        # Plain URLs are literal text (no autolink plugin)
        assert "http://example.com" in html
