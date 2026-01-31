"""
Tests for ConfigSnapshot frozen configuration.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 6)

Tests the frozen, typed configuration snapshot that provides:
- Thread-safe access to configuration
- Typed attribute access with IDE autocomplete
- Unified access pattern (always nested: config.site.title)
"""

from __future__ import annotations

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


class TestSiteSection:
    """Tests for SiteSection dataclass."""

    def test_default_values(self):
        """Test SiteSection default values."""
        section = SiteSection()

        assert section.title == "Bengal Site"
        assert section.baseurl == ""
        assert section.description == ""
        assert section.author == ""
        assert section.language == "en"

    def test_custom_values(self):
        """Test SiteSection with custom values."""
        section = SiteSection(
            title="My Site",
            baseurl="/docs/",
            description="A great site",
            author="Test Author",
            language="es",
        )

        assert section.title == "My Site"
        assert section.baseurl == "/docs/"
        assert section.language == "es"

    def test_frozen(self):
        """Test SiteSection is immutable."""
        section = SiteSection(title="Test")

        with pytest.raises(AttributeError):
            section.title = "Modified"  # type: ignore[misc]


class TestBuildSection:
    """Tests for BuildSection dataclass."""

    def test_default_values(self):
        """Test BuildSection default values."""
        section = BuildSection()

        assert section.output_dir == "public"
        assert section.content_dir == "content"
        assert section.parallel is True
        assert section.incremental is None
        assert section.max_workers is None
        assert section.pretty_urls is True
        assert section.minify_html is True

    def test_custom_values(self):
        """Test BuildSection with custom values."""
        section = BuildSection(
            output_dir="dist",
            parallel=False,
            incremental=True,
            max_workers=8,
        )

        assert section.output_dir == "dist"
        assert section.parallel is False
        assert section.incremental is True
        assert section.max_workers == 8


class TestDevSection:
    """Tests for DevSection dataclass."""

    def test_default_values(self):
        """Test DevSection default values."""
        section = DevSection()

        assert section.cache_templates is True
        assert section.watch_backend is True
        assert section.live_reload is True
        assert section.port == 8000

    def test_custom_port(self):
        """Test DevSection with custom port."""
        section = DevSection(port=3000)

        assert section.port == 3000


class TestThemeSection:
    """Tests for ThemeSection dataclass."""

    def test_default_values(self):
        """Test ThemeSection default values."""
        section = ThemeSection()

        assert section.name == "default"
        assert section.default_appearance == "system"
        assert section.default_palette == "snow-lynx"
        assert section.features == ()

    def test_features_tuple(self):
        """Test ThemeSection features is a tuple."""
        section = ThemeSection(features=("search", "toc"))

        assert section.features == ("search", "toc")
        assert isinstance(section.features, tuple)


class TestConfigSnapshotFromDict:
    """Tests for ConfigSnapshot.from_dict() class method."""

    def test_empty_dict_uses_defaults(self):
        """Test that empty dict uses all defaults."""
        config = ConfigSnapshot.from_dict({})

        assert config.site.title == "Bengal Site"
        assert config.build.parallel is True
        assert config.dev.port == 8000

    def test_nested_site_section(self):
        """Test site section extraction."""
        config = ConfigSnapshot.from_dict(
            {
                "site": {
                    "title": "Custom Title",
                    "baseurl": "/custom/",
                    "language": "fr",
                }
            }
        )

        assert config.site.title == "Custom Title"
        assert config.site.baseurl == "/custom/"
        assert config.site.language == "fr"

    def test_nested_build_section(self):
        """Test build section extraction."""
        config = ConfigSnapshot.from_dict(
            {
                "build": {
                    "output_dir": "dist",
                    "parallel": False,
                    "max_workers": 4,
                }
            }
        )

        assert config.build.output_dir == "dist"
        assert config.build.parallel is False
        assert config.build.max_workers == 4

    def test_theme_features_conversion(self):
        """Test theme features list is converted to tuple."""
        config = ConfigSnapshot.from_dict(
            {
                "theme": {
                    "features": ["search", "toc", "graph"],
                }
            }
        )

        assert config.theme.features == ("search", "toc", "graph")

    def test_invalid_appearance_uses_default(self):
        """Test invalid appearance value uses default."""
        config = ConfigSnapshot.from_dict(
            {
                "theme": {
                    "default_appearance": "invalid",
                }
            }
        )

        assert config.theme.default_appearance == "system"

    def test_raw_dict_preserved(self):
        """Test raw dict is preserved in _raw field."""
        data = {
            "site": {"title": "Test"},
            "custom": {"key": "value"},
        }
        config = ConfigSnapshot.from_dict(data)

        assert "site" in config._raw
        assert "custom" in config._raw
        assert config["custom"]["key"] == "value"


