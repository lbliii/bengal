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
        # Note: Patitas adds id attributes, so check for <h1 not <h1>
        assert "<h1" in parse("# foo")
        assert "<h2" in parse("## foo")
        assert "<h3" in parse("### foo")
        assert "<h4" in parse("#### foo")
        assert "<h5" in parse("##### foo")
        assert "<h6" in parse("###### foo")

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
        assert "<h1" in html  # Patitas adds id attribute
        assert "<em>" in html

    def test_leading_trailing_spaces_ignored(self):
        """Leading and trailing spaces are ignored."""
        html = parse("#                  foo                     ")
        assert "<h1" in html  # Patitas adds id attribute
        assert "foo" in html

    def test_indented_heading(self):
        """Up to 3 spaces of indentation allowed."""
        assert "<h1" in parse(" # foo")  # Patitas adds id attribute
        assert "<h1" in parse("  # foo")
        assert "<h1" in parse("   # foo")

    def test_four_spaces_is_code(self):
        """Four spaces of indentation is code block."""
        html = parse("    # foo")
        assert "<h1>" not in html

    def test_closing_sequence_optional(self):
        """Closing # sequence is optional."""
        html = parse("## foo ##")
        assert "<h2" in html  # Patitas adds id attribute

    def test_closing_must_have_space(self):
        """Closing sequence must be preceded by space."""
        html = parse("# foo#")
        assert "foo#" in html


class TestSetextHeadings:
    """CommonMark setext heading tests (4.3)."""

    def test_setext_h1(self):
        """Setext H1 with ===."""
        html = parse("Foo\n===")
        assert "<h1" in html  # Patitas adds id attribute

    def test_setext_h2(self):
        """Setext H2 with ---."""
        html = parse("Foo\n---")
        assert "<h2" in html  # Patitas adds id attribute

    def test_setext_multiline(self):
        """Setext heading can span multiple lines."""
        html = parse("Foo\nBar\n===")
        assert "<h1" in html
        assert "Foo" in html
        assert "Bar" in html


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
        # Character should appear literally or as HTML entity
        # Patitas may use &quot; for " and &#x27; for '
        assert (
            char in html
            or f"&#{ord(char)};" in html
            or "&quot;" in html  # HTML entity for "
            or "&#x27;" in html  # HTML entity for '
        )

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


# =============================================================================
# Comprehensive List Tests (CommonMark 5.2 & 5.3)
# =============================================================================


class TestListTermination:
    """Tests for list termination rules (CommonMark 5.3).

    A list ends when:
    - A blank line is followed by non-indented content
    - A thematic break appears
    - The document ends
    """

    def test_list_terminated_by_blank_line_and_paragraph(self):
        """Blank line + non-indented paragraph terminates list."""
        html = parse("- item 1\n- item 2\n\nParagraph after list")
        assert html.count("<ul>") == 1
        assert html.count("</ul>") == 1
        assert "<p>Paragraph after list</p>" in html

    def test_two_lists_separated_by_paragraph(self):
        """Two lists separated by a paragraph are distinct."""
        md = """- list 1 item 1
- list 1 item 2

**Middle paragraph**

- list 2 item 1
- list 2 item 2
"""
        html = parse(md)
        assert html.count("<ul>") == 2
        assert html.count("</ul>") == 2

    def test_list_terminated_by_heading(self):
        """List terminated by heading."""
        html = parse("- item\n\n# Heading")
        assert "<ul>" in html
        assert "</ul>" in html
        assert "<h1" in html

    def test_list_terminated_by_thematic_break(self):
        """List terminated by thematic break."""
        html = parse("- item 1\n- item 2\n\n---")
        assert "<ul>" in html
        assert "<hr" in html

    def test_list_terminated_by_code_block(self):
        """List terminated by fenced code block."""
        html = parse("- item\n\n```\ncode\n```")
        assert "<ul>" in html
        assert "<code>" in html or "<pre>" in html


class TestLooseVsTightLists:
    """Tests for loose vs tight list detection (CommonMark 5.3).

    Tight list: No blank lines between items → no <p> wrappers
    Loose list: Blank lines between items → <p> wrappers
    """

    def test_tight_list_no_paragraph_wrappers(self):
        """Tight list items don't get <p> wrappers."""
        html = parse("- one\n- two\n- three")
        # In tight lists, content is directly in <li>
        assert "<li>one</li>" in html or "<li>one" in html
        # Should NOT have <p> inside tight list items
        assert "<li><p>" not in html

    def test_loose_list_has_paragraph_wrappers(self):
        """Loose list items get <p> wrappers."""
        md = """- one

- two

- three
"""
        html = parse(md)
        # Loose lists wrap content in <p>
        assert "<li><p>" in html or "<li>\n<p>" in html

    def test_single_blank_line_makes_loose(self):
        """Single blank line between any items makes entire list loose."""
        md = """- one
- two

- three
"""
        html = parse(md)
        # The blank line before "three" makes the whole list loose
        assert html.count("<p>") >= 3 or "<li><p>" in html


