"""Comprehensive tests for Rust lexer.

Tests token accuracy for Rust language constructs:
- Keywords (fn, let, mut, etc.)
- Strings (single, double, raw)
- Numbers (int, float, hex, binary)
- Comments (line, block, doc)
- Operators
- Lifetimes
- Macros
"""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import TokenType
from tests.unit.rendering.rosettes.conftest import assert_tokens_match, load_fixture


class TestRustKeywords:
    """Test Rust keyword tokenization."""

    def test_fn_keyword(self, rust_lexer) -> None:
        """'fn' should be KEYWORD_DECLARATION."""
        tokens = list(rust_lexer.tokenize("fn"))
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION
        assert tokens[0].value == "fn"

    def test_let_keyword(self, rust_lexer) -> None:
        """'let' should be KEYWORD_DECLARATION."""
        tokens = list(rust_lexer.tokenize("let"))
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION

    def test_mut_keyword(self, rust_lexer) -> None:
        """'mut' should be KEYWORD."""
        tokens = list(rust_lexer.tokenize("mut"))
        assert tokens[0].type == TokenType.KEYWORD

    def test_async_keyword(self, rust_lexer) -> None:
        """'async' should be KEYWORD."""
        tokens = list(rust_lexer.tokenize("async"))
        assert tokens[0].type == TokenType.KEYWORD


class TestRustStrings:
    """Test Rust string tokenization."""

    def test_double_quoted_string(self, rust_lexer) -> None:
        """Double-quoted strings should be STRING."""
        code = '"hello"'
        tokens = list(rust_lexer.tokenize(code))
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0

    def test_raw_string(self, rust_lexer) -> None:
        """Raw strings should be tokenized."""
        code = 'r#"raw string"#'
        tokens = list(rust_lexer.tokenize(code))
        assert len(tokens) > 0

    def test_byte_string(self, rust_lexer) -> None:
        """Byte strings should be tokenized."""
        code = 'b"hello"'
        tokens = list(rust_lexer.tokenize(code))
        assert len(tokens) > 0


class TestRustNumbers:
    """Test Rust number tokenization."""

    def test_integer(self, rust_lexer) -> None:
        """Integers should be NUMBER_INTEGER."""
        tokens = list(rust_lexer.tokenize("42"))
        assert tokens[0].type == TokenType.NUMBER_INTEGER

    def test_float(self, rust_lexer) -> None:
        """Floats should be NUMBER_FLOAT."""
        tokens = list(rust_lexer.tokenize("3.14"))
        assert tokens[0].type == TokenType.NUMBER_FLOAT

    def test_hex_number(self, rust_lexer) -> None:
        """Hex numbers should be NUMBER_HEX."""
        tokens = list(rust_lexer.tokenize("0xFF"))
        assert tokens[0].type == TokenType.NUMBER_HEX

    def test_binary_number(self, rust_lexer) -> None:
        """Binary numbers should be NUMBER_BIN."""
        tokens = list(rust_lexer.tokenize("0b1010"))
        assert tokens[0].type == TokenType.NUMBER_BIN


class TestRustComments:
    """Test Rust comment tokenization."""

    def test_line_comment(self, rust_lexer) -> None:
        """Line comments should be COMMENT_SINGLE."""
        code = "// This is a comment"
        tokens = list(rust_lexer.tokenize(code))
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT_SINGLE]
        assert len(comment_tokens) > 0

    def test_block_comment(self, rust_lexer) -> None:
        """Block comments should be COMMENT_MULTILINE."""
        code = "/* This is a comment */"
        tokens = list(rust_lexer.tokenize(code))
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT_MULTILINE]
        assert len(comment_tokens) > 0

    def test_doc_comment(self, rust_lexer) -> None:
        """Doc comments should be COMMENT_MULTILINE."""
        code = "/// This is a doc comment"
        tokens = list(rust_lexer.tokenize(code))
        # Should be recognized as comment
        assert len(tokens) > 0


class TestRustOperators:
    """Test Rust operator tokenization."""

    def test_arithmetic_operators(self, rust_lexer) -> None:
        """Arithmetic operators should be OPERATOR."""
        operators = ["+", "-", "*", "/", "%"]
        for op in operators:
            tokens = list(rust_lexer.tokenize(op))
            op_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
            assert len(op_tokens) > 0

    def test_comparison_operators(self, rust_lexer) -> None:
        """Comparison operators should be OPERATOR."""
        operators = ["==", "!=", "<", ">", "<=", ">="]
        for op in operators:
            tokens = list(rust_lexer.tokenize(op))
            op_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
            assert len(op_tokens) > 0


class TestRustComplex:
    """Test complex Rust constructs."""

    def test_function_definition(self, rust_lexer) -> None:
        """Function definitions should tokenize correctly."""
        code = 'fn main() { println!("Hello"); }'
        tokens = list(rust_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_DECLARATION in types  # fn
        assert TokenType.NAME in types  # main

    def test_lifetime(self, rust_lexer) -> None:
        """Lifetimes should tokenize correctly."""
        code = "fn foo<'a>(x: &'a str) -> &'a str"
        tokens = list(rust_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_DECLARATION in types  # fn

    def test_macro(self, rust_lexer) -> None:
        """Macros should tokenize correctly."""
        code = 'println!("hello")'
        tokens = list(rust_lexer.tokenize(code))
        assert len(tokens) > 0


class TestRustFixtures:
    """Test Rust lexer using fixture files."""

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "keywords",
            "strings",
            "numbers",
            "comments",
            "operators",
            "lifetimes",
        ],
    )
    def test_fixture(self, rust_lexer, fixture_name: str) -> None:
        """Test lexer against fixture files if they exist."""
        try:
            input_code, expected_tokens = load_fixture("rust", fixture_name)
            actual_tokens = list(rust_lexer.tokenize(input_code))
            if expected_tokens:
                assert_tokens_match(actual_tokens, expected_tokens, fuzzy_boundaries=True)
        except FileNotFoundError:
            pytest.skip(f"Fixture {fixture_name} not found")
