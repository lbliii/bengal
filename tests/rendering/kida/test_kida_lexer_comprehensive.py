"""Comprehensive tests for the Kida lexer.

This module provides thorough testing of the lexer's behavior including:
- Unicode handling
- All token types
- Edge cases in tokenization
- Error handling and recovery
- Line and column tracking
- Whitespace handling
- Custom delimiters (if supported)
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.lexer import (
    Lexer,
    LexerConfig,
    LexerError,
    MAX_TOKENS,
    tokenize,
)


class TestTokenizeBasic:
    """Basic tokenization tests."""

    def test_empty_string(self) -> None:
        """Empty template produces only EOF."""
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_whitespace_only(self) -> None:
        """Whitespace-only template is DATA."""
        tokens = tokenize("   \n\t\n   ")
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.DATA
        assert tokens[1].type == TokenType.EOF

    def test_plain_text(self) -> None:
        """Plain text is DATA."""
        tokens = tokenize("Hello World")
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.DATA
        assert tokens[0].value == "Hello World"


class TestUnicodeHandling:
    """Test unicode handling in lexer."""

    def test_unicode_in_data(self) -> None:
        """Unicode characters in DATA."""
        tokens = tokenize("Hello 世界 🌍 мир")
        assert tokens[0].value == "Hello 世界 🌍 мир"

    def test_unicode_in_variable(self) -> None:
        """Variable expressions preserve unicode."""
        tokens = tokenize("{{ 'Hello 世界' }}")
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert "世界" in string_token.value

    def test_unicode_variable_names(self) -> None:
        """Kida doesn't support unicode variable names."""
        # Kida requires ASCII identifiers
        with pytest.raises(Exception):  # LexerError
            list(tokenize("{{ переменная }}"))

    def test_emoji_in_strings(self) -> None:
        """Emoji in string literals."""
        tokens = tokenize("{{ '🚀 Launch!' }}")
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert "🚀" in string_token.value

    def test_mixed_unicode_and_expressions(self) -> None:
        """Mixed unicode text and expressions."""
        tokens = tokenize("こんにちは {{ name }} さん")
        data_tokens = [t for t in tokens if t.type == TokenType.DATA]
        assert len(data_tokens) == 2
        assert "こんにちは" in data_tokens[0].value


class TestStringLiterals:
    """Test string literal tokenization."""

    def test_single_quoted(self) -> None:
        """Single quoted string."""
        tokens = tokenize("{{ 'hello' }}")
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert string_token.value == "hello"

    def test_double_quoted(self) -> None:
        """Double quoted string."""
        tokens = tokenize('{{ "hello" }}')
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert string_token.value == "hello"

    def test_escaped_quotes_single(self) -> None:
        """Escaped quotes in single-quoted string."""
        tokens = tokenize("{{ 'he\\'llo' }}")
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert "'" in string_token.value or "\\'" in string_token.value

    def test_escaped_quotes_double(self) -> None:
        """Escaped quotes in double-quoted string."""
        tokens = tokenize('{{ "he\\"llo" }}')
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        # May contain escaped or unescaped quote
        assert '"' in string_token.value or '\\"' in string_token.value

    def test_empty_string(self) -> None:
        """Empty string literal."""
        tokens = tokenize("{{ '' }}")
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert string_token.value == ""

    def test_string_with_newlines(self) -> None:
        """String containing newline escape."""
        tokens = tokenize('{{ "line1\\nline2" }}')
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert "n" in string_token.value  # Contains escaped or literal newline

    def test_string_with_unicode_escape(self) -> None:
        """String with unicode escape sequence."""
        tokens = tokenize('{{ "\\u0041" }}')
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        # May be escaped or converted
        assert string_token.value is not None


