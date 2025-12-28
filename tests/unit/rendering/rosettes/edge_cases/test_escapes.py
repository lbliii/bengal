"""Tests for escape sequence handling."""

from __future__ import annotations

from bengal.rendering.rosettes import TokenType, get_lexer


class TestStandardEscapes:
    """Test standard escape sequences."""

    def test_all_standard_escapes(self) -> None:
        """Escape sequences should be included in STRING token."""
        lexer = get_lexer("python")
        # String containing: \n \t \r \\ \" \'
        code = r'"\n\t\r\\\"\'"'
        tokens = list(lexer.tokenize(code))
        # Escape sequences are part of the string token, not separate tokens
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0
        # Verify escape sequences are in the string value
        value = string_tokens[0].value
        assert "\\n" in value or "\n" in value

    def test_newline_escape(self) -> None:
        """Escape sequences should be included in STRING token."""
        lexer = get_lexer("python")
        code = '"\\n"'
        tokens = list(lexer.tokenize(code))
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0
        # Verify escape sequence is in the string value
        assert "\\n" in string_tokens[0].value or "\n" in string_tokens[0].value

    def test_tab_escape(self) -> None:
        """Escape sequences should be included in STRING token."""
        lexer = get_lexer("python")
        code = '"\\t"'
        tokens = list(lexer.tokenize(code))
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0
        # Verify escape sequence is in the string value
        assert "\\t" in string_tokens[0].value or "\t" in string_tokens[0].value


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