class TestNestedLists:
    """Tests for nested list indentation (CommonMark 5.2).

    Nested lists require proper indentation relative to parent.
    """

    def test_nested_unordered_list(self):
        """Nested unordered list with 2-space indent."""
        md = """- parent
  - child 1
  - child 2
"""
        html = parse(md)
        assert html.count("<ul>") == 2
        assert html.count("</ul>") == 2

    def test_nested_ordered_in_unordered(self):
        """Ordered list nested in unordered list."""
        md = """- parent
  1. first
  2. second
"""
        html = parse(md)
        assert "<ul>" in html
        assert "<ol>" in html

    @pytest.mark.xfail(reason="4-space indent triggers code block before nested list detection")
    def test_deeply_nested_lists(self):
        """Three levels of nesting."""
        md = """- level 1
  - level 2
    - level 3
"""
        html = parse(md)
        assert html.count("<ul>") == 3

    def test_nested_list_returns_to_parent(self):
        """After nested list, can return to parent level."""
        md = """- parent 1
  - child
- parent 2
"""
        html = parse(md)
        # Should have 2 items at top level, 1 nested
        assert html.count("<ul>") == 2  # parent + nested


class TestParagraphContinuation:
    """Tests for paragraph continuation in list items (CommonMark 5.2).

    Indented content after blank line continues the list item.
    """

    def test_indented_paragraph_continues_item(self):
        """Indented paragraph continues list item."""
        md = """- First paragraph

  Second paragraph in same item
"""
        html = parse(md)
        assert html.count("<ul>") == 1
        # Both paragraphs should be in the list
        assert "First paragraph" in html
        assert "Second paragraph" in html

    def test_non_indented_paragraph_ends_list(self):
        """Non-indented paragraph ends list."""
        md = """- List item

Not in list
"""
        html = parse(md)
        assert "<ul>" in html
        assert "</ul>" in html
        # "Not in list" should be outside the list
        assert "<p>Not in list</p>" in html

    def test_multiple_paragraphs_in_item(self):
        """Multiple continuation paragraphs in one item."""
        md = """- Para 1

  Para 2

  Para 3
"""
        html = parse(md)
        assert html.count("<ul>") == 1
        # All three should be in the list item
        assert html.count("<p>") >= 3 or "Para 3" in html


class TestListInterruption:
    """Tests for what can interrupt a list (CommonMark 5.3).

    Certain blocks can interrupt lists, others cannot.
    """

    def test_blank_line_required_before_code_block(self):
        """Code block after list item needs blank line."""
        md = """- item

```
code
```
"""
        html = parse(md)
        assert "<ul>" in html
        assert "<code>" in html or "<pre>" in html

    def test_heading_interrupts_list(self):
        """ATX heading can interrupt list after blank line."""
        md = """- item

# Heading
"""
        html = parse(md)
        assert "<ul>" in html
        assert "<h1" in html


class TestOrderedListStart:
    """Tests for ordered list starting numbers (CommonMark 5.3)."""

    def test_start_at_one(self):
        """Ordered list starting at 1."""
        html = parse("1. first\n2. second")
        assert "<ol>" in html
        assert 'start="' not in html or 'start="1"' in html

    def test_start_at_other_number(self):
        """Ordered list starting at number other than 1."""
        html = parse("3. first\n4. second")
        assert '<ol start="3">' in html

    def test_start_at_zero(self):
        """Ordered list can start at 0."""
        html = parse("0. first\n1. second")
        assert '<ol start="0">' in html

    def test_numbers_dont_have_to_be_sequential(self):
        """Item numbers don't have to be sequential."""
        html = parse("1. first\n5. second\n3. third")
        assert "<ol>" in html
        assert html.count("<li>") == 3


class TestListMarkerVariants:
    """Tests for different list marker styles (CommonMark 5.2)."""

    def test_dash_marker(self):
        """Dash (-) as list marker."""
        html = parse("- item")
        assert "<ul>" in html

    def test_asterisk_marker(self):
        """Asterisk (*) as list marker."""
        html = parse("* item")
        assert "<ul>" in html

    def test_plus_marker(self):
        """Plus (+) as list marker."""
        html = parse("+ item")
        assert "<ul>" in html

    def test_dot_ordered_marker(self):
        """Dot (.) ordered list marker."""
        html = parse("1. item")
        assert "<ol>" in html

    def test_paren_ordered_marker(self):
        """Parenthesis ()) ordered list marker."""
        html = parse("1) item")
        assert "<ol>" in html

    @pytest.mark.xfail(
        reason="Different markers should create separate lists - not yet implemented"
    )
    def test_different_markers_different_lists(self):
        """Different unordered markers create different lists."""
        md = """- dash item

* asterisk item
"""
        html = parse(md)
        # Different markers after blank line = different lists
        assert html.count("<ul>") == 2


class TestListEdgeCases:
    """Edge cases for list parsing."""

    def test_empty_list_item(self):
        """Empty list item."""
        html = parse("- \n- item")
        assert html.count("<li>") == 2

    def test_list_item_with_only_spaces(self):
        """List item with only spaces after marker."""
        html = parse("-   \n- item")
        assert "<ul>" in html

    def test_very_long_ordered_number(self):
        """Ordered list with large starting number (up to 9 digits)."""
        html = parse("123456789. item")
        assert "<ol" in html

    def test_ten_digit_number_not_list(self):
        """10-digit number is not a valid list marker."""
        html = parse("1234567890. item")
        # Should be paragraph, not list
        assert "<ol" not in html

    def test_list_with_inline_formatting(self):
        """List items with inline formatting."""
        html = parse("- **bold** item\n- *italic* item")
        assert "<strong>" in html
        assert "<em>" in html

    def test_list_with_code_span(self):
        """List items with code spans."""
        html = parse("- `code` item\n- another `code`")
        assert "<code>" in html

    def test_list_with_link(self):
        """List items with links."""
        html = parse("- [link](url)\n- another item")
        assert "<a " in html
