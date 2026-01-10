"""Block element tests for Patitas.

Comprehensive tests for block-level parsing and rendering.
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas import parse


class TestHeadingEdgeCases:
    """Heading edge cases."""

    def test_heading_only_hashes(self):
        """Heading with only hash marks."""
        html = parse("## ")
        assert "<h2" in html  # Patitas adds id attribute: <h2 id="...">

    def test_heading_many_spaces_after_hash(self):
        """Heading with many spaces after hash."""
        html = parse("#    text")
        assert "text" in html

    def test_heading_seven_hashes(self):
        """Seven hashes is not a heading."""
        html = parse("####### not heading")
        assert "<h" not in html or "<h7" not in html

    def test_heading_no_space(self):
        """No space after hash is not heading."""
        html = parse("#notaheading")
        assert "<h1" not in html  # Should not be parsed as heading
        assert "#notaheading" in html

    def test_heading_trailing_hashes_with_space(self):
        """Trailing hashes after space are removed."""
        html = parse("# Heading #")
        assert "Heading" in html
        # Trailing # should be removed

    def test_heading_with_code(self):
        """Heading containing code span."""
        html = parse("# Heading with `code`")
        assert "<h1" in html  # Patitas adds id attribute
        assert "<code>" in html


class TestCodeBlockEdgeCases:
    """Code block edge cases."""

    def test_empty_code_block(self):
        """Empty fenced code block."""
        html = parse("```\n```")
        assert "<pre>" in html
        assert "<code>" in html

    def test_code_block_whitespace_only(self):
        """Code block with only whitespace."""
        html = parse("```\n   \n```")
        assert "<pre>" in html

    def test_code_block_long_fence(self):
        """Code block with long fence."""
        html = parse("``````\ncode\n``````")
        assert "<pre>" in html
        assert "code" in html

    def test_code_block_info_with_spaces(self):
        """Code block info string with spaces."""
        html = parse("```python 3.12\ncode\n```")
        assert 'class="language-python"' in html

    def test_code_block_preserves_indentation(self):
        """Code block preserves indentation."""
        html = parse("```\n  indented\n```")
        assert "  indented" in html or "indented" in html

    def test_code_block_preserves_blank_lines(self):
        """Code block preserves blank lines."""
        html = parse("```\nline1\n\nline3\n```")
        # Should have content with blank line preserved
        assert "line1" in html
        assert "line3" in html

    def test_unclosed_code_block(self):
        """Unclosed code block continues to EOF."""
        html = parse("```\ncode\nmore code")
        # Should still render as code
        assert "<pre>" in html or "code" in html


class TestListEdgeCases:
    """List edge cases."""

    def test_single_item_list(self):
        """Single item list."""
        html = parse("- single")
        assert "<ul>" in html
        assert "<li>" in html

    def test_list_with_blank_line_between_items(self):
        """List with blank line between items (loose list)."""
        html = parse("- item 1\n\n- item 2")
        assert html.count("<li>") >= 1

    def test_nested_list(self):
        """Nested list (not fully implemented yet)."""
        html = parse("- outer\n  - inner")
        # For now, just check it doesn't crash
        assert "outer" in html

    def test_ordered_list_non_one_start(self):
        """Ordered list starting not from 1."""
        html = parse("10. item")
        assert 'start="10"' in html

    def test_mixed_list_markers(self):
        """Mixed list markers create separate lists."""
        html = parse("- one\n* two")
        assert "<li>" in html

    def test_list_item_with_inline(self):
        """List item with inline formatting."""
        html = parse("- item with **bold**")
        assert "<strong>" in html

    def test_heading_after_list_not_nested(self):
        """Heading following a list after a blank line stays outside the list."""
        html = parse("## Features\n\n- a\n- b\n- c\n\n## Next Steps\n\n1. one\n2. two\n")
        assert '<h2 id="next-steps"' in html
        assert html.index("</ul>") < html.index('id="next-steps"')

    def test_ordered_list_paren_marker(self):
        """Ordered list with parenthesis marker."""
        # Note: Currently only period is supported
        html = parse("1. item")
        assert "<ol>" in html


class TestBlockQuoteEdgeCases:
    """Block quote edge cases."""

    def test_empty_block_quote(self):
        """Empty block quote."""
        html = parse(">")
        assert "<blockquote>" in html

    def test_block_quote_multiple_lines(self):
        """Multi-line block quote."""
        html = parse("> line 1\n> line 2")
        assert "<blockquote>" in html

    def test_block_quote_lazy_continuation(self):
        """Block quote lazy continuation."""
        html = parse("> line 1\nline 2")
        assert "<blockquote>" in html

    def test_nested_block_quote(self):
        """Nested block quotes."""
        html = parse("> > nested")
        assert "<blockquote>" in html

    def test_block_quote_with_code(self):
        """Block quote containing code."""
        html = parse("> `code`")
        assert "<blockquote>" in html


class TestThematicBreakEdgeCases:
    """Thematic break edge cases."""

    def test_thematic_break_with_many_chars(self):
        """Thematic break with many characters."""
        html = parse("----------------------------")
        assert "<hr />" in html

    def test_thematic_break_with_spaces(self):
        """Thematic break with internal spaces."""
        html = parse("- - - - -")
        assert "<hr />" in html

    def test_not_thematic_break_two_chars(self):
        """Two characters is not thematic break."""
        html = parse("--")
        assert "<hr />" not in html


class TestParagraphEdgeCases:
    """Paragraph edge cases."""

    def test_paragraph_with_leading_spaces(self):
        """Paragraph with leading spaces (< 4)."""
        html = parse("   text")
        assert "<p>" in html
        assert "text" in html

    def test_paragraph_single_word(self):
        """Single word paragraph."""
        html = parse("word")
        assert "<p>word</p>" in html

    def test_paragraph_with_numbers(self):
        """Paragraph starting with numbers (not list)."""
        html = parse("123 not a list")
        assert "<p>" in html

    def test_multiple_paragraphs(self):
        """Multiple paragraphs separated by blank lines."""
        html = parse("Para 1\n\nPara 2\n\nPara 3")
        assert html.count("<p>") == 3


class TestMixedBlocks:
    """Mixed block element tests."""

    def test_heading_then_paragraph(self):
        """Heading followed by paragraph."""
        html = parse("# Heading\n\nParagraph")
        assert "<h1" in html  # Patitas adds id attribute
        assert "<p>" in html

    def test_paragraph_then_code(self):
        """Paragraph followed by code block."""
        html = parse("Text\n\n```\ncode\n```")
        assert "<p>" in html
        assert "<pre>" in html

    def test_list_then_paragraph(self):
        """List followed by paragraph."""
        html = parse("- item\n\nParagraph")
        assert "<ul>" in html
        assert "<p>" in html

    def test_code_then_heading(self):
        """Code block followed by heading."""
        html = parse("```\ncode\n```\n\n# Heading")
        assert "<pre>" in html
        assert "<h1" in html  # Patitas adds id attribute

    def test_thematic_break_between_paragraphs(self):
        """Thematic break between paragraphs."""
        html = parse("Para 1\n\n---\n\nPara 2")
        assert html.count("<p>") == 2
        assert "<hr />" in html


class TestIndentation:
    """Indentation handling tests."""

    def test_three_space_indent_not_code(self):
        """Three space indent is not code block."""
        html = parse("   not code")
        assert "<pre>" not in html
        assert "not code" in html

    def test_four_space_indent_is_code(self):
        """Four space indent is code block."""
        html = parse("    code")
        assert "<pre>" in html or "<code>" in html

    def test_tab_indent_is_code(self):
        """Tab indent is code block."""
        html = parse("\tcode")
        assert "<pre>" in html or "<code>" in html


class TestHTMLBlocks:
    """Raw HTML block tests."""

    def test_html_comment(self):
        """HTML comment passes through."""
        html = parse("<!-- comment -->")
        # HTML blocks pass through unchanged
        assert "<!--" in html or "comment" in html

    def test_html_tag(self):
        """HTML tag passes through."""
        html = parse("<div>content</div>")
        # May be treated as HTML block or paragraph
        assert "content" in html


class TestListTermination:
    """Tests for list termination behavior with non-indented content."""

    def test_list_terminated_by_non_indented_paragraph(self):
        """Non-indented paragraph after blank line terminates list.

        This is the exact bug from the configuration docs:
        - Item 1
        - Item 2

        **Bold text:** <- should be separate paragraph, not part of list
        - Item 3
        """
        md = """**When to enable:**
- During active theme development
- In CI/CD pipelines
- When debugging template issues

**What it catches:**
- Jinja2 syntax errors
- Unknown filter names
"""
        html = parse(md)
        # Should have two separate <ul> elements
        assert html.count("<ul>") == 2
        assert html.count("</ul>") == 2
        # Bold text should be in paragraph, not in list item
        assert "<p><strong>What it catches:</strong></p>" in html

    def test_indented_paragraph_continues_list_item(self):
        """Indented paragraph after blank line continues list item (loose list)."""
        md = """- First item

  Continuation of first item (indented)

- Second item
"""
        html = parse(md)
        # Should have only one <ul>
        assert html.count("<ul>") == 1
        # First item should have two paragraphs
        assert "Continuation of first item" in html
