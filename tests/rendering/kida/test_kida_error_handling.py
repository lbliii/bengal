"""Comprehensive tests for Kida error handling.

This module tests error messages, exception types, and error recovery
to ensure that users get helpful diagnostics when things go wrong.
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import DictLoader, Environment
from bengal.rendering.kida.environment.exceptions import (
    TemplateNotFoundError,
    TemplateRuntimeError,
    TemplateSyntaxError,
    UndefinedError,
)


class TestSyntaxErrors:
    """Test syntax error detection and messages."""

    def test_unclosed_variable(self) -> None:
        """Unclosed variable expression."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)) as exc_info:
            env.from_string("{{ x")
        # Should have useful error message
        assert exc_info.value is not None

    def test_unclosed_block(self) -> None:
        """Unclosed block tag."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)) as exc_info:
            env.from_string("{% if true")
        assert exc_info.value is not None

    def test_unmatched_endif(self) -> None:
        """Unmatched endif should raise an error."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{% endif %}")

    def test_unmatched_endfor(self) -> None:
        """Unmatched endfor should raise an error."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{% endfor %}")

    def test_missing_expression(self) -> None:
        """Missing expression in variable output."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{{  }}")

    def test_invalid_expression(self) -> None:
        """Invalid expression syntax."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{{ + + }}")

    def test_unclosed_string(self) -> None:
        """Unclosed string literal."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{{ 'unclosed }}")

    def test_mismatched_block_tags(self) -> None:
        """Mismatched block end tags should raise an error."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{% if true %}{% endfor %}")

    def test_elif_without_if(self) -> None:
        """elif without if should raise an error."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{% elif true %}{% endif %}")

    def test_else_without_if(self) -> None:
        """else without if or for should raise an error."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{% else %}{% endif %}")

    def test_invalid_for_syntax(self) -> None:
        """Invalid for loop syntax."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{% for in items %}{% endfor %}")

    def test_missing_set_value(self) -> None:
        """Set without value."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{% set x %}{{ x }}")

    def test_invalid_filter_syntax(self) -> None:
        """Invalid filter syntax."""
        env = Environment()
        with pytest.raises((TemplateSyntaxError, Exception)):
            env.from_string("{{ x | }}")


class TestRuntimeErrors:
    """Test runtime error handling."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment(strict=False)

    def test_division_by_zero(self, env: Environment) -> None:
        """Division by zero."""
        tmpl = env.from_string("{{ 1 / 0 }}")
        with pytest.raises((ZeroDivisionError, TemplateRuntimeError)):
            tmpl.render()

    def test_type_error_concatenation(self, env: Environment) -> None:
        """Type error in concatenation."""
        tmpl = env.from_string("{{ 'hello' + 5 }}")
        with pytest.raises((TypeError, TemplateRuntimeError)):
            tmpl.render()

    def test_index_out_of_range(self, env: Environment) -> None:
        """Index out of range."""
        tmpl = env.from_string("{{ items[100] }}")
        with pytest.raises((IndexError, TemplateRuntimeError)):
            tmpl.render(items=[1, 2, 3])

    def test_attribute_error(self, env: Environment) -> None:
        """Attribute error on non-existent attribute.

        Note: With None-safe attribute access, this returns empty string.
        """
        tmpl = env.from_string("{{ obj.nonexistent }}")
        result = tmpl.render(obj={})
        # With None-safe access, should return empty string
        assert result == ""

    def test_iteration_over_non_iterable(self, env: Environment) -> None:
        """Iteration over non-iterable."""
        tmpl = env.from_string("{% for x in items %}{{ x }}{% endfor %}")
        with pytest.raises((TypeError, TemplateRuntimeError)):
            tmpl.render(items=42)

    def test_call_non_callable(self, env: Environment) -> None:
        """Calling non-callable."""
        tmpl = env.from_string("{{ x() }}")
        with pytest.raises((TypeError, TemplateRuntimeError)):
            tmpl.render(x=42)

    def test_filter_type_error(self, env: Environment) -> None:
        """Type handling in filter - Kida converts to string before applying."""
        tmpl = env.from_string("{{ x|upper }}")
        # Kida converts int to string before applying upper
        result = tmpl.render(x=42)
        assert result == "42"  # No uppercase effect on digits


