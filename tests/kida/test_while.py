"""Tests for {% while %} loop statement.

Part of RFC: kida-2.0-moonshot (While Loops).
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import Environment


@pytest.fixture
def env() -> Environment:
    """Create a Kida environment for testing."""
    return Environment()


class TestWhileLoop:
    """Test suite for {% while %} loops."""

    def test_basic_while_loop(self, env: Environment) -> None:
        """Test simple while loop with counter."""
        template = env.from_string("""
{%- let counter = 0 -%}
{%- while counter < 3 -%}
{{ counter }}{%- let counter = counter + 1 -%}
{%- end -%}
""")
        result = template.render()
        assert result == "012"

    def test_while_loop_with_break(self, env: Environment) -> None:
        """Test while loop with {% break %} statement."""
        template = env.from_string("""
{%- let i = 0 -%}
{%- while true -%}
{{ i }}{%- if i >= 2 -%}{% break %}{%- end -%}
{%- let i = i + 1 -%}
{%- end -%}
""")
        result = template.render()
        assert result == "012"

    def test_while_loop_with_continue(self, env: Environment) -> None:
        """Test while loop with {% continue %} statement."""
        template = env.from_string("""
{%- let n = 0 -%}
{%- while n < 5 -%}
{%- let n = n + 1 -%}
{%- if n == 2 or n == 4 -%}{% continue %}{%- end -%}
{{ n }}
{%- end -%}
""")
        result = template.render()
        assert "1" in result
        assert "3" in result
        assert "5" in result
        assert "2" not in result
        assert "4" not in result

    def test_nested_while_loops(self, env: Environment) -> None:
        """Test nested while loops."""
        template = env.from_string("""
{%- let i = 0 -%}
{%- while i < 2 -%}
{%- let j = 0 -%}
{%- while j < 2 -%}
({{ i }},{{ j }}){%- let j = j + 1 -%}
{%- end -%}
{%- let i = i + 1 -%}
{%- end -%}
""")
        result = template.render()
        assert "(0,0)" in result
        assert "(0,1)" in result
        assert "(1,0)" in result
        assert "(1,1)" in result

    def test_while_with_empty_body(self, env: Environment) -> None:
        """Test while loop with empty body (edge case)."""
        template = env.from_string("""
{%- let x = 0 -%}
{%- while false -%}
{%- end -%}
done
""")
        result = template.render()
        assert result.strip() == "done"

    def test_while_with_complex_condition(self, env: Environment) -> None:
        """Test while loop with complex condition expression."""
        template = env.from_string("""
{%- let items = ['a', 'b', 'c'] -%}
{%- let idx = 0 -%}
{%- while idx < items | length and items[idx] != 'c' -%}
{{ items[idx] }}{%- let idx = idx + 1 -%}
{%- end -%}
""")
        result = template.render()
        assert result == "ab"

    def test_while_with_endwhile(self, env: Environment) -> None:
        """Test while loop with explicit {% endwhile %} tag."""
        template = env.from_string("""
{%- let n = 0 -%}
{%- while n < 2 -%}
{{ n }}{%- let n = n + 1 -%}
{%- endwhile -%}
""")
        result = template.render()
        assert result == "01"

    def test_while_in_macro(self, env: Environment) -> None:
        """Test while loop inside a macro definition."""
        template = env.from_string("""
{%- def countdown(start) -%}
{%- let n = start -%}
{%- while n > 0 -%}
{{ n }}{%- let n = n - 1 -%}
{%- end -%}
{%- end -%}
{{ countdown(3) }}
""")
        result = template.render()
        assert result.strip() == "321"


class TestWhileLoopErrors:
    """Test error handling for {% while %} loops."""

    def test_break_outside_while_raises(self, env: Environment) -> None:
        """Test that {% break %} outside loop raises ParseError."""
        with pytest.raises(Exception, match="outside loop"):
            env.from_string("{% break %}")

    def test_continue_outside_while_raises(self, env: Environment) -> None:
        """Test that {% continue %} outside loop raises ParseError."""
        with pytest.raises(Exception, match="outside loop"):
            env.from_string("{% continue %}")
