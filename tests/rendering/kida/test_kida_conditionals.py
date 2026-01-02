"""Test conditional functionality in Kida template engine.

Based on Jinja2's test_core_tags.py TestIfCondition class.
Tests if/elif/else, boolean expressions, and edge cases.
"""

import pytest

from bengal.rendering.kida import Environment


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


class TestIfCondition:
    """Basic if/elif/else tests."""

    def test_simple_true(self, env):
        """Simple if true."""
        tmpl = env.from_string("{% if true %}yes{% endif %}")
        assert tmpl.render() == "yes"

    def test_simple_false(self, env):
        """Simple if false."""
        tmpl = env.from_string("{% if false %}yes{% endif %}")
        assert tmpl.render() == ""

    def test_else(self, env):
        """If with else."""
        tmpl = env.from_string("{% if false %}yes{% else %}no{% endif %}")
        assert tmpl.render() == "no"

    def test_elif(self, env):
        """If with elif."""
        tmpl = env.from_string("{% if false %}A{% elif true %}B{% else %}C{% endif %}")
        assert tmpl.render() == "B"

    def test_elif_chain(self, env):
        """Multiple elif."""
        tmpl = env.from_string(
            "{% if a == 1 %}ONE{% elif a == 2 %}TWO{% elif a == 3 %}THREE{% else %}OTHER{% endif %}"
        )
        assert tmpl.render(a=1) == "ONE"
        assert tmpl.render(a=2) == "TWO"
        assert tmpl.render(a=3) == "THREE"
        assert tmpl.render(a=4) == "OTHER"

    def test_empty_bodies(self, env):
        """Empty if/else bodies."""
        tmpl = env.from_string("[{% if true %}{% else %}{% endif %}]")
        assert tmpl.render() == "[]"

    def test_complete(self, env):
        """Complete if/elif/else."""
        tmpl = env.from_string("{% if a %}A{% elif b %}B{% elif c == d %}C{% else %}D{% endif %}")
        assert tmpl.render(a=0, b=False, c=42, d=42.0) == "C"


class TestBooleanExpressions:
    """Boolean operators and expressions."""

    def test_and(self, env):
        """and operator."""
        tmpl = env.from_string("{% if a and b %}yes{% endif %}")
        assert tmpl.render(a=True, b=True) == "yes"
        assert tmpl.render(a=True, b=False) == ""
        assert tmpl.render(a=False, b=True) == ""

    def test_or(self, env):
        """or operator."""
        tmpl = env.from_string("{% if a or b %}yes{% endif %}")
        assert tmpl.render(a=True, b=False) == "yes"
        assert tmpl.render(a=False, b=True) == "yes"
        assert tmpl.render(a=False, b=False) == ""

    def test_not(self, env):
        """not operator."""
        tmpl = env.from_string("{% if not a %}yes{% endif %}")
        assert tmpl.render(a=False) == "yes"
        assert tmpl.render(a=True) == ""

    def test_combined(self, env):
        """Combined boolean operators."""
        tmpl = env.from_string("{% if (a and b) or c %}yes{% endif %}")
        assert tmpl.render(a=True, b=True, c=False) == "yes"
        assert tmpl.render(a=False, b=False, c=True) == "yes"
        assert tmpl.render(a=False, b=False, c=False) == ""

    def test_not_with_and(self, env):
        """not with and."""
        tmpl = env.from_string("{% if a and not b %}yes{% endif %}")
        assert tmpl.render(a=True, b=False) == "yes"
        assert tmpl.render(a=True, b=True) == ""