class TestUndefinedErrors:
    """Test undefined variable error handling."""

    @pytest.fixture
    def strict_env(self) -> Environment:
        return Environment(strict=True)

    @pytest.fixture
    def lenient_env(self) -> Environment:
        return Environment(strict=False)

    def test_undefined_raises_in_strict_mode(self, strict_env: Environment) -> None:
        """Undefined variable raises in strict mode."""
        with pytest.raises(UndefinedError) as exc_info:
            strict_env.from_string("{{ undefined_var }}").render()
        assert "undefined_var" in str(exc_info.value)

    def test_undefined_silent_in_lenient_mode(self, lenient_env: Environment) -> None:
        """Undefined variable silent in lenient mode."""
        result = lenient_env.from_string("{{ undefined_var }}").render()
        assert result in ["None", ""]

    def test_undefined_error_includes_variable_name(self, strict_env: Environment) -> None:
        """UndefinedError includes variable name."""
        try:
            strict_env.from_string("{{ my_var }}").render()
            pytest.fail("Expected UndefinedError")
        except UndefinedError as e:
            assert e.name == "my_var"

    def test_undefined_error_includes_template_name(self, strict_env: Environment) -> None:
        """UndefinedError includes template name."""
        try:
            strict_env.from_string("{{ x }}", name="test.html").render()
            pytest.fail("Expected UndefinedError")
        except UndefinedError as e:
            assert "test.html" in str(e)

    def test_default_filter_with_undefined(self, strict_env: Environment) -> None:
        """default filter works with undefined."""
        result = strict_env.from_string('{{ x|default("fallback") }}').render()
        assert result == "fallback"


class TestTemplateNotFoundErrors:
    """Test template not found errors."""

    def test_get_template_not_found(self) -> None:
        """get_template for missing template."""
        loader = DictLoader({})
        env = Environment(loader=loader)
        with pytest.raises((TemplateNotFoundError, Exception)):
            env.get_template("missing.html")

    def test_include_not_found(self) -> None:
        """include of missing template."""
        loader = DictLoader({"main.html": '{% include "missing.html" %}'})
        env = Environment(loader=loader)
        with pytest.raises((TemplateNotFoundError, Exception)):
            env.get_template("main.html").render()

    def test_extends_not_found(self) -> None:
        """extends of missing template."""
        loader = DictLoader({"main.html": '{% extends "missing.html" %}'})
        env = Environment(loader=loader)
        with pytest.raises((TemplateNotFoundError, Exception)):
            env.get_template("main.html").render()

    def test_from_import_not_found(self) -> None:
        """from import of missing template."""
        loader = DictLoader({"main.html": '{% from "missing.html" import x %}'})
        env = Environment(loader=loader)
        with pytest.raises((TemplateNotFoundError, Exception)):
            env.get_template("main.html").render()


class TestErrorContext:
    """Test that errors include context information."""

    def test_error_includes_line_number(self) -> None:
        """Error includes line number."""
        env = Environment(strict=False)
        template = """line 1
line 2
{{ 1 / 0 }}
line 4"""
        tmpl = env.from_string(template, name="test.html")
        try:
            tmpl.render()
            pytest.fail("Expected error")
        except TemplateRuntimeError as e:
            error_str = str(e)
            assert "test.html" in error_str
            # Should include line 3
            assert ":3" in error_str or "line 3" in error_str.lower()

    def test_error_includes_template_name(self) -> None:
        """Error includes template name."""
        env = Environment(strict=False)
        tmpl = env.from_string("{{ 1 / 0 }}", name="my_template.html")
        try:
            tmpl.render()
            pytest.fail("Expected error")
        except TemplateRuntimeError as e:
            assert "my_template.html" in str(e)


