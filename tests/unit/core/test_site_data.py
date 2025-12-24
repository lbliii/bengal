"""
Unit tests for SiteData.

Tests the SiteData frozen dataclass which provides immutable
configuration storage with path computation.

See: plan/drafted/rfc-site-responsibility-separation.md
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from bengal.core.site_data import SiteData


class TestSiteDataCreation:
    """Test SiteData creation."""

    def test_from_config_basic(self, tmp_path: Path) -> None:
        """SiteData can be created from config."""
        config = {"title": "Test Site"}
        data = SiteData.from_config(tmp_path, config)

        assert data.root_path == tmp_path.resolve()
        assert data.title == "Test Site"

    def test_from_config_with_theme(self, tmp_path: Path) -> None:
        """Theme name is extracted from config."""
        config = {"theme": {"name": "custom-theme"}}
        data = SiteData.from_config(tmp_path, config)

        assert data.theme_name == "custom-theme"

    def test_from_config_theme_string(self, tmp_path: Path) -> None:
        """Theme can be specified as string."""
        config = {"theme": "simple-theme"}
        data = SiteData.from_config(tmp_path, config)

        assert data.theme_name == "simple-theme"

    def test_from_config_default_theme(self, tmp_path: Path) -> None:
        """Default theme is 'default'."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.theme_name == "default"

    def test_from_config_output_dir_relative(self, tmp_path: Path) -> None:
        """Relative output_dir is resolved to absolute."""
        config = {"output_dir": "dist"}
        data = SiteData.from_config(tmp_path, config)

        assert data.output_dir == tmp_path.resolve() / "dist"

    def test_from_config_output_dir_absolute(self, tmp_path: Path) -> None:
        """Absolute output_dir is preserved."""
        output_path = Path("/custom/output")
        config = {"output_dir": str(output_path)}
        data = SiteData.from_config(tmp_path, config)

        assert data.output_dir == output_path

    def test_from_config_default_output_dir(self, tmp_path: Path) -> None:
        """Default output_dir is 'public'."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.output_dir == tmp_path.resolve() / "public"


class TestSiteDataPaths:
    """Test computed path attributes."""

    def test_content_dir(self, tmp_path: Path) -> None:
        """Content directory is computed."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.content_dir == tmp_path.resolve() / "content"

    def test_content_dir_custom(self, tmp_path: Path) -> None:
        """Custom content directory is resolved."""
        config = {"content_dir": "docs"}
        data = SiteData.from_config(tmp_path, config)

        assert data.content_dir == tmp_path.resolve() / "docs"

    def test_assets_dir(self, tmp_path: Path) -> None:
        """Assets directory is computed."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.assets_dir == tmp_path.resolve() / "assets"

    def test_data_dir(self, tmp_path: Path) -> None:
        """Data directory is computed."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.data_dir == tmp_path.resolve() / "data"

    def test_cache_dir(self, tmp_path: Path) -> None:
        """Cache directory is computed."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.cache_dir == tmp_path.resolve() / ".bengal"


class TestSiteDataImmutability:
    """Test immutability guarantees."""

    def test_frozen_dataclass(self, tmp_path: Path) -> None:
        """SiteData is frozen (immutable)."""
        config = {"title": "Test"}
        data = SiteData.from_config(tmp_path, config)

        with pytest.raises(AttributeError):
            data.title = "Modified"  # type: ignore[misc]

    def test_config_is_mapping_proxy(self, tmp_path: Path) -> None:
        """Config is wrapped in MappingProxyType."""
        config = {"title": "Test"}
        data = SiteData.from_config(tmp_path, config)

        assert isinstance(data.config, MappingProxyType)

    def test_config_is_read_only(self, tmp_path: Path) -> None:
        """Config mapping cannot be modified."""
        config = {"title": "Test"}
        data = SiteData.from_config(tmp_path, config)

        with pytest.raises(TypeError):
            data.config["title"] = "Modified"  # type: ignore[index]


class TestSiteDataProperties:
    """Test property accessors."""

    def test_baseurl_default(self, tmp_path: Path) -> None:
        """Baseurl defaults to empty string."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.baseurl == ""

    def test_baseurl_configured(self, tmp_path: Path) -> None:
        """Baseurl is read from config."""
        config = {"baseurl": "/blog"}
        data = SiteData.from_config(tmp_path, config)

        assert data.baseurl == "/blog"

    def test_title_default(self, tmp_path: Path) -> None:
        """Title defaults to empty string."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.title == ""

    def test_title_configured(self, tmp_path: Path) -> None:
        """Title is read from config."""
        config = {"title": "My Blog"}
        data = SiteData.from_config(tmp_path, config)

        assert data.title == "My Blog"

    def test_author_default(self, tmp_path: Path) -> None:
        """Author defaults to None."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.author is None

    def test_author_configured(self, tmp_path: Path) -> None:
        """Author is read from config."""
        config = {"author": "Jane Doe"}
        data = SiteData.from_config(tmp_path, config)

        assert data.author == "Jane Doe"

    def test_description_default(self, tmp_path: Path) -> None:
        """Description defaults to None."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.description is None

    def test_description_configured(self, tmp_path: Path) -> None:
        """Description is read from config."""
        config = {"description": "A great blog"}
        data = SiteData.from_config(tmp_path, config)

        assert data.description == "A great blog"

    def test_language_default(self, tmp_path: Path) -> None:
        """Language defaults to 'en'."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        assert data.language == "en"

    def test_language_configured(self, tmp_path: Path) -> None:
        """Language is read from config."""
        config = {"language": "es"}
        data = SiteData.from_config(tmp_path, config)

        assert data.language == "es"


class TestGetConfigSection:
    """Test get_config_section method."""

    def test_existing_section(self, tmp_path: Path) -> None:
        """Existing section is returned as MappingProxyType."""
        config = {"build": {"strict_mode": True, "parallel": True}}
        data = SiteData.from_config(tmp_path, config)

        build_cfg = data.get_config_section("build")

        assert isinstance(build_cfg, MappingProxyType)
        assert build_cfg.get("strict_mode") is True
        assert build_cfg.get("parallel") is True

    def test_missing_section(self, tmp_path: Path) -> None:
        """Missing section returns empty MappingProxyType."""
        config = {}
        data = SiteData.from_config(tmp_path, config)

        build_cfg = data.get_config_section("build")

        assert isinstance(build_cfg, MappingProxyType)
        assert len(build_cfg) == 0

    def test_non_dict_section(self, tmp_path: Path) -> None:
        """Non-dict value returns empty MappingProxyType."""
        config = {"theme": "simple"}  # String, not dict
        data = SiteData.from_config(tmp_path, config)

        theme_cfg = data.get_config_section("theme")

        assert isinstance(theme_cfg, MappingProxyType)
        assert len(theme_cfg) == 0


class TestSiteDataRepr:
    """Test string representation."""

    def test_repr(self, tmp_path: Path) -> None:
        """Repr shows root and theme."""
        config = {"theme": {"name": "custom"}}
        data = SiteData.from_config(tmp_path, config)

        repr_str = repr(data)

        assert "SiteData" in repr_str
        assert tmp_path.name in repr_str
        assert "custom" in repr_str


