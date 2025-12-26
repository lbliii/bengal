"""Tests for multi-set syntax: {% set a = 1, b = 2 %}.

Multi-set syntax allows comma-separated independent variable assignments
in a single {% set %} block, reducing template verbosity.

Syntax:
    {% set name1 = expr1, name2 = expr2, name3 = expr3 %}

With line breaks:
    {% set
        name1 = expr1,
        name2 = expr2,
        name3 = expr3
    %}

Trailing comma is allowed for easier editing.

Disambiguation rules:
    - {% set a = 1, b = 2 %} → multi-set (two vars)
    - {% set a = 1, 2, 3 %} → single var with tuple value
    - {% set a, b = 1, 2 %} → tuple unpacking (unchanged)
"""

import pytest

from bengal.rendering.kida import Environment


class TestMultiSetSyntax:
    """Test comma-separated multi-set assignments."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_basic_multi_set(self, env):
        """Two variables in one set block."""
        tmpl = env.from_string("{% set a = 1, b = 2 %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_three_variables(self, env):
        """Three variables in one set block."""
        tmpl = env.from_string("{% set x = 'a', y = 'b', z = 'c' %}{{ x }}{{ y }}{{ z }}")
        assert tmpl.render() == "abc"

    def test_five_variables(self, env):
        """Five variables in one set block (common pattern)."""
        tmpl = env.from_string(
            "{% set a = 1, b = 2, c = 3, d = 4, e = 5 %}{{ a }}{{ b }}{{ c }}{{ d }}{{ e }}"
        )
        assert tmpl.render() == "12345"

    def test_with_expressions(self, env):
        """Multi-set with complex expressions."""
        tmpl = env.from_string(
            "{% set items = [1,2,3], count = items|length, first = items[0] %}"
            "{{ count }}-{{ first }}"
        )
        assert tmpl.render() == "3-1"

    def test_with_filters(self, env):
        """Multi-set with filter expressions."""
        tmpl = env.from_string(
            "{% set name = 'HELLO'|lower, length = name|length %}{{ name }}:{{ length }}"
        )
        assert tmpl.render() == "hello:5"

    def test_with_chained_filters(self, env):
        """Multi-set with chained filter expressions."""
        tmpl = env.from_string(
            "{% set text = '  hello  '|trim|upper, size = text|length %}{{ text }}:{{ size }}"
        )
        assert tmpl.render() == "HELLO:5"

    def test_multiline_format(self, env):
        """Multi-set with line breaks."""
        tmpl = env.from_string(
            """{% set
            a = 1,
            b = 2,
            c = 3
        %}{{ a }}{{ b }}{{ c }}"""
        )
        assert tmpl.render() == "123"

    def test_multiline_with_expressions(self, env):
        """Multiline multi-set with complex expressions."""
        tmpl = env.from_string(
            """{% set
            items = [1, 2, 3],
            count = items | length,
            total = items | sum
        %}items={{ count }}, total={{ total }}"""
        )
        assert tmpl.render() == "items=3, total=6"

    def test_trailing_comma(self, env):
        """Trailing comma is allowed."""
        tmpl = env.from_string("{% set a = 1, b = 2, %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_single_with_trailing_comma(self, env):
        """Single set with trailing comma."""
        tmpl = env.from_string("{% set a = 1, %}{{ a }}")
        assert tmpl.render() == "1"


class TestMultiSetBackwardCompatibility:
    """Ensure existing syntax remains unchanged."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_single_set_unchanged(self, env):
        """Single set still works."""
        tmpl = env.from_string("{% set x = 42 %}{{ x }}")
        assert tmpl.render() == "42"

    def test_single_set_with_string(self, env):
        """Single set with string value."""
        tmpl = env.from_string("{% set name = 'World' %}Hello {{ name }}")
        assert tmpl.render() == "Hello World"

    def test_single_set_with_expression(self, env):
        """Single set with expression."""
        tmpl = env.from_string("{% set result = a + b %}{{ result }}")
        assert tmpl.render(a=2, b=3) == "5"

    def test_tuple_unpacking_unchanged(self, env):
        """Tuple unpacking still works."""
        tmpl = env.from_string("{% set a, b = 1, 2 %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_tuple_unpacking_three_vars(self, env):
        """Tuple unpacking with three variables."""
        tmpl = env.from_string("{% set a, b, c = 1, 2, 3 %}{{ a }}-{{ b }}-{{ c }}")
        assert tmpl.render() == "1-2-3"

    def test_tuple_unpacking_from_list(self, env):
        """Tuple unpacking from list context variable."""
        tmpl = env.from_string("{% set a, b, c = items %}{{ a }}-{{ b }}-{{ c }}")
        assert tmpl.render(items=[1, 2, 3]) == "1-2-3"

    def test_tuple_value_unchanged(self, env):
        """Tuple as value still works."""
        tmpl = env.from_string("{% set x = 1, 2, 3 %}{{ x }}")
        assert tmpl.render() == "(1, 2, 3)"

    def test_tuple_value_two_elements(self, env):
        """Two-element tuple as value."""
        tmpl = env.from_string("{% set x = 1, 2 %}{{ x }}")
        assert tmpl.render() == "(1, 2)"


class TestMultiSetDisambiguation:
    """Test disambiguation between multi-set and tuple values."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_multi_set_two_vars(self, env):
        """a = 1, b = 2 → multi-set (two vars)."""
        tmpl = env.from_string("{% set a = 1, b = 2 %}{{ a }}|{{ b }}")
        assert tmpl.render() == "1|2"

    def test_tuple_value(self, env):
        """a = 1, 2 → single var with tuple value."""
        tmpl = env.from_string("{% set a = 1, 2 %}{{ a }}")
        assert tmpl.render() == "(1, 2)"

    def test_parenthesized_tuple(self, env):
        """a = (1, 2) → single var with explicit tuple."""
        tmpl = env.from_string("{% set a = (1, 2) %}{{ a }}")
        assert tmpl.render() == "(1, 2)"

    def test_mixed_tuple_and_scalar(self, env):
        """Multi-set with tuple value in first assignment."""
        tmpl = env.from_string("{% set x = (1, 2), y = 5 %}{{ x }}|{{ y }}")
        assert tmpl.render() == "(1, 2)|5"


class TestMultiSetNestedCommas:
    """Test disambiguation with commas inside expressions."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_list_literal_with_commas(self, env):
        """List literal commas don't trigger multi-set."""
        tmpl = env.from_string("{% set items = [1, 2, 3], count = 3 %}{{ items }}|{{ count }}")
        assert tmpl.render() == "[1, 2, 3]|3"

    def test_list_only(self, env):
        """List literal without multi-set."""
        tmpl = env.from_string("{% set items = [1, 2, 3] %}{{ items }}")
        assert tmpl.render() == "[1, 2, 3]"

    def test_dict_literal_with_commas(self, env):
        """Dict literal commas don't trigger multi-set."""
        tmpl = env.from_string("{% set d = {'a': 1, 'b': 2}, x = 5 %}{{ d['a'] }}|{{ x }}")
        assert tmpl.render() == "1|5"

    def test_dict_only(self, env):
        """Dict literal without multi-set."""
        tmpl = env.from_string("{% set d = {'a': 1, 'b': 2} %}{{ d['a'] }}-{{ d['b'] }}")
        assert tmpl.render() == "1-2"

    def test_function_call_with_commas(self, env):
        """Function call commas don't trigger multi-set."""
        tmpl = env.from_string(
            "{% set result = range(1, 5) | list, count = 4 %}{{ result }}|{{ count }}"
        )
        assert tmpl.render() == "[1, 2, 3, 4]|4"

    def test_nested_parens_with_commas(self, env):
        """Nested parentheses with commas work correctly."""
        tmpl = env.from_string("{% set a = (1 + 2), b = (3, 4) %}{{ a }}|{{ b }}")
        assert tmpl.render() == "3|(3, 4)"

    def test_filter_with_comma_args(self, env):
        """Filter with comma args doesn't trigger multi-set."""
        tmpl = env.from_string(
            "{% set x = 'hello' | replace('l', 'L'), y = 'world' %}{{ x }}|{{ y }}"
        )
        assert tmpl.render() == "heLLo|world"

    def test_conditional_with_tuples(self, env):
        """Ternary with tuples works correctly."""
        tmpl = env.from_string("{% set x = (1, 2) if true else (3, 4), y = 5 %}{{ x }}|{{ y }}")
        assert tmpl.render() == "(1, 2)|5"

    def test_nested_list_in_multi_set(self, env):
        """Nested list in multi-set."""
        tmpl = env.from_string(
            "{% set matrix = [[1, 2], [3, 4]], rows = 2 %}{{ matrix[0] }}|{{ rows }}"
        )
        assert tmpl.render() == "[1, 2]|2"


class TestMultiSetWithDefaultFilter:
    """Test common pattern: params extraction with defaults."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_params_extraction_with_get(self, env):
        """Extract params using .get() for defaults."""
        tmpl = env.from_string(
            """{% set
                layout = params.get('layout', 'grid'),
                count = params.get('count', 10),
                show = params.get('show', true)
            %}{{ layout }}-{{ count }}-{{ show }}"""
        )
        result = tmpl.render(params={}).strip()
        assert result == "grid-10-True"

    def test_params_extraction_partial_with_get(self, env):
        """Extract params with defaults when some params provided."""
        tmpl = env.from_string(
            """{% set
                layout = params.get('layout', 'grid'),
                count = params.get('count', 10)
            %}{{ layout }}-{{ count }}"""
        )
        result = tmpl.render(params={"layout": "list"}).strip()
        assert result == "list-10"

    def test_params_extraction_all(self, env):
        """Extract params when all provided (no defaults needed)."""
        tmpl = env.from_string(
            """{% set
                layout = params.layout,
                count = params.count
            %}{{ layout }}-{{ count }}"""
        )
        result = tmpl.render(params={"layout": "card", "count": 5}).strip()
        assert result == "card-5"

    def test_default_filter_with_none(self, env):
        """Test default filter works with explicit None values in multi-set."""
        tmpl = env.from_string(
            """{% set
                name = value | default('fallback'),
                other = 'other'
            %}{{ name }}-{{ other }}"""
        )
        result = tmpl.render(value=None).strip()
        assert result == "fallback-other"

    def test_default_filter_with_undefined(self, env):
        """Test default filter works with undefined variables in multi-set."""
        tmpl = env.from_string(
            """{% set
                name = undefined_var | default('fallback'),
                other = 'other'
            %}{{ name }}-{{ other }}"""
        )
        result = tmpl.render().strip()
        assert result == "fallback-other"


class TestMultiSetWithContextVariables:
    """Test multi-set referencing context variables."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_reference_previous_in_same_block(self, env):
        """Variables set earlier in multi-set can be referenced later."""
        tmpl = env.from_string("{% set items = [1, 2, 3], count = items | length %}{{ count }}")
        assert tmpl.render() == "3"

    def test_reference_context_variable(self, env):
        """Multi-set can reference context variables."""
        tmpl = env.from_string(
            "{% set doubled = value * 2, tripled = value * 3 %}{{ doubled }}-{{ tripled }}"
        )
        assert tmpl.render(value=5) == "10-15"

    def test_complex_chain(self, env):
        """Complex chain of references in multi-set."""
        tmpl = env.from_string(
            "{% set a = 1, b = a + 1, c = b + 1, d = c + 1 %}{{ a }}{{ b }}{{ c }}{{ d }}"
        )
        assert tmpl.render() == "1234"


class TestMultiSetEdgeCases:
    """Edge cases and error handling."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_empty_not_allowed(self, env):
        """Empty set block is an error."""
        with pytest.raises(Exception):  # TemplateSyntaxError
            env.from_string("{% set %}")

    def test_missing_value(self, env):
        """Missing value after = is an error."""
        with pytest.raises(Exception):
            env.from_string("{% set a = %}")

    def test_missing_equals(self, env):
        """Missing = is an error."""
        with pytest.raises(Exception):
            env.from_string("{% set a 1 %}")

    def test_complex_expression_chain(self, env):
        """Complex chained expression with multi-set."""
        tmpl = env.from_string(
            "{% set x = items | first | upper, y = items | last | lower %}{{ x }}-{{ y }}"
        )
        assert tmpl.render(items=["Hello", "World"]) == "HELLO-world"

    def test_multiline_with_complex_expressions(self, env):
        """Multiline with complex chained expressions."""
        tmpl = env.from_string(
            """{% set
                entries = data.entries,
                count = entries | length,
                has_entries = count > 0
            %}{{ has_entries }}-{{ count }}"""
        )
        result = tmpl.render(data={"entries": [1, 2]}).strip()
        assert result == "True-2"

    def test_multiline_with_get_defaults(self, env):
        """Multiline with .get() for default values."""
        tmpl = env.from_string(
            """{% set
                entries = data.get('entries', []),
                count = entries | length,
                has_entries = count > 0
            %}{{ has_entries }}-{{ count }}"""
        )
        # With empty data
        result1 = tmpl.render(data={}).strip()
        assert result1 == "False-0"
        # With entries
        result2 = tmpl.render(data={"entries": [1, 2]}).strip()
        assert result2 == "True-2"

    def test_boolean_values(self, env):
        """Multi-set with boolean values."""
        tmpl = env.from_string(
            "{% set active = true, disabled = false %}{{ active }}-{{ disabled }}"
        )
        assert tmpl.render() == "True-False"

    def test_none_values(self, env):
        """Multi-set with none values."""
        tmpl = env.from_string("{% set a = none, b = 'value' %}{{ a }}-{{ b }}")
        assert tmpl.render() == "None-value"

    def test_empty_string_values(self, env):
        """Multi-set with empty string values."""
        tmpl = env.from_string("{% set a = '', b = 'text' %}[{{ a }}]-{{ b }}")
        assert tmpl.render() == "[]-text"

    def test_zero_values(self, env):
        """Multi-set with zero values."""
        tmpl = env.from_string("{% set a = 0, b = 1 %}{{ a }}-{{ b }}")
        assert tmpl.render() == "0-1"


class TestMultiSetInControlFlow:
    """Test multi-set inside control flow blocks."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_inside_if_block(self, env):
        """Multi-set inside if block."""
        tmpl = env.from_string("{% if true %}{% set a = 1, b = 2 %}{{ a }}-{{ b }}{% endif %}")
        assert tmpl.render() == "1-2"

    def test_inside_for_loop(self, env):
        """Multi-set inside for loop."""
        tmpl = env.from_string(
            "{% for i in [1,2] %}{% set x = i * 2, y = i * 3 %}{{ x }},{{ y }};{% endfor %}"
        )
        assert tmpl.render() == "2,3;4,6;"

    def test_multiple_multi_sets(self, env):
        """Multiple multi-set blocks in same template."""
        tmpl = env.from_string(
            "{% set a = 1, b = 2 %}{% set c = 3, d = 4 %}{{ a }}{{ b }}{{ c }}{{ d }}"
        )
        assert tmpl.render() == "1234"