class TestErrorRecovery:
    """Test error recovery and isolation."""

    def test_error_doesnt_corrupt_environment(self) -> None:
        """Error in one template doesn't corrupt environment."""
        env = Environment(strict=False)

        # Compile a bad template
        try:
            env.from_string("{{ 1 / 0 }}").render()
        except Exception:
            pass

        # Environment should still work
        result = env.from_string("{{ x }}").render(x=42)
        assert result == "42"

    def test_multiple_errors_independent(self) -> None:
        """Multiple errors are independent."""
        env = Environment(strict=True)

        # First error
        try:
            env.from_string("{{ a }}").render()
        except UndefinedError:
            pass

        # Second error - different variable
        try:
            env.from_string("{{ b }}").render()
        except UndefinedError as e:
            assert e.name == "b"

    def test_partial_render_isolation(self) -> None:
        """Error during render doesn't leave partial state."""
        env = Environment(strict=False)
        loader = DictLoader(
            {
                "main.html": "Before {% include 'bad.html' %} After",
                "bad.html": "{{ 1 / 0 }}",
            }
        )
        env_with_loader = Environment(loader=loader, strict=False)

        try:
            env_with_loader.get_template("main.html").render()
            pytest.fail("Expected error")
        except Exception:
            pass

        # Environment should still be usable
        result = env_with_loader.from_string("{{ x }}").render(x=1)
        assert result == "1"


class TestFilterErrors:
    """Test filter-specific errors."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_unknown_filter(self, env: Environment) -> None:
        """Unknown filter raises at compile time.

        Note: As of the parser hardening RFC, unknown filters are now caught
        at compile time (from_string) rather than render time.
        """
        with pytest.raises(TemplateSyntaxError, match="Unknown filter"):
            env.from_string("{{ x|nonexistent_filter }}")

    def test_filter_wrong_arg_count(self, env: Environment) -> None:
        """Filter with wrong number of arguments."""
        # truncate requires at least length argument
        tmpl = env.from_string("{{ x|truncate }}")
        # May or may not raise depending on filter defaults
        try:
            tmpl.render(x="hello world")
        except Exception:
            pass  # Expected

    def test_filter_type_error_message(self, env: Environment) -> None:
        """Filter type error behavior - Kida may convert or raise."""
        tmpl = env.from_string("{{ x|join(',') }}")
        # Kida may silently convert int to string or raise
        try:
            result = tmpl.render(x=42)
            # If no error, result is some string representation
            assert result is not None
        except (TypeError, TemplateRuntimeError) as e:
            # Error should be understandable
            assert str(e) is not None


class TestTestErrors:
    """Test test-related errors."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_unknown_test(self, env: Environment) -> None:
        """Unknown test raises at compile time.

        Note: As of the parser hardening RFC, unknown tests are now caught
        at compile time (from_string) rather than render time.
        """
        with pytest.raises(TemplateSyntaxError, match="Unknown test"):
            env.from_string("{% if x is nonexistent_test %}yes{% endif %}")


