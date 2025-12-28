"""Tests for Unicode handling."""

from __future__ import annotations

from bengal.rendering.rosettes import TokenType, get_lexer


class TestUnicodeIdentifiers:
    """Test Unicode in identifiers."""

    def test_unicode_identifier_python(self) -> None:
        """Unicode identifiers should be tokenized."""
        lexer = get_lexer("python")
        code = "привет = 42"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0
        # Should have identifier token
        types = [t.type for t in tokens]
        assert TokenType.NAME in types or TokenType.NAME_VARIABLE in types

    def test_cjk_identifier(self) -> None:
        """CJK identifiers should be tokenized."""
        lexer = get_lexer("python")
        code = "变量 = '值'"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0


class TestUnicodeInStrings:
    """Test Unicode in string literals."""

    def test_emoji_in_string(self) -> None:
        """Emoji in strings should be preserved."""
        lexer = get_lexer("python")
        code = '"emoji: 🎉"'
        tokens = list(lexer.tokenize(code))
        # Should tokenize correctly
        assert len(tokens) > 0
        # Value should contain emoji
        all_values = "".join(t.value for t in tokens)
        assert "🎉" in all_values

    def test_cjk_in_string(self) -> None:
        """CJK characters in strings should be preserved."""
        lexer = get_lexer("python")
        code = '"cjk: 日本語"'
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0
        all_values = "".join(t.value for t in tokens)
        assert "日本語" in all_values

    def test_unicode_escape_sequences(self) -> None:
        """Unicode escape sequences should be included in STRING token."""
        lexer = get_lexer("python")
        code = '"\\u0041"'  # Unicode escape
        tokens = list(lexer.tokenize(code))
        # Escape sequences are part of the string token, not separate tokens
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0
        # Verify escape sequence is in the string value
        assert "\\u0041" in string_tokens[0].value


class TestUnicodeBoundaries:
    """Test Unicode boundary conditions."""

    def test_unicode_whitespace(self) -> None:
        """Unicode whitespace should be handled."""
        lexer = get_lexer("python")
        code = "x\u2000y"  # En quad space
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0

    def test_unicode_operators(self) -> None:
        """Unicode operators should be handled."""
        lexer = get_lexer("python")
        code = "x ≠ y"  # Not equal
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0
