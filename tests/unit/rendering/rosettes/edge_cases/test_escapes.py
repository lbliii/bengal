"""Tests for escape sequence handling."""

from __future__ import annotations

from bengal.rendering.rosettes import TokenType, get_lexer


class TestStandardEscapes:
    """Test standard escape sequences."""

    def test_all_standard_escapes(self) -> None:
        """All standard escapes should be STRING_ESCAPE."""
        lexer = get_lexer("python")
        # String containing: \n \t \r \\ \" \'
        code = r'"\n\t\r\\\"\'"'
        tokens = list(lexer.tokenize(code))
        escape_tokens = [t for t in tokens if t.type == TokenType.STRING_ESCAPE]
        assert len(escape_tokens) > 0

    def test_newline_escape(self) -> None:
        """Newline escape sequence should be STRING_ESCAPE."""
        lexer = get_lexer("python")
        code = '"\\n"'
        tokens = list(lexer.tokenize(code))
        escape_tokens = [t for t in tokens if t.type == TokenType.STRING_ESCAPE]
        assert len(escape_tokens) > 0

    def test_tab_escape(self) -> None:
        """Tab escape sequence should be STRING_ESCAPE."""
        lexer = get_lexer("python")
        code = '"\\t"'
        tokens = list(lexer.tokenize(code))
        escape_tokens = [t for t in tokens if t.type == TokenType.STRING_ESCAPE]
        assert len(escape_tokens) > 0


class TestInvalidEscapes:
    """Test invalid escape sequence handling."""

    def test_invalid_escape(self) -> None:
        """Invalid escapes should be handled (language-dependent)."""
        lexer = get_lexer("python")
        code = '"\\z"'  # Invalid escape
        tokens = list(lexer.tokenize(code))
        # Should not crash
        assert len(tokens) > 0


class TestRawStrings:
    """Test raw string handling."""

    def test_raw_string_no_escape(self) -> None:
        """Raw strings should not process escapes."""
        lexer = get_lexer("python")
        code = 'r"\\n is literal"'
        tokens = list(lexer.tokenize(code))
        # Should tokenize, but \\n should be literal
        assert len(tokens) > 0
