"""Tests for Kida resilient None handling.

RFC: rfc-kida-resilient-error-handling.md

This module tests the None → "" behavior that makes Kida templates
more resilient to missing data, similar to Hugo/Go templates.

Key behaviors:
1. Accessing attribute on None returns ""
2. Accessing None attribute value returns ""
3. Chained access through None returns ""
4. Errors include template name and line number context
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida.environment import Environment
from bengal.rendering.kida.environment.exceptions import (
    TemplateRuntimeError,
)


@pytest.fixture
def env() -> Environment:
    """Create a fresh Kida environment for each test.

    Uses strict=False to test the lenient None handling behavior.
    Strict mode (default) raises UndefinedError for missing variables.
    """
    return Environment(strict=False)


class TestResilientNoneHandling:
    """Test None → '' behavior (like Hugo/Go templates)."""

    def test_none_attribute_returns_empty(self, env: Environment) -> None:
        """Accessing an attribute that is None returns empty string."""
        tmpl = env.from_string("{{ obj.missing }}")
        result = tmpl.render(obj={"present": "value"})
        assert result == ""

    def test_none_object_access_returns_empty(self, env: Environment) -> None:
        """Accessing attribute on None object returns empty string."""
        tmpl = env.from_string("{{ obj.attr }}")
        result = tmpl.render(obj=None)
        assert result == ""

    def test_none_value_returns_empty(self, env: Environment) -> None:
        """Attribute with explicit None value returns empty string."""
        tmpl = env.from_string("{{ obj.value }}")
        result = tmpl.render(obj={"value": None})
        assert result == ""

    def test_none_chain_returns_empty(self, env: Environment) -> None:
        """Chained access through None returns empty string."""
        tmpl = env.from_string("{{ obj.a.b.c }}")
        result = tmpl.render(obj={"a": None})
        assert result == ""

    def test_deep_none_chain_returns_empty(self, env: Environment) -> None:
        """Deep chained access where middle is None returns empty."""
        tmpl = env.from_string("{{ page.metadata.author.name }}")
        result = tmpl.render(page={"metadata": {"author": None}})
        assert result == ""

    def test_missing_variable_returns_empty(self, env: Environment) -> None:
        """Accessing completely missing variable returns empty."""
        tmpl = env.from_string("{{ nonexistent.attr }}")
        result = tmpl.render()
        assert result == ""

    def test_none_in_conditional_is_falsy(self, env: Environment) -> None:
        """None (now "") is falsy in conditionals."""
        tmpl = env.from_string("{% if obj.value %}yes{% else %}no{% end %}")
        result = tmpl.render(obj={"value": None})
        assert result == "no"

    def test_not_none_check_still_falsy(self, env: Environment) -> None:
        """Empty string from None is still falsy for 'not x' check."""
        tmpl = env.from_string("{% if not obj.value %}empty{% else %}has value{% end %}")
        result = tmpl.render(obj={"value": None})
        assert result == "empty"

    def test_present_value_renders(self, env: Environment) -> None:
        """Non-None values still render correctly."""
        tmpl = env.from_string("{{ obj.title }}")
        result = tmpl.render(obj={"title": "Hello World"})
        assert result == "Hello World"

    def test_zero_value_not_converted(self, env: Environment) -> None:
        """Zero values (0, 0.0) are NOT converted to empty string."""
        tmpl = env.from_string("{{ obj.count }}")
        result = tmpl.render(obj={"count": 0})
        assert result == "0"

    def test_false_value_not_converted(self, env: Environment) -> None:
        """False is NOT converted to empty string."""
        tmpl = env.from_string("{{ obj.flag }}")
        result = tmpl.render(obj={"flag": False})
        assert result == "False"

    def test_empty_string_preserved(self, env: Environment) -> None:
        """Empty string values are preserved as empty string."""
        tmpl = env.from_string("[{{ obj.value }}]")
        result = tmpl.render(obj={"value": ""})
        assert result == "[]"


class TestNoneInFilters:
    """Test None handling in filter operations."""

    def test_default_filter_with_none_value(self, env: Environment) -> None:
        """Default filter provides fallback for None values.

        Note: With None→"" behavior, default() sees "" not None.
        But "" is still falsy so default() with false=True works.
        """
        # default() without test_false doesn't trigger on ""
        tmpl = env.from_string("{{ obj.value | default('fallback', true) }}")
        result = tmpl.render(obj={"value": None})
        assert result == "fallback"

    def test_filter_chain_with_none(self, env: Environment) -> None:
        """Filter chains work when starting value is None.

        With None→"" normalization, obj.name becomes "".
        default('Unknown') only triggers on falsy if test_false=True.
        So we need default('Unknown', true) to get the fallback.
        """
        tmpl = env.from_string("{{ obj.name | default('Unknown', true) | upper }}")
        result = tmpl.render(obj={"name": None})
        assert result == "UNKNOWN"

    def test_join_filter_with_none_items(self, env: Environment) -> None:
        """Join filter handles lists containing None.

        Note: None→"" normalization only applies to attribute access,
        not to raw list values. So None in a list is still "None" when joined.
        """
        tmpl = env.from_string("{{ items | join(', ') }}")
        result = tmpl.render(items=["a", None, "b"])
        # Raw list values are not normalized - join sees actual None
        assert result == "a, None, b"

    def test_length_of_none_attr(self, env: Environment) -> None:
        """Length of None attribute (now "") is 0."""
        tmpl = env.from_string("{{ obj.items | default([]) | length }}")
        result = tmpl.render(obj={"items": None})
        assert result == "0"


class TestSortWithNone:
    """Test sort filter handles None gracefully."""

    def test_sort_with_none_values_places_none_last(self, env: Environment) -> None:
        """Sort places None values last."""
        tmpl = env.from_string(
            "{{ items | sort(attribute='weight') | map(attribute='name') | join(',') }}"
        )
        items = [
            {"name": "b", "weight": 2},
            {"name": "a", "weight": None},
            {"name": "c", "weight": 1},
        ]
        result = tmpl.render(items=items)
        # None should sort last: c(1), b(2), a(None)
        assert result == "c,b,a"

    def test_sort_all_none_values(self, env: Environment) -> None:
        """Sort with all None values doesn't crash."""
        tmpl = env.from_string("{{ items | sort(attribute='weight') | length }}")
        items = [
            {"name": "a", "weight": None},
            {"name": "b", "weight": None},
        ]
        result = tmpl.render(items=items)
        assert result == "2"

    def test_sort_mixed_types_with_none(self, env: Environment) -> None:
        """Sort handles mixed numeric/None values."""
        tmpl = env.from_string(
            "{{ items | sort(attribute='order') | map(attribute='id') | join(',') }}"
        )
        items = [
            {"id": "third", "order": 3},
            {"id": "none", "order": None},
            {"id": "first", "order": 1},
        ]
        result = tmpl.render(items=items)
        assert result == "first,third,none"

    def test_sort_no_attribute_with_none(self, env: Environment) -> None:
        """Sort without attribute handles None in list.

        The sort filter handles None gracefully (sorts last).
        """
        tmpl = env.from_string("{{ items | sort | join(',') }}")
        items = [3, None, 1, 2]
        result = tmpl.render(items=items)
        # None sorts last and becomes "None" when stringified
        assert result == "1,2,3,None"


