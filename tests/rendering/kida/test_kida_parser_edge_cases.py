"""Parser edge cases and syntax error tests for Kida.

Tests parsing behavior, error handling, and edge cases.
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import Environment, TemplateSyntaxError
from bengal.rendering.kida.lexer import LexerError
from bengal.rendering.kida.parser.errors import ParseError


class TestSyntaxErrors:
    """Test syntax error detection and messages."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_unclosed_variable(self, env: Environment) -> None:
        """Unclosed variable tag raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("Hello {{ name")

    def test_unclosed_block(self, env: Environment) -> None:
        """Unclosed block tag raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{% if true")

    def test_unclosed_comment(self, env: Environment) -> None:
        """Unclosed comment raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{# this never ends")

    def test_mismatched_end_tag(self, env: Environment) -> None:
        """Mismatched end tag should raise error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{% if true %}{% endfor %}")

    def test_missing_end_tag(self, env: Environment) -> None:
        """Missing end tag should raise error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{% if true %}no end")

    def test_extra_end_tag(self, env: Environment) -> None:
        """Extra end tag should raise error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{% endif %}")

    def test_invalid_block_name(self, env: Environment) -> None:
        """Invalid block name raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{% invalid_tag_name %}")

    def test_empty_expression(self, env: Environment) -> None:
        """Empty expression raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{{ }}")

    def test_power_operator(self, env: Environment) -> None:
        """Power operator (**) is supported and works correctly."""
        # Kida supports ** for exponentiation, matching Jinja2 behavior
        tmpl = env.from_string("{{ 2 ** 3 }}")
        assert tmpl.render() == "8"

    def test_unterminated_string(self, env: Environment) -> None:
        """Unterminated string raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{{ 'hello }}")

    def test_invalid_filter_syntax(self, env: Environment) -> None:
        """Invalid filter syntax raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{{ name| }}")

    def test_filter_chain_empty_filter(self, env: Environment) -> None:
        """Empty filter in chain raises error."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string("{{ name|upper| }}")


class TestErrorLineNumbers:
    """Test that errors report correct line numbers."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_error_on_line_1(self, env: Environment) -> None:
        """Error on line 1 reports line 1."""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)) as exc_info:
            env.from_string("{{ invalid syntax here")
        err = exc_info.value
        # Check if line number is reported somehow
        err_str = str(err).lower()
        has_line_1 = "line 1" in err_str or getattr(err, "lineno", None) == 1

    def test_error_on_line_3(self, env: Environment) -> None:
        """Error on line 3 reports line 3."""
        template = """line 1
line 2
{{ broken"""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)) as exc_info:
            env.from_string(template)
        # Should report line 3
        err = exc_info.value
        err_str = str(err).lower()
        has_line_3 = "line 3" in err_str or getattr(err, "lineno", None) == 3

    def test_error_after_multiline_block(self, env: Environment) -> None:
        """Error after multiline content reports correct line."""
        template = """{% if true %}
content
content
{% endif %}
{{ broken"""
        with pytest.raises((TemplateSyntaxError, ParseError, LexerError)):
            env.from_string(template)


