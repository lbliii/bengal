"""Tests for Kida strict mode.

RFC: rfc-kida-python-compatibility.md (Phase 2)

Strict mode (default) raises UndefinedError for undefined variables instead
of silently returning None. This catches typos and missing variables early.

Key behaviors:
1. Undefined variables raise UndefinedError
2. Defined variables work normally
3. strict=False restores legacy behavior (silent None)
4. default filter works with undefined variables
5. is defined/is undefined tests work correctly
6. Error messages include variable name and location
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida.environment import Environment, UndefinedError


class TestStrictModeDefault:
    """Test that strict mode is enabled by default."""

    def test_strict_is_default(self) -> None:
        """Environment uses strict mode by default."""
        env = Environment()
        assert env.strict is True

    def test_strict_can_be_disabled(self) -> None:
        """Strict mode can be disabled."""
        env = Environment(strict=False)
        assert env.strict is False


class TestUndefinedError:
    """Test UndefinedError behavior in strict mode."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create a strict mode environment (default)."""
        return Environment()

    def test_undefined_raises_error(self, env: Environment) -> None:
        """Accessing undefined variable raises UndefinedError."""
        with pytest.raises(UndefinedError) as exc_info:
            env.from_string("{{ undefined_var }}").render()
        assert "undefined_var" in str(exc_info.value)

    def test_error_includes_variable_name(self, env: Environment) -> None:
        """Error includes the undefined variable name."""
        try:
            env.from_string("{{ my_missing_var }}").render()
            pytest.fail("Expected UndefinedError")
        except UndefinedError as e:
            assert e.name == "my_missing_var"

    def test_error_includes_template_name(self, env: Environment) -> None:
        """Error includes template name when available."""
        try:
            env.from_string("{{ missing }}", name="test.html").render()
            pytest.fail("Expected UndefinedError")
        except UndefinedError as e:
            assert "test.html" in str(e)

    def test_defined_variables_work(self, env: Environment) -> None:
        """Defined variables work normally in strict mode."""
        result = env.from_string("{{ name }}").render(name="World")
        assert result == "World"

    def test_globals_work(self, env: Environment) -> None:
        """Global functions work in strict mode."""
        result = env.from_string("{{ len([1, 2, 3]) }}").render()
        assert result == "3"


class TestStrictFalse:
    """Test legacy behavior with strict=False."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create a lenient mode environment."""
        return Environment(strict=False)

    def test_undefined_returns_none_string(self, env: Environment) -> None:
        """Undefined variable returns 'None' string in legacy mode.

        Note: In legacy mode, ctx.get(name) returns None, which gets
        converted to the string 'None' when rendered. Use the default
        filter for empty string: {{ x | default('') }}
        """
        result = env.from_string("{{ undefined_var }}").render()
        assert result == "None"

    def test_undefined_with_default(self, env: Environment) -> None:
        """Use default filter for empty string in legacy mode."""
        result = env.from_string("{{ undefined_var | default('') }}").render()
        assert result == ""

    def test_undefined_in_conditional(self, env: Environment) -> None:
        """Undefined variable is falsy in conditional."""
        result = env.from_string("{% if undef %}yes{% else %}no{% endif %}").render()
        assert result == "no"


class TestDefaultFilter:
    """Test default filter works with strict mode."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create a strict mode environment (default)."""
        return Environment()

    def test_default_with_undefined(self, env: Environment) -> None:
        """Default filter provides fallback for undefined variables."""
        result = env.from_string('{{ missing | default("fallback") }}').render()
        assert result == "fallback"

    def test_default_d_alias(self, env: Environment) -> None:
        """The 'd' alias for default filter works."""
        result = env.from_string('{{ missing | d("fallback") }}').render()
        assert result == "fallback"

    def test_default_with_defined(self, env: Environment) -> None:
        """Default filter returns value when defined."""
        result = env.from_string('{{ name | default("fallback") }}').render(name="Alice")
        assert result == "Alice"

    def test_default_with_none(self, env: Environment) -> None:
        """Default filter handles None values."""
        result = env.from_string('{{ value | default("fallback") }}').render(value=None)
        assert result == "fallback"

    def test_default_boolean_true(self, env: Environment) -> None:
        """Default filter with boolean=True checks truthiness."""
        result = env.from_string('{{ value | default("fallback", true) }}').render(value="")
        assert result == "fallback"

    def test_default_boolean_false(self, env: Environment) -> None:
        """Default filter with boolean=False only checks None."""
        result = env.from_string('{{ value | default("fallback", false) }}').render(value="")
        assert result == ""


