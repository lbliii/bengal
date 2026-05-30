"""
Tests for the Component Model (Identity/Mode/Data).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.page.page_core import PageCore
from bengal.core.records import build_page_core

if TYPE_CHECKING:
    from pathlib import Path


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
            description="A test page",
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
            description="Desc",
        )

        data = core.to_cache_dict()
        restored = PageCore.from_cache_dict(data)

        assert restored.type == "doc"
        assert restored.variant == "editorial"
        assert restored.props == {"key": "value"}
        assert restored.description == "Desc"


class TestPageCoreMetadataComponentModel:
    """Test Component Model metadata normalization into PageCore."""

    def test_legacy_normalization_layout(self, tmp_path: Path) -> None:
        """Test that layout maps to variant."""
        core = build_page_core(tmp_path / "test.md", {"layout": "grid", "title": "Test"})

        assert core.variant == "grid"

    def test_legacy_normalization_hero_style(self, tmp_path: Path) -> None:
        """Test that hero_style maps to variant."""
        core = build_page_core(tmp_path / "test.md", {"hero_style": "comic", "title": "Test"})

        assert core.variant == "comic"

    def test_variant_priority(self, tmp_path: Path) -> None:
        """Test that explicit variant beats legacy fields."""
        core = build_page_core(
            tmp_path / "test.md",
            {"variant": "modern", "layout": "old-grid", "title": "Test"},
        )

        assert core.variant == "modern"

    def test_props_access(self, tmp_path: Path) -> None:
        """Test that metadata is accessible via props."""
        core = build_page_core(tmp_path / "test.md", {"title": "Test", "custom": "value"})

        assert core.props["custom"] == "value"