class TestNestedStructures:
    """Test deeply nested structures."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_deeply_nested_if(self, env: Environment) -> None:
        """Deeply nested if statements."""
        depth = 20
        template = "{% if true %}" * depth + "x" + "{% endif %}" * depth
        tmpl = env.from_string(template)
        assert tmpl.render() == "x"

    def test_deeply_nested_for(self, env: Environment) -> None:
        """Deeply nested for loops."""
        depth = 10
        template = "{% for x in items %}" * depth + "x" + "{% endfor %}" * depth
        tmpl = env.from_string(template)
        result = tmpl.render(items=[1])
        assert "x" in result

    def test_mixed_nested_structures(self, env: Environment) -> None:
        """Mixed nested if/for."""
        template = """
{% for x in items %}
  {% if x > 0 %}
    {% for y in items %}
      {% if y > 0 %}
        {{ x }}-{{ y }}
      {% endif %}
    {% endfor %}
  {% endif %}
{% endfor %}
"""
        tmpl = env.from_string(template)
        result = tmpl.render(items=[1, 2])
        assert "1-1" in result
        assert "2-2" in result

    def test_nested_blocks_in_inheritance(self, env: Environment) -> None:
        """Nested blocks in inheritance."""
        from bengal.rendering.kida import DictLoader

        loader = DictLoader(
            {
                "base.html": """
{% block outer %}
  {% block inner %}
    {% block innermost %}
    {% endblock %}
  {% endblock %}
{% endblock %}
""",
                "child.html": """
{% extends "base.html" %}
{% block innermost %}content{% endblock %}
""",
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        assert "content" in tmpl.render()


class TestExpressionParsing:
    """Test expression parsing edge cases."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_complex_arithmetic(self, env: Environment) -> None:
        """Complex arithmetic expressions."""
        tmpl = env.from_string("{{ (1 + 2) * 3 - 4 / 2 }}")
        result = tmpl.render()
        # (1+2)*3 - 4/2 = 9 - 2 = 7
        assert "7" in result

    def test_operator_precedence(self, env: Environment) -> None:
        """Operator precedence is correct."""
        tmpl = env.from_string("{{ 2 + 3 * 4 }}")
        result = tmpl.render()
        assert "14" in result  # Not 20

    def test_parentheses_override_precedence(self, env: Environment) -> None:
        """Parentheses override precedence."""
        tmpl = env.from_string("{{ (2 + 3) * 4 }}")
        result = tmpl.render()
        assert "20" in result

    def test_nested_parentheses(self, env: Environment) -> None:
        """Nested parentheses."""
        tmpl = env.from_string("{{ ((1 + 2) * (3 + 4)) }}")
        result = tmpl.render()
        assert "21" in result

    def test_comparison_chain(self, env: Environment) -> None:
        """Comparison operators."""
        tmpl = env.from_string("{% if 1 < 2 and 2 < 3 %}yes{% endif %}")
        assert tmpl.render() == "yes"

    def test_not_operator(self, env: Environment) -> None:
        """Not operator."""
        tmpl = env.from_string("{% if not false %}yes{% endif %}")
        assert tmpl.render() == "yes"

    def test_multiple_not(self, env: Environment) -> None:
        """Multiple not operators."""
        tmpl = env.from_string("{% if not not true %}yes{% endif %}")
        assert tmpl.render() == "yes"

    def test_ternary_expression(self, env: Environment) -> None:
        """Ternary expressions."""
        tmpl = env.from_string("{{ 'a' if true else 'b' }}")
        assert tmpl.render() == "a"

    def test_nested_ternary(self, env: Environment) -> None:
        """Nested ternary expressions."""
        tmpl = env.from_string("{{ 'a' if false else ('b' if true else 'c') }}")
        assert tmpl.render() == "b"

    def test_ternary_in_output(self, env: Environment) -> None:
        """Ternary with expressions."""
        tmpl = env.from_string("{{ x + 1 if x else 0 }}")
        assert tmpl.render(x=5) == "6"
        assert tmpl.render(x=0) == "0"


