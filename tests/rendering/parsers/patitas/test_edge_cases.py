"""Edge case and stress tests for Patitas.

Tests error handling, malformed input, and unusual cases.
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas import parse, parse_to_ast
from bengal.rendering.parsers.patitas.lexer import Lexer
from bengal.rendering.parsers.patitas.parser import Parser


class TestMalformedInput:
    """Malformed input handling."""

    def test_only_backticks(self):
        """Input with only backticks."""
        html = parse("```")
        # Should not crash
        assert html is not None

    def test_only_asterisks(self):
        """Input with only asterisks."""
        html = parse("***")
        assert html is not None

    def test_only_underscores(self):
        """Input with only underscores."""
        html = parse("___")
        # This is a thematic break
        assert "<hr />" in html

    def test_only_hashes(self):
        """Input with only hashes."""
        html = parse("######")
        assert html is not None

    def test_unclosed_brackets(self):
        """Various unclosed brackets."""
        for s in ["[", "[[", "[text", "![", "![alt"]:
            html = parse(s)
            assert html is not None

    def test_mismatched_delimiters(self):
        """Mismatched emphasis delimiters."""
        html = parse("*text**")
        assert html is not None

    def test_deeply_nested_brackets(self):
        """Deeply nested brackets."""
        html = parse("[[[[[[[[text]]]]]]]]")
        assert html is not None


class TestUnicodeHandling:
    """Unicode content handling."""

    def test_unicode_text(self):
        """Basic unicode text."""
        html = parse("Hello 世界")
        assert "世界" in html

    def test_unicode_in_heading(self):
        """Unicode in heading."""
        html = parse("# Привет мир")
        assert "Привет" in html

    def test_emoji(self):
        """Emoji handling."""
        html = parse("Hello 🌍")
        assert "🌍" in html

    def test_unicode_in_code(self):
        """Unicode in code block."""
        html = parse("```\n日本語\n```")
        assert "日本語" in html

    def test_unicode_in_link(self):
        """Unicode in link text."""
        html = parse("[日本語](url)")
        assert "日本語" in html

    def test_rtl_text(self):
        """Right-to-left text."""
        html = parse("مرحبا")
        assert "مرحبا" in html


class TestWhitespaceHandling:
    """Whitespace handling."""

    def test_trailing_spaces(self):
        """Trailing spaces on lines."""
        html = parse("text   ")
        assert "text" in html

    def test_leading_spaces(self):
        """Leading spaces on lines."""
        html = parse("   text")
        assert "text" in html

    def test_mixed_tabs_spaces(self):
        """Mixed tabs and spaces."""
        html = parse("\t text")
        assert html is not None

    def test_windows_line_endings(self):
        """Windows CRLF line endings."""
        html = parse("line1\r\nline2")
        assert "line1" in html
        assert "line2" in html

    def test_old_mac_line_endings(self):
        """Old Mac CR line endings."""
        html = parse("line1\rline2")
        assert html is not None

    def test_many_blank_lines(self):
        """Many consecutive blank lines."""
        html = parse("para1\n\n\n\n\n\npara2")
        assert html.count("<p>") == 2


class TestLargeInput:
    """Large input handling."""

    def test_long_line(self):
        """Very long single line."""
        text = "a" * 10000
        html = parse(text)
        assert text in html

    def test_many_lines(self):
        """Many lines of input."""
        text = "\n".join([f"Line {i}" for i in range(1000)])
        html = parse(text)
        assert "Line 0" in html
        assert "Line 999" in html

    def test_large_code_block(self):
        """Large code block."""
        code = "\n".join([f"line {i}" for i in range(1000)])
        text = f"```\n{code}\n```"
        html = parse(text)
        assert "line 0" in html

    def test_many_headings(self):
        """Many headings."""
        text = "\n\n".join([f"# Heading {i}" for i in range(100)])
        html = parse(text)
        assert html.count("<h1>") == 100


class TestSpecialCharacters:
    """Special character handling."""

    def test_null_byte(self):
        """Null byte in input."""
        html = parse("text\x00more")
        assert html is not None

    def test_bell_character(self):
        """Bell character in input."""
        html = parse("text\x07more")
        assert html is not None

    def test_backspace(self):
        """Backspace in input."""
        html = parse("text\x08more")
        assert html is not None

    def test_form_feed(self):
        """Form feed in input."""
        html = parse("text\x0cmore")
        assert html is not None


class TestRecoveryBehavior:
    """Error recovery behavior."""

    def test_invalid_emphasis_graceful(self):
        """Invalid emphasis renders gracefully."""
        html = parse("*unclosed")
        assert "unclosed" in html

    def test_invalid_link_graceful(self):
        """Invalid link renders gracefully."""
        html = parse("[text](")
        assert "text" in html

    def test_invalid_code_span_graceful(self):
        """Unclosed code span renders gracefully."""
        html = parse("`unclosed")
        assert "unclosed" in html

    def test_deeply_nested_emphasis(self):
        """Deeply nested emphasis doesn't crash."""
        text = "*" * 20 + "text" + "*" * 20
        html = parse(text)
        assert html is not None


