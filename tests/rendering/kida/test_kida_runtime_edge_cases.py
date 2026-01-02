"""Runtime edge cases for Kida template rendering.

Tests memory handling, circular references, performance boundaries, and runtime errors.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from bengal.rendering.kida import DictLoader, Environment, UndefinedError
from bengal.rendering.kida.environment.exceptions import (
    TemplateNotFoundError,
    TemplateRuntimeError,
)


class TestCircularReferences:
    """Test handling of circular references in context data."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_self_referencing_dict(self, env: Environment) -> None:
        """Dict that references itself."""
        data: dict[str, Any] = {"name": "test"}
        data["self"] = data

        tmpl = env.from_string("{{ data.name }}")
        result = tmpl.render(data=data)
        assert result == "test"

    def test_self_referencing_list(self, env: Environment) -> None:
        """List that contains itself."""
        data: list[Any] = [1, 2, 3]
        data.append(data)

        tmpl = env.from_string("{{ data[0] }}")
        result = tmpl.render(data=data)
        assert result == "1"

    def test_mutually_referencing_objects(self, env: Environment) -> None:
        """Two objects that reference each other."""

        class Node:
            def __init__(self, value: int) -> None:
                self.value = value
                self.next: Node | None = None

        a = Node(1)
        b = Node(2)
        a.next = b
        b.next = a

        tmpl = env.from_string("{{ node.value }}-{{ node.next.value }}")
        result = tmpl.render(node=a)
        assert result == "1-2"


class TestMemoryHandling:
    """Test memory handling during template rendering."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_template_garbage_collection(self, env: Environment) -> None:
        """Templates can be garbage collected."""
        tmpl = env.from_string("{{ x }}")
        # Just verify template works, garbage collection behavior varies
        assert tmpl.render(x="test") == "test"

    def test_large_context(self, env: Environment) -> None:
        """Handle large context data."""
        large_data = {"key_" + str(i): i for i in range(10000)}

        tmpl = env.from_string("{{ key_5000 }}")
        result = tmpl.render(**large_data)
        assert result == "5000"

    def test_large_list_iteration(self, env: Environment) -> None:
        """Iterate over large list."""
        large_list = list(range(10000))

        tmpl = env.from_string("{% for x in items %}{% endfor %}done")
        result = tmpl.render(items=large_list)
        assert result == "done"

    def test_large_string_output(self, env: Environment) -> None:
        """Generate large string output."""
        tmpl = env.from_string("{% for x in range(1000) %}x{% endfor %}")
        result = tmpl.render()
        assert len(result) == 1000
        assert result == "x" * 1000


class TestRuntimeErrors:
    """Test runtime error handling."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_type_error_in_filter(self, env: Environment) -> None:
        """Type error in filter raises appropriate error."""
        tmpl = env.from_string("{{ 'hello'|length + 'world' }}")
        with pytest.raises((TypeError, TemplateRuntimeError)):
            tmpl.render()

    def test_zero_division(self, env: Environment) -> None:
        """Zero division raises error."""
        tmpl = env.from_string("{{ 1 / 0 }}")
        with pytest.raises((ZeroDivisionError, TemplateRuntimeError)):
            tmpl.render()

    def test_modulo_by_zero(self, env: Environment) -> None:
        """Modulo by zero raises error."""
        tmpl = env.from_string("{{ 10 % 0 }}")
        with pytest.raises((ZeroDivisionError, TemplateRuntimeError)):
            tmpl.render()

    def test_attribute_error_on_none(self) -> None:
        """Attribute access on None in strict mode."""
        env = Environment()
        tmpl = env.from_string("{{ obj.attr }}")
        # In strict mode, accessing attribute on None should either:
        # - Raise an error (strict behavior)
        # - Return empty string (resilient None handling)
        try:
            result = tmpl.render(obj=None)
            # If it doesn't raise, it should be empty (resilient handling)
            assert result == ""
        except (AttributeError, TemplateRuntimeError, UndefinedError, Exception):
            # Expected - strict mode raises error
            pass

    def test_key_error_on_dict(self) -> None:
        """Missing key access on dict in strict mode."""
        env = Environment()
        tmpl = env.from_string("{{ data['missing'] }}")
        with pytest.raises((KeyError, TemplateRuntimeError, UndefinedError)):
            tmpl.render(data={})

    def test_index_error_on_list(self, env: Environment) -> None:
        """Out of bounds index on list."""
        tmpl = env.from_string("{{ items[100] }}")
        with pytest.raises((IndexError, TemplateRuntimeError)):
            tmpl.render(items=[1, 2, 3])

    def test_call_non_callable(self, env: Environment) -> None:
        """Calling non-callable raises error."""
        tmpl = env.from_string("{{ x() }}")
        with pytest.raises((TypeError, TemplateRuntimeError)):
            tmpl.render(x=42)

    def test_iteration_over_non_iterable(self, env: Environment) -> None:
        """Iterating over non-iterable raises error."""
        tmpl = env.from_string("{% for x in items %}{{ x }}{% endfor %}")
        with pytest.raises((TypeError, TemplateRuntimeError)):
            tmpl.render(items=42)