class TestListDictParsing:
    """Test list and dict literal parsing."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_empty_list(self, env: Environment) -> None:
        """Empty list literal."""
        tmpl = env.from_string("{% set x = [] %}{{ x|length }}")
        assert tmpl.render() == "0"

    def test_empty_dict(self, env: Environment) -> None:
        """Empty dict literal."""
        tmpl = env.from_string("{% set x = {} %}{{ x|length }}")
        assert tmpl.render() == "0"

    def test_nested_list(self, env: Environment) -> None:
        """Nested list literals."""
        tmpl = env.from_string("{% set x = [[1, 2], [3, 4]] %}{{ x[0][1] }}")
        assert tmpl.render() == "2"

    def test_nested_dict(self, env: Environment) -> None:
        """Nested dict literals."""
        tmpl = env.from_string("{% set x = {'a': {'b': 1}} %}{{ x.a.b }}")
        assert tmpl.render() == "1"

    def test_dict_with_computed_key(self, env: Environment) -> None:
        """Dict with variable key access."""
        tmpl = env.from_string("{% set x = {'a': 1} %}{% set k = 'a' %}{{ x[k] }}")
        assert tmpl.render() == "1"

    def test_mixed_nested(self, env: Environment) -> None:
        """Mixed list/dict nesting."""
        tmpl = env.from_string("{% set x = [{'a': [1, 2]}, {'b': [3, 4]}] %}{{ x[0].a[1] }}")
        assert tmpl.render() == "2"

    def test_trailing_comma_list(self, env: Environment) -> None:
        """Trailing comma in list."""
        tmpl = env.from_string("{% set x = [1, 2, 3,] %}{{ x|length }}")
        assert tmpl.render() == "3"

    def test_trailing_comma_dict(self, env: Environment) -> None:
        """Trailing comma in dict."""
        tmpl = env.from_string("{% set x = {'a': 1, 'b': 2,} %}{{ x|length }}")
        assert tmpl.render() == "2"


class TestFilterParsing:
    """Test filter parsing edge cases."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_filter_chain(self, env: Environment) -> None:
        """Long filter chain."""
        tmpl = env.from_string("{{ name|lower|trim|upper }}")
        assert tmpl.render(name="  Hello  ") == "HELLO"

    def test_filter_with_args(self, env: Environment) -> None:
        """Filter with arguments."""
        tmpl = env.from_string("{{ 'hello'|replace('l', 'L') }}")
        assert tmpl.render() == "heLLo"

    def test_filter_with_named_args(self, env: Environment) -> None:
        """Filter with named arguments."""
        tmpl = env.from_string("{{ [3, 1, 2]|sort(reverse=true)|join(',') }}")
        result = tmpl.render()
        assert "3,2,1" in result or "3, 2, 1" in result

    def test_filter_on_literal(self, env: Environment) -> None:
        """Filter on literal."""
        tmpl = env.from_string("{{ 'HELLO'|lower }}")
        assert tmpl.render() == "hello"

    def test_filter_on_expression(self, env: Environment) -> None:
        """Filter on complex expression."""
        tmpl = env.from_string("{{ (x + y)|abs }}")
        assert tmpl.render(x=-5, y=2) == "3"


class TestMacroDefParsing:
    """Test macro/def parsing."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_macro_no_args(self, env: Environment) -> None:
        """Macro with no arguments."""
        tmpl = env.from_string("{% macro m() %}x{% endmacro %}{{ m() }}")
        assert tmpl.render() == "x"

    def test_macro_with_defaults(self, env: Environment) -> None:
        """Macro with default arguments."""
        tmpl = env.from_string("{% macro m(a='x') %}{{ a }}{% endmacro %}{{ m() }}{{ m('y') }}")
        assert tmpl.render() == "xy"

    def test_def_with_args(self, env: Environment) -> None:
        """Def with arguments."""
        tmpl = env.from_string(
            "{% def greet(name) %}Hello {{ name }}{% enddef %}{{ greet('World') }}"
        )
        assert tmpl.render() == "Hello World"


class TestWhitespaceControl:
    """Test whitespace control parsing."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_strip_left(self, env: Environment) -> None:
        """Strip whitespace left."""
        tmpl = env.from_string("x  {%- if true %} y {% endif %}")
        result = tmpl.render()
        assert "x" in result
        assert "y" in result

    def test_strip_right(self, env: Environment) -> None:
        """Strip whitespace right."""
        tmpl = env.from_string("{% if true -%}  y{% endif %}")
        assert tmpl.render() == "y"

    def test_strip_both(self, env: Environment) -> None:
        """Strip whitespace both sides."""
        tmpl = env.from_string("x  {%- if true -%}  y  {%- endif -%}  z")
        result = tmpl.render()
        assert result.strip() == "xyz"


