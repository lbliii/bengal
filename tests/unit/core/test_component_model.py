"""
Tests for the Component Model (Identity/Mode/Data).
"""

from __future__ import annotations

from typing import Any

import pytest

from bengal.core.page import Page, PageCore


class TestPageCoreComponentModel:
    """Test Component Model fields in PageCore."""

    def test_new_fields(self) -> None:
        """Test that new fields (type, variant, props) are stored correctly."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            type="blog",
            variant="magazine",
            props={"author": "Jane"},
            description="A test page"
        )
        
        assert core.type == "blog"
        assert core.variant == "magazine"
        assert core.props == {"author": "Jane"}
        assert core.description == "A test page"

    def test_serialization(self) -> None:
        """Test that new fields survive serialization."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            type="doc",
            variant="editorial",
            props={"key": "value"},
            description="Desc"
        )
        
        data = core.to_cache_dict()
        restored = PageCore.from_cache_dict(data)
        
        assert restored.type == "doc"
        assert restored.variant == "editorial"
        assert restored.props == {"key": "value"}
        assert restored.description == "Desc"


class TestPageMetadataComponentModel:
    """Test Component Model logic in Page (via mixin)."""

    def test_legacy_normalization_layout(self, tmp_path: Path) -> None:
        """Test that layout maps to variant."""
        page = Page(
            source_path=tmp_path / "test.md",
            metadata={"layout": "grid", "title": "Test"}
        )
        # Should be available via .variant property
        assert page.variant == "grid"
        # And populated in core
        assert page.core.variant == "grid"

    def test_legacy_normalization_hero_style(self, tmp_path: Path) -> None:
        """Test that hero_style maps to variant."""
        page = Page(
            source_path=tmp_path / "test.md",
            metadata={"hero_style": "comic", "title": "Test"}
        )
        assert page.variant == "comic"
        assert page.core.variant == "comic"

    def test_variant_priority(self, tmp_path: Path) -> None:
        """Test that explicit variant beats legacy fields."""
        page = Page(
            source_path=tmp_path / "test.md",
            metadata={
                "variant": "modern",
                "layout": "old-grid",
                "title": "Test"
            }
        )
        assert page.variant == "modern"
        assert page.core.variant == "modern"

    def test_props_access(self, tmp_path: Path) -> None:
        """Test that metadata is accessible via props."""
        page = Page(
            source_path=tmp_path / "test.md",
            metadata={"title": "Test", "custom": "value"}
        )
        assert page.props["custom"] == "value"