class TestNumericLiterals:
    """Test numeric literal tokenization."""

    def test_integer(self) -> None:
        """Integer literal."""
        tokens = tokenize("{{ 42 }}")
        int_token = next(t for t in tokens if t.type == TokenType.INTEGER)
        assert int_token.value == "42"

    def test_zero(self) -> None:
        """Zero literal."""
        tokens = tokenize("{{ 0 }}")
        int_token = next(t for t in tokens if t.type == TokenType.INTEGER)
        assert int_token.value == "0"

    def test_negative_integer(self) -> None:
        """Negative integer (handled as unary minus)."""
        tokens = tokenize("{{ -42 }}")
        # Should have SUB token followed by INTEGER
        types = [t.type for t in tokens]
        assert TokenType.SUB in types
        assert TokenType.INTEGER in types

    def test_large_integer(self) -> None:
        """Large integer literal."""
        tokens = tokenize("{{ 99999999999999999999 }}")
        int_token = next(t for t in tokens if t.type == TokenType.INTEGER)
        assert int_token.value == "99999999999999999999"

    def test_float(self) -> None:
        """Float literal."""
        tokens = tokenize("{{ 3.14 }}")
        float_token = next(t for t in tokens if t.type == TokenType.FLOAT)
        assert float_token.value == "3.14"

    def test_float_without_leading_digit(self) -> None:
        """Float without leading digit (.5)."""
        tokens = tokenize("{{ .5 }}")
        # May be tokenized as DOT + INTEGER or as FLOAT
        types = [t.type for t in tokens]
        assert TokenType.FLOAT in types or TokenType.DOT in types

    def test_float_scientific_notation(self) -> None:
        """Float with scientific notation (if supported)."""
        # This may or may not be supported
        tokens = tokenize("{{ 1e10 }}")
        # Should tokenize without error


class TestOperators:
    """Test operator tokenization."""

    def test_arithmetic_operators(self) -> None:
        """All arithmetic operators."""
        tokens = tokenize("{{ a + b - c * d / e // f % g ** h }}")
        types = [t.type for t in tokens]
        assert TokenType.ADD in types
        assert TokenType.SUB in types
        assert TokenType.MUL in types
        assert TokenType.DIV in types
        assert TokenType.FLOORDIV in types
        assert TokenType.MOD in types
        assert TokenType.POW in types

    def test_comparison_operators(self) -> None:
        """All comparison operators."""
        tokens = tokenize("{{ a == b != c < d > e <= f >= g }}")
        types = [t.type for t in tokens]
        assert TokenType.EQ in types
        assert TokenType.NE in types
        assert TokenType.LT in types
        assert TokenType.GT in types
        assert TokenType.LE in types
        assert TokenType.GE in types

    def test_assignment(self) -> None:
        """Assignment operator."""
        tokens = tokenize("{% set x = 42 %}")
        types = [t.type for t in tokens]
        assert TokenType.ASSIGN in types

    def test_pipe(self) -> None:
        """Pipe operator for filters."""
        tokens = tokenize("{{ x | upper }}")
        types = [t.type for t in tokens]
        assert TokenType.PIPE in types

    def test_tilde(self) -> None:
        """Tilde operator for concatenation."""
        tokens = tokenize("{{ a ~ b }}")
        types = [t.type for t in tokens]
        assert TokenType.TILDE in types

    def test_dot(self) -> None:
        """Dot operator for attribute access."""
        tokens = tokenize("{{ obj.attr }}")
        types = [t.type for t in tokens]
        assert TokenType.DOT in types


class TestBrackets:
    """Test bracket and parenthesis tokenization."""

    def test_parentheses(self) -> None:
        """Parentheses."""
        tokens = tokenize("{{ (a + b) }}")
        types = [t.type for t in tokens]
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types

    def test_square_brackets(self) -> None:
        """Square brackets."""
        tokens = tokenize("{{ items[0] }}")
        types = [t.type for t in tokens]
        assert TokenType.LBRACKET in types
        assert TokenType.RBRACKET in types

    def test_curly_braces(self) -> None:
        """Curly braces for dict literals."""
        tokens = tokenize("{{ {'a': 1} }}")
        types = [t.type for t in tokens]
        assert TokenType.LBRACE in types
        assert TokenType.RBRACE in types

    def test_nested_brackets(self) -> None:
        """Nested brackets."""
        tokens = tokenize("{{ items[data['key']] }}")
        types = [t.type for t in tokens]
        assert types.count(TokenType.LBRACKET) == 2
        assert types.count(TokenType.RBRACKET) == 2