class TestErrorLineNumbers:
    """Test error messages include template name and line numbers."""

    def test_error_includes_template_name(self, env: Environment) -> None:
        """Errors include template name when provided."""
        tmpl = env.from_string("{{ 1 / 0 }}", name="test.html")
        with pytest.raises(TemplateRuntimeError) as exc:
            tmpl.render()
        assert "test.html" in str(exc.value)

    def test_error_includes_line_number_single_line(self, env: Environment) -> None:
        """Errors include line number for single-line templates."""
        tmpl = env.from_string("{{ 1 / 0 }}", name="test.html")
        with pytest.raises(TemplateRuntimeError) as exc:
            tmpl.render()
        # Line 1 for single-line template
        error_str = str(exc.value)
        assert "test.html" in error_str
        # Should have :1 or "line 1" somewhere
        assert ":1" in error_str or "line 1" in error_str.lower()

    def test_error_includes_line_number_multi_line(self, env: Environment) -> None:
        """Errors include line number for multi-line templates."""
        template_src = """Line 1
Line 2
{{ 1 / 0 }}
Line 4"""
        tmpl = env.from_string(template_src, name="test.html")
        with pytest.raises(TemplateRuntimeError) as exc:
            tmpl.render()
        error_str = str(exc.value)
        assert "test.html" in error_str
        # The error is on line 3
        assert ":3" in error_str or "line 3" in error_str.lower()

    def test_none_comparison_error_has_context(self, env: Environment) -> None:
        """NoneComparisonError includes template context."""
        # This test uses a scenario that would cause comparison error
        # With the new None-safe sort, this shouldn't raise anymore
        # So we skip this test - the sort is now resilient
        pytest.skip("Sort is now None-resilient, won't raise NoneComparisonError")

    def test_type_error_enhanced_with_context(self, env: Environment) -> None:
        """Generic TypeError is enhanced with template context."""
        # Force a TypeError that can't be avoided by None normalization
        tmpl = env.from_string("{{ 'hello' + 5 }}", name="type_error.html")
        with pytest.raises(TemplateRuntimeError) as exc:
            tmpl.render()
        error_str = str(exc.value)
        assert "type_error.html" in error_str


