"""Tests for Kida compile-time validation of filters and tests.

Verifies that unknown filters and tests are caught at compile time
(during env.from_string()) rather than at render time.
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida.environment import Environment
from bengal.rendering.kida.environment.exceptions import TemplateSyntaxError


@pytest.fixture
def env() -> Environment:
    """Create a fresh Environment for each test."""
    return Environment()


class TestFilterCompileTimeValidation:
    """Compile-time validation for filters."""

    def test_unknown_filter_raises_at_compile_time(self, env: Environment) -> None:
        """Unknown filter should raise TemplateSyntaxError during compilation."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'typo'"):
            env.from_string("{{ x|typo }}")

    def test_unknown_filter_suggests_similar_upper(self, env: Environment) -> None:
        """Typo in filter name should suggest similar filter (upper -> uper)."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean 'upper'"):
            env.from_string("{{ x|uper }}")

    def test_unknown_filter_suggests_similar_lower(self, env: Environment) -> None:
        """Typo in filter name should suggest similar filter (lower -> lowr)."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean 'lower'"):
            env.from_string("{{ x|lowr }}")

    def test_unknown_filter_suggests_similar_title(self, env: Environment) -> None:
        """Typo in filter name should suggest similar filter (title -> titel)."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean 'title'"):
            env.from_string("{{ x|titel }}")

    def test_unknown_filter_no_suggestion_when_distant(self, env: Environment) -> None:
        """Very different filter name should not suggest alternatives."""
        with pytest.raises(TemplateSyntaxError) as exc_info:
            env.from_string("{{ x|xyzabc }}")
        assert "Did you mean" not in str(exc_info.value)

    def test_known_filter_compiles_successfully(self, env: Environment) -> None:
        """Known filters should compile without error."""
        # These should not raise
        tmpl = env.from_string("{{ x|upper }}")
        assert tmpl.render(x="hello") == "HELLO"

        tmpl = env.from_string("{{ x|lower }}")
        assert tmpl.render(x="HELLO") == "hello"

    def test_default_filter_compiles_in_strict_mode(self, env: Environment) -> None:
        """Default filter should compile in strict mode."""
        tmpl = env.from_string("{{ x|default('fallback') }}")
        assert tmpl.render(x=None) == "fallback"

    def test_chained_filters_validates_all(self, env: Environment) -> None:
        """Chained filters should validate each filter."""
        # First filter valid, second unknown
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'unkwn'"):
            env.from_string("{{ x|upper|unkwn }}")

    def test_filter_with_args_validates(self, env: Environment) -> None:
        """Filter with arguments should still validate."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'formatt'"):
            env.from_string("{{ x|formatt('%Y-%m-%d') }}")


class TestTestCompileTimeValidation:
    """Compile-time validation for tests (is odd, is even, etc.)."""

    def test_unknown_test_raises_at_compile_time(self, env: Environment) -> None:
        """Unknown test should raise TemplateSyntaxError during compilation."""
        with pytest.raises(TemplateSyntaxError, match="Unknown test 'typo'"):
            env.from_string("{% if x is typo %}yes{% endif %}")

    def test_unknown_test_suggests_similar_odd(self, env: Environment) -> None:
        """Typo in test name should suggest similar test (odd -> od)."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean 'odd'"):
            env.from_string("{% if x is od %}yes{% endif %}")

    def test_unknown_test_suggests_similar_even(self, env: Environment) -> None:
        """Typo in test name should suggest similar test (even -> evn)."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean 'even'"):
            env.from_string("{% if x is evn %}yes{% endif %}")

    def test_unknown_test_no_suggestion_when_distant(self, env: Environment) -> None:
        """Very different test name should not suggest alternatives."""
        with pytest.raises(TemplateSyntaxError) as exc_info:
            env.from_string("{% if x is xyzabc %}yes{% endif %}")
        assert "Did you mean" not in str(exc_info.value)

    def test_known_test_compiles_successfully(self, env: Environment) -> None:
        """Known tests should compile without error."""
        # These should not raise
        tmpl = env.from_string("{% if x is odd %}odd{% else %}even{% endif %}")
        assert tmpl.render(x=3) == "odd"
        assert tmpl.render(x=4) == "even"

    def test_defined_test_works_in_strict_mode(self, env: Environment) -> None:
        """The 'defined' test should work in strict mode."""
        tmpl = env.from_string("{% if x is defined %}yes{% else %}no{% endif %}")
        assert tmpl.render(x=1) == "yes"
        assert tmpl.render() == "no"

    def test_undefined_test_works_in_strict_mode(self, env: Environment) -> None:
        """The 'undefined' test should work in strict mode."""
        tmpl = env.from_string("{% if x is undefined %}yes{% else %}no{% endif %}")
        assert tmpl.render() == "yes"
        assert tmpl.render(x=1) == "no"

    def test_negated_test_validates(self, env: Environment) -> None:
        """Negated tests should still validate the test name."""
        with pytest.raises(TemplateSyntaxError, match="Unknown test 'unkwn'"):
            env.from_string("{% if x is not unkwn %}yes{% endif %}")


class TestCompileTimeValidationEdgeCases:
    """Edge cases for compile-time validation."""

    def test_filter_in_for_loop_validates(self, env: Environment) -> None:
        """Filters inside for loops should validate."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'unkwn'"):
            env.from_string("{% for item in items|unkwn %}{{ item }}{% endfor %}")

    def test_filter_in_if_condition_validates(self, env: Environment) -> None:
        """Filters inside if conditions should validate."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'unkwn'"):
            env.from_string("{% if items|unkwn %}yes{% endif %}")

    def test_filter_in_macro_body_validates(self, env: Environment) -> None:
        """Filters inside macro bodies should validate."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'unkwn'"):
            env.from_string("{% macro foo(x) %}{{ x|unkwn }}{% endmacro %}")

    def test_filter_in_set_statement_validates(self, env: Environment) -> None:
        """Filters in set statements should validate."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter 'unkwn'"):
            env.from_string("{% set x = y|unkwn %}")

    def test_multiple_templates_validate_independently(self, env: Environment) -> None:
        """Each template should validate independently."""
        # First template with unknown filter
        with pytest.raises(TemplateSyntaxError):
            env.from_string("{{ x|unkwn }}")

        # Second template with known filter should still work
        tmpl = env.from_string("{{ x|upper }}")
        assert tmpl.render(x="hello") == "HELLO"

    def test_error_includes_lineno_when_available(self, env: Environment) -> None:
        """Error should include line number when available."""
        # Multi-line template
        template_src = """
{% set x = 1 %}
{% set y = 2 %}
{{ x|unknown_filter }}
"""
        with pytest.raises(TemplateSyntaxError) as exc_info:
            env.from_string(template_src)
        # Should mention the unknown filter
        assert "unknown_filter" in str(exc_info.value)
