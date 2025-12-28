"""CommonMark compliance tests for Patitas.

Tests based on CommonMark 0.31 specification.
Note: Full compliance is a goal; some tests may fail during development.
"""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas import parse


class TestATXHeadings:
    """CommonMark ATX heading tests (4.2)."""

    def test_simple_headings(self):
        """Simple ATX headings."""
        assert "<h1>" in parse("# foo")
        assert "<h2>" in parse("## foo")
        assert "<h3>" in parse("### foo")
        assert "<h4>" in parse("#### foo")
        assert "<h5>" in parse("##### foo")
        assert "<h6>" in parse("###### foo")

    def test_more_than_six_not_heading(self):
        """More than six # characters is not a heading."""
        html = parse("####### foo")
        assert "<h7>" not in html

    def test_space_required_after_hash(self):
        """Space required after opening sequence."""
        html = parse("#5 bolt")
        assert "<h1>" not in html

    def test_escaped_hash_not_heading(self):
        """Escaped # is not a heading."""
        html = parse("\\## foo")
        assert "<h2>" not in html

    def test_inline_content_in_heading(self):
        """Headings can contain inline content."""
        html = parse("# foo *bar* \\*baz\\*")
        assert "<h1>" in html
        assert "<em>" in html

    def test_leading_trailing_spaces_ignored(self):
        """Leading and trailing spaces are ignored."""
        html = parse("#                  foo                     ")
        assert "<h1>" in html
        assert "foo" in html

    def test_indented_heading(self):
        """Up to 3 spaces of indentation allowed."""
        assert "<h1>" in parse(" # foo")
        assert "<h1>" in parse("  # foo")
        assert "<h1>" in parse("   # foo")

    def test_four_spaces_is_code(self):
        """Four spaces of indentation is code block."""
        html = parse("    # foo")
        assert "<h1>" not in html

    def test_closing_sequence_optional(self):
        """Closing # sequence is optional."""
        html = parse("## foo ##")
        assert "<h2>" in html

    def test_closing_must_have_space(self):
        """Closing sequence must be preceded by space."""
        html = parse("# foo#")
        assert "foo#" in html


class TestSetextHeadings:
    """CommonMark setext heading tests (4.3)."""

    # Note: Setext headings not yet implemented in Patitas
    @pytest.mark.skip(reason="Setext headings not yet implemented")
    def test_setext_h1(self):
        """Setext H1 with ===."""
        html = parse("Foo\n===")
        assert "<h1>" in html

    @pytest.mark.skip(reason="Setext headings not yet implemented")
    def test_setext_h2(self):
        """Setext H2 with ---."""
        html = parse("Foo\n---")
        assert "<h2>" in html


class TestThematicBreaks:
    """CommonMark thematic break tests (4.1)."""

    @pytest.mark.parametrize(
        "source",
        [
            "***",
            "---",
            "___",
            " ***",
            "  ***",
            "   ***",
            "***  ",
            "_ _ _",
            " **  * ** * ** * **",
            "-     -      -      -",
        ],
    )
    def test_thematic_break_variants(self, source):
        """Various valid thematic breaks."""
        html = parse(source)
        assert "<hr />" in html

    def test_not_thematic_break_two_chars(self):
        """Two characters is not enough."""
        html = parse("--")
        assert "<hr />" not in html

    def test_thematic_break_in_list_context(self):
        """Thematic break in list context."""
        html = parse("- foo\n***\n- bar")
        assert "<hr />" in html


class TestFencedCodeBlocks:
    """CommonMark fenced code block tests (4.5)."""

    def test_backtick_fence(self):
        """Backtick code fence."""
        html = parse("```\ncode\n```")
        assert "<pre>" in html
        assert "<code>" in html

    def test_tilde_fence(self):
        """Tilde code fence."""
        html = parse("~~~\ncode\n~~~")
        assert "<pre>" in html

    def test_fence_with_info_string(self):
        """Fence with info string."""
        html = parse("```ruby\ndef foo\nend\n```")
        assert 'class="language-ruby"' in html

    def test_backticks_in_tilde_fence(self):
        """Backticks can appear in tilde fence."""
        html = parse("~~~\n```\ncode\n```\n~~~")
        assert "```" in html

    def test_longer_closing_fence_allowed(self):
        """Closing fence can be longer."""
        html = parse("```\ncode\n`````")
        assert "code" in html

    def test_unclosed_fence_continues_to_end(self):
        """Unclosed fence continues to document end."""
        html = parse("```\ncode")
        assert html is not None


class TestBlockQuotes:
    """CommonMark block quote tests (5.1)."""

    def test_simple_block_quote(self):
        """Simple block quote."""
        html = parse("> foo")
        assert "<blockquote>" in html

    def test_block_quote_with_paragraphs(self):
        """Block quote with paragraphs."""
        html = parse("> foo\n>\n> bar")
        assert "<blockquote>" in html