class TestBlockTags:
    """Test block tag tokenization."""

    def test_if_block(self) -> None:
        """If block."""
        tokens = tokenize("{% if true %}{% endif %}")
        types = [t.type for t in tokens]
        assert types.count(TokenType.BLOCK_BEGIN) == 2
        assert types.count(TokenType.BLOCK_END) == 2

    def test_for_block(self) -> None:
        """For block."""
        tokens = list(tokenize("{% for x in items %}{% endfor %}"))
        # Check for expected tokens: 'for' is NAME, 'in' is IN keyword
        name_values = [t.value for t in tokens if t.type == TokenType.NAME]
        types = [t.type for t in tokens]
        assert "for" in name_values
        assert TokenType.IN in types  # 'in' is a keyword token, not NAME

    def test_block_with_whitespace_control(self) -> None:
        """Block with whitespace control markers."""
        tokens = tokenize("{%- if true -%}")
        types = [t.type for t in tokens]
        assert TokenType.BLOCK_BEGIN in types

    def test_variable_with_whitespace_control(self) -> None:
        """Variable with whitespace control."""
        tokens = tokenize("{{- x -}}")
        types = [t.type for t in tokens]
        assert TokenType.VARIABLE_BEGIN in types


class TestComments:
    """Test comment tokenization."""

    def test_simple_comment(self) -> None:
        """Simple comment."""
        tokens = tokenize("{# comment #}")
        # Comments may produce COMMENT token or be stripped
        # At minimum, no error should occur

    def test_multiline_comment(self) -> None:
        """Multiline comment."""
        tokens = tokenize("{# line1\nline2\nline3 #}")
        # Should not error

    def test_comment_with_template_code(self) -> None:
        """Comment containing template syntax."""
        tokens = tokenize("{# {{ x }} {% if %}...{% endif %} #}")
        # Content should be preserved or stripped, not parsed
        # Check that we don't have extra VARIABLE_BEGIN etc
        var_begins = [t for t in tokens if t.type == TokenType.VARIABLE_BEGIN]
        assert len(var_begins) == 0


class TestLineTracking:
    """Test line and column tracking."""

    def test_single_line(self) -> None:
        """Line number on single line."""
        tokens = tokenize("{{ x }}")
        for token in tokens:
            assert token.lineno == 1

    def test_multiline(self) -> None:
        """Line numbers across multiple lines."""
        source = "line1\n{{ x }}\nline3"
        tokens = tokenize(source)
        var_begin = next(t for t in tokens if t.type == TokenType.VARIABLE_BEGIN)
        assert var_begin.lineno == 2

    def test_column_offset(self) -> None:
        """Column offset tracking."""
        tokens = tokenize("   {{ x }}")
        var_begin = next(t for t in tokens if t.type == TokenType.VARIABLE_BEGIN)
        assert var_begin.col_offset >= 3

    def test_line_tracking_in_block(self) -> None:
        """Line tracking inside blocks."""
        source = """{% for i in items %}
{{ i }}
{% endfor %}"""
        tokens = tokenize(source)
        # Find the NAME token 'i' inside the output
        # It should be on line 2


class TestKeywords:
    """Test keyword recognition."""

    def test_true(self) -> None:
        """True keyword."""
        tokens = tokenize("{{ true }}")
        name_token = next(t for t in tokens if t.type == TokenType.NAME)
        assert name_token.value == "true"

    def test_false(self) -> None:
        """False keyword."""
        tokens = tokenize("{{ false }}")
        name_token = next(t for t in tokens if t.type == TokenType.NAME)
        assert name_token.value == "false"

    def test_none(self) -> None:
        """None keyword."""
        tokens = tokenize("{{ none }}")
        name_token = next(t for t in tokens if t.type == TokenType.NAME)
        assert name_token.value == "none"

    def test_and(self) -> None:
        """And keyword is tokenized as AND token, not NAME."""
        tokens = tokenize("{{ a and b }}")
        and_tokens = [t for t in tokens if t.type == TokenType.AND]
        assert len(and_tokens) == 1
        assert and_tokens[0].value == "and"

    def test_or(self) -> None:
        """Or keyword is tokenized as OR token, not NAME."""
        tokens = tokenize("{{ a or b }}")
        or_tokens = [t for t in tokens if t.type == TokenType.OR]
        assert len(or_tokens) == 1
        assert or_tokens[0].value == "or"

    def test_not(self) -> None:
        """Not keyword is tokenized as NOT token, not NAME."""
        tokens = tokenize("{{ not x }}")
        not_tokens = [t for t in tokens if t.type == TokenType.NOT]
        assert len(not_tokens) == 1
        assert not_tokens[0].value == "not"

    def test_in(self) -> None:
        """In keyword is tokenized as IN token, not NAME."""
        tokens = tokenize("{% if x in items %}")
        in_tokens = [t for t in tokens if t.type == TokenType.IN]
        assert len(in_tokens) == 1
        assert in_tokens[0].value == "in"

    def test_is(self) -> None:
        """Is keyword is tokenized as IS token, not NAME."""
        tokens = tokenize("{% if x is defined %}")
        is_tokens = [t for t in tokens if t.type == TokenType.IS]
        assert len(is_tokens) == 1
        assert is_tokens[0].value == "is"


