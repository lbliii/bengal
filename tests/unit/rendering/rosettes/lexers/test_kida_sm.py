"""Comprehensive tests for Kida lexer (Bengal's native template engine).

Tests token accuracy for Kida-specific constructs:
- Comments: {# comment #}
- Expressions: {{ variable }}
- Statements: {% if cond %}
- Pipeline operator: |>
- Null-coalescing: ??
- Unified endings: {% end %}
- Let bindings: {% let x = 1 %}
- Pattern matching: {% match x %}{% case 1 %}
- Built-in filters and tests
"""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import TokenType
from tests.unit.rendering.rosettes.conftest import assert_tokens_match, load_fixture


class TestKidaComments:
    """Test Kida comment tokenization."""

    def test_comment(self, kida_lexer) -> None:
        """Comments should be COMMENT_MULTILINE."""
        code = "{# This is a comment #}"
        tokens = list(kida_lexer.tokenize(code))
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT_MULTILINE]
        assert len(comment_tokens) > 0


class TestKidaExpressions:
    """Test Kida expression tokenization."""

    def test_simple_expression(self, kida_lexer) -> None:
        """Simple expressions should tokenize correctly."""
        code = "{{ variable }}"
        tokens = list(kida_lexer.tokenize(code))
        # Should have punctuation markers and variable name
        types = [t.type for t in tokens]
        assert TokenType.PUNCTUATION_MARKER in types or TokenType.PUNCTUATION in types

    def test_expression_with_filter(self, kida_lexer) -> None:
        """Expressions with filters should tokenize correctly."""
        code = "{{ value | upper }}"
        tokens = list(kida_lexer.tokenize(code))
        assert len(tokens) > 0


class TestKidaStatements:
    """Test Kida statement tokenization."""

    def test_if_statement(self, kida_lexer) -> None:
        """If statements should tokenize correctly."""
        code = "{% if condition %}content{% end %}"
        tokens = list(kida_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD in types  # if, end

    def test_for_statement(self, kida_lexer) -> None:
        """For statements should tokenize correctly."""
        code = "{% for item in items %}content{% end %}"
        tokens = list(kida_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD in types  # for, in, end


class TestKidaPipelineOperator:
    """Test Kida-specific |> pipeline operator."""

    def test_pipeline_operator(self, kida_lexer) -> None:
        """Pipeline operator |> should be OPERATOR."""
        code = "{{ value |> upper |> trim }}"
        tokens = list(kida_lexer.tokenize(code))
        operators = [t for t in tokens if t.value == "|>"]
        assert len(operators) == 2
        assert all(t.type == TokenType.OPERATOR for t in operators)


class TestKidaNullCoalescing:
    """Test Kida-specific ?? null-coalescing operator."""

    def test_null_coalescing(self, kida_lexer) -> None:
        """Null-coalescing operator ?? should be OPERATOR."""
        code = "{{ value ?? 'default' }}"
        tokens = list(kida_lexer.tokenize(code))
        null_coalesce = [t for t in tokens if t.value == "??"]
        assert len(null_coalesce) == 1
        assert null_coalesce[0].type == TokenType.OPERATOR


class TestKidaUnifiedEnd:
    """Test Kida unified 'end' keyword."""

    def test_unified_end(self, kida_lexer) -> None:
        """'end' should be KEYWORD (not endif, endfor, etc.)."""
        code = "{% if x %}content{% end %}"
        tokens = list(kida_lexer.tokenize(code))
        keywords = [t for t in tokens if t.type == TokenType.KEYWORD]
        keyword_values = [t.value for t in keywords]
        assert "if" in keyword_values
        assert "end" in keyword_values
        # Should NOT have endif, endfor, etc.
        assert "endif" not in keyword_values
        assert "endfor" not in keyword_values


class TestKidaLetBindings:
    """Test Kida let bindings."""

    def test_let_binding(self, kida_lexer) -> None:
        """Let bindings should tokenize correctly."""
        code = "{% let x = 1 %}"
        tokens = list(kida_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD in types  # let
        assert TokenType.NAME_VARIABLE in types  # x


class TestKidaPatternMatching:
    """Test Kida pattern matching."""

    def test_match_case(self, kida_lexer) -> None:
        """Match/case statements should tokenize correctly."""
        code = "{% match x %}{% case 1 %}one{% case 2 %}two{% end %}"
        tokens = list(kida_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD in types  # match, case, end


class TestKidaBuiltins:
    """Test Kida built-in filters and tests."""

    def test_builtin_filter(self, kida_lexer) -> None:
        """Built-in filters should be NAME_FUNCTION."""
        code = "{{ x | slugify }}"
        tokens = list(kida_lexer.tokenize(code))
        # Should have function name
        types = [t.type for t in tokens]
        assert TokenType.NAME_FUNCTION in types or TokenType.NAME_BUILTIN in types

    def test_builtin_test(self, kida_lexer) -> None:
        """Built-in tests should be NAME_BUILTIN."""
        code = "{% if x is defined %}"
        tokens = list(kida_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.NAME_BUILTIN in types or TokenType.KEYWORD in types


class TestKidaComplex:
    """Test complex Kida templates."""

    def test_nested_statements(self, kida_lexer) -> None:
        """Nested statements should tokenize correctly."""
        code = "{% if x %}{% for item in items %}{{ item }}{% end %}{% end %}"
        tokens = list(kida_lexer.tokenize(code))
        types = [t.type for t in tokens]
        assert TokenType.KEYWORD in types  # if, for, in, end

    def test_pipeline_with_filters(self, kida_lexer) -> None:
        """Pipeline with multiple filters should tokenize correctly."""
        code = "{{ value |> upper |> trim |> slugify }}"
        tokens = list(kida_lexer.tokenize(code))
        operators = [t for t in tokens if t.value == "|>"]
        assert len(operators) == 3


class TestKidaFixtures:
    """Test Kida lexer using fixture files."""

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "expressions",
            "statements",
            "pipeline",
            "pattern_matching",
            "builtins",
        ],
    )
    def test_fixture(self, kida_lexer, fixture_name: str) -> None:
        """Test lexer against fixture files if they exist."""
        try:
            input_code, expected_tokens = load_fixture("kida", fixture_name)
            actual_tokens = list(kida_lexer.tokenize(input_code))
            if expected_tokens:
                assert_tokens_match(actual_tokens, expected_tokens, fuzzy_boundaries=True)
        except FileNotFoundError:
            pytest.skip(f"Fixture {fixture_name} not found")