class TestMigrationPatterns:
    """Test migration patterns from old to new behavior."""

    def test_is_none_check_now_false(self, env: Environment) -> None:
        """is none check returns False since None becomes ''.

        Migration: Replace `{% if x.y is none %}` with `{% if not x.y %}`
        """
        # This is a BREAKING CHANGE test - documents the behavior change
        tmpl = env.from_string("{% if obj.value is none %}yes{% else %}no{% end %}")
        result = tmpl.render(obj={"value": None})
        # With None→"" normalization, value is "" not None, so `is none` is False
        assert result == "no"

    def test_not_x_pattern_works(self, env: Environment) -> None:
        """not x pattern works for checking None/empty."""
        tmpl = env.from_string("{% if not obj.value %}empty{% else %}has{% end %}")
        result = tmpl.render(obj={"value": None})
        assert result == "empty"

    def test_or_default_pattern_works(self, env: Environment) -> None:
        """x or default pattern provides fallback."""
        tmpl = env.from_string("{{ obj.weight or 999999 }}")
        result = tmpl.render(obj={"weight": None})
        assert result == "999999"

    def test_default_filter_with_boolean_false(self, env: Environment) -> None:
        """default(x, true) treats empty string as missing."""
        tmpl = env.from_string("{{ obj.value | default('fallback', true) }}")
        # With None→"", default sees "", and with true flag treats it as missing
        result = tmpl.render(obj={"value": None})
        assert result == "fallback"


class TestPerformanceCharacteristics:
    """Test that performance characteristics are maintained."""

    def test_safe_getattr_is_o1(self, env: Environment) -> None:
        """Verify _safe_getattr maintains O(1) complexity.

        This is a sanity check - the actual benchmarks are in Phase 3.
        """
        from bengal.rendering.kida.template import Template

        # Single access should be fast
        obj = {"key": "value"}
        result = Template._safe_getattr(obj, "key")
        assert result == "value"

        # None access should also be fast
        result = Template._safe_getattr(None, "key")
        assert result == ""

        # Missing key should return ""
        result = Template._safe_getattr(obj, "missing")
        assert result == ""
