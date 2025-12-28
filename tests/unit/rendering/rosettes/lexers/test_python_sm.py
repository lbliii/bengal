"""Comprehensive tests for Python lexer.

Tests token accuracy for Python language constructs:
- Keywords (def, class, if, etc.)
- Strings (single, double, triple, f-strings, raw)
- Numbers (int, float, hex, bin, oct)
- Comments (line, docstrings)
- Operators and punctuation
- Decorators
- Type annotations
- Escape sequences
"""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import TokenType
from tests.unit.rendering.rosettes.conftest import assert_tokens_match, load_fixture


class TestPythonKeywords:
    """Test Python keyword tokenization."""

    def test_def_keyword(self, python_lexer) -> None:
        """'def' should be tokenized as KEYWORD_DECLARATION."""
        tokens = list(python_lexer.tokenize("def"))
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION
        assert tokens[0].value == "def"

    def test_class_keyword(self, python_lexer) -> None:
        """'class' should be tokenized as KEYWORD_DECLARATION."""
        tokens = list(python_lexer.tokenize("class"))
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION
        assert tokens[0].value == "class"

    def test_if_keyword(self, python_lexer) -> None:
        """'if' should be tokenized as KEYWORD."""
        tokens = list(python_lexer.tokenize("if"))
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.KEYWORD
        assert tokens[0].value == "if"

    def test_true_false_none(self, python_lexer) -> None:
        """True, False, None should be KEYWORD_CONSTANT."""
        for value in ["True", "False", "None"]:
            tokens = list(python_lexer.tokenize(value))
            assert tokens[0].type == TokenType.KEYWORD_CONSTANT
            assert tokens[0].value == value

    def test_import_from(self, python_lexer) -> None:
        """'import' and 'from' should be KEYWORD_NAMESPACE."""
        tokens = list(python_lexer.tokenize("import"))
        assert tokens[0].type == TokenType.KEYWORD_NAMESPACE

        tokens = list(python_lexer.tokenize("from"))
        assert tokens[0].type == TokenType.KEYWORD_NAMESPACE


class TestPythonStrings:
    """Test Python string tokenization."""

    def test_single_quoted_string(self, python_lexer) -> None:
        """Single-quoted strings should be STRING_SINGLE."""
        code = "'hello'"
        tokens = list(python_lexer.tokenize(code))
        assert len(tokens) >= 1
        string_tokens = [t for t in tokens if t.type == TokenType.STRING_SINGLE]
        assert len(string_tokens) > 0

    def test_double_quoted_string(self, python_lexer) -> None:
        """Double-quoted strings should be STRING_DOUBLE."""
        code = '"hello"'
        tokens = list(python_lexer.tokenize(code))
        string_tokens = [t for t in tokens if t.type == TokenType.STRING_DOUBLE]
        assert len(string_tokens) > 0

    def test_triple_quoted_string(self, python_lexer) -> None:
        """Triple-quoted strings should be STRING_DOC."""
        code = '"""docstring"""'
        tokens = list(python_lexer.tokenize(code))
        doc_tokens = [t for t in tokens if t.type == TokenType.STRING_DOC]
        assert len(doc_tokens) > 0

    def test_f_string(self, python_lexer) -> None:
        """f-strings should be tokenized correctly."""
        code = 'f"value: {x}"'
        tokens = list(python_lexer.tokenize(code))
        # Should have string token and interpolation
        string_types = [t.type for t in tokens]
        assert TokenType.STRING in string_types or TokenType.STRING_DOUBLE in string_types

    def test_raw_string(self, python_lexer) -> None:
        """Raw strings should be tokenized."""
        code = 'r"\\n is literal"'
        tokens = list(python_lexer.tokenize(code))
        assert len(tokens) > 0

    def test_escape_sequences(self, python_lexer) -> None:
        """Escape sequences should be STRING_ESCAPE."""
        code = '"\\n\\t\\r"'
        tokens = list(python_lexer.tokenize(code))
        escape_tokens = [t for t in tokens if t.type == TokenType.STRING_ESCAPE]
        assert len(escape_tokens) > 0


class TestPythonNumbers:
    """Test Python number tokenization."""

    def test_integer(self, python_lexer) -> None:
        """Integers should be NUMBER_INTEGER."""
        tokens = list(python_lexer.tokenize("42"))
        assert tokens[0].type == TokenType.NUMBER_INTEGER
        assert tokens[0].value == "42"

    def test_float(self, python_lexer) -> None:
        """Floats should be NUMBER_FLOAT."""
        tokens = list(python_lexer.tokenize("3.14"))
        assert tokens[0].type == TokenType.NUMBER_FLOAT
        assert tokens[0].value == "3.14"

    def test_hex_number(self, python_lexer) -> None:
        """Hex numbers should be NUMBER_HEX."""
        tokens = list(python_lexer.tokenize("0xFF"))
        assert tokens[0].type == TokenType.NUMBER_HEX

    def test_binary_number(self, python_lexer) -> None:
        """Binary numbers should be NUMBER_BIN."""
        tokens = list(python_lexer.tokenize("0b1010"))
        assert tokens[0].type == TokenType.NUMBER_BIN

    def test_octal_number(self, python_lexer) -> None:
        """Octal numbers should be NUMBER_OCT."""
        tokens = list(python_lexer.tokenize("0o755"))
        assert tokens[0].type == TokenType.NUMBER_OCT


