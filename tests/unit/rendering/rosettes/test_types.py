"""Tests for Token and TokenType."""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import Token, TokenType


class TestTokenType:
    """Test TokenType enum."""

    def test_token_type_values(self) -> None:
        """TokenType values should be Pygments-compatible."""
        assert TokenType.KEYWORD.value == "k"
        assert TokenType.STRING.value == "s"
        assert TokenType.NUMBER.value == "m"
        assert TokenType.COMMENT.value == "c"

    def test_token_type_keywords(self) -> None:
        """All keyword types should exist."""
        assert TokenType.KEYWORD
        assert TokenType.KEYWORD_CONSTANT
        assert TokenType.KEYWORD_DECLARATION
        assert TokenType.KEYWORD_NAMESPACE
        assert TokenType.KEYWORD_TYPE

    def test_token_type_strings(self) -> None:
        """All string types should exist."""
        assert TokenType.STRING
        assert TokenType.STRING_SINGLE
        assert TokenType.STRING_DOUBLE
        assert TokenType.STRING_DOC
        assert TokenType.STRING_ESCAPE

    def test_token_type_numbers(self) -> None:
        """All number types should exist."""
        assert TokenType.NUMBER
        assert TokenType.NUMBER_INTEGER
        assert TokenType.NUMBER_FLOAT
        assert TokenType.NUMBER_HEX
        assert TokenType.NUMBER_BIN
        assert TokenType.NUMBER_OCT


class TestToken:
    """Test Token named tuple."""

    def test_token_creation(self) -> None:
        """Token should be created with required fields."""
        token = Token(TokenType.KEYWORD, "def", line=1, column=1)
        assert token.type == TokenType.KEYWORD
        assert token.value == "def"
        assert token.line == 1
        assert token.column == 1

    def test_token_defaults(self) -> None:
        """Token should have default line/column values."""
        token = Token(TokenType.KEYWORD, "def")
        assert token.line == 1
        assert token.column == 1

    def test_token_immutable(self) -> None:
        """Token should be immutable (NamedTuple)."""
        token = Token(TokenType.KEYWORD, "def")
        with pytest.raises(AttributeError):
            token.value = "class"  # type: ignore[misc]

    def test_token_equality(self) -> None:
        """Tokens with same values should be equal."""
        token1 = Token(TokenType.KEYWORD, "def", line=1, column=1)
        token2 = Token(TokenType.KEYWORD, "def", line=1, column=1)
        assert token1 == token2

    def test_token_representation(self) -> None:
        """Token should have useful string representation."""
        token = Token(TokenType.KEYWORD, "def", line=1, column=1)
        repr_str = repr(token)
        assert "Token" in repr_str
        assert "def" in repr_str
