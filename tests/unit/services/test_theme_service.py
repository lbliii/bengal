"""
Unit tests for theme resolution pure functions.

Tests theme asset and template resolution via pure functions
that operate on root_path + theme_name.
"""

from pathlib import Path

from bengal.services.theme import (
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
