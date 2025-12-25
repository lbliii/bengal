"""Tests for Rosettes core types."""

from rosettes import Token, TokenType


class TestTokenType:
    """Tests for TokenType enum."""

    def test_token_type_is_strenum(self) -> None:
        """TokenType values are their CSS class names."""
        assert TokenType.KEYWORD == "k"
        assert TokenType.STRING == "s"
        assert TokenType.COMMENT == "c"
        assert TokenType.NUMBER == "m"

    def test_pygments_compatibility(self) -> None:
        """Verify CSS class names match Pygments."""
        # These are the most common Pygments token classes
        expected = {
            TokenType.KEYWORD: "k",
            TokenType.KEYWORD_CONSTANT: "kc",
            TokenType.KEYWORD_DECLARATION: "kd",
            TokenType.NAME: "n",
            TokenType.NAME_FUNCTION: "nf",
            TokenType.NAME_CLASS: "nc",
            TokenType.NAME_BUILTIN: "nb",
            TokenType.STRING: "s",
            TokenType.STRING_DOC: "sd",
            TokenType.NUMBER: "m",
            TokenType.NUMBER_INTEGER: "mi",
            TokenType.NUMBER_FLOAT: "mf",
            TokenType.COMMENT: "c",
            TokenType.COMMENT_SINGLE: "c1",
            TokenType.OPERATOR: "o",
            TokenType.PUNCTUATION: "p",
        }
        for token_type, expected_class in expected.items():
            assert token_type.value == expected_class, f"{token_type} != {expected_class}"


class TestToken:
    """Tests for Token namedtuple."""

    def test_token_immutable(self) -> None:
        """Tokens are immutable namedtuples."""
        token = Token(type=TokenType.KEYWORD, value="def", line=1, column=1)
        assert token.type == TokenType.KEYWORD
        assert token.value == "def"
        assert token.line == 1
        assert token.column == 1

    def test_token_defaults(self) -> None:
        """Token has sensible defaults for line and column."""
        token = Token(type=TokenType.NAME, value="foo")
        assert token.line == 1
        assert token.column == 1

    def test_token_hashable(self) -> None:
        """Tokens can be used in sets/dicts."""
        t1 = Token(type=TokenType.KEYWORD, value="def", line=1, column=1)
        t2 = Token(type=TokenType.KEYWORD, value="def", line=1, column=1)
        t3 = Token(type=TokenType.KEYWORD, value="class", line=1, column=1)

        assert t1 == t2
        assert t1 != t3
        assert len({t1, t2, t3}) == 2
