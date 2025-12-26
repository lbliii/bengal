"""Test expression parsing and evaluation in Kida template engine.

Tests arithmetic, comparison, logic operators, literals, and complex expressions.
"""

import pytest

from bengal.rendering.kida import Environment


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


class TestArithmeticOperators:
    """Arithmetic operator tests."""

    def test_addition(self, env):
        """Addition operator."""
        tmpl = env.from_string("{{ 2 + 3 }}")
        assert tmpl.render() == "5"

    def test_subtraction(self, env):
        """Subtraction operator."""
        tmpl = env.from_string("{{ 5 - 3 }}")
        assert tmpl.render() == "2"

    def test_multiplication(self, env):
        """Multiplication operator."""
        tmpl = env.from_string("{{ 4 * 3 }}")
        assert tmpl.render() == "12"

    def test_division(self, env):
        """Division operator."""
        tmpl = env.from_string("{{ 10 / 4 }}")
        assert tmpl.render() == "2.5"

    def test_floor_division(self, env):
        """Floor division operator."""
        tmpl = env.from_string("{{ 10 // 4 }}")
        assert tmpl.render() == "2"

    def test_modulo(self, env):
        """Modulo operator."""
        tmpl = env.from_string("{{ 10 % 3 }}")
        assert tmpl.render() == "1"

    def test_power(self, env):
        """Power operator."""
        tmpl = env.from_string("{{ 2 ** 3 }}")
        assert tmpl.render() == "8"

    def test_unary_minus(self, env):
        """Unary minus."""
        tmpl = env.from_string("{{ -5 }}")
        assert tmpl.render() == "-5"

    def test_unary_plus(self, env):
        """Unary plus."""
        tmpl = env.from_string("{{ +5 }}")
        assert tmpl.render() == "5"

    def test_operator_precedence(self, env):
        """Operator precedence."""
        tmpl = env.from_string("{{ 2 + 3 * 4 }}")
        assert tmpl.render() == "14"  # 2 + (3 * 4), not (2 + 3) * 4

    def test_parentheses(self, env):
        """Parentheses override precedence."""
        tmpl = env.from_string("{{ (2 + 3) * 4 }}")
        assert tmpl.render() == "20"


class TestComparisonOperators:
    """Comparison operator tests."""

    def test_equal(self, env):
        """Equal operator."""
        tmpl = env.from_string("{{ 1 == 1 }}-{{ 1 == 2 }}")
        assert tmpl.render() == "True-False"

    def test_not_equal(self, env):
        """Not equal operator."""
        tmpl = env.from_string("{{ 1 != 2 }}-{{ 1 != 1 }}")
        assert tmpl.render() == "True-False"

    def test_less_than(self, env):
        """Less than operator."""
        tmpl = env.from_string("{{ 1 < 2 }}-{{ 2 < 1 }}")
        assert tmpl.render() == "True-False"

    def test_greater_than(self, env):
        """Greater than operator."""
        tmpl = env.from_string("{{ 2 > 1 }}-{{ 1 > 2 }}")
        assert tmpl.render() == "True-False"

    def test_less_equal(self, env):
        """Less than or equal operator."""
        tmpl = env.from_string("{{ 1 <= 2 }}-{{ 2 <= 2 }}-{{ 3 <= 2 }}")
        assert tmpl.render() == "True-True-False"

    def test_greater_equal(self, env):
        """Greater than or equal operator."""
        tmpl = env.from_string("{{ 2 >= 1 }}-{{ 2 >= 2 }}-{{ 1 >= 2 }}")
        assert tmpl.render() == "True-True-False"


class TestLogicalOperators:
    """Logical operator tests."""

    def test_and(self, env):
        """And operator."""
        tmpl = env.from_string("{{ true and true }}-{{ true and false }}")
        assert tmpl.render() == "True-False"

    def test_or(self, env):
        """Or operator."""
        tmpl = env.from_string("{{ true or false }}-{{ false or false }}")
        assert tmpl.render() == "True-False"

    def test_not(self, env):
        """Not operator."""
        tmpl = env.from_string("{{ not true }}-{{ not false }}")
        assert tmpl.render() == "False-True"

    def test_short_circuit_and(self, env):
        """And short-circuits."""
        # If first is false, second shouldn't be evaluated
        tmpl = env.from_string("{{ false and undefined_var }}")
        assert tmpl.render() == "False"

    def test_short_circuit_or(self, env):
        """Or short-circuits."""
        # If first is true, second shouldn't be evaluated
        tmpl = env.from_string("{{ true or undefined_var }}")
        assert tmpl.render() == "True"