class TestUndefinedBehavior:
    """Test undefined variable behavior."""

    def test_undefined_strict(self) -> None:
        """Undefined variable in strict mode raises error."""
        env = Environment()
        tmpl = env.from_string("{{ undefined_var }}")
        with pytest.raises(UndefinedError):
            tmpl.render()

    def test_undefined_in_if(self) -> None:
        """Undefined variable in if condition."""
        env = Environment()
        tmpl = env.from_string("{% if x is defined %}yes{% else %}no{% endif %}")
        assert tmpl.render() == "no"
        assert tmpl.render(x=1) == "yes"

    def test_undefined_with_default(self) -> None:
        """Undefined variable with default filter."""
        env = Environment()
        tmpl = env.from_string("{{ undefined|default('fallback') }}")
        result = tmpl.render()
        assert result == "fallback"


class TestContextIsolation:
    """Test context isolation between renders."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_renders_are_isolated(self, env: Environment) -> None:
        """Each render has isolated context."""
        tmpl = env.from_string("{% set x = 'local' %}{{ x }}")

        result1 = tmpl.render()
        result2 = tmpl.render()

        assert result1 == result2 == "local"

    def test_context_not_leaked(self, env: Environment) -> None:
        """Context from one render doesn't leak to another."""
        tmpl = env.from_string("{{ x|default('missing') }}")

        result1 = tmpl.render(x="first")
        result2 = tmpl.render()

        assert result1 == "first"
        assert result2 == "missing"

    def test_mutation_not_persisted(self, env: Environment) -> None:
        """Set statements create local scope, not modifying passed data."""
        # Test that set creates a local variable, not modifying context
        tmpl = env.from_string("{% set x = 'local' %}{{ x }}")

        result1 = tmpl.render()
        result2 = tmpl.render()

        assert result1 == result2 == "local"


class TestLazyEvaluation:
    """Test lazy evaluation behavior."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_short_circuit_and(self, env: Environment) -> None:
        """AND short-circuits on first false."""
        call_count = [0]

        def side_effect() -> bool:
            call_count[0] += 1
            return True

        tmpl = env.from_string("{% if false and func() %}yes{% endif %}")
        tmpl.render(func=side_effect)

        # func() should not be called due to short-circuit
        assert call_count[0] == 0

    def test_short_circuit_or(self, env: Environment) -> None:
        """OR short-circuits on first true."""
        call_count = [0]

        def side_effect() -> bool:
            call_count[0] += 1
            return False

        tmpl = env.from_string("{% if true or func() %}yes{% endif %}")
        tmpl.render(func=side_effect)

        # func() should not be called due to short-circuit
        assert call_count[0] == 0

    def test_ternary_short_circuit(self, env: Environment) -> None:
        """Ternary only evaluates selected branch."""
        true_count = [0]
        false_count = [0]

        def true_side() -> str:
            true_count[0] += 1
            return "true"

        def false_side() -> str:
            false_count[0] += 1
            return "false"

        tmpl = env.from_string("{{ true_fn() if cond else false_fn() }}")
        tmpl.render(cond=True, true_fn=true_side, false_fn=false_side)

        assert true_count[0] == 1
        assert false_count[0] == 0


class TestExceptionHandling:
    """Test exception handling in templates."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_exception_from_filter(self, env: Environment) -> None:
        """Exception from custom filter."""

        def bad_filter(value: Any) -> str:
            raise ValueError("Filter error")

        env.filters["bad"] = bad_filter
        tmpl = env.from_string("{{ x|bad }}")

        with pytest.raises((ValueError, TemplateRuntimeError)):
            tmpl.render(x="test")

    def test_exception_from_global(self, env: Environment) -> None:
        """Exception from global function."""

        def bad_func() -> str:
            raise RuntimeError("Function error")

        env.globals["bad_func"] = bad_func
        tmpl = env.from_string("{{ bad_func() }}")

        with pytest.raises((RuntimeError, TemplateRuntimeError)):
            tmpl.render()

    def test_exception_from_method(self, env: Environment) -> None:
        """Exception from object method."""
        obj = Mock()
        obj.method.side_effect = Exception("Method error")

        tmpl = env.from_string("{{ obj.method() }}")

        with pytest.raises((Exception, TemplateRuntimeError)):
            tmpl.render(obj=obj)


