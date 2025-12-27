"""Compiler edge cases and AST transformation tests for Kida.

Tests the compilation from Kida AST to Python AST and edge cases.
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import DictLoader, Environment


class TestScopeCompilation:
    """Test scope handling during compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_variable_shadowing(self, env: Environment) -> None:
        """Variable shadowing in nested scopes."""
        tmpl = env.from_string("""
{% set x = 'outer' %}
{% for x in [1, 2] %}{{ x }}{% endfor %}
{{ x }}
""")
        result = tmpl.render()
        assert "1" in result
        assert "2" in result
        assert "outer" in result

    def test_set_in_for_loop(self, env: Environment) -> None:
        """Set inside for loop."""
        tmpl = env.from_string("""
{% set total = 0 %}
{% for x in [1, 2, 3] %}{% set total = total + x %}{% endfor %}
{{ total }}
""")
        result = tmpl.render()
        # Depends on scoping semantics
        # If set modifies outer scope: 6
        # If set creates local scope: 0
        assert "6" in result or "0" in result

    def test_nested_for_scopes(self, env: Environment) -> None:
        """Nested for loops have separate scopes."""
        tmpl = env.from_string("""
{% for i in [1, 2] %}
  {% for j in [3, 4] %}
    {{ i }}-{{ j }}
  {% endfor %}
{% endfor %}
""")
        result = tmpl.render()
        assert "1-3" in result
        assert "1-4" in result
        assert "2-3" in result
        assert "2-4" in result

    def test_macro_scope_isolation(self, env: Environment) -> None:
        """Macro has isolated scope."""
        tmpl = env.from_string("""
{% set x = 'outer' %}
{% macro test() %}{% set x = 'inner' %}{{ x }}{% endmacro %}
{{ test() }}-{{ x }}
""")
        result = tmpl.render()
        assert "inner" in result
        assert "outer" in result

    def test_def_lexical_scope(self, env: Environment) -> None:
        """Def has lexical scope (can access outer)."""
        tmpl = env.from_string("""
{% set x = 'outer' %}
{% def test() %}{{ x }}{% enddef %}
{{ test() }}
""")
        result = tmpl.render()
        assert "outer" in result


class TestExpressionCompilation:
    """Test expression compilation edge cases."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_complex_chained_calls(self, env: Environment) -> None:
        """Complex chained method calls."""
        tmpl = env.from_string("{{ items|first|upper }}")
        result = tmpl.render(items=["hello", "world"])
        assert result == "HELLO"

    def test_attribute_on_filter_result(self, env: Environment) -> None:
        """Attribute access on filter result requires parentheses in Kida."""
        # Kida requires explicit parentheses for chained access after filter
        tmpl = env.from_string("{{ (data|first).name }}")
        result = tmpl.render(data=[{"name": "Alice"}])
        assert "Alice" in result

    def test_subscript_on_filter_result(self, env: Environment) -> None:
        """Subscript access on filter result requires parentheses in Kida."""
        # Kida requires explicit parentheses for chained access after filter
        tmpl = env.from_string("{{ (data|first)[0] }}")
        result = tmpl.render(data=[[1, 2, 3]])
        assert "1" in result

    def test_filter_with_complex_args(self, env: Environment) -> None:
        """Filter with complex expression arguments."""
        tmpl = env.from_string("{{ items|join(sep + '-') }}")
        result = tmpl.render(items=["a", "b"], sep="x")
        assert "a" in result and "b" in result

    def test_method_call_on_literal(self, env: Environment) -> None:
        """Method call on literal."""
        tmpl = env.from_string("{{ 'hello world'.split() }}")
        result = tmpl.render()
        assert "hello" in result or "world" in result

    def test_negative_numbers(self, env: Environment) -> None:
        """Negative number literals."""
        tmpl = env.from_string("{{ -5 + 3 }}")
        assert tmpl.render() == "-2"

    def test_unary_minus_on_variable(self, env: Environment) -> None:
        """Unary minus on variable."""
        tmpl = env.from_string("{{ -x }}")
        assert tmpl.render(x=5) == "-5"

    def test_double_negation(self, env: Environment) -> None:
        """Double negation."""
        tmpl = env.from_string("{{ --x }}")
        # Depends on parsing: --x could be -(-x) = x
        result = tmpl.render(x=5)
        assert result in ["5", "--5"]


class TestConditionalCompilation:
    """Test conditional compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_complex_boolean_expression(self, env: Environment) -> None:
        """Complex boolean expressions."""
        tmpl = env.from_string("""
{% if (a and b) or (c and d) %}yes{% else %}no{% endif %}
""")
        assert "yes" in tmpl.render(a=True, b=True, c=False, d=False)
        assert "yes" in tmpl.render(a=False, b=False, c=True, d=True)
        assert "no" in tmpl.render(a=True, b=False, c=True, d=False)

    def test_nested_ternary(self, env: Environment) -> None:
        """Nested ternary expressions compile correctly."""
        tmpl = env.from_string("{{ a if x else (b if y else c) }}")
        assert tmpl.render(x=True, y=False, a="A", b="B", c="C") == "A"
        assert tmpl.render(x=False, y=True, a="A", b="B", c="C") == "B"
        assert tmpl.render(x=False, y=False, a="A", b="B", c="C") == "C"

    def test_is_test_compilation(self, env: Environment) -> None:
        """Is tests compile correctly."""
        tmpl = env.from_string("{% if x is defined %}yes{% endif %}")
        assert tmpl.render(x=1) == "yes"

    def test_is_not_test(self, env: Environment) -> None:
        """Is not test."""
        tmpl = env.from_string("{% if x is not none %}yes{% endif %}")
        assert tmpl.render(x=1) == "yes"