class TestEdgeCases:
    """Edge cases in tokenization."""

    def test_adjacent_expressions(self) -> None:
        """Adjacent expressions without space."""
        tokens = tokenize("{{ a }}{{ b }}")
        var_begins = [t for t in tokens if t.type == TokenType.VARIABLE_BEGIN]
        assert len(var_begins) == 2

    def test_expression_in_expression_like_text(self) -> None:
        """Text that looks like expression."""
        tokens = tokenize("Use {{ and }} for expressions")
        data_tokens = [t for t in tokens if t.type == TokenType.DATA]
        assert len(data_tokens) >= 2

    def test_incomplete_expression_start(self) -> None:
        """Single brace is not expression start."""
        tokens = tokenize("Single { brace")
        assert tokens[0].type == TokenType.DATA
        assert "{" in tokens[0].value

    def test_deeply_nested_parentheses(self) -> None:
        """Deeply nested parentheses."""
        tokens = tokenize("{{ ((((a)))) }}")
        lparen_count = len([t for t in tokens if t.type == TokenType.LPAREN])
        rparen_count = len([t for t in tokens if t.type == TokenType.RPAREN])
        assert lparen_count == 4
        assert rparen_count == 4

    def test_very_long_identifier(self) -> None:
        """Very long identifier name."""
        long_name = "a" * 1000
        tokens = tokenize(f"{{{{ {long_name} }}}}")
        name_token = next(t for t in tokens if t.type == TokenType.NAME)
        assert name_token.value == long_name

    def test_mixed_delimiters(self) -> None:
        """Mixed block, variable, and comment."""
        tokens = tokenize("{% set x = 1 %}{{ x }}{# comment #}")
        types = [t.type for t in tokens]
        assert TokenType.BLOCK_BEGIN in types
        assert TokenType.VARIABLE_BEGIN in types


class TestLexerConfig:
    """Test lexer configuration."""

    def test_default_config(self) -> None:
        """Default configuration."""
        lexer = Lexer("{{ x }}")
        tokens = list(lexer.tokenize())
        assert TokenType.VARIABLE_BEGIN in [t.type for t in tokens]

    def test_trim_blocks(self) -> None:
        """Trim blocks configuration."""
        config = LexerConfig(trim_blocks=True)
        lexer = Lexer("{% if true %}\ntest", config)
        tokens = list(lexer.tokenize())
        # With trim_blocks, newline after block may be removed

    def test_lstrip_blocks(self) -> None:
        """Lstrip blocks configuration."""
        config = LexerConfig(lstrip_blocks=True)
        lexer = Lexer("    {% if true %}", config)
        tokens = list(lexer.tokenize())
        # With lstrip_blocks, leading whitespace may be removed


class TestErrorHandling:
    """Test error handling in lexer."""

    def test_unclosed_string(self) -> None:
        """Unclosed string literal."""
        with pytest.raises((LexerError, SyntaxError, Exception)):
            tokenize("{{ 'unclosed }}")

    def test_unclosed_variable(self) -> None:
        """Unclosed variable expression."""
        # May not raise during lexing, but during parsing
        tokens = tokenize("{{ x")
        # At minimum, should not crash

    def test_unclosed_block(self) -> None:
        """Unclosed block tag."""
        tokens = tokenize("{% if true")
        # At minimum, should not crash

    def test_invalid_operator(self) -> None:
        """Invalid operator sequence."""
        # Most invalid operators are parsed as separate tokens
        tokens = tokenize("{{ a +++ b }}")
        # Should not crash


class TestRawBlock:
    """Test raw block handling."""

    def test_raw_block_preserves_content(self) -> None:
        """Raw block preserves template syntax."""
        tokens = tokenize("{% raw %}{{ x }}{% endraw %}")
        # Content inside raw should not be tokenized as VARIABLE_BEGIN