class TestPythonComments:
    """Test Python comment tokenization."""

    def test_line_comment(self, python_lexer) -> None:
        """Line comments should be COMMENT_SINGLE."""
        code = "# This is a comment"
        tokens = list(python_lexer.tokenize(code))
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT_SINGLE]
        assert len(comment_tokens) > 0

    def test_docstring(self, python_lexer) -> None:
        """Docstrings should be STRING_DOC."""
        code = '"""This is a docstring"""'
        tokens = list(python_lexer.tokenize(code))
        doc_tokens = [t for t in tokens if t.type == TokenType.STRING_DOC]
        assert len(doc_tokens) > 0


class TestPythonOperators:
    """Test Python operator tokenization."""

    def test_arithmetic_operators(self, python_lexer) -> None:
        """Arithmetic operators should be OPERATOR."""
        operators = ["+", "-", "*", "/", "//", "%", "**"]
        for op in operators:
            tokens = list(python_lexer.tokenize(op))
            op_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
            assert len(op_tokens) > 0

    def test_comparison_operators(self, python_lexer) -> None:
        """Comparison operators should be OPERATOR."""
        operators = ["==", "!=", "<", ">", "<=", ">=", "is", "in"]
        for op in operators:
            tokens = list(python_lexer.tokenize(op))
            op_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
            assert len(op_tokens) > 0


class TestPythonDecorators:
    """Test Python decorator tokenization."""

    def test_decorator(self, python_lexer) -> None:
        """Decorators should be NAME_DECORATOR."""
        code = "@decorator"
        tokens = list(python_lexer.tokenize(code))
        decorator_tokens = [t for t in tokens if t.type == TokenType.NAME_DECORATOR]
        assert len(decorator_tokens) > 0

    def test_decorator_with_function(self, python_lexer) -> None:
        """Decorator before function should tokenize correctly."""
        code = "@decorator\ndef foo(): pass"
        tokens = list(python_lexer.tokenize(code))
        # Should have decorator and function definition
        types = [t.type for t in tokens]
        assert TokenType.NAME_DECORATOR in types
        assert TokenType.KEYWORD_DECLARATION in types


class TestPythonTypeAnnotations:
    """Test Python type annotation tokenization."""

    def test_type_hint(self, python_lexer) -> None:
        """Type hints should be tokenized."""
        code = "def foo(x: int) -> str:"
        tokens = list(python_lexer.tokenize(code))
        # Should have function, parameter, type hint
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_DECLARATION in types  # def
        assert TokenType.NAME_FUNCTION in types  # foo


class TestPythonComplex:
    """Test complex Python code constructs."""

    def test_function_definition(self, python_lexer) -> None:
        """Function definition should tokenize correctly."""
        code = "def hello(name: str) -> str:\n    return f'Hello, {name}'"
        tokens = list(python_lexer.tokenize(code))
        # Should have keywords, names, strings
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_DECLARATION in types
        assert TokenType.NAME_FUNCTION in types
        assert TokenType.STRING in types or TokenType.STRING_DOUBLE in types

    def test_class_definition(self, python_lexer) -> None:
        """Class definition should tokenize correctly."""
        code = "class MyClass:\n    def __init__(self): pass"
        tokens = list(python_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_DECLARATION in types  # class, def
        assert TokenType.NAME_CLASS in types

    def test_import_statement(self, python_lexer) -> None:
        """Import statements should tokenize correctly."""
        code = "from typing import List, Dict"
        tokens = list(python_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD_NAMESPACE in types  # from, import

    def test_list_comprehension(self, python_lexer) -> None:
        """List comprehensions should tokenize correctly."""
        code = "[x for x in range(10) if x % 2 == 0]"
        tokens = list(python_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD in types  # for, in, if
        assert TokenType.OPERATOR in types  # %, ==


class TestPythonFixtures:
    """Test Python lexer using fixture files."""

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "keywords",
            "strings",
            "numbers",
            "comments",
            "operators",
            "decorators",
            "type_annotations",
        ],
    )
    def test_fixture(self, python_lexer, fixture_name: str) -> None:
        """Test lexer against fixture files if they exist."""
        try:
            input_code, expected_tokens = load_fixture("python", fixture_name)
            actual_tokens = list(python_lexer.tokenize(input_code))
            if expected_tokens:
                assert_tokens_match(actual_tokens, expected_tokens, fuzzy_boundaries=True)
        except FileNotFoundError:
            # Fixture doesn't exist yet - skip
            pytest.skip(f"Fixture {fixture_name} not found")