class TestComparisonOperators:
    """Comparison operators."""

    def test_equal(self, env):
        """== operator."""
        tmpl = env.from_string("{% if a == b %}yes{% endif %}")
        assert tmpl.render(a=1, b=1) == "yes"
        assert tmpl.render(a=1, b=2) == ""

    def test_not_equal(self, env):
        """!= operator."""
        tmpl = env.from_string("{% if a != b %}yes{% endif %}")
        assert tmpl.render(a=1, b=2) == "yes"
        assert tmpl.render(a=1, b=1) == ""

    def test_less_than(self, env):
        """< operator."""
        tmpl = env.from_string("{% if a < b %}yes{% endif %}")
        assert tmpl.render(a=1, b=2) == "yes"
        assert tmpl.render(a=2, b=1) == ""

    def test_greater_than(self, env):
        """> operator."""
        tmpl = env.from_string("{% if a > b %}yes{% endif %}")
        assert tmpl.render(a=2, b=1) == "yes"
        assert tmpl.render(a=1, b=2) == ""

    def test_less_equal(self, env):
        """<= operator."""
        tmpl = env.from_string("{% if a <= b %}yes{% endif %}")
        assert tmpl.render(a=1, b=2) == "yes"
        assert tmpl.render(a=2, b=2) == "yes"
        assert tmpl.render(a=3, b=2) == ""

    def test_greater_equal(self, env):
        """>= operator."""
        tmpl = env.from_string("{% if a >= b %}yes{% endif %}")
        assert tmpl.render(a=2, b=1) == "yes"
        assert tmpl.render(a=2, b=2) == "yes"
        assert tmpl.render(a=1, b=2) == ""


class TestInOperator:
    """in/not in operators."""

    def test_in_list(self, env):
        """in operator with list."""
        tmpl = env.from_string("{% if item in items %}yes{% endif %}")
        assert tmpl.render(item=2, items=[1, 2, 3]) == "yes"
        assert tmpl.render(item=4, items=[1, 2, 3]) == ""

    def test_in_string(self, env):
        """in operator with string."""
        tmpl = env.from_string("{% if 'ell' in text %}yes{% endif %}")
        assert tmpl.render(text="hello") == "yes"
        assert tmpl.render(text="world") == ""

    def test_not_in(self, env):
        """not in operator."""
        tmpl = env.from_string("{% if item not in items %}yes{% endif %}")
        assert tmpl.render(item=4, items=[1, 2, 3]) == "yes"
        assert tmpl.render(item=2, items=[1, 2, 3]) == ""


class TestTernaryExpression:
    """Ternary/conditional expressions."""

    def test_basic_ternary(self, env):
        """Basic ternary expression."""
        tmpl = env.from_string("{{ 'yes' if true else 'no' }}")
        assert tmpl.render() == "yes"

    def test_ternary_with_var(self, env):
        """Ternary with variable condition."""
        tmpl = env.from_string("{{ 'active' if is_active else 'inactive' }}")
        assert tmpl.render(is_active=True) == "active"
        assert tmpl.render(is_active=False) == "inactive"

    def test_ternary_expression_values(self, env):
        """Ternary with expression values."""
        tmpl = env.from_string("{{ (a + b) if use_sum else (a * b) }}")
        assert tmpl.render(a=2, b=3, use_sum=True) == "5"
        assert tmpl.render(a=2, b=3, use_sum=False) == "6"

    def test_nested_ternary(self, env):
        """Nested ternary expressions."""
        tmpl = env.from_string("{{ 'A' if a else ('B' if b else 'C') }}")
        assert tmpl.render(a=True, b=True) == "A"
        assert tmpl.render(a=False, b=True) == "B"
        assert tmpl.render(a=False, b=False) == "C"