class TestConfigSnapshotAccess:
    """Tests for ConfigSnapshot access patterns."""

    def test_getitem_access(self):
        """Test config[key] access."""
        config = ConfigSnapshot.from_dict(
            {
                "custom_key": {"nested": "value"},
            }
        )

        assert config["custom_key"]["nested"] == "value"

    def test_getitem_keyerror(self):
        """Test config[key] raises KeyError for missing keys."""
        config = ConfigSnapshot.from_dict({})

        with pytest.raises(KeyError):
            _ = config["nonexistent"]

    def test_get_method(self):
        """Test config.get() method."""
        config = ConfigSnapshot.from_dict(
            {
                "existing": "value",
            }
        )

        assert config.get("existing") == "value"
        assert config.get("nonexistent") is None
        assert config.get("nonexistent", "default") == "default"

    def test_contains_operator(self):
        """Test 'in' operator."""
        config = ConfigSnapshot.from_dict(
            {
                "site": {"title": "Test"},
            }
        )

        assert "site" in config
        assert "nonexistent" not in config

    def test_params_property(self):
        """Test params property shortcut."""
        config = ConfigSnapshot.from_dict(
            {
                "params": {
                    "author": "Test Author",
                    "custom_param": "value",
                }
            }
        )

        assert config.params["author"] == "Test Author"
        assert isinstance(config.params, MappingProxyType)

    def test_params_empty(self):
        """Test params property when not set."""
        config = ConfigSnapshot.from_dict({})

        assert config.params == MappingProxyType({})

    def test_raw_property(self):
        """Test raw property for serialization."""
        config = ConfigSnapshot.from_dict(
            {
                "site": {"title": "Test"},
            }
        )

        assert isinstance(config.raw, MappingProxyType)
        assert "site" in config.raw


class TestConfigSnapshotImmutability:
    """Tests for ConfigSnapshot immutability guarantees."""

    def test_cannot_modify_section(self):
        """Test that sections cannot be replaced."""
        config = ConfigSnapshot.from_dict({})

        with pytest.raises(AttributeError):
            config.site = SiteSection()  # type: ignore[misc]

    def test_cannot_modify_raw(self):
        """Test that _raw cannot be modified."""
        config = ConfigSnapshot.from_dict({})

        # MappingProxyType doesn't support item assignment
        with pytest.raises(TypeError):
            config._raw["new_key"] = "value"  # type: ignore[index]

    def test_thread_safe_by_construction(self):
        """Test that frozen dataclass is safe for concurrent access."""
        config = ConfigSnapshot.from_dict(
            {
                "site": {"title": "Test"},
                "build": {"parallel": True},
            }
        )

        # All fields are either frozen dataclasses or MappingProxyType
        assert hasattr(config.site, "__dataclass_fields__")
        assert isinstance(config._raw, MappingProxyType)


class TestConfigSnapshotEdgeCases:
    """Tests for ConfigSnapshot edge cases."""

    def test_non_dict_section_uses_defaults(self):
        """Test that non-dict section values use defaults."""
        config = ConfigSnapshot.from_dict(
            {
                "site": "not a dict",  # Invalid
                "build": None,  # Invalid
            }
        )

        # Should use defaults
        assert config.site.title == "Bengal Site"
        assert config.build.parallel is True

    def test_partial_section_merges_defaults(self):
        """Test that partial sections merge with defaults."""
        config = ConfigSnapshot.from_dict(
            {
                "site": {"title": "Custom"},  # Only title, rest defaults
            }
        )

        assert config.site.title == "Custom"
        assert config.site.language == "en"  # Default

    def test_none_values_in_section(self):
        """Test handling of None values in sections."""
        config = ConfigSnapshot.from_dict(
            {
                "build": {
                    "incremental": None,
                    "max_workers": None,
                }
            }
        )

        assert config.build.incremental is None
        assert config.build.max_workers is None
