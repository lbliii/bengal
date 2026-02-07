"""Tests for the CascadeView immutable mapping view."""

import pytest

from bengal.core.cascade import CascadeSnapshot, CascadeView


class TestCascadeViewBasics:
    """Test basic CascadeView functionality."""

    def test_empty_view(self):
        """Test creating an empty cascade view."""
        view = CascadeView.empty()

        assert len(view) == 0
        assert "type" not in view
        with pytest.raises(KeyError):
            _ = view["type"]
        assert view.get("type") is None
        assert view.get("type", "default") == "default"

    def test_frontmatter_only(self):
        """Test view with only frontmatter values."""
        snapshot = CascadeSnapshot.empty()
        view = CascadeView.for_page(
            frontmatter={"title": "My Page", "type": "doc"},
            section_path="docs",
            snapshot=snapshot,
        )

        assert view["title"] == "My Page"
        assert view["type"] == "doc"
        assert view.get("unknown") is None
        assert len(view) == 2
        assert set(view.keys()) == {"title", "type"}

    def test_cascade_only(self):
        """Test view with only cascade values (no frontmatter)."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "variant": "standard"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={},
            section_path="docs",
            snapshot=snapshot,
        )

        assert view["type"] == "doc"
        assert view["variant"] == "standard"
        assert len(view) == 2
        assert set(view.keys()) == {"type", "variant"}

    def test_frontmatter_wins_over_cascade(self):
        """Test that frontmatter values override cascade values."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "variant": "standard", "layout": "docs"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"type": "tutorial", "title": "My Tutorial"},
            section_path="docs",
            snapshot=snapshot,
        )

        # Frontmatter wins for 'type'
        assert view["type"] == "tutorial"
        # Cascade provides 'variant' and 'layout'
        assert view["variant"] == "standard"
        assert view["layout"] == "docs"
        # Frontmatter provides 'title'
        assert view["title"] == "My Tutorial"

    def test_cascade_inheritance(self):
        """Test that cascade values are inherited from parent sections."""
        snapshot = CascadeSnapshot.from_data(
            {
                "docs": {"type": "doc", "version": "1.0"},
                "docs/tutorials": {"difficulty": "beginner"},
            },
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Getting Started"},
            section_path="docs/tutorials",
            snapshot=snapshot,
        )

        # Inherited from docs
        assert view["type"] == "doc"
        assert view["version"] == "1.0"
        # From docs/tutorials
        assert view["difficulty"] == "beginner"
        # From frontmatter
        assert view["title"] == "Getting Started"


class TestCascadeViewMappingProtocol:
    """Test Mapping protocol implementation."""

    def test_contains(self):
        """Test 'in' operator for membership testing."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test"},
            section_path="docs",
            snapshot=snapshot,
        )

        assert "title" in view  # frontmatter
        assert "type" in view  # cascade
        assert "unknown" not in view

    def test_iteration(self):
        """Test iterating over keys."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "variant": "standard"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test", "weight": 10},
            section_path="docs",
            snapshot=snapshot,
        )

        keys = list(view)
        # Should have all keys from both frontmatter and cascade
        assert set(keys) == {"title", "weight", "type", "variant"}
        # Frontmatter keys should come first
        assert keys[0] in {"title", "weight"}
        assert keys[1] in {"title", "weight"}

    def test_len(self):
        """Test length calculation."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "variant": "standard"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test", "type": "custom"},  # type overrides cascade
            section_path="docs",
            snapshot=snapshot,
        )

        # title, type (from frontmatter), variant (from cascade)
        # type is not double-counted
        assert len(view) == 3

    def test_keys_values_items(self):
        """Test keys(), values(), and items() methods."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test"},
            section_path="docs",
            snapshot=snapshot,
        )

        assert set(view.keys()) == {"title", "type"}
        assert set(view.values()) == {"Test", "doc"}
        assert set(view.items()) == {("title", "Test"), ("type", "doc")}

    def test_get_with_default(self):
        """Test get() method with various defaults."""
        view = CascadeView.empty()

        assert view.get("missing") is None
        assert view.get("missing", "default") == "default"
        assert view.get("missing", 0) == 0
        assert view.get("missing", []) == []