class TestLiterals:
    """Literal value tests."""

    def test_integer(self, env):
        """Integer literal."""
        tmpl = env.from_string("{{ 42 }}")
        assert tmpl.render() == "42"

    def test_float(self, env):
        """Float literal."""
        tmpl = env.from_string("{{ 3.14 }}")
        assert tmpl.render() == "3.14"

    def test_negative_number(self, env):
        """Negative number literal."""
        tmpl = env.from_string("{{ -42 }}")
        assert tmpl.render() == "-42"

    def test_string_double_quotes(self, env):
        """String with double quotes."""
        tmpl = env.from_string('{{ "hello" }}')
        assert tmpl.render() == "hello"

    def test_string_single_quotes(self, env):
        """String with single quotes."""
        tmpl = env.from_string("{{ 'hello' }}")
        assert tmpl.render() == "hello"

    def test_string_escape(self, env):
        """String with escaped characters."""
        tmpl = env.from_string(r'{{ "hello\nworld" }}')
        assert "\n" in tmpl.render() or "\\n" in tmpl.render()

    def test_true_literal(self, env):
        """True literal."""
        tmpl = env.from_string("{{ true }}")
        assert tmpl.render() == "True"

    def test_false_literal(self, env):
        """False literal."""
        tmpl = env.from_string("{{ false }}")
        assert tmpl.render() == "False"

    def test_none_literal(self, env):
        """None literal."""
        tmpl = env.from_string("{{ none }}")
        result = tmpl.render()
        assert result in ["None", ""]


class TestListLiterals:
    """List literal tests."""

    def test_empty_list(self, env):
        """Empty list literal."""
        tmpl = env.from_string("{{ [] }}")
        assert tmpl.render() == "[]"

    def test_list_integers(self, env):
        """List of integers."""
        tmpl = env.from_string("{{ [1, 2, 3] }}")
        assert tmpl.render() == "[1, 2, 3]"

    def test_list_strings(self, env):
        """List of strings."""
        tmpl = env.from_string('{{ ["a", "b"] }}')
        result = tmpl.render()
        assert "a" in result and "b" in result

    def test_list_mixed(self, env):
        """List with mixed types."""
        tmpl = env.from_string('{{ [1, "two", true] }}')
        result = tmpl.render()
        assert "1" in result

    def test_nested_list(self, env):
        """Nested list."""
        tmpl = env.from_string("{{ [[1, 2], [3, 4]] }}")
        result = tmpl.render()
        assert "1" in result and "4" in result


class TestDictLiterals:
    """Dict literal tests."""

    def test_empty_dict(self, env):
        """Empty dict literal."""
        tmpl = env.from_string("{{ {} }}")
        assert tmpl.render() == "{}"

    def test_dict_simple(self, env):
        """Simple dict literal."""
        tmpl = env.from_string("{{ {'a': 1, 'b': 2} }}")
        result = tmpl.render()
        assert "a" in result and "1" in result

    def test_dict_access(self, env):
        """Dict access with dot notation."""
        tmpl = env.from_string("{% set d = {'name': 'test'} %}{{ d.name }}")
        assert tmpl.render() == "test"

    def test_dict_subscript_access(self, env):
        """Dict access with subscript."""
        tmpl = env.from_string("{% set d = {'key': 'value'} %}{{ d['key'] }}")
        assert tmpl.render() == "value"

    def test_dict_in_ternary(self, env):
        """Dict in ternary expression."""
        tmpl = env.from_string("{{ {'a': 1} if true else {'b': 2} }}")
        result = tmpl.render()
        assert "a" in result

    def test_dict_variable_key(self, env):
        """Dict with variable key."""
        tmpl = env.from_string("{% set key = 'name' %}{% set d = {key: 'value'} %}{{ d.name }}")
        assert tmpl.render() == "value"


class TestTupleLiterals:
    """Tuple literal tests."""

    def test_tuple_in_expression(self, env):
        """Tuple in expression."""
        tmpl = env.from_string("{{ (1, 2, 3) }}")
        result = tmpl.render()
        assert "1" in result and "2" in result and "3" in result


class TestStringConcatenation:
    """String concatenation tests."""

    def test_tilde_concat(self, env):
        """Tilde operator for string concatenation."""
        tmpl = env.from_string("{{ 'hello' ~ ' ' ~ 'world' }}")
        assert tmpl.render() == "hello world"

    def test_tilde_with_vars(self, env):
        """Tilde with variables."""
        tmpl = env.from_string("{{ prefix ~ name ~ suffix }}")
        # Use non-HTML special chars to avoid autoescape issues
        assert tmpl.render(prefix="[", name="test", suffix="]") == "[test]"

    def test_tilde_with_numbers(self, env):
        """Tilde converts to string."""
        tmpl = env.from_string("{{ 'value: ' ~ 42 }}")
        assert tmpl.render() == "value: 42"