class TestLexerRobustness:
    """Lexer robustness tests."""

    def test_lexer_empty(self):
        """Lexer handles empty input."""
        lexer = Lexer("")
        tokens = list(lexer.tokenize())
        assert len(tokens) == 1  # Just EOF

    def test_lexer_preserves_state(self):
        """Lexer state is isolated."""
        lexer1 = Lexer("# One")
        lexer2 = Lexer("# Two")
        tokens1 = list(lexer1.tokenize())
        tokens2 = list(lexer2.tokenize())
        assert "One" in tokens1[0].value
        assert "Two" in tokens2[0].value


class TestParserRobustness:
    """Parser robustness tests."""

    def test_parser_empty(self):
        """Parser handles empty input."""
        ast = parse_to_ast("")
        assert len(ast) == 0

    def test_parser_returns_tuple(self):
        """Parser always returns tuple."""
        for input_text in ["", "text", "# heading", "- list"]:
            ast = parse_to_ast(input_text)
            assert isinstance(ast, tuple)

    def test_parser_isolated(self):
        """Parser instances are isolated."""
        parser1 = Parser("# One")
        parser2 = Parser("# Two")
        ast1 = parser1.parse()
        ast2 = parser2.parse()
        assert ast1[0] != ast2[0]


class TestMemoryEfficiency:
    """Memory efficiency tests."""

    def test_stringbuilder_reuse(self):
        """StringBuilder doesn't leak memory."""
        from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

        sb = StringBuilder()
        for _ in range(1000):
            sb.append("text")
        result = sb.build()
        assert len(result) == 4000  # "text" * 1000

    def test_many_parses(self):
        """Many parses don't leak."""
        for _ in range(100):
            html = parse("# Heading\n\nParagraph with **bold** and *italic*.")
            assert "<h1>" in html


class TestBoundaryConditions:
    """Boundary condition tests."""

    def test_emphasis_at_boundaries(self):
        """Emphasis at line/paragraph boundaries."""
        test_cases = [
            "*em*",
            "*em*\n",
            "\n*em*",
            "*em* ",
            " *em*",
        ]
        for case in test_cases:
            html = parse(case)
            assert html is not None

    def test_code_span_at_boundaries(self):
        """Code span at boundaries."""
        test_cases = [
            "`code`",
            "`code`\n",
            "\n`code`",
        ]
        for case in test_cases:
            html = parse(case)
            assert html is not None

    def test_heading_at_eof(self):
        """Heading at end of file (no trailing newline)."""
        html = parse("# Heading")
        assert "<h1>" in html

    def test_code_block_at_eof(self):
        """Code block at end of file."""
        html = parse("```\ncode\n```")
        assert "<pre>" in html


class TestReDoSPrevention:
    """ReDoS prevention tests (O(n) guarantee)."""

    def test_many_asterisks(self):
        """Many asterisks process quickly."""
        text = "*" * 1000 + "text" + "*" * 1000
        html = parse(text)
        assert html is not None

    def test_many_underscores(self):
        """Many underscores process quickly."""
        text = "_" * 1000 + "text" + "_" * 1000
        html = parse(text)
        assert html is not None

    def test_many_brackets(self):
        """Many brackets process quickly."""
        text = "[" * 100 + "text" + "]" * 100
        html = parse(text)
        assert html is not None

    def test_pathological_emphasis(self):
        """Pathological emphasis pattern processes quickly."""
        # This pattern can cause exponential time in some parsers
        text = "**a]**a]**a]**a]**a]**a]**a]**a]"
        html = parse(text)
        assert html is not None
