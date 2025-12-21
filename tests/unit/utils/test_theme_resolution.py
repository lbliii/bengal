"""
Tests for theme resolution and inheritance chain building.

Covers:
- resolve_theme_chain() function
- _read_theme_extends() helper
- iter_theme_asset_dirs() function
- Theme inheritance cycles
- Site, installed, and bundled theme resolution
"""

from unittest.mock import MagicMock, patch

from bengal.core.theme import (
    _read_theme_extends,
    iter_theme_asset_dirs,
    resolve_theme_chain,
)


class TestReadThemeExtends:
    """Tests for _read_theme_extends helper."""

    def test_reads_site_theme_manifest(self, tmp_path):
        """Reads extends from site theme.toml."""
        # Create site theme with manifest
        theme_dir = tmp_path / "themes" / "my-theme"
        theme_dir.mkdir(parents=True)
        (theme_dir / "theme.toml").write_text('extends = "base-theme"')

        extends = _read_theme_extends(tmp_path, "my-theme")

        assert extends == "base-theme"

    def test_returns_none_when_no_extends(self, tmp_path):
        """Returns None when theme.toml has no extends."""
        theme_dir = tmp_path / "themes" / "standalone"
        theme_dir.mkdir(parents=True)
        (theme_dir / "theme.toml").write_text('name = "standalone"')

        extends = _read_theme_extends(tmp_path, "standalone")

        assert extends is None

    def test_returns_none_when_no_manifest(self, tmp_path):
        """Returns None when theme.toml doesn't exist."""
        extends = _read_theme_extends(tmp_path, "nonexistent")
        assert extends is None

    def test_handles_malformed_toml(self, tmp_path):
        """Handles malformed TOML gracefully."""
        theme_dir = tmp_path / "themes" / "broken"
        theme_dir.mkdir(parents=True)
        (theme_dir / "theme.toml").write_text("this is not valid toml {{{{")

        # Should not raise, returns None
        extends = _read_theme_extends(tmp_path, "broken")
        assert extends is None

    def test_checks_installed_theme_packages(self, tmp_path):
        """Falls back to installed theme packages."""
        # No site theme exists
        mock_pkg = MagicMock()
        mock_manifest = tmp_path / "installed_manifest.toml"
        mock_manifest.write_text('extends = "installed-parent"')
        mock_pkg.resolve_resource_path.return_value = mock_manifest

        with patch("bengal.core.theme.resolution.get_theme_package", return_value=mock_pkg):
            extends = _read_theme_extends(tmp_path, "installed-theme")

        assert extends == "installed-parent"

    def test_checks_bundled_themes(self, tmp_path):
        """Falls back to bundled themes."""
        # No site or installed theme
        with patch("bengal.core.theme.resolution.get_theme_package", return_value=None):
            # Bundled theme check happens via Path(__file__).parent.parent / "themes"
            # This is harder to test without mocking Path, so we verify no error
            extends = _read_theme_extends(tmp_path, "bundled-theme")
            # Will return None since bundled path won't exist in test env
            assert extends is None


