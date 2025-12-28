"""Lexer tests for Patitas.

Tests the state-machine lexer for correct tokenization.
"""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas.lexer import Lexer
from bengal.rendering.parsers.patitas.tokens import TokenType


class TestLexerBasics:
    """Basic lexer functionality."""

    def test_empty_input(self, tokenize):
        """Empty input produces only EOF."""
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_single_newline(self, tokenize):
        """Single newline is a blank line."""
        tokens = tokenize("\n")
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.BLANK_LINE
        assert tokens[1].type == TokenType.EOF

    def test_multiple_blank_lines(self, tokenize):
        """Multiple blank lines produce multiple blank line tokens."""
        tokens = tokenize("\n\n\n")
        blank_lines = [t for t in tokens if t.type == TokenType.BLANK_LINE]
        assert len(blank_lines) == 3


class TestATXHeadings:
    """ATX heading tokenization."""

    @pytest.mark.parametrize(
        "source,expected_value",
        [
            ("# H1", "# H1"),
            ("## H2", "## H2"),
            ("### H3", "### H3"),
            ("#### H4", "#### H4"),
            ("##### H5", "##### H5"),
            ("###### H6", "###### H6"),
        ],
    )
    def test_heading_levels(self, tokenize, source, expected_value):
        """All heading levels are tokenized correctly."""
        tokens = tokenize(source)
        assert tokens[0].type == TokenType.ATX_HEADING
        assert tokens[0].value == expected_value

    def test_heading_with_trailing_hashes(self, tokenize):
        """Trailing hashes are removed from headings."""
        tokens = tokenize("# Heading #")
        assert tokens[0].type == TokenType.ATX_HEADING
        assert "Heading" in tokens[0].value

    def test_heading_without_space(self, tokenize):
        """#text without space is not a heading."""
        tokens = tokenize("#notaheading")
        assert tokens[0].type == TokenType.PARAGRAPH_LINE

    def test_heading_with_inline_content(self, tokenize):
        """Headings preserve inline content."""
        tokens = tokenize("# Hello **World**")
        assert tokens[0].type == TokenType.ATX_HEADING
        assert "**World**" in tokens[0].value


class TestFencedCode:
    """Fenced code block tokenization."""

    def test_basic_fenced_code(self, tokenize):
        """Basic fenced code block."""
        tokens = tokenize("```\ncode\n```")
        types = [t.type for t in tokens]
        assert TokenType.FENCED_CODE_START in types
        assert TokenType.FENCED_CODE_CONTENT in types
        assert TokenType.FENCED_CODE_END in types

    def test_fenced_code_with_language(self, tokenize):
        """Fenced code with language info."""
        tokens = tokenize("```python\ncode\n```")
        start_token = next(t for t in tokens if t.type == TokenType.FENCED_CODE_START)
        assert "python" in start_token.value

    def test_fenced_code_with_tilde(self, tokenize):
        """Tilde fenced code block."""
        tokens = tokenize("~~~\ncode\n~~~")
        start_token = next(t for t in tokens if t.type == TokenType.FENCED_CODE_START)
        assert start_token.value.startswith("~")

    def test_fenced_code_preserves_content(self, tokenize):
        """Fenced code preserves exact content."""
        tokens = tokenize("```\nline1\nline2\n```")
        content_tokens = [t for t in tokens if t.type == TokenType.FENCED_CODE_CONTENT]
        content = "".join(t.value for t in content_tokens)
        assert "line1" in content
        assert "line2" in content

    def test_nested_backticks_in_code(self, tokenize):
        """Backticks inside code don't close the fence."""
        tokens = tokenize("````\n```\ninner\n```\n````")
        # Should have exactly one start and one end
        starts = [t for t in tokens if t.type == TokenType.FENCED_CODE_START]
        ends = [t for t in tokens if t.type == TokenType.FENCED_CODE_END]
        assert len(starts) == 1
        assert len(ends) == 1


class TestBlockQuotes:
    """Block quote tokenization."""

    def test_basic_block_quote(self, tokenize):
        """Basic block quote marker."""
        tokens = tokenize("> quote")
        assert tokens[0].type == TokenType.BLOCK_QUOTE_MARKER
        assert tokens[0].value == ">"

    def test_block_quote_with_content(self, tokenize):
        """Block quote followed by content."""
        tokens = tokenize("> quoted text")
        types = [t.type for t in tokens]
        assert TokenType.BLOCK_QUOTE_MARKER in types
        # Content follows the marker
        assert TokenType.PARAGRAPH_LINE in types


class TestLists:
    """List tokenization."""

    @pytest.mark.parametrize("marker", ["-", "*", "+"])
    def test_unordered_list_markers(self, tokenize, marker):
        """All unordered list markers work."""
        tokens = tokenize(f"{marker} item")
        assert tokens[0].type == TokenType.LIST_ITEM_MARKER
        assert tokens[0].value == marker

    def test_ordered_list(self, tokenize):
        """Ordered list marker."""
        tokens = tokenize("1. item")
        assert tokens[0].type == TokenType.LIST_ITEM_MARKER
        assert tokens[0].value == "1."

    def test_ordered_list_different_numbers(self, tokenize):
        """Ordered list with different starting numbers."""
        tokens = tokenize("42. item")
        assert tokens[0].type == TokenType.LIST_ITEM_MARKER
        assert "42" in tokens[0].value


class TestThematicBreaks:
    """Thematic break tokenization."""

    @pytest.mark.parametrize(
        "source",
        [
            "---",
            "***",
            "___",
            "- - -",
            "* * *",
            "_ _ _",
            "----------",
        ],
    )
    def test_thematic_break_variants(self, tokenize, source):
        """Various thematic break formats."""
        tokens = tokenize(source)
        assert tokens[0].type == TokenType.THEMATIC_BREAK


class TestIndentedCode:
    """Indented code block tokenization."""

    def test_basic_indented_code(self, tokenize):
        """4-space indented code."""
        tokens = tokenize("    code")
        assert tokens[0].type == TokenType.INDENTED_CODE

    def test_tab_indented_code(self, tokenize):
        """Tab-indented code."""
        tokens = tokenize("\tcode")
        assert tokens[0].type == TokenType.INDENTED_CODE


class TestParagraphs:
    """Paragraph tokenization."""

    def test_simple_paragraph(self, tokenize):
        """Simple paragraph text."""
        tokens = tokenize("Hello world")
        assert tokens[0].type == TokenType.PARAGRAPH_LINE
        assert tokens[0].value == "Hello world"

    def test_multiline_paragraph(self, tokenize):
        """Multi-line paragraph."""
        tokens = tokenize("Line 1\nLine 2")
        para_tokens = [t for t in tokens if t.type == TokenType.PARAGRAPH_LINE]
        assert len(para_tokens) == 2


class TestLocationTracking:
    """Source location tracking."""

    def test_line_numbers(self, tokenize):
        """Tokens track line numbers."""
        tokens = tokenize("Line 1\n\nLine 3")
        # First token on line 1
        assert tokens[0].location.lineno == 1
        # Blank line on line 2
        blank = next(t for t in tokens if t.type == TokenType.BLANK_LINE)
        assert blank.location.lineno == 2

    def test_column_numbers(self, tokenize):
        """Tokens track column numbers."""
        tokens = tokenize("# Heading")
        assert tokens[0].location.col_offset == 1

    def test_source_file_tracking(self):
        """Source file path is tracked."""
        lexer = Lexer("# Test", source_file="test.md")
        tokens = list(lexer.tokenize())
        assert tokens[0].location.source_file == "test.md"