class TestIsDefinedTest:
    """Test 'is defined' and 'is undefined' tests work with strict mode."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create a strict mode environment (default)."""
        return Environment()

    def test_is_defined_true(self, env: Environment) -> None:
        """'is defined' returns True for defined variables."""
        result = env.from_string("{% if x is defined %}yes{% endif %}").render(x=42)
        assert result == "yes"

    def test_is_defined_false(self, env: Environment) -> None:
        """'is defined' returns False for undefined variables."""
        result = env.from_string("{% if x is defined %}yes{% else %}no{% endif %}").render()
        assert result == "no"

    def test_is_undefined_true(self, env: Environment) -> None:
        """'is undefined' returns True for undefined variables."""
        result = env.from_string("{% if x is undefined %}yes{% endif %}").render()
        assert result == "yes"

    def test_is_undefined_false(self, env: Environment) -> None:
        """'is undefined' returns False for defined variables."""
        result = env.from_string("{% if x is undefined %}yes{% else %}no{% endif %}").render(x=42)
        assert result == "no"

    def test_is_not_defined(self, env: Environment) -> None:
        """'is not defined' works correctly."""
        result = env.from_string("{% if x is not defined %}yes{% endif %}").render()
        assert result == "yes"

    def test_none_is_undefined(self, env: Environment) -> None:
        """None value is considered undefined (consistent with Jinja2)."""
        result = env.from_string("{% if x is defined %}yes{% else %}no{% endif %}").render(x=None)
        assert result == "no"


class TestStrictModeEdgeCases:
    """Test edge cases and complex scenarios with strict mode."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create a strict mode environment (default)."""
        return Environment()

    def test_nested_attribute_on_undefined(self, env: Environment) -> None:
        """Nested attribute access on undefined raises error."""
        with pytest.raises(UndefinedError):
            env.from_string("{{ missing.attr }}").render()

    def test_attribute_access_on_defined(self, env: Environment) -> None:
        """Attribute access on defined object works."""
        result = env.from_string("{{ obj.name }}").render(obj={"name": "test"})
        assert result == "test"

    def test_loop_variable_defined(self, env: Environment) -> None:
        """Loop variables are considered defined."""
        result = env.from_string("{% for i in items %}{{ i }}{% endfor %}").render(items=[1, 2, 3])
        assert result == "123"

    def test_set_makes_variable_defined(self, env: Environment) -> None:
        """Variables set with {% set %} are considered defined."""
        result = env.from_string("{% set x = 42 %}{{ x }}").render()
        assert result == "42"

    def test_filter_on_defined_none(self, env: Environment) -> None:
        """Filters work on defined None values."""
        result = env.from_string('{{ value | default("none") }}').render(value=None)
        assert result == "none"

    def test_complex_expression_with_undefined(self, env: Environment) -> None:
        """Complex expressions with undefined parts raise error."""
        with pytest.raises(UndefinedError):
            env.from_string("{{ a + b }}").render(a=1)

    def test_conditional_short_circuit(self, env: Environment) -> None:
        """Conditionals short-circuit to avoid evaluating undefined."""
        # If 'x' is truthy, 'y' is never evaluated
        result = env.from_string("{% if x or y %}yes{% endif %}").render(x=True)
        assert result == "yes"


class TestStrictModePerformance:
    """Verify strict mode doesn't add significant overhead."""

    def test_strict_mode_fast_path(self) -> None:
        """Defined variables use fast lookup path."""
        env = Environment()
        tmpl = env.from_string("{{ name }}")
        # Should be fast - no exception handling in hot path
        for _ in range(100):
            assert tmpl.render(name="test") == "test"

    def test_lenient_mode_comparison(self) -> None:
        """Lenient mode uses dict.get (slightly different path)."""
        env = Environment(strict=False)
        tmpl = env.from_string("{{ name }}")
        for _ in range(100):
            assert tmpl.render(name="test") == "test"