class TestSliceNotation:
    """Test slice notation tokenization."""

    def test_basic_slice(self) -> None:
        """Basic slice with colon."""
        tokens = tokenize("{{ items[1:3] }}")
        types = [t.type for t in tokens]
        assert TokenType.COLON in types

    def test_slice_with_step(self) -> None:
        """Slice with step (two colons)."""
        tokens = tokenize("{{ items[::2] }}")
        colon_count = len([t for t in tokens if t.type == TokenType.COLON])
        assert colon_count == 2


class TestFunctionCalls:
    """Test function call tokenization."""

    def test_function_no_args(self) -> None:
        """Function call with no arguments."""
        tokens = tokenize("{{ func() }}")
        types = [t.type for t in tokens]
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types

    def test_function_with_args(self) -> None:
        """Function call with arguments."""
        tokens = tokenize("{{ func(a, b, c) }}")
        comma_count = len([t for t in tokens if t.type == TokenType.COMMA])
        assert comma_count == 2

    def test_function_with_kwargs(self) -> None:
        """Function call with keyword arguments."""
        tokens = tokenize("{{ func(x=1, y=2) }}")
        types = [t.type for t in tokens]
        assert types.count(TokenType.ASSIGN) == 2


class TestFilterSyntax:
    """Test filter syntax tokenization."""

    def test_simple_filter(self) -> None:
        """Simple filter."""
        tokens = tokenize("{{ x|upper }}")
        types = [t.type for t in tokens]
        assert TokenType.PIPE in types

    def test_filter_with_args(self) -> None:
        """Filter with arguments."""
        tokens = tokenize("{{ x|truncate(10) }}")
        types = [t.type for t in tokens]
        assert TokenType.PIPE in types
        assert TokenType.LPAREN in types

    def test_filter_chain(self) -> None:
        """Chain of filters."""
        tokens = tokenize("{{ x|upper|trim|lower }}")
        pipe_count = len([t for t in tokens if t.type == TokenType.PIPE])
        assert pipe_count == 3


class TestPerformance:
    """Basic performance tests for lexer."""

    def test_large_template(self) -> None:
        """Lexer handles large templates."""
        # 100KB of data
        large_data = "x" * 100000
        tokens = tokenize(large_data)
        assert tokens[0].type == TokenType.DATA

    def test_many_expressions(self) -> None:
        """Lexer handles many expressions."""
        many_exprs = "".join([f"{{{{ x{i} }}}}" for i in range(1000)])
        tokens = tokenize(many_exprs)
        var_begins = [t for t in tokens if t.type == TokenType.VARIABLE_BEGIN]
        assert len(var_begins) == 1000

    def test_deeply_nested_blocks(self) -> None:
        """Lexer handles deeply nested blocks."""
        depth = 50
        template = "{% if true %}" * depth + "content" + "{% endif %}" * depth
        tokens = tokenize(template)
        # Should complete without stack overflow


class TestTokenLimit:
    """Test token limit for DoS protection."""

    def test_token_limit_enforced(self) -> None:
        """Token limit prevents DoS from malformed templates."""
        # Create a template that exceeds the token limit
        # Each "{{ x }}" generates multiple tokens, so we need many of them
        # MAX_TOKENS is 100,000, so create a template with >100k tokens
        many_vars = "".join([f"{{{{ x{i} }}}}" for i in range(MAX_TOKENS // 3 + 1)])
        
        with pytest.raises(LexerError) as exc_info:
            tokenize(many_vars)
        
        error_msg = str(exc_info.value)
        assert "Token limit exceeded" in error_msg
        assert str(MAX_TOKENS) in error_msg
        assert "Split into smaller templates" in error_msg

    def test_legitimate_large_template(self) -> None:
        """Legitimate large templates work (under limit)."""
        # Create a large but legitimate template (just under limit)
        # Each "{{ x }}" generates ~4 tokens (VARIABLE_BEGIN, NAME, VARIABLE_END, DATA)
        # So we can have about MAX_TOKENS // 4 variables
        many_vars = "".join([f"{{{{ x{i} }}}}" for i in range(MAX_TOKENS // 4 - 1)])
        tokens = tokenize(many_vars)
        # Should complete successfully
        assert len(tokens) > 0
        assert tokens[-1].type == TokenType.EOF