class TestCascadeViewProvenance:
    """Test provenance tracking methods."""

    def test_cascade_keys(self):
        """Test cascade_keys() returns keys from cascade only."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "variant": "standard", "layout": "docs"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test", "type": "custom"},  # type overrides
            section_path="docs",
            snapshot=snapshot,
        )

        cascade_keys = view.cascade_keys()
        # type is in frontmatter, so not in cascade_keys
        assert "type" not in cascade_keys
        # variant and layout are from cascade
        assert "variant" in cascade_keys
        assert "layout" in cascade_keys
        # title is frontmatter only
        assert "title" not in cascade_keys

    def test_frontmatter_keys(self):
        """Test frontmatter_keys() returns keys from frontmatter only."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test", "weight": 10},
            section_path="docs",
            snapshot=snapshot,
        )

        frontmatter_keys = view.frontmatter_keys()
        assert frontmatter_keys == frozenset({"title", "weight"})


class TestCascadeViewCompatibility:
    """Test compatibility methods for dict-like behavior."""

    def test_resolve_all(self):
        """Test resolve_all() materializes to dict."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "variant": "standard"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test"},
            section_path="docs",
            snapshot=snapshot,
        )

        result = view.resolve_all()
        assert isinstance(result, dict)
        assert result == {"title": "Test", "type": "doc", "variant": "standard"}

    def test_copy(self):
        """Test copy() returns mutable dict."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test"},
            section_path="docs",
            snapshot=snapshot,
        )

        copy = view.copy()
        assert isinstance(copy, dict)
        assert copy == {"title": "Test", "type": "doc"}

        # Copy should be mutable
        copy["new_key"] = "value"
        assert copy["new_key"] == "value"
        # Original view should be unaffected
        assert "new_key" not in view

    def test_dict_conversion(self):
        """Test converting view to dict via dict()."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test"},
            section_path="docs",
            snapshot=snapshot,
        )

        result = dict(view)
        assert result == {"title": "Test", "type": "doc"}


class TestCascadeViewImmutability:
    """Test that CascadeView is truly immutable."""

    def test_cannot_setitem(self):
        """Test that __setitem__ is not supported."""
        view = CascadeView.empty()

        with pytest.raises(TypeError):
            view["key"] = "value"

    def test_cannot_delitem(self):
        """Test that __delitem__ is not supported."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test"},
            section_path="docs",
            snapshot=snapshot,
        )

        with pytest.raises(TypeError):
            del view["title"]

    def test_frozen_dataclass(self):
        """Test that the dataclass is frozen."""
        view = CascadeView.empty()

        with pytest.raises(AttributeError):
            view._section_path = "new/path"


class TestCascadeViewEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_section_path(self):
        """Test view with empty/root section path."""
        snapshot = CascadeSnapshot.from_data(
            {"": {"type": "page"}},  # Root cascade
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Home"},
            section_path="",
            snapshot=snapshot,
        )

        assert view["title"] == "Home"
        assert view["type"] == "page"

    def test_deeply_nested_section(self):
        """Test view with deeply nested section path."""
        snapshot = CascadeSnapshot.from_data(
            {
                "": {"root": True},
                "a": {"level": 1},
                "a/b": {"level": 2},
                "a/b/c": {"level": 3},
            },
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Deep Page"},
            section_path="a/b/c/d",
            snapshot=snapshot,
        )

        # Should inherit from all ancestors
        assert view["root"] is True
        assert view["level"] == 3  # Closest ancestor wins

    def test_none_values_in_frontmatter(self):
        """Test handling of None values in frontmatter."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test", "description": None},
            section_path="docs",
            snapshot=snapshot,
        )

        # None is a valid frontmatter value
        assert view["description"] is None
        assert "description" in view

    def test_repr(self):
        """Test string representation."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "variant": "standard"}},
            content_dir="/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Test"},
            section_path="docs",
            snapshot=snapshot,
        )

        repr_str = repr(view)
        assert "CascadeView" in repr_str
        assert "docs" in repr_str
        assert "frontmatter=1" in repr_str
        assert "cascade=2" in repr_str
