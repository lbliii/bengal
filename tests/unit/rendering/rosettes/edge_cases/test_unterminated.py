"""Tests for unterminated constructs (strings, comments, etc.)."""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import TokenType, get_lexer


class TestUnterminatedStrings:
    """Test handling of unterminated strings."""

    @pytest.mark.parametrize("language", ["python", "javascript", "rust", "go"])
    def test_unterminated_string_at_eof(self, language: str) -> None:
        """Unterminated string at EOF should not hang or crash."""
        lexer = get_lexer(language)
        code = '"hello'

        # Should not hang or raise exception
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0
        # Should emit STRING or ERROR token
        types = [t.type for t in tokens]
        assert (
            TokenType.STRING in types
            or TokenType.STRING_DOUBLE in types
            or TokenType.STRING_SINGLE in types
            or TokenType.ERROR in types
        )

    def test_unterminated_single_quote(self) -> None:
        """Unterminated single quote should be handled."""
        lexer = get_lexer("python")
        code = "'hello"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0

    def test_unterminated_triple_quote(self) -> None:
        """Unterminated triple quote should be handled."""
        lexer = get_lexer("python")
        code = '"""hello'
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0


class TestUnterminatedComments:
    """Test handling of unterminated comments."""

    def test_unterminated_block_comment(self) -> None:
        """Unterminated block comment should not hang."""
        lexer = get_lexer("javascript")
        code = "/* hello"

        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0
        # Should emit COMMENT_MULTILINE or handle gracefully
        types = [t.type for t in tokens]
        assert TokenType.COMMENT_MULTILINE in types or TokenType.ERROR in types

    def test_unterminated_nested_comment(self) -> None:
        """Unterminated nested comment should not hang."""
        lexer = get_lexer("rust")
        code = "/* outer /* inner"

        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0


class TestUnterminatedConstructs:
    """Test various unterminated language constructs."""

    def test_unterminated_template_literal(self) -> None:
        """Unterminated template literal should be handled."""
        lexer = get_lexer("javascript")
        code = "`hello ${"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0

    def test_unterminated_f_string(self) -> None:
        """Unterminated f-string should be handled."""
        lexer = get_lexer("python")
        code = 'f"hello {'
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0
