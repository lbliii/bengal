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
        """Unicode escape sequences should be STRING_ESCAPE."""
        lexer = get_lexer("python")
        code = '"\\u0041"'  # Should be STRING_ESCAPE
        tokens = list(lexer.tokenize(code))
        escape_tokens = [t for t in tokens if t.type == TokenType.STRING_ESCAPE]
        assert len(escape_tokens) > 0


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
