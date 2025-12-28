"""Comprehensive tests for JavaScript lexer.

Tests token accuracy for JavaScript language constructs:
- Keywords (const, let, function, etc.)
- Strings (single, double, template literals)
- Numbers (int, float, hex, binary)
- Comments (line, block)
- Operators
- Arrow functions
- Destructuring
"""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import TokenType
from tests.unit.rendering.rosettes.conftest import assert_tokens_match, load_fixture


class TestJavaScriptKeywords:
    """Test JavaScript keyword tokenization."""

    def test_const_keyword(self, javascript_lexer) -> None:
        """'const' should be KEYWORD_DECLARATION."""
        tokens = list(javascript_lexer.tokenize("const"))
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION
        assert tokens[0].value == "const"

    def test_let_keyword(self, javascript_lexer) -> None:
        """'let' should be KEYWORD_DECLARATION."""
        tokens = list(javascript_lexer.tokenize("let"))
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION

    def test_function_keyword(self, javascript_lexer) -> None:
        """'function' should be KEYWORD_DECLARATION."""
        tokens = list(javascript_lexer.tokenize("function"))
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION

    def test_async_await(self, javascript_lexer) -> None:
        """'async' and 'await' should be KEYWORD."""
        tokens = list(javascript_lexer.tokenize("async"))
        assert tokens[0].type == TokenType.KEYWORD

        tokens = list(javascript_lexer.tokenize("await"))
        assert tokens[0].type == TokenType.KEYWORD


class TestJavaScriptStrings:
    """Test JavaScript string tokenization."""

    def test_single_quoted_string(self, javascript_lexer) -> None:
        """Single-quoted strings should be STRING."""
        code = "'hello'"
        tokens = list(javascript_lexer.tokenize(code))
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0

    def test_double_quoted_string(self, javascript_lexer) -> None:
        """Double-quoted strings should be STRING."""
        code = '"hello"'
        tokens = list(javascript_lexer.tokenize(code))
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0

    def test_template_literal(self, javascript_lexer) -> None:
        """Template literals should be tokenized."""
        code = "`Hello ${name}`"
        tokens = list(javascript_lexer.tokenize(code))
        # Should have string and interpolation
        assert len(tokens) > 0

    def test_escape_sequences(self, javascript_lexer) -> None:
        """Escape sequences should be included in STRING token."""
        code = '"\\n\\t\\r"'
        tokens = list(javascript_lexer.tokenize(code))
        # Escape sequences are part of the string token, not separate tokens
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0
        # Verify escape sequences are in the string value
        assert "\\n" in string_tokens[0].value or "\n" in string_tokens[0].value


class TestJavaScriptNumbers:
    """Test JavaScript number tokenization."""

    def test_integer(self, javascript_lexer) -> None:
        """Integers should be NUMBER_INTEGER."""
        tokens = list(javascript_lexer.tokenize("42"))
        assert tokens[0].type == TokenType.NUMBER_INTEGER

    def test_float(self, javascript_lexer) -> None:
        """Floats should be NUMBER_FLOAT."""
        tokens = list(javascript_lexer.tokenize("3.14"))
        assert tokens[0].type == TokenType.NUMBER_FLOAT

    def test_hex_number(self, javascript_lexer) -> None:
        """Hex numbers should be NUMBER_HEX."""
        tokens = list(javascript_lexer.tokenize("0xFF"))
        assert tokens[0].type == TokenType.NUMBER_HEX

    def test_binary_number(self, javascript_lexer) -> None:
        """Binary numbers should be NUMBER_BIN."""
        tokens = list(javascript_lexer.tokenize("0b1010"))
        assert tokens[0].type == TokenType.NUMBER_BIN


class TestJavaScriptComments:
    """Test JavaScript comment tokenization."""

    def test_line_comment(self, javascript_lexer) -> None:
        """Line comments should be COMMENT_SINGLE."""
        code = "// This is a comment"
        tokens = list(javascript_lexer.tokenize(code))
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT_SINGLE]
        assert len(comment_tokens) > 0

    def test_block_comment(self, javascript_lexer) -> None:
        """Block comments should be COMMENT_MULTILINE."""
        code = "/* This is a comment */"
        tokens = list(javascript_lexer.tokenize(code))
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT_MULTILINE]
        assert len(comment_tokens) > 0


class TestJavaScriptOperators:
    """Test JavaScript operator tokenization."""

    def test_arithmetic_operators(self, javascript_lexer) -> None:
        """Arithmetic operators should be OPERATOR."""
        operators = ["+", "-", "*", "/", "%", "**"]
        for op in operators:
            tokens = list(javascript_lexer.tokenize(op))
            op_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
            assert len(op_tokens) > 0

    def test_comparison_operators(self, javascript_lexer) -> None:
        """Comparison operators should be OPERATOR."""
        operators = ["==", "===", "!=", "!==", "<", ">", "<=", ">="]
        for op in operators:
            tokens = list(javascript_lexer.tokenize(op))
            op_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
            assert len(op_tokens) > 0


class TestJavaScriptComplex:
    """Test complex JavaScript constructs."""

    def test_arrow_function(self, javascript_lexer) -> None:
        """Arrow functions should tokenize correctly."""
        code = "const foo = (x) => x + 1"
        tokens = list(javascript_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_DECLARATION in types  # const
        assert TokenType.OPERATOR in types  # =>, +

    def test_destructuring(self, javascript_lexer) -> None:
        """Destructuring should tokenize correctly."""
        code = "const {x, y} = obj"
        tokens = list(javascript_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_DECLARATION in types  # const

    def test_function_declaration(self, javascript_lexer) -> None:
        """Function declarations should tokenize correctly."""
        code = "function hello(name) { return `Hello, ${name}`; }"
        tokens = list(javascript_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD in types  # function, return


class TestJavaScriptFixtures:
    """Test JavaScript lexer using fixture files."""

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "keywords",
            "strings",
            "numbers",
            "comments",
            "operators",
            "arrow_functions",
        ],
    )
    def test_fixture(self, javascript_lexer, fixture_name: str) -> None:
        """Test lexer against fixture files if they exist."""
        try:
            input_code, expected_tokens = load_fixture("javascript", fixture_name)
            actual_tokens = list(javascript_lexer.tokenize(input_code))
            if expected_tokens:
                assert_tokens_match(actual_tokens, expected_tokens, fuzzy_boundaries=True)
        except FileNotFoundError:
            pytest.skip(f"Fixture {fixture_name} not found")