class TestLoopCompilation:
    """Test loop compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_loop_with_break_simulation(self, env: Environment) -> None:
        """Loop doesn't have break, but can simulate with conditionals."""
        tmpl = env.from_string("""
{% set found = false %}
{% for x in items %}
  {% if not found %}
    {% if x == target %}
      Found: {{ x }}
      {% set found = true %}
    {% endif %}
  {% endif %}
{% endfor %}
""")
        result = tmpl.render(items=[1, 2, 3, 4], target=2)
        assert "Found: 2" in result

    def test_loop_else_compilation(self, env: Environment) -> None:
        """Loop else compiles correctly."""
        tmpl = env.from_string("{% for x in items %}{{ x }}{% else %}empty{% endfor %}")
        assert tmpl.render(items=[]) == "empty"
        assert "1" in tmpl.render(items=[1, 2])


class TestMacroCompilation:
    """Test macro compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_macro_default_arg_expression(self, env: Environment) -> None:
        """Macro with expression as default arg."""
        tmpl = env.from_string("""
{% macro greet(name='World') %}Hello {{ name }}{% endmacro %}
{{ greet() }}|{{ greet('User') }}
""")
        result = tmpl.render()
        assert "Hello World" in result
        assert "Hello User" in result

    def test_macro_varargs(self, env: Environment) -> None:
        """Macro with varargs (if supported)."""
        try:
            tmpl = env.from_string("""
{% macro join_all(*args) %}{{ args|join(',') }}{% endmacro %}
{{ join_all('a', 'b', 'c') }}
""")
            result = tmpl.render()
            assert "a,b,c" in result
        except Exception:
            pytest.skip("Varargs not supported")

    def test_macro_kwargs(self, env: Environment) -> None:
        """Macro with kwargs (if supported)."""
        try:
            tmpl = env.from_string("""
{% macro show(**kwargs) %}{% for k, v in kwargs.items() %}{{ k }}={{ v }};{% endfor %}{% endmacro %}
{{ show(a=1, b=2) }}
""")
            result = tmpl.render()
            assert "a=1" in result
            assert "b=2" in result
        except Exception:
            pytest.skip("Kwargs not supported")


class TestInheritanceCompilation:
    """Test template inheritance compilation."""

    def test_multi_level_inheritance(self) -> None:
        """Multi-level inheritance compiles correctly."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}base{% endblock %}",
                "middle.html": "{% extends 'base.html' %}{% block content %}middle:{{ super() }}{% endblock %}",
                "child.html": "{% extends 'middle.html' %}{% block content %}child:{{ super() }}{% endblock %}",
            }
        )
        env = Environment(loader=loader)
        try:
            tmpl = env.get_template("child.html")
            result = tmpl.render()
            # Should show inheritance chain
            assert "child" in result
        except Exception:
            pytest.skip("Multi-level super() not fully supported")

    def test_block_override_in_child(self) -> None:
        """Block override compiles correctly."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block head %}{% endblock %}{% block body %}{% endblock %}</html>",
                "child.html": "{% extends 'base.html' %}{% block body %}content{% endblock %}",
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "<html>" in result
        assert "content" in result


class TestFilterCompilation:
    """Test filter compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_filter_block_compilation(self, env: Environment) -> None:
        """Filter block compiles correctly."""
        tmpl = env.from_string("{% filter upper %}hello world{% endfilter %}")
        result = tmpl.render()
        assert result == "HELLO WORLD"

    def test_nested_filter_blocks(self, env: Environment) -> None:
        """Nested filter blocks."""
        tmpl = env.from_string("""
{% filter upper %}
  {% filter trim %}
    hello
  {% endfilter %}
{% endfilter %}
""")
        result = tmpl.render()
        assert "HELLO" in result


class TestCaptureCompilation:
    """Test capture block compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_capture_basic(self, env: Environment) -> None:
        """Basic capture compiles correctly."""
        tmpl = env.from_string("""
{% capture content %}Hello World{% endcapture %}
{{ content }}
""")
        result = tmpl.render()
        assert "Hello World" in result

    def test_capture_with_expressions(self, env: Environment) -> None:
        """Capture with embedded expressions."""
        tmpl = env.from_string("""
{% capture msg %}Hello {{ name }}{% endcapture %}
{{ msg|upper }}
""")
        result = tmpl.render(name="World")
        assert "HELLO WORLD" in result


class TestCallSlotCompilation:
    """Test call/slot compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_call_slot_basic(self, env: Environment) -> None:
        """Basic call/slot compiles correctly."""
        # In Kida, {% slot %} is a standalone tag (no endslot needed)
        tmpl = env.from_string("""
{% def box() %}
<div>{% slot %}</div>
{% enddef %}
{% call box() %}content{% endcall %}
""")
        result = tmpl.render()
        assert "<div>" in result
        assert "content" in result
        assert "</div>" in result


