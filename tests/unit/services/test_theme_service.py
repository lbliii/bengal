"""
Unit tests for ThemeService.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 4: Service Extraction)

Tests theme resolution via pure functions that operate on
root_path + theme_name instead of mutable Site.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.services.theme import (
    ThemeService,
    get_theme_assets_chain,
    get_theme_assets_dir,
    get_theme_templates_chain,
)
from bengal.services.utils import get_bundled_themes_dir


class TestGetThemeAssetsDir:
    """Tests for get_theme_assets_dir function."""

    def test_returns_none_for_no_theme(self, tmp_path: Path) -> None:
        """get_theme_assets_dir returns None when theme_name is None."""
        result = get_theme_assets_dir(tmp_path, None)
        assert result is None

    def test_site_theme_takes_priority(self, tmp_path: Path) -> None:
        """get_theme_assets_dir checks site themes first."""
        # Create site theme directory
        site_theme_assets = tmp_path / "themes" / "custom" / "assets"
        site_theme_assets.mkdir(parents=True)

        result = get_theme_assets_dir(tmp_path, "custom")
        assert result == site_theme_assets

    def test_falls_back_to_bundled_theme(self, tmp_path: Path) -> None:
        """get_theme_assets_dir falls back to bundled themes."""
        # Don't create site theme - should find bundled "default" theme
        result = get_theme_assets_dir(tmp_path, "default")

        expected = get_bundled_themes_dir() / "default" / "assets"
        if expected.exists():
            assert result == expected
        else:
            # If bundled theme doesn't have assets, returns None
            assert result is None

    def test_returns_none_for_nonexistent_theme(self, tmp_path: Path) -> None:
        """get_theme_assets_dir returns None for nonexistent theme."""
        result = get_theme_assets_dir(tmp_path, "nonexistent-theme-xyz")
        assert result is None


class TestGetThemeAssetsChain:
    """Tests for get_theme_assets_chain function."""

    def test_returns_empty_for_no_theme(self, tmp_path: Path) -> None:
        """get_theme_assets_chain returns empty list when theme_name is None."""
        result = get_theme_assets_chain(tmp_path, None)
        assert result == []

    def test_returns_list_of_paths(self, tmp_path: Path) -> None:
        """get_theme_assets_chain returns list of Path objects."""
        # Create a site theme
        site_theme_assets = tmp_path / "themes" / "test" / "assets"
        site_theme_assets.mkdir(parents=True)

        result = get_theme_assets_chain(tmp_path, "test")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, Path)

    def test_includes_site_theme(self, tmp_path: Path) -> None:
        """get_theme_assets_chain includes site theme assets."""
        site_theme_assets = tmp_path / "themes" / "mysite" / "assets"
        site_theme_assets.mkdir(parents=True)

        result = get_theme_assets_chain(tmp_path, "mysite")
        assert site_theme_assets in result


class TestGetThemeTemplatesChain:
    """Tests for get_theme_templates_chain function."""

    def test_returns_empty_for_no_theme(self, tmp_path: Path) -> None:
        """get_theme_templates_chain returns empty list when theme_name is None."""
        result = get_theme_templates_chain(tmp_path, None)
        assert result == []

    def test_returns_list_of_paths(self, tmp_path: Path) -> None:
        """get_theme_templates_chain returns list of Path objects."""
        # Create a site theme with templates
        site_theme_templates = tmp_path / "themes" / "test" / "templates"
        site_theme_templates.mkdir(parents=True)

        result = get_theme_templates_chain(tmp_path, "test")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, Path)

    def test_includes_site_theme_templates(self, tmp_path: Path) -> None:
        """get_theme_templates_chain includes site theme templates."""
        site_theme_templates = tmp_path / "themes" / "docs" / "templates"
        site_theme_templates.mkdir(parents=True)

        result = get_theme_templates_chain(tmp_path, "docs")
        assert site_theme_templates in result

    def test_bundled_theme_templates(self, tmp_path: Path) -> None:
        """get_theme_templates_chain finds bundled theme templates."""
        # Don't create site theme - should find bundled "default"
        result = get_theme_templates_chain(tmp_path, "default")

        expected = get_bundled_themes_dir() / "default" / "templates"
        if expected.exists():
            assert expected in result


class TestThemeService:
    """Tests for ThemeService class."""

    def test_create_with_path_and_theme(self, tmp_path: Path) -> None:
        """ThemeService can be created with root_path and theme_name."""
        service = ThemeService(root_path=tmp_path, theme_name="test")
        assert service.root_path == tmp_path
        assert service.theme_name == "test"

    def test_get_assets_dir(self, tmp_path: Path) -> None:
        """ThemeService.get_assets_dir delegates to get_theme_assets_dir."""
        # Create site theme
        site_theme_assets = tmp_path / "themes" / "custom" / "assets"
        site_theme_assets.mkdir(parents=True)

        service = ThemeService(root_path=tmp_path, theme_name="custom")
        result = service.get_assets_dir()
        assert result == site_theme_assets

    def test_get_assets_chain(self, tmp_path: Path) -> None:
        """ThemeService.get_assets_chain delegates to get_theme_assets_chain."""
        site_theme_assets = tmp_path / "themes" / "custom" / "assets"
        site_theme_assets.mkdir(parents=True)

        service = ThemeService(root_path=tmp_path, theme_name="custom")
        result = service.get_assets_chain()
        assert isinstance(result, list)

    def test_get_templates_chain(self, tmp_path: Path) -> None:
        """ThemeService.get_templates_chain delegates to get_theme_templates_chain."""
        site_theme_templates = tmp_path / "themes" / "custom" / "templates"
        site_theme_templates.mkdir(parents=True)

        service = ThemeService(root_path=tmp_path, theme_name="custom")
        result = service.get_templates_chain()
        assert site_theme_templates in result

    def test_no_theme_returns_none_or_empty(self, tmp_path: Path) -> None:
        """ThemeService with no theme returns None/empty from methods."""
        service = ThemeService(root_path=tmp_path, theme_name=None)
        assert service.get_assets_dir() is None
        assert service.get_assets_chain() == []
        assert service.get_templates_chain() == []

    def test_from_config_snapshot(self, tmp_path: Path) -> None:
        """ThemeService.from_config creates service from ConfigSnapshot."""
        mock_config = MagicMock()
        mock_config.theme = MagicMock()
        mock_config.theme.name = "test-theme"

        service = ThemeService.from_config(tmp_path, mock_config)
        assert service.root_path == tmp_path
        assert service.theme_name == "test-theme"

    def test_from_config_snapshot_no_theme(self, tmp_path: Path) -> None:
        """ThemeService.from_config handles ConfigSnapshot without theme."""
        mock_config = MagicMock()
        mock_config.theme = None

        service = ThemeService.from_config(tmp_path, mock_config)
        assert service.theme_name is None

    def test_from_site_snapshot(self, tmp_path: Path) -> None:
        """ThemeService.from_snapshot creates service from SiteSnapshot."""
        mock_snapshot = MagicMock()
        mock_snapshot.root_path = tmp_path
        mock_snapshot.config_snapshot = MagicMock()
        mock_snapshot.config_snapshot.theme = MagicMock()
        mock_snapshot.config_snapshot.theme.name = "snapshot-theme"

        service = ThemeService.from_snapshot(mock_snapshot)
        assert service.root_path == tmp_path
        assert service.theme_name == "snapshot-theme"

    def test_from_site_snapshot_no_config(self, tmp_path: Path) -> None:
        """ThemeService.from_snapshot handles SiteSnapshot without config."""
        mock_snapshot = MagicMock()
        mock_snapshot.root_path = tmp_path
        mock_snapshot.config_snapshot = None

        service = ThemeService.from_snapshot(mock_snapshot)
        assert service.theme_name is None


class TestThemeServiceFrozen:
    """Tests verifying ThemeService is immutable."""

    def test_is_frozen_dataclass(self, tmp_path: Path) -> None:
        """ThemeService is a frozen dataclass."""
        service = ThemeService(root_path=tmp_path, theme_name="test")
        with pytest.raises(AttributeError):
            service.theme_name = "different"  # type: ignore[misc]

    def test_has_slots(self, tmp_path: Path) -> None:
        """ThemeService uses slots for memory efficiency."""
        service = ThemeService(root_path=tmp_path, theme_name="test")
        assert hasattr(service, "__slots__") or hasattr(ThemeService, "__slots__")