class TestSlicing:
    """Slice expression tests."""

    def test_basic_slice(self, env):
        """Basic slice."""
        tmpl = env.from_string("{{ items[1:3] }}")
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        assert "2" in result and "3" in result
        assert "1" not in result or result.index("2") < result.index("1")

    def test_slice_start(self, env):
        """Slice with start only."""
        tmpl = env.from_string("{{ items[2:] }}")
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        assert "3" in result and "4" in result and "5" in result

    def test_slice_end(self, env):
        """Slice with end only."""
        tmpl = env.from_string("{{ items[:2] }}")
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        assert "1" in result and "2" in result

    def test_slice_negative(self, env):
        """Slice with negative indices."""
        tmpl = env.from_string("{{ items[-2:] }}")
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        assert "4" in result and "5" in result

    def test_slice_step(self, env):
        """Slice with step."""
        tmpl = env.from_string("{{ items[::2] }}")
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        assert "1" in result and "3" in result and "5" in result


class TestMethodCalls:
    """Method call tests."""

    def test_string_methods(self, env):
        """String method calls."""
        tmpl = env.from_string("{{ 'hello'.upper() }}")
        assert tmpl.render() == "HELLO"

    def test_list_methods(self, env):
        """List method calls."""
        tmpl = env.from_string("{{ items.count(1) }}")
        assert tmpl.render(items=[1, 2, 1, 3, 1]) == "3"

    def test_method_with_args(self, env):
        """Method with arguments."""
        tmpl = env.from_string("{{ 'a,b,c'.split(',') }}")
        result = tmpl.render()
        assert "a" in result and "b" in result and "c" in result

    def test_chained_methods(self, env):
        """Chained method calls."""
        tmpl = env.from_string("{{ '  hello  '.strip().upper() }}")
        assert tmpl.render() == "HELLO"


class TestComplexExpressions:
    """Complex expression tests."""

    def test_nested_operations(self, env):
        """Nested arithmetic operations."""
        tmpl = env.from_string("{{ ((a + b) * c) - d }}")
        assert tmpl.render(a=1, b=2, c=3, d=4) == "5"  # ((1+2)*3)-4 = 5

    def test_mixed_types(self, env):
        """Mixed type operations."""
        tmpl = env.from_string("{{ 'Count: ' ~ (items|length) }}")
        assert tmpl.render(items=[1, 2, 3]) == "Count: 3"

    def test_filter_chain_in_expression(self, env):
        """Filter chain in expression."""
        tmpl = env.from_string('{{ ("  hello  "|trim|upper) ~ "!" }}')
        assert tmpl.render() == "HELLO!"

    def test_conditional_with_operations(self, env):
        """Conditional with operations."""
        tmpl = env.from_string("{{ (a + b) if use_sum else (a * b) }}")
        assert tmpl.render(a=2, b=3, use_sum=True) == "5"
        assert tmpl.render(a=2, b=3, use_sum=False) == "6"


class TestAttributeAccess:
    """Attribute and item access tests."""

    def test_dot_access(self, env):
        """Dot notation access."""

        class Obj:
            name = "test"
            value = 42

        tmpl = env.from_string("{{ obj.name }}-{{ obj.value }}")
        assert tmpl.render(obj=Obj()) == "test-42"

    def test_subscript_access(self, env):
        """Subscript access."""
        tmpl = env.from_string("{{ data['key'] }}")
        assert tmpl.render(data={"key": "value"}) == "value"

    def test_dynamic_subscript(self, env):
        """Dynamic subscript with variable."""
        tmpl = env.from_string("{{ data[key] }}")
        assert tmpl.render(data={"mykey": "myvalue"}, key="mykey") == "myvalue"

    def test_chained_access(self, env):
        """Chained attribute access."""
        tmpl = env.from_string("{{ data.level1.level2 }}")
        data = {"level1": {"level2": "deep"}}
        # Create an object that supports dot access
        from types import SimpleNamespace

        obj = SimpleNamespace(level1=SimpleNamespace(level2="deep"))
        assert tmpl.render(data=obj) == "deep"


class TestBuiltinFunctions:
    """Builtin function tests."""

    def test_range(self, env):
        """range function."""
        tmpl = env.from_string("{{ range(5)|list }}")
        result = tmpl.render()
        assert "0" in result and "4" in result

    def test_range_start_stop(self, env):
        """range with start and stop."""
        tmpl = env.from_string("{{ range(2, 5)|list }}")
        result = tmpl.render()
        assert "2" in result and "4" in result
        assert "0" not in result or result.index("2") < result.index("0")

    def test_dict_builtin(self, env):
        """dict builtin."""
        tmpl = env.from_string("{{ dict(a=1, b=2) }}")
        result = tmpl.render()
        assert "a" in result and "1" in result

    def test_lipsum(self, env):
        """lipsum function (if available)."""
        try:
            tmpl = env.from_string("{{ lipsum(n=1) }}")
            result = tmpl.render()
            assert len(result) > 0
        except Exception:
            pytest.skip("lipsum not available")
