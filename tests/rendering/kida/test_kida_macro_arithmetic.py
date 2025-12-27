"""Tests for Kida macro arithmetic with numeric coercion.

Verifies that arithmetic operations with macro results correctly coerce
Markup objects to numeric values, preventing string multiplication.
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida.environment import Environment


@pytest.fixture
def env() -> Environment:
    """Create a fresh Environment for each test."""
    return Environment()


class TestMacroArithmeticCoercion:
    """Test numeric coercion for macro results in arithmetic."""

    def test_recursive_factorial(self, env: Environment) -> None:
        """Recursive macro with arithmetic should produce correct numeric result."""
        tmpl = env.from_string(
            "{% macro factorial(n) %}"
            "{% if n <= 1 %}1{% else %}{{ n * factorial(n - 1) }}{% endif %}"
            "{% endmacro %}"
            "{{ factorial(5) }}"
        )
        result = tmpl.render().strip()
        # 5! = 120
        # Without coercion, this would produce string multiplication like "11111..."
        assert "120" in result

    def test_factorial_base_case(self, env: Environment) -> None:
        """Factorial of 1 should return 1."""
        tmpl = env.from_string(
            "{% macro factorial(n) %}"
            "{% if n <= 1 %}1{% else %}{{ n * factorial(n - 1) }}{% endif %}"
            "{% endmacro %}"
            "{{ factorial(1) }}"
        )
        result = tmpl.render().strip()
        assert "1" in result

    def test_factorial_of_zero(self, env: Environment) -> None:
        """Factorial of 0 should return 1."""
        tmpl = env.from_string(
            "{% macro factorial(n) %}"
            "{% if n <= 1 %}1{% else %}{{ n * factorial(n - 1) }}{% endif %}"
            "{% endmacro %}"
            "{{ factorial(0) }}"
        )
        result = tmpl.render().strip()
        assert "1" in result

    def test_macro_multiplication(self, env: Environment) -> None:
        """Simple macro result multiplied by number."""
        tmpl = env.from_string("{% macro double(n) %}{{ n * 2 }}{% endmacro %}{{ 3 * double(5) }}")
        result = tmpl.render().strip()
        # double(5) = 10, 3 * 10 = 30
        assert "30" in result

    def test_macro_addition(self, env: Environment) -> None:
        """Macro result in addition."""
        tmpl = env.from_string(
            "{% macro add_five(n) %}{{ n + 5 }}{% endmacro %}{{ add_five(10) + 3 }}"
        )
        result = tmpl.render().strip()
        # add_five(10) = 15, 15 + 3 = 18
        assert "18" in result

    def test_macro_subtraction(self, env: Environment) -> None:
        """Macro result in subtraction."""
        tmpl = env.from_string("{% macro get_ten() %}10{% endmacro %}{{ get_ten() - 3 }}")
        result = tmpl.render().strip()
        # 10 - 3 = 7
        assert "7" in result

    def test_macro_division(self, env: Environment) -> None:
        """Macro result in division."""
        tmpl = env.from_string("{% macro get_twenty() %}20{% endmacro %}{{ get_twenty() / 4 }}")
        result = tmpl.render().strip()
        # 20 / 4 = 5.0
        assert "5" in result

    def test_macro_with_whitespace_output(self, env: Environment) -> None:
        """Macro with internal whitespace should still compute correctly."""
        tmpl = env.from_string(
            "{% macro padded_number() %}\n  24\n{% endmacro %}{{ padded_number() * 2 }}"
        )
        result = tmpl.render().strip()
        # "  24  ".strip() = "24", 24 * 2 = 48
        assert "48" in result

    def test_chained_macro_arithmetic(self, env: Environment) -> None:
        """Multiple macro calls in arithmetic expression."""
        tmpl = env.from_string(
            "{% macro five() %}5{% endmacro %}"
            "{% macro three() %}3{% endmacro %}"
            "{{ five() * three() }}"
        )
        result = tmpl.render().strip()
        # 5 * 3 = 15
        assert "15" in result

    def test_macro_with_int_filter(self, env: Environment) -> None:
        """Macro result can be explicitly converted with |int filter."""
        tmpl = env.from_string("{% macro get_num() %}  42  {% endmacro %}{{ (get_num()|int) * 2 }}")
        result = tmpl.render().strip()
        # get_num() returns "  42  ", |int converts to 42, 42 * 2 = 84
        assert "84" in result


class TestNumericCoercionEdgeCases:
    """Edge cases for numeric coercion."""

    def test_non_numeric_string_coerces_to_zero(self, env: Environment) -> None:
        """Non-numeric macro result should coerce to 0."""
        tmpl = env.from_string("{% macro get_text() %}hello{% endmacro %}{{ get_text() + 5 }}")
        result = tmpl.render().strip()
        # "hello" -> 0, 0 + 5 = 5
        assert "5" in result

    def test_float_string_coercion(self, env: Environment) -> None:
        """Float string from macro should coerce correctly."""
        tmpl = env.from_string("{% macro get_pi() %}3.14{% endmacro %}{{ get_pi() * 2 }}")
        result = tmpl.render().strip()
        # 3.14 * 2 = 6.28
        assert "6.28" in result

    def test_negative_number_coercion(self, env: Environment) -> None:
        """Negative number string from macro should coerce correctly."""
        tmpl = env.from_string(
            "{% macro get_negative() %}-5{% endmacro %}{{ get_negative() + 10 }}"
        )
        result = tmpl.render().strip()
        # -5 + 10 = 5
        assert "5" in result

    def test_regular_arithmetic_unaffected(self, env: Environment) -> None:
        """Regular arithmetic (not involving macros) should work as before."""
        tmpl = env.from_string("{{ 5 * 3 }}")
        assert tmpl.render().strip() == "15"

        tmpl = env.from_string("{{ 10 + 5 }}")
        assert tmpl.render().strip() == "15"

        tmpl = env.from_string("{{ 20 / 4 }}")
        assert tmpl.render().strip() == "5.0"

    def test_variable_arithmetic_unaffected(self, env: Environment) -> None:
        """Arithmetic with context variables should work as before."""
        tmpl = env.from_string("{{ x * y }}")
        assert tmpl.render(x=5, y=3).strip() == "15"

    def test_string_concatenation_preserved(self, env: Environment) -> None:
        """String concatenation operator ~ should not be affected."""
        tmpl = env.from_string("{% macro greet() %}Hello{% endmacro %}{{ greet() ~ ' World' }}")
        result = tmpl.render().strip()
        assert "Hello World" in result

    def test_modulo_with_macro(self, env: Environment) -> None:
        """Modulo operator with macro result."""
        tmpl = env.from_string("{% macro get_ten() %}10{% endmacro %}{{ get_ten() % 3 }}")
        result = tmpl.render().strip()
        # 10 % 3 = 1
        assert "1" in result

    def test_power_with_macro(self, env: Environment) -> None:
        """Power operator with macro result."""
        tmpl = env.from_string("{% macro get_two() %}2{% endmacro %}{{ get_two() ** 3 }}")
        result = tmpl.render().strip()
        # 2 ** 3 = 8
        assert "8" in result

    def test_floor_division_with_macro(self, env: Environment) -> None:
        """Floor division with macro result."""
        tmpl = env.from_string("{% macro get_seven() %}7{% endmacro %}{{ get_seven() // 2 }}")
        result = tmpl.render().strip()
        # 7 // 2 = 3
        assert "3" in result