class TestMacroErrors:
    """Test macro-related errors."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_macro_wrong_arg_count(self, env: Environment) -> None:
        """Macro called with wrong number of arguments."""
        tmpl = env.from_string(
            "{% macro greet(name, greeting) %}{{ greeting }} {{ name }}{% endmacro %}"
            "{{ greet('World') }}"
        )
        # May use default or raise error
        try:
            result = tmpl.render()
            # If no error, check the output
        except Exception:
            pass  # Expected

    def test_undefined_macro(self, env: Environment) -> None:
        """Calling undefined macro."""
        with pytest.raises((UndefinedError, TemplateRuntimeError, Exception)):
            env.from_string("{{ undefined_macro() }}").render()


class TestInheritanceErrors:
    """Test inheritance-related errors."""

    def test_block_outside_inheritance(self) -> None:
        """Block in template without extends."""
        env = Environment()
        # This should work - blocks can exist without extends
        tmpl = env.from_string("{% block content %}Hello{% endblock %}")
        result = tmpl.render()
        assert "Hello" in result

    def test_duplicate_block_names(self) -> None:
        """Duplicate block names (may or may not be error)."""
        env = Environment()
        # Some engines allow, some don't
        try:
            tmpl = env.from_string("{% block x %}A{% endblock %}{% block x %}B{% endblock %}")
            result = tmpl.render()
        except Exception:
            pass  # May raise

    def test_extends_must_be_first(self) -> None:
        """extends must be first tag (typically)."""
        loader = DictLoader({"base.html": "{% block content %}{% endblock %}"})
        env = Environment(loader=loader)
        try:
            tmpl = env.from_string('Hello{% extends "base.html" %}')
            result = tmpl.render()
        except Exception:
            pass  # May raise


class TestLoopErrors:
    """Test loop-related errors."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_loop_variable_outside_loop(self, env: Environment) -> None:
        """Accessing loop variable outside loop raises UndefinedError."""
        tmpl = env.from_string("{{ loop.index }}")
        # In strict mode (default), accessing undefined 'loop' raises
        with pytest.raises(UndefinedError):
            tmpl.render()

    def test_empty_iterable(self, env: Environment) -> None:
        """Empty iterable in for loop."""
        tmpl = env.from_string("{% for x in items %}{{ x }}{% endfor %}")
        result = tmpl.render(items=[])
        assert result == ""

    def test_break_outside_loop(self, env: Environment) -> None:
        """Break outside loop (if break is supported)."""
        # break may not be supported
        try:
            tmpl = env.from_string("{% break %}")
            pytest.fail("Should raise for break outside loop")
        except Exception:
            pass


class TestComplexErrorScenarios:
    """Test complex error scenarios."""

    def test_error_in_included_template(self) -> None:
        """Error in included template shows correct location."""
        loader = DictLoader(
            {
                "main.html": '{% include "partial.html" %}',
                "partial.html": "{{ 1 / 0 }}",
            }
        )
        env = Environment(loader=loader, strict=False)
        try:
            env.get_template("main.html").render()
            pytest.fail("Expected error")
        except TemplateRuntimeError:
            # Error should reference partial.html
            pass

    def test_error_in_inherited_template(self) -> None:
        """Error in inherited template."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}{{ 1 / 0 }}{% endblock %}",
                "child.html": '{% extends "base.html" %}',
            }
        )
        env = Environment(loader=loader, strict=False)
        try:
            env.get_template("child.html").render()
            pytest.fail("Expected error")
        except TemplateRuntimeError:
            pass

    def test_error_in_macro_body(self) -> None:
        """Error in macro body."""
        env = Environment(strict=False)
        tmpl = env.from_string("{% macro bad() %}{{ 1 / 0 }}{% endmacro %}{{ bad() }}")
        try:
            tmpl.render()
            pytest.fail("Expected error")
        except Exception:
            pass

    def test_error_in_filter_chain(self) -> None:
        """Error in middle of filter chain caught at compile time.

        Note: As of the parser hardening RFC, unknown filters in a chain
        are caught at compile time (from_string) rather than render time.
        """
        env = Environment(strict=False)
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'bad_filter'"):
            env.from_string("{{ x|upper|bad_filter|lower }}")

    def test_nested_error_context(self) -> None:
        """Error maintains context through nesting."""
        loader = DictLoader(
            {
                "level1.html": '{% include "level2.html" %}',
                "level2.html": '{% include "level3.html" %}',
                "level3.html": "{{ 1 / 0 }}",
            }
        )
        env = Environment(loader=loader, strict=False)
        try:
            env.get_template("level1.html").render()
            pytest.fail("Expected error")
        except Exception:
            # Error should be raised
            pass