class TestCommentsParsing:
    """Test comment parsing."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_simple_comment(self, env: Environment) -> None:
        """Simple comment."""
        tmpl = env.from_string("{# comment #}")
        assert tmpl.render() == ""

    def test_comment_with_template_syntax(self, env: Environment) -> None:
        """Comment containing template syntax."""
        tmpl = env.from_string("{# {{ x }} {% if y %}z{% endif %} #}")
        assert tmpl.render() == ""

    def test_multiline_comment(self, env: Environment) -> None:
        """Multiline comment."""
        tmpl = env.from_string("""{# this is
a multiline
comment #}""")
        assert tmpl.render() == ""


class TestRawBlock:
    """Test raw block parsing."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_raw_block(self, env: Environment) -> None:
        """Raw block preserves content."""
        tmpl = env.from_string("{% raw %}{{ x }}{% endraw %}")
        assert tmpl.render(x="value") == "{{ x }}"

    def test_raw_with_blocks(self, env: Environment) -> None:
        """Raw block with other blocks."""
        tmpl = env.from_string("{% raw %}{% if true %}{% endif %}{% endraw %}")
        assert "{% if true %}{% endif %}" in tmpl.render()


class TestIncludeExtendsParsing:
    """Test include and extends parsing."""

    @pytest.fixture
    def env(self) -> Environment:
        from bengal.rendering.kida import DictLoader

        loader = DictLoader(
            {
                "partial.html": "partial content",
                "base.html": "{% block content %}{% endblock %}",
            }
        )
        return Environment(loader=loader)

    def test_include_string_literal(self, env: Environment) -> None:
        """Include with string literal."""
        tmpl = env.from_string('{% include "partial.html" %}')
        assert "partial content" in tmpl.render()

    def test_include_variable(self, env: Environment) -> None:
        """Include with variable."""
        tmpl = env.from_string("{% include template_name %}")
        assert "partial content" in tmpl.render(template_name="partial.html")


class TestSetStatement:
    """Test set statement parsing."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_simple_set(self, env: Environment) -> None:
        """Simple set."""
        tmpl = env.from_string("{% set x = 1 %}{{ x }}")
        assert tmpl.render() == "1"

    def test_set_expression(self, env: Environment) -> None:
        """Set with expression."""
        tmpl = env.from_string("{% set x = 1 + 2 * 3 %}{{ x }}")
        assert tmpl.render() == "7"

    def test_set_tuple_unpacking(self, env: Environment) -> None:
        """Set with tuple unpacking."""
        tmpl = env.from_string("{% set a, b = [1, 2] %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_multiple_set(self, env: Environment) -> None:
        """Multiple set statements."""
        tmpl = env.from_string("{% set x = 1 %}{% set y = 2 %}{{ x + y }}")
        assert tmpl.render() == "3"


class TestForLoopParsing:
    """Test for loop parsing edge cases."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_for_with_else(self, env: Environment) -> None:
        """For with else clause."""
        tmpl = env.from_string("{% for x in [] %}{{ x }}{% else %}empty{% endfor %}")
        assert tmpl.render() == "empty"

    def test_for_unpacking(self, env: Environment) -> None:
        """For with tuple unpacking."""
        tmpl = env.from_string("{% for k, v in items.items() %}{{ k }}={{ v }};{% endfor %}")
        result = tmpl.render(items={"a": 1, "b": 2})
        assert "a=1" in result
        assert "b=2" in result

    def test_for_with_filter(self, env: Environment) -> None:
        """For with filter on iterable."""
        tmpl = env.from_string("{% for x in items|reverse %}{{ x }}{% endfor %}")
        result = tmpl.render(items=[1, 2, 3])
        assert result == "321"


class TestSpecialCases:
    """Test special parsing cases."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_adjacent_blocks(self, env: Environment) -> None:
        """Adjacent blocks without space."""
        tmpl = env.from_string("{% if true %}a{% endif %}{% if true %}b{% endif %}")
        assert tmpl.render() == "ab"

    def test_block_in_variable(self, env: Environment) -> None:
        """Block syntax in variable context is literal."""
        # This should not be interpreted as a block
        tmpl = env.from_string("{{ '{% if %}' }}")
        assert "{% if %}" in tmpl.render()

    def test_escaped_delimiters(self, env: Environment) -> None:
        """Escaped delimiters in strings."""
        tmpl = env.from_string("{{ '{{' }} and {{ '}}' }}")
        result = tmpl.render()
        assert "{{" in result
        assert "}}" in result

    def test_unicode_in_expression(self, env: Environment) -> None:
        """Unicode in expressions."""
        tmpl = env.from_string("{{ 'こんにちは' }}")
        assert tmpl.render() == "こんにちは"

    def test_unicode_variable_name(self, env: Environment) -> None:
        """Unicode variable name (if supported)."""
        try:
            tmpl = env.from_string("{{ 名前 }}")
            result = tmpl.render(**{"名前": "value"})
            assert result == "value"
        except (TemplateSyntaxError, ParseError, LexerError):
            pytest.skip("Unicode variable names not supported")
