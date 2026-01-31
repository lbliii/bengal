"""
Tests for Snapshot-Enabled v2 features.

RFC: Snapshot-Enabled v2 Opportunities

Tests cover:
- Opportunity 5: TemplateSnapshot and template dependency tracking
- Opportunity 6: ConfigSnapshot frozen typed configuration
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from bengal.config.snapshot import (
    AssetsSection,
    BuildSection,
    ConfigSnapshot,
    ContentSection,
    DevSection,
    FeaturesSection,
    SiteSection,
    ThemeSection,
)
from bengal.snapshots.types import TemplateSnapshot


# =============================================================================
# ConfigSnapshot Tests (Opportunity 6)
# =============================================================================


class TestConfigSnapshot:
    """Tests for ConfigSnapshot frozen configuration."""

    def test_from_dict_basic(self):
        """Test ConfigSnapshot creation from dict."""
        config = ConfigSnapshot.from_dict(
            {
                "site": {"title": "Test Site", "baseurl": "/test/"},
            }
        )

        assert config.site.title == "Test Site"
        assert config.site.baseurl == "/test/"

    def test_from_dict_with_build_section(self):
        """Test build section extraction."""
        config = ConfigSnapshot.from_dict(
            {
                "build": {
                    "parallel": False,
                    "incremental": True,
                    "output_dir": "dist",
                    "max_workers": 4,
                }
            }
        )

        assert config.build.parallel is False
        assert config.build.incremental is True
        assert config.build.output_dir == "dist"
        assert config.build.max_workers == 4

    def test_from_dict_with_theme_features(self):
        """Test theme section with features list."""
        config = ConfigSnapshot.from_dict(
            {
                "theme": {
                    "name": "custom",
                    "features": ["search", "toc", "graph"],
                    "default_appearance": "dark",
                }
            }
        )

        assert config.theme.name == "custom"
        assert config.theme.features == ("search", "toc", "graph")
        assert config.theme.default_appearance == "dark"

    def test_from_dict_with_dev_section(self):
        """Test dev section extraction."""
        config = ConfigSnapshot.from_dict(
            {
                "dev": {
                    "port": 3000,
                    "live_reload": False,
                }
            }
        )

        assert config.dev.port == 3000
        assert config.dev.live_reload is False

    def test_from_dict_applies_defaults(self):
        """Test that defaults are applied for missing values."""
        config = ConfigSnapshot.from_dict({})

        # Defaults from DEFAULTS
        assert config.site.title == "Bengal Site"
        assert config.build.parallel is True
        assert config.dev.port == 8000
        assert config.theme.name == "default"

    def test_frozen_immutability(self):
        """Test that ConfigSnapshot is truly frozen."""
        config = ConfigSnapshot.from_dict({"site": {"title": "Test"}})

        with pytest.raises(AttributeError):
            config.site = SiteSection(title="Modified")  # type: ignore[misc]

    def test_raw_dict_access(self):
        """Test raw dict access for custom sections."""
        config = ConfigSnapshot.from_dict(
            {
                "custom_section": {"key": "value"},
                "params": {"author": "Test Author"},
            }
        )

        assert config["custom_section"] == {"key": "value"}
        assert config.params["author"] == "Test Author"

    def test_get_with_default(self):
        """Test .get() method with default."""
        config = ConfigSnapshot.from_dict({})

        assert config.get("nonexistent") is None
        assert config.get("nonexistent", "default") == "default"

    def test_contains_check(self):
        """Test 'in' operator for key checking."""
        config = ConfigSnapshot.from_dict({"site": {"title": "Test"}})

        assert "site" in config
        assert "nonexistent" not in config


class TestConfigSectionImmutability:
    """Tests for section dataclass immutability."""

    def test_site_section_frozen(self):
        """Test SiteSection is frozen."""
        section = SiteSection(title="Test")

        with pytest.raises(AttributeError):
            section.title = "Modified"  # type: ignore[misc]

    def test_build_section_frozen(self):
        """Test BuildSection is frozen."""
        section = BuildSection(parallel=True)

        with pytest.raises(AttributeError):
            section.parallel = False  # type: ignore[misc]

    def test_theme_section_frozen(self):
        """Test ThemeSection is frozen."""
        section = ThemeSection(name="test")

        with pytest.raises(AttributeError):
            section.name = "modified"  # type: ignore[misc]


# =============================================================================
# TemplateSnapshot Tests (Opportunity 5)
# =============================================================================


class TestTemplateSnapshot:
    """Tests for TemplateSnapshot template dependency tracking."""

    def test_basic_creation(self):
        """Test basic TemplateSnapshot creation."""
        template = TemplateSnapshot(
            path=Path("templates/page.html"),
            name="page.html",
            extends="base.html",
            includes=("header.html", "footer.html"),
            imports=("macros.html",),
            blocks=("content", "title"),
            macros_defined=("render_nav",),
            macros_used=("nav_item",),
            content_hash="abc123",
            all_dependencies=frozenset({"base.html", "header.html", "footer.html", "macros.html"}),
        )

        assert template.name == "page.html"
        assert template.extends == "base.html"
        assert template.includes == ("header.html", "footer.html")
        assert "base.html" in template.all_dependencies

    def test_frozen_immutability(self):
        """Test that TemplateSnapshot is frozen."""
        template = TemplateSnapshot(
            path=Path("test.html"),
            name="test.html",
            extends=None,
            includes=(),
            imports=(),
            blocks=(),
            macros_defined=(),
            macros_used=(),
            content_hash="abc",
            all_dependencies=frozenset(),
        )

        with pytest.raises(AttributeError):
            template.name = "modified"  # type: ignore[misc]

    def test_no_extends_template(self):
        """Test template without extends."""
        template = TemplateSnapshot(
            path=Path("base.html"),
            name="base.html",
            extends=None,
            includes=("nav.html",),
            imports=(),
            blocks=("body", "head"),
            macros_defined=(),
            macros_used=(),
            content_hash="xyz",
            all_dependencies=frozenset({"nav.html"}),
        )

        assert template.extends is None
        assert "nav.html" in template.all_dependencies

    def test_dependency_frozenset(self):
        """Test that dependencies are a frozenset."""
        template = TemplateSnapshot(
            path=Path("test.html"),
            name="test.html",
            extends="base.html",
            includes=(),
            imports=(),
            blocks=(),
            macros_defined=(),
            macros_used=(),
            content_hash="abc",
            all_dependencies=frozenset({"base.html", "shared.html"}),
        )

        # frozenset is hashable and immutable
        assert isinstance(template.all_dependencies, frozenset)
        assert len(template.all_dependencies) == 2


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.bengal(testroot="test-basic")
class TestSnapshotV2Integration:
    """Integration tests for v2 snapshot features."""

    def test_site_snapshot_has_config_snapshot(self, site, build_site):
        """Test that SiteSnapshot includes config_snapshot field."""
        from bengal.snapshots import create_site_snapshot

        build_site()
        snapshot = create_site_snapshot(site)

        # config_snapshot should be populated
        assert snapshot.config_snapshot is not None
        assert isinstance(snapshot.config_snapshot, ConfigSnapshot)

        # Should have typed access
        assert snapshot.config_snapshot.site.title is not None
        assert isinstance(snapshot.config_snapshot.build.parallel, bool)

    def test_site_snapshot_has_template_snapshots(self, site, build_site):
        """Test that SiteSnapshot includes template snapshots."""
        from bengal.snapshots import create_site_snapshot

        build_site()
        snapshot = create_site_snapshot(site)

        # templates should be a MappingProxyType
        assert isinstance(snapshot.templates, MappingProxyType)

        # template_dependency_graph should be populated
        assert isinstance(snapshot.template_dependency_graph, MappingProxyType)

        # template_dependents should be populated
        assert isinstance(snapshot.template_dependents, MappingProxyType)

    def test_legacy_config_dict_still_works(self, site, build_site):
        """Test that legacy config dict access still works."""
        from bengal.snapshots import create_site_snapshot

        build_site()
        snapshot = create_site_snapshot(site)

        # Legacy dict access should still work
        assert isinstance(snapshot.config, MappingProxyType)
        assert "site" in snapshot.config or "title" in snapshot.config