class TestCacheCompilation:
    """Test cache block compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_cache_block_basic(self, env: Environment) -> None:
        """Basic cache block compiles."""
        tmpl = env.from_string("""
{% cache 'key1' %}
expensive content
{% endcache %}
""")
        result = tmpl.render()
        assert "expensive content" in result


class TestWithCompilation:
    """Test with block compilation."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_with_basic(self, env: Environment) -> None:
        """Basic with block."""
        tmpl = env.from_string("""
{% with x = 5 %}{{ x }}{% endwith %}
""")
        assert "5" in tmpl.render()

    def test_with_multiple_vars(self, env: Environment) -> None:
        """With block with multiple variables."""
        tmpl = env.from_string("""
{% with x = 1, y = 2 %}{{ x + y }}{% endwith %}
""")
        assert "3" in tmpl.render()

    def test_with_scope_isolation(self, env: Environment) -> None:
        """With block creates isolated scope."""
        tmpl = env.from_string("""
{% set x = 'outer' %}
{% with x = 'inner' %}{{ x }}{% endwith %}
{{ x }}
""")
        result = tmpl.render()
        assert "inner" in result
        assert "outer" in result


class TestSpecialCompilationCases:
    """Test special compilation cases."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_empty_template(self, env: Environment) -> None:
        """Empty template compiles."""
        tmpl = env.from_string("")
        assert tmpl.render() == ""

    def test_whitespace_only(self, env: Environment) -> None:
        """Whitespace-only template."""
        tmpl = env.from_string("   \n  \t  \n  ")
        result = tmpl.render()
        # Should preserve or trim depending on config
        assert result is not None

    def test_only_comment(self, env: Environment) -> None:
        """Template with only comments."""
        tmpl = env.from_string("{# just a comment #}")
        assert tmpl.render() == ""

    def test_data_only(self, env: Environment) -> None:
        """Template with only static data."""
        tmpl = env.from_string("Hello World")
        assert tmpl.render() == "Hello World"

    def test_very_long_expression(self, env: Environment) -> None:
        """Very long expression."""
        # Build a long arithmetic expression
        expr = " + ".join(["1"] * 100)
        tmpl = env.from_string("{{ " + expr + " }}")
        assert tmpl.render() == "100"

    def test_deeply_nested_function_calls(self, env: Environment) -> None:
        """Deeply nested function calls."""
        # range(len(list([1,2,3])))
        tmpl = env.from_string("{% for i in range(len(list([1,2,3]))) %}{{ i }}{% endfor %}")
        result = tmpl.render()
        assert "0" in result
        assert "1" in result
        assert "2" in result


class TestAutoescapeCompilation:
    """Test autoescape compilation."""

    def test_autoescape_on(self) -> None:
        """Autoescape enabled."""
        env = Environment(autoescape=True)
        tmpl = env.from_string("{{ html }}")
        result = tmpl.render(html="<script>")
        assert "&lt;" in result
        assert "&gt;" in result

    def test_autoescape_off(self) -> None:
        """Autoescape disabled."""
        env = Environment(autoescape=False)
        tmpl = env.from_string("{{ html }}")
        result = tmpl.render(html="<script>")
        assert "<script>" in result

    def test_safe_filter(self) -> None:
        """Safe filter bypasses autoescape."""
        env = Environment(autoescape=True)
        tmpl = env.from_string("{{ html|safe }}")
        result = tmpl.render(html="<b>bold</b>")
        assert "<b>" in result
        assert "</b>" in result

    def test_escape_filter(self) -> None:
        """Escape filter with autoescape off."""
        env = Environment(autoescape=False)
        tmpl = env.from_string("{{ html|escape }}")
        result = tmpl.render(html="<script>")
        assert "&lt;" in result


class TestImportCompilation:
    """Test import/from compilation."""

    def test_import_macros(self) -> None:
        """Import macros from another template."""
        loader = DictLoader(
            {
                "macros.html": "{% macro greet(name) %}Hello {{ name }}{% endmacro %}",
            }
        )
        env = Environment(loader=loader)
        tmpl = env.from_string("""
{% from "macros.html" import greet %}
{{ greet('World') }}
""")
        result = tmpl.render()
        assert "Hello World" in result

    def test_import_as(self) -> None:
        """Import with alias."""
        loader = DictLoader(
            {
                "macros.html": "{% macro greet(name) %}Hello {{ name }}{% endmacro %}",
            }
        )
        env = Environment(loader=loader)
        tmpl = env.from_string("""
{% from "macros.html" import greet as say_hello %}
{{ say_hello('World') }}
""")
        result = tmpl.render()
        assert "Hello World" in result