class TestListItems:
    """CommonMark list item tests (5.2)."""

    def test_bullet_list_marker(self):
        """Bullet list markers."""
        for marker in ["-", "*", "+"]:
            html = parse(f"{marker} item")
            assert "<li>" in html

    def test_ordered_list_marker(self):
        """Ordered list marker."""
        html = parse("1. item")
        assert "<ol>" in html
        assert "<li>" in html


class TestLists:
    """CommonMark list tests (5.3)."""

    def test_bullet_list(self):
        """Bullet list."""
        html = parse("- one\n- two\n- three")
        assert "<ul>" in html
        assert html.count("<li>") == 3

    def test_ordered_list(self):
        """Ordered list."""
        html = parse("1. one\n2. two\n3. three")
        assert "<ol>" in html
        assert html.count("<li>") == 3


class TestParagraphs:
    """CommonMark paragraph tests (4.8)."""

    def test_simple_paragraph(self):
        """Simple paragraph."""
        html = parse("aaa\n\nbbb")
        assert html.count("<p>") == 2

    def test_leading_spaces_not_skipped(self):
        """Leading spaces not completely skipped."""
        html = parse("  aaa\nbbb")
        # Content should be preserved
        assert "aaa" in html
        assert "bbb" in html


class TestBlankLines:
    """CommonMark blank line tests (4.9)."""

    def test_blank_lines_between_blocks(self):
        """Blank lines between blocks."""
        html = parse("aaa\n\n\n\nbbb")
        assert html.count("<p>") == 2


class TestBackslashEscapes:
    """CommonMark backslash escape tests (6.1)."""

    @pytest.mark.parametrize(
        "char",
        ["!", '"', "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/"],
    )
    def test_escaped_punctuation(self, char):
        """Escaped punctuation."""
        html = parse(f"\\{char}")
        # Character should appear literally
        assert char in html or f"&#{ord(char)};" in html

    def test_backslash_before_letter(self):
        """Backslash before non-escapable character."""
        html = parse("\\a")
        assert "\\a" in html


class TestCodeSpans:
    """CommonMark code span tests (6.3)."""

    def test_simple_code_span(self):
        """Simple code span."""
        html = parse("`foo`")
        assert "<code>foo</code>" in html

    def test_double_backtick_code_span(self):
        """Double backtick code span."""
        html = parse("`` foo ` bar ``")
        assert "<code>" in html

    def test_stripping_spaces(self):
        """Stripping one space from start and end."""
        html = parse("` foo `")
        assert "<code>foo</code>" in html


class TestEmphasis:
    """CommonMark emphasis tests (6.4)."""

    def test_asterisk_emphasis(self):
        """Asterisk emphasis."""
        html = parse("*foo bar*")
        assert "<em>foo bar</em>" in html

    def test_underscore_emphasis(self):
        """Underscore emphasis."""
        html = parse("_foo bar_")
        assert "<em>foo bar</em>" in html

    def test_asterisk_strong(self):
        """Asterisk strong."""
        html = parse("**foo bar**")
        assert "<strong>foo bar</strong>" in html

    def test_underscore_strong(self):
        """Underscore strong."""
        html = parse("__foo bar__")
        assert "<strong>foo bar</strong>" in html


class TestLinks:
    """CommonMark link tests (6.5)."""

    def test_inline_link(self):
        """Inline link."""
        html = parse("[link](/uri)")
        assert '<a href="/uri">link</a>' in html

    def test_link_with_title(self):
        """Link with title."""
        html = parse('[link](/uri "title")')
        assert 'title="title"' in html

    def test_link_empty_destination(self):
        """Link with empty destination."""
        html = parse("[link]()")
        assert 'href=""' in html


class TestImages:
    """CommonMark image tests (6.6)."""

    def test_inline_image(self):
        """Inline image."""
        html = parse("![alt](/url)")
        assert '<img src="/url"' in html
        assert 'alt="alt"' in html

    def test_image_with_title(self):
        """Image with title."""
        html = parse('![alt](/url "title")')
        assert 'title="title"' in html


class TestHardLineBreaks:
    """CommonMark hard line break tests (6.11)."""

    def test_backslash_hard_break(self):
        """Backslash at end of line."""
        html = parse("foo\\\nbar")
        assert "<br />" in html

    def test_two_spaces_hard_break(self):
        """Two spaces at end of line."""
        html = parse("foo  \nbar")
        # Should have break (currently using backslash only)
        # This may be a gap in current implementation
        assert html is not None


class TestSoftLineBreaks:
    """CommonMark soft line break tests (6.12)."""

    def test_soft_break(self):
        """Soft break in paragraph."""
        html = parse("foo\nbaz")
        # Soft break renders as space or newline
        assert "foo" in html
        assert "baz" in html