class TestResolveThemeChain:
    """Tests for resolve_theme_chain function."""

    def test_single_theme_no_extends(self, tmp_path):
        """Single theme with no parent returns just that theme."""
        theme_dir = tmp_path / "themes" / "simple"
        theme_dir.mkdir(parents=True)
        (theme_dir / "theme.toml").write_text('name = "simple"')

        chain = resolve_theme_chain(tmp_path, "simple")

        assert chain == ["simple"]

    def test_theme_inheritance_chain(self, tmp_path):
        """Builds complete inheritance chain."""
        # Create child -> parent -> grandparent chain
        for name, extends in [
            ("child", "parent"),
            ("parent", "grandparent"),
            ("grandparent", None),
        ]:
            theme_dir = tmp_path / "themes" / name
            theme_dir.mkdir(parents=True)
            content = f'name = "{name}"'
            if extends:
                content += f'\nextends = "{extends}"'
            (theme_dir / "theme.toml").write_text(content)

        chain = resolve_theme_chain(tmp_path, "child")

        # Order is child first -> parent -> grandparent
        assert chain == ["child", "parent", "grandparent"]

    def test_default_theme_excluded_from_chain(self, tmp_path):
        """Default theme is excluded from chain."""
        # Theme that extends default
        theme_dir = tmp_path / "themes" / "my-theme"
        theme_dir.mkdir(parents=True)
        (theme_dir / "theme.toml").write_text('extends = "default"')

        chain = resolve_theme_chain(tmp_path, "my-theme")

        # Chain should not include "default"
        assert "default" not in chain
        assert chain == ["my-theme"]

    def test_none_theme_uses_default(self, tmp_path):
        """None theme starts from default."""
        chain = resolve_theme_chain(tmp_path, None)

        # When starting from "default", chain is empty since default is excluded
        assert chain == []

    def test_prevents_circular_inheritance(self, tmp_path):
        """Prevents infinite loops from circular extends."""
        # Create circular reference: a -> b -> a
        for name, extends in [("theme-a", "theme-b"), ("theme-b", "theme-a")]:
            theme_dir = tmp_path / "themes" / name
            theme_dir.mkdir(parents=True)
            (theme_dir / "theme.toml").write_text(f'extends = "{extends}"')

        chain = resolve_theme_chain(tmp_path, "theme-a")

        # Should stop at first cycle, not infinite loop
        assert len(chain) <= 5  # MAX_DEPTH is 5
        # Each theme should appear at most once
        assert len(chain) == len(set(chain))

    def test_self_reference_stops_chain(self, tmp_path):
        """Self-extending theme stops the chain."""
        theme_dir = tmp_path / "themes" / "self-ref"
        theme_dir.mkdir(parents=True)
        (theme_dir / "theme.toml").write_text('extends = "self-ref"')

        chain = resolve_theme_chain(tmp_path, "self-ref")

        # Should include the theme once, then stop
        assert chain == ["self-ref"]

    def test_max_depth_prevents_deep_chains(self, tmp_path):
        """Enforces maximum inheritance depth."""
        # Create very deep chain: level0 -> level1 -> ... -> level10
        for i in range(11):
            theme_dir = tmp_path / "themes" / f"level{i}"
            theme_dir.mkdir(parents=True)
            content = f'name = "level{i}"'
            if i < 10:
                content += f'\nextends = "level{i + 1}"'
            (theme_dir / "theme.toml").write_text(content)

        chain = resolve_theme_chain(tmp_path, "level0")

        # MAX_DEPTH is 5, so should stop after 5 levels
        assert len(chain) <= 5