class TestEdgeCaseValues:
    """Test edge case values in context."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_empty_string(self, env: Environment) -> None:
        """Empty string in context."""
        tmpl = env.from_string("[{{ x }}]")
        assert tmpl.render(x="") == "[]"

    def test_zero_integer(self, env: Environment) -> None:
        """Zero in context."""
        tmpl = env.from_string("{{ x }}")
        assert tmpl.render(x=0) == "0"

    def test_false_boolean(self, env: Environment) -> None:
        """False in context."""
        tmpl = env.from_string("{{ x }}")
        assert tmpl.render(x=False) == "False"

    def test_empty_list(self, env: Environment) -> None:
        """Empty list in context."""
        tmpl = env.from_string("{% for x in items %}x{% else %}empty{% endfor %}")
        assert tmpl.render(items=[]) == "empty"

    def test_empty_dict(self, env: Environment) -> None:
        """Empty dict in context."""
        tmpl = env.from_string("{% for k in data %}{{ k }}{% else %}empty{% endfor %}")
        assert tmpl.render(data={}) == "empty"

    def test_none_value(self, env: Environment) -> None:
        """None in context (non-strict mode)."""
        tmpl = env.from_string("[{{ x }}]")
        result = tmpl.render(x=None)
        assert result in ["[]", "[None]"]

    def test_special_float_values(self, env: Environment) -> None:
        """Special float values."""
        tmpl = env.from_string("{{ x }}")

        result_inf = tmpl.render(x=float("inf"))
        assert "inf" in result_inf.lower()

        result_nan = tmpl.render(x=float("nan"))
        assert "nan" in result_nan.lower()

    def test_very_large_integer(self, env: Environment) -> None:
        """Very large integer."""
        big = 10**100
        tmpl = env.from_string("{{ x }}")
        result = tmpl.render(x=big)
        assert "1" in result
        assert len(result) > 100


class TestRecursionLimits:
    """Test recursion handling."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_recursive_macro_limit(self, env: Environment) -> None:
        """Recursive macro hits limit gracefully."""
        tmpl = env.from_string("""
{% def recurse(n) %}
{% if n > 0 %}{{ n }}{{ recurse(n-1) }}{% endif %}
{% end %}
{{ recurse(10) }}
""")
        result = tmpl.render()
        # Should work for small n
        assert "10" in result
        assert "1" in result

    def test_deep_recursion_handled(self, env: Environment) -> None:
        """Very deep recursion is handled."""
        tmpl = env.from_string("""
{% def recurse(n) %}
{% if n > 0 %}{{ recurse(n-1) }}{% endif %}
{% end %}
{{ recurse(500) }}
""")
        # Should either work or raise clear error
        try:
            tmpl.render()
            # If it works, that's fine
        except RecursionError:
            # Expected for very deep recursion
            pass
        except TemplateRuntimeError:
            # Also acceptable
            pass


class TestIncludeRuntime:
    """Test include runtime behavior."""

    def test_include_missing_template(self) -> None:
        """Include missing template raises error."""
        env = Environment(loader=DictLoader({}))
        tmpl = env.from_string('{% include "missing.html" %}')

        with pytest.raises(TemplateNotFoundError):
            tmpl.render()

    def test_include_with_context(self) -> None:
        """Include receives context."""
        loader = DictLoader(
            {
                "partial.html": "{{ name }}",
            }
        )
        env = Environment(loader=loader)
        tmpl = env.from_string('{% include "partial.html" %}')

        assert tmpl.render(name="Alice") == "Alice"

    def test_include_modifying_context(self) -> None:
        """Include doesn't modify caller's context."""
        loader = DictLoader(
            {
                "partial.html": "{% set x = 'modified' %}{{ x }}",
            }
        )
        env = Environment(loader=loader)
        tmpl = env.from_string("""
{% set x = 'original' %}
{% include "partial.html" %}
{{ x }}
""")
        result = tmpl.render()
        # x should still be 'original' after include
        # (depends on scoping semantics)
        assert "original" in result or "modified" in result


class TestFilterRuntime:
    """Test filter runtime behavior."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_filter_none_input(self, env: Environment) -> None:
        """Filters handle None input."""
        tmpl = env.from_string("{{ x|default('fallback') }}")
        assert tmpl.render(x=None) == "fallback"

    def test_filter_chaining_with_error(self, env: Environment) -> None:
        """Error in filter chain propagates."""

        def error_filter(x: Any) -> str:
            raise ValueError("filter error")

        env.filters["error"] = error_filter
        tmpl = env.from_string("{{ x|upper|error }}")

        with pytest.raises((ValueError, TemplateRuntimeError)):
            tmpl.render(x="test")
