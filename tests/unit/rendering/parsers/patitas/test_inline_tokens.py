"""Unit tests for typed inline tokens.

Tests the NamedTuple-based inline token types that provide
type safety and memory efficiency.
"""

from __future__ import annotations

import pytest

from patitas.parsing.inline.tokens import (
    CodeSpanToken,
    DelimiterToken,
    HardBreakToken,
    InlineToken,
    NodeToken,
    SoftBreakToken,
    TextToken,
)


class TestDelimiterToken:
    """Tests for DelimiterToken."""

    def test_create_asterisk_delimiter(self):
        """Test creating an asterisk delimiter token."""
        token = DelimiterToken(char="*", count=2, can_open=True, can_close=False)
        assert token.char == "*"
        assert token.count == 2
        assert token.can_open is True
        assert token.can_close is False

    def test_create_underscore_delimiter(self):
        """Test creating an underscore delimiter token."""
        token = DelimiterToken(char="_", count=1, can_open=True, can_close=True)
        assert token.char == "_"
        assert token.count == 1
        assert token.can_open is True
        assert token.can_close is True

    def test_create_tilde_delimiter(self):
        """Test creating a tilde delimiter token (strikethrough)."""
        token = DelimiterToken(char="~", count=2, can_open=True, can_close=True)
        assert token.char == "~"
        assert token.count == 2

    def test_type_property(self):
        """Test that type property returns 'delimiter'."""
        token = DelimiterToken(char="*", count=1, can_open=True, can_close=False)
        assert token.type == "delimiter"

    def test_original_count_property(self):
        """Test original_count property returns count."""
        token = DelimiterToken(char="*", count=3, can_open=True, can_close=False)
        assert token.original_count == 3

    def test_immutability(self):
        """Test that DelimiterToken is immutable."""
        token = DelimiterToken(char="*", count=2, can_open=True, can_close=False)
        with pytest.raises(AttributeError):
            token.count = 5  # type: ignore[misc]

    def test_tuple_unpacking(self):
        """Test that NamedTuple supports unpacking."""
        token = DelimiterToken(char="*", count=2, can_open=True, can_close=False)
        char, count, can_open, can_close = token
        assert char == "*"
        assert count == 2
        assert can_open is True
        assert can_close is False


class TestTextToken:
    """Tests for TextToken."""

    def test_create_text_token(self):
        """Test creating a text token."""
        token = TextToken(content="Hello, world!")
        assert token.content == "Hello, world!"

    def test_type_property(self):
        """Test that type property returns 'text'."""
        token = TextToken(content="test")
        assert token.type == "text"

    def test_empty_content(self):
        """Test text token with empty content."""
        token = TextToken(content="")
        assert token.content == ""


class TestCodeSpanToken:
    """Tests for CodeSpanToken."""

    def test_create_code_span_token(self):
        """Test creating a code span token."""
        token = CodeSpanToken(code="print('hello')")
        assert token.code == "print('hello')"

    def test_type_property(self):
        """Test that type property returns 'code_span'."""
        token = CodeSpanToken(code="x = 1")
        assert token.type == "code_span"


class TestNodeToken:
    """Tests for NodeToken."""

    def test_create_node_token(self):
        """Test creating a node token with a mock node."""
        mock_node = {"type": "link", "url": "https://example.com"}
        token = NodeToken(node=mock_node)
        assert token.node == mock_node

    def test_type_property(self):
        """Test that type property returns 'node'."""
        token = NodeToken(node=None)
        assert token.type == "node"


class TestHardBreakToken:
    """Tests for HardBreakToken."""

    def test_create_hard_break_token(self):
        """Test creating a hard break token."""
        token = HardBreakToken()
        assert isinstance(token, HardBreakToken)

    def test_type_property(self):
        """Test that type property returns 'hard_break'."""
        token = HardBreakToken()
        assert token.type == "hard_break"


class TestSoftBreakToken:
    """Tests for SoftBreakToken."""

    def test_create_soft_break_token(self):
        """Test creating a soft break token."""
        token = SoftBreakToken()
        assert isinstance(token, SoftBreakToken)

    def test_type_property(self):
        """Test that type property returns 'soft_break'."""
        token = SoftBreakToken()
        assert token.type == "soft_break"


class TestPatternMatching:
    """Tests for pattern matching with typed tokens."""

    def test_match_delimiter_token(self):
        """Test pattern matching on DelimiterToken."""
        token: InlineToken = DelimiterToken(char="*", count=2, can_open=True, can_close=False)

        match token:
            case DelimiterToken(char=char, count=count):
                assert char == "*"
                assert count == 2
            case _:
                pytest.fail("Should match DelimiterToken")

    def test_match_text_token(self):
        """Test pattern matching on TextToken."""
        token: InlineToken = TextToken(content="hello")

        match token:
            case TextToken(content=content):
                assert content == "hello"
            case _:
                pytest.fail("Should match TextToken")

    def test_match_code_span_token(self):
        """Test pattern matching on CodeSpanToken."""
        token: InlineToken = CodeSpanToken(code="x = 1")

        match token:
            case CodeSpanToken(code=code):
                assert code == "x = 1"
            case _:
                pytest.fail("Should match CodeSpanToken")

    def test_match_break_tokens(self):
        """Test pattern matching on break tokens."""
        hard_break: InlineToken = HardBreakToken()
        soft_break: InlineToken = SoftBreakToken()

        match hard_break:
            case HardBreakToken():
                pass  # Expected
            case _:
                pytest.fail("Should match HardBreakToken")

        match soft_break:
            case SoftBreakToken():
                pass  # Expected
            case _:
                pytest.fail("Should match SoftBreakToken")

    def test_exhaustive_matching(self):
        """Test exhaustive pattern matching over all token types."""
        tokens: list[InlineToken] = [
            DelimiterToken(char="*", count=1, can_open=True, can_close=False),
            TextToken(content="text"),
            CodeSpanToken(code="code"),
            NodeToken(node=None),
            HardBreakToken(),
            SoftBreakToken(),
        ]

        for token in tokens:
            match token:
                case DelimiterToken():
                    assert token.type == "delimiter"
                case TextToken():
                    assert token.type == "text"
                case CodeSpanToken():
                    assert token.type == "code_span"
                case NodeToken():
                    assert token.type == "node"
                case HardBreakToken():
                    assert token.type == "hard_break"
                case SoftBreakToken():
                    assert token.type == "soft_break"
                case _:
                    pytest.fail(f"Unhandled token type: {type(token)}")