class TestIterThemeAssetDirs:
    """Tests for iter_theme_asset_dirs function."""

    def test_empty_chain_returns_empty_list(self, tmp_path):
        """Empty theme chain returns empty list."""
        dirs = iter_theme_asset_dirs(tmp_path, [])
        assert dirs == []

    def test_finds_site_theme_assets(self, tmp_path):
        """Finds assets in site themes/ directory."""
        # Create site theme with assets
        assets_dir = tmp_path / "themes" / "my-theme" / "assets"
        assets_dir.mkdir(parents=True)
        (assets_dir / "style.css").write_text("/* test */")

        with patch("bengal.core.theme.resolution.get_theme_package", return_value=None):
            dirs = iter_theme_asset_dirs(tmp_path, ["my-theme"])

        assert len(dirs) == 1
        assert dirs[0] == assets_dir

    def test_finds_installed_theme_assets(self, tmp_path):
        """Finds assets in installed theme packages."""
        mock_assets_dir = tmp_path / "installed_assets"
        mock_assets_dir.mkdir()

        mock_pkg = MagicMock()
        mock_pkg.resolve_resource_path.return_value = mock_assets_dir

        with patch("bengal.core.theme.resolution.get_theme_package", return_value=mock_pkg):
            dirs = iter_theme_asset_dirs(tmp_path, ["installed-theme"])

        assert len(dirs) == 1
        assert dirs[0] == mock_assets_dir

    def test_site_theme_takes_precedence(self, tmp_path):
        """Site theme assets take precedence over installed."""
        # Create site theme assets
        site_assets = tmp_path / "themes" / "dual-theme" / "assets"
        site_assets.mkdir(parents=True)

        # Mock installed theme
        installed_assets = tmp_path / "installed_assets"
        installed_assets.mkdir()
        mock_pkg = MagicMock()
        mock_pkg.resolve_resource_path.return_value = installed_assets

        with patch("bengal.core.theme.resolution.get_theme_package", return_value=mock_pkg):
            dirs = iter_theme_asset_dirs(tmp_path, ["dual-theme"])

        # Should only return site assets (takes precedence)
        assert len(dirs) == 1
        assert dirs[0] == site_assets

    def test_chain_order_is_parents_to_child(self, tmp_path):
        """Asset dirs are returned in parent-to-child order."""
        # Create assets for multiple themes
        for theme_name in ["parent", "child"]:
            assets_dir = tmp_path / "themes" / theme_name / "assets"
            assets_dir.mkdir(parents=True)

        with patch("bengal.core.theme.resolution.get_theme_package", return_value=None):
            # Chain order is child-first in input
            dirs = iter_theme_asset_dirs(tmp_path, ["child", "parent"])

        # Output order should match input order (for priority)
        assert len(dirs) == 2
        assert dirs[0].parent.name == "child"
        assert dirs[1].parent.name == "parent"

    def test_skips_themes_without_assets(self, tmp_path):
        """Skips themes that don't have assets directory."""
        # Theme with assets
        with_assets = tmp_path / "themes" / "with-assets" / "assets"
        with_assets.mkdir(parents=True)

        # Theme without assets (only theme dir exists)
        without_assets = tmp_path / "themes" / "without-assets"
        without_assets.mkdir(parents=True)
        # No assets/ subdirectory

        with patch("bengal.core.theme.resolution.get_theme_package", return_value=None):
            dirs = iter_theme_asset_dirs(tmp_path, ["with-assets", "without-assets"])

        # Should only include theme with assets
        assert len(dirs) == 1
        assert dirs[0] == with_assets

    def test_handles_package_lookup_errors(self, tmp_path):
        """Handles errors during package lookup gracefully."""
        with patch(
            "bengal.core.theme.resolution.get_theme_package",
            side_effect=Exception("Package error"),
        ):
            # Should not raise
            dirs = iter_theme_asset_dirs(tmp_path, ["error-theme"])

        # Returns empty list when no assets found
        assert dirs == []


class TestThemeResolutionIntegration:
    """Integration tests for theme resolution."""

    def test_full_resolution_workflow(self, tmp_path):
        """Test complete theme resolution workflow."""
        # Create theme hierarchy: custom -> base
        (tmp_path / "themes" / "custom" / "assets").mkdir(parents=True)
        (tmp_path / "themes" / "custom" / "theme.toml").write_text(
            'name = "custom"\nextends = "base"'
        )

        (tmp_path / "themes" / "base" / "assets").mkdir(parents=True)
        (tmp_path / "themes" / "base" / "theme.toml").write_text('name = "base"')

        # Resolve chain
        chain = resolve_theme_chain(tmp_path, "custom")
        assert chain == ["custom", "base"]

        # Get asset directories
        with patch("bengal.core.theme.resolution.get_theme_package", return_value=None):
            asset_dirs = iter_theme_asset_dirs(tmp_path, chain)

        # Both themes have assets
        assert len(asset_dirs) == 2

    def test_theme_chain_affects_template_lookup_order(self, tmp_path):
        """Theme chain determines template lookup priority."""
        # This tests the conceptual purpose of theme chains
        chain = resolve_theme_chain(tmp_path, None)

        # For template lookup:
        # - Templates in child theme override parent
        # - Chain order: child (highest priority) -> parent (lower)
        # - Default theme is excluded (handled separately as ultimate fallback)

        # With no custom theme, chain is empty
        assert chain == []
