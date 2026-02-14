"""
Unit tests for CascadingParamsContext.

Verifies page → section → site cascade order, nested dict wrapping,
and edge cases for template params resolution.
"""

from __future__ import annotations

import pytest

from bengal.rendering.context.data_wrappers import CascadingParamsContext


class TestCascadeOrder:
    """Test that page overrides section overrides site."""

    def test_page_overrides_section_and_site(self) -> None:
        """Page value wins when present at all levels."""
        ctx = CascadingParamsContext(
            page_params={"author": "Jane Doe"},
            section_params={"author": "Blog Team"},
            site_params={"author": "Acme Corp"},
        )
        assert ctx.author == "Jane Doe"
        assert ctx["author"] == "Jane Doe"

    def test_section_overrides_site_when_page_missing(self) -> None:
        """Section value wins when page has no value."""
        ctx = CascadingParamsContext(
            page_params={},
            section_params={"author": "Blog Team"},
            site_params={"author": "Acme Corp"},
        )
        assert ctx.author == "Blog Team"

    def test_site_used_when_page_and_section_missing(self) -> None:
        """Site value used when only defined at site level."""
        ctx = CascadingParamsContext(
            page_params={},
            section_params={},
            site_params={"company": "Acme Corp"},
        )
        assert ctx.company == "Acme Corp"

    def test_page_only(self) -> None:
        """Page-only params work with empty section/site."""
        ctx = CascadingParamsContext(
            page_params={"title": "My Post"},
            section_params=None,
            site_params=None,
        )
        assert ctx.title == "My Post"


class TestMissingKeys:
    """Test behavior for missing keys."""

    def test_getattr_returns_none_for_missing(self) -> None:
        """__getattr__ returns None for keys not in any level."""
        ctx = CascadingParamsContext(
            page_params={"a": 1},
            section_params={},
            site_params={},
        )
        assert ctx.missing is None
        assert ctx["nonexistent"] is None

    def test_get_returns_default_for_missing(self) -> None:
        """get() returns default when key not in cascade."""
        ctx = CascadingParamsContext(
            page_params={},
            section_params={},
            site_params={},
        )
        assert ctx.get("missing") == ""
        assert ctx.get("missing", "fallback") == "fallback"

    def test_get_returns_default_when_value_is_none(self) -> None:
        """get() returns default when key exists but value is None."""
        ctx = CascadingParamsContext(
            page_params={"author": None},
            section_params={},
            site_params={},
        )
        assert ctx.get("author", "Anonymous") == "Anonymous"


class TestNestedDicts:
    """Test recursive wrapping of nested dicts with cascade."""

    def test_nested_dict_wrapped_from_page(self) -> None:
        """Nested dict at page level is wrapped and cascades."""
        ctx = CascadingParamsContext(
            page_params={"author": {"name": "Jane", "role": "Writer"}},
            section_params={"author": {"name": "Blog Team", "role": "Editor"}},
            site_params={"author": {"name": "Acme", "role": "Publisher"}},
        )
        assert ctx.author.name == "Jane"
        assert ctx.author.role == "Writer"

    def test_nested_dict_from_section_when_page_missing(self) -> None:
        """Nested dict at section level used when page has no author."""
        ctx = CascadingParamsContext(
            page_params={},
            section_params={"author": {"name": "Blog Team", "role": "Editor"}},
            site_params={"author": {"name": "Acme", "role": "Publisher"}},
        )
        assert ctx.author.name == "Blog Team"
        assert ctx.author.role == "Editor"

    def test_nested_dict_from_site_when_page_and_section_missing(self) -> None:
        """Nested dict at site level used when only defined there."""
        ctx = CascadingParamsContext(
            page_params={},
            section_params={},
            site_params={"author": {"name": "Acme", "role": "Publisher"}},
        )
        assert ctx.author.name == "Acme"
        assert ctx.author.role == "Publisher"

    def test_nested_dict_cached_on_repeated_access(self) -> None:
        """Wrapped nested dict is cached; same instance returned."""
        ctx = CascadingParamsContext(
            page_params={"meta": {"key": "value"}},
            section_params={},
            site_params={},
        )
        first = ctx.meta
        second = ctx.meta
        assert first is second


class TestContainsAndBool:
    """Test __contains__ and __bool__."""

    def test_contains_checks_all_levels(self) -> None:
        """Key in any level returns True."""
        ctx = CascadingParamsContext(
            page_params={},
            section_params={"b": 2},
            site_params={"c": 3},
        )
        assert "b" in ctx
        assert "c" in ctx
        assert "a" not in ctx

    def test_bool_false_when_all_empty(self) -> None:
        """Empty context is falsy."""
        ctx = CascadingParamsContext()
        assert bool(ctx) is False

    def test_bool_true_when_any_level_has_data(self) -> None:
        """Context is truthy if any level has keys."""
        ctx = CascadingParamsContext(
            page_params={},
            section_params={},
            site_params={"x": 1},
        )
        assert bool(ctx) is True


class TestIterationAndKeys:
    """Test __iter__, keys(), and items()."""

    def test_keys_union_from_all_levels(self) -> None:
        """keys() returns union of all levels."""
        ctx = CascadingParamsContext(
            page_params={"a": 1, "b": 2},
            section_params={"b": 20, "c": 3},
            site_params={"c": 30, "d": 4},
        )
        assert ctx.keys() == {"a", "b", "c", "d"}

    def test_iter_yields_unique_keys_page_first(self) -> None:
        """__iter__ yields keys in page, section, site order, deduplicated."""
        ctx = CascadingParamsContext(
            page_params={"a": 1},
            section_params={"b": 2},
            site_params={"c": 3},
        )
        assert list(ctx) == ["a", "b", "c"]

    def test_items_respects_cascade_override_order(self) -> None:
        """items() merges site → section → page with overrides."""
        ctx = CascadingParamsContext(
            page_params={"author": "Jane"},
            section_params={"author": "Blog Team", "company": "Blog Inc"},
            site_params={"author": "Acme", "company": "Acme Corp"},
        )
        items = dict(ctx.items())
        assert items["author"] == "Jane"
        assert items["company"] == "Blog Inc"


class TestPrivateAttributes:
    """Test that _* names bypass normal lookup."""

    def test_private_attrs_not_exposed_via_getattr(self) -> None:
        """Names starting with _ use object.__getattribute__, not cascade."""
        ctx = CascadingParamsContext(
            page_params={"_page": "should not shadow"},
            section_params={},
            site_params={},
        )
        # _page in page_params is a string; internal _page is the dict
        assert isinstance(ctx._page, dict)
        assert ctx._page == {"_page": "should not shadow"}


class TestRepr:
    """Test __repr__."""

    def test_repr_shows_all_levels(self) -> None:
        """__repr__ includes page, section, site."""
        ctx = CascadingParamsContext(
            page_params={"a": 1},
            section_params={"b": 2},
            site_params={"c": 3},
        )
        r = repr(ctx)
        assert "page=" in r
        assert "section=" in r
        assert "site=" in r