class TestIsTests:
    """Tests with 'is' operator."""

    def test_is_defined(self, env):
        """is defined test."""
        tmpl = env.from_string("{% if x is defined %}yes{% endif %}")
        assert tmpl.render(x=1) == "yes"
        assert tmpl.render() == ""

    def test_is_undefined(self, env):
        """is undefined test."""
        tmpl = env.from_string("{% if x is undefined %}yes{% endif %}")
        assert tmpl.render() == "yes"
        assert tmpl.render(x=1) == ""

    def test_is_none(self, env):
        """is none test."""
        tmpl = env.from_string("{% if x is none %}yes{% endif %}")
        assert tmpl.render(x=None) == "yes"
        assert tmpl.render(x=0) == ""

    def test_is_true(self, env):
        """is true test."""
        tmpl = env.from_string("{% if x is true %}yes{% endif %}")
        assert tmpl.render(x=True) == "yes"
        assert tmpl.render(x=1) == ""

    def test_is_false(self, env):
        """is false test."""
        tmpl = env.from_string("{% if x is false %}yes{% endif %}")
        assert tmpl.render(x=False) == "yes"
        assert tmpl.render(x=0) == ""

    def test_is_string(self, env):
        """is string test."""
        tmpl = env.from_string("{% if x is string %}yes{% endif %}")
        assert tmpl.render(x="hello") == "yes"
        assert tmpl.render(x=42) == ""

    def test_is_number(self, env):
        """is number test."""
        tmpl = env.from_string("{% if x is number %}yes{% endif %}")
        assert tmpl.render(x=42) == "yes"
        assert tmpl.render(x=3.14) == "yes"
        assert tmpl.render(x="42") == ""

    def test_is_sequence(self, env):
        """is sequence test."""
        tmpl = env.from_string("{% if x is sequence %}yes{% endif %}")
        assert tmpl.render(x=[1, 2, 3]) == "yes"
        assert tmpl.render(x=(1, 2, 3)) == "yes"
        assert tmpl.render(x="abc") == "yes"

    def test_is_mapping(self, env):
        """is mapping test."""
        tmpl = env.from_string("{% if x is mapping %}yes{% endif %}")
        assert tmpl.render(x={"a": 1}) == "yes"
        assert tmpl.render(x=[1, 2]) == ""

    def test_is_iterable(self, env):
        """is iterable test."""
        tmpl = env.from_string("{% if x is iterable %}yes{% endif %}")
        assert tmpl.render(x=[1, 2, 3]) == "yes"
        assert tmpl.render(x="abc") == "yes"
        assert tmpl.render(x=42) == ""

    def test_is_callable(self, env):
        """is callable test."""
        tmpl = env.from_string("{% if x is callable %}yes{% endif %}")
        assert tmpl.render(x=len) == "yes"
        assert tmpl.render(x=42) == ""

    def test_is_even(self, env):
        """is even test."""
        tmpl = env.from_string("{% if x is even %}yes{% endif %}")
        assert tmpl.render(x=2) == "yes"
        assert tmpl.render(x=3) == ""

    def test_is_odd(self, env):
        """is odd test."""
        tmpl = env.from_string("{% if x is odd %}yes{% endif %}")
        assert tmpl.render(x=3) == "yes"
        assert tmpl.render(x=2) == ""

    def test_is_not(self, env):
        """is not test."""
        tmpl = env.from_string("{% if x is not none %}yes{% endif %}")
        assert tmpl.render(x=1) == "yes"
        assert tmpl.render(x=None) == ""


class TestScopingWithIf:
    """Scoping behavior with if statements."""

    def test_scope_leak_with_let(self, env):
        """Variables declared with let persist across blocks."""
        tmpl = env.from_string("{% let foo = 0 %}{% if a %}{% let foo = 1 %}{% endif %}{{ foo }}")
        # In Kida, let variables persist outside the block where they're modified
        assert tmpl.render(a=True) == "1"

    def test_let_in_both_branches(self, env):
        """Let in both if and else persists."""
        tmpl = env.from_string(
            "{% let x = '' %}{% if cond %}{% let x = 'A' %}{% else %}{% let x = 'B' %}{% endif %}{{ x }}"
        )
        assert tmpl.render(cond=True) == "A"
        assert tmpl.render(cond=False) == "B"


class TestTruthyFalsy:
    """Truthy/falsy value handling."""

    def test_empty_string_falsy(self, env):
        """Empty string is falsy."""
        tmpl = env.from_string("{% if text %}yes{% else %}no{% endif %}")
        assert tmpl.render(text="") == "no"
        assert tmpl.render(text="hello") == "yes"

    def test_zero_falsy(self, env):
        """Zero is falsy."""
        tmpl = env.from_string("{% if num %}yes{% else %}no{% endif %}")
        assert tmpl.render(num=0) == "no"
        assert tmpl.render(num=1) == "yes"

    def test_empty_list_falsy(self, env):
        """Empty list is falsy."""
        tmpl = env.from_string("{% if items %}yes{% else %}no{% endif %}")
        assert tmpl.render(items=[]) == "no"
        assert tmpl.render(items=[1]) == "yes"

    def test_none_falsy(self, env):
        """None is falsy."""
        tmpl = env.from_string("{% if value %}yes{% else %}no{% endif %}")
        assert tmpl.render(value=None) == "no"
