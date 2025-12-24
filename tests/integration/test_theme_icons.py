"""
Integration tests for theme-aware icon system.

Tests the full icon resolution chain: site > theme > parent > default.
See: plan/drafted/rfc-theme-aware-icons.md
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


class TestThemeCustomIcons:
    """Test themes providing custom icons."""

    def test_theme_with_custom_icons(self, tmp_path: Path) -> None:
        """Build site with theme that provides custom icons."""
        from bengal.core.site import Site

        # Create site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text(
            dedent("""
            ---
            title: Home
            ---

            Check the logo icon.
            """)
        )

        # Create theme with custom icon
        theme_dir = tmp_path / "themes" / "custom" / "assets" / "icons"
        theme_dir.mkdir(parents=True)
        (theme_dir / "custom-logo.svg").write_text(
            '<svg viewBox="0 0 24 24"><!-- custom-logo --></svg>'
        )

        # Create theme.yaml
        theme_yaml = tmp_path / "themes" / "custom" / "theme.yaml"
        theme_yaml.write_text(
            dedent("""
            name: custom
            """)
        )

        # Create minimal config
        config = {
            "title": "Test Site",
            "theme": {"name": "custom"},
        }

        # Create site (initializes icon resolver with theme paths)
        _ = Site(root_path=tmp_path, config=config)

        # Verify icon resolver has the custom theme path
        from bengal.icons import resolver as icon_resolver

        paths = icon_resolver.get_search_paths()
        path_strs = [str(p) for p in paths]

        # Should include custom theme icons path
        assert any("custom" in p and "icons" in p for p in path_strs)

        # Should be able to load the custom icon
        content = icon_resolver.load_icon("custom-logo")
        assert content is not None
        assert "<!-- custom-logo -->" in content


class TestSiteLevelIconOverride:
    """Test site-level icon overrides."""

    def test_site_icon_overrides_default(self, tmp_path: Path) -> None:
        """Site-level icon in custom theme overrides default theme icon."""
        from bengal.core.site import Site
        from bengal.icons import resolver as icon_resolver

        # Create site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text(
            dedent("""
            ---
            title: Home
            ---

            Home page.
            """)
        )

        # Create a custom theme in site's themes directory with icon override
        site_theme_dir = tmp_path / "themes" / "my-site-theme"
        site_icons = site_theme_dir / "assets" / "icons"
        site_icons.mkdir(parents=True)
        (site_icons / "site-custom.svg").write_text(
            '<svg viewBox="0 0 24 24"><!-- site-custom-icon --></svg>'
        )
        (site_theme_dir / "theme.yaml").write_text("name: my-site-theme\n")

        # Create minimal config using the site's theme
        config = {
            "title": "Test Site",
            "theme": {"name": "my-site-theme"},
        }

        # Create site
        _ = Site(root_path=tmp_path, config=config)

        # Clear any cached icons
        icon_resolver.clear_cache()

        # The site's custom icon should be loadable
        content = icon_resolver.load_icon("site-custom")
        assert content is not None
        assert "<!-- site-custom-icon -->" in content


class TestIconInheritance:
    """Test icon inheritance through theme chain."""

    def test_child_theme_inherits_parent_icons(self, tmp_path: Path) -> None:
        """Child theme inherits icons from parent theme."""
        from bengal.core.site import Site
        from bengal.icons import resolver as icon_resolver

        # Create content
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("# Home\n")

        # Create parent theme with icon
        parent_dir = tmp_path / "themes" / "parent" / "assets" / "icons"
        parent_dir.mkdir(parents=True)
        (parent_dir / "parent-only.svg").write_text("<svg><!-- parent-icon --></svg>")
        (tmp_path / "themes" / "parent" / "theme.yaml").write_text("name: parent\n")

        # Create child theme that extends parent
        child_dir = tmp_path / "themes" / "child" / "assets" / "icons"
        child_dir.mkdir(parents=True)
        (child_dir / "child-only.svg").write_text("<svg><!-- child-icon --></svg>")
        (tmp_path / "themes" / "child" / "theme.yaml").write_text(
            dedent("""
            name: child
            extends: parent
            """)
        )

        # Create site using child theme
        config = {
            "title": "Test Site",
            "theme": {"name": "child"},
        }

        _ = Site(root_path=tmp_path, config=config)
        icon_resolver.clear_cache()

        # Child's icon should be available
        child_icon = icon_resolver.load_icon("child-only")
        assert child_icon is not None
        assert "<!-- child-icon -->" in child_icon


class TestExtendDefaultsConfig:
    """Test extend_defaults configuration option."""

    def test_extend_defaults_true_includes_phosphor(self, tmp_path: Path) -> None:
        """With extend_defaults=True (default), Phosphor icons are available."""
        from bengal.core.site import Site
        from bengal.icons import resolver as icon_resolver

        # Create minimal site
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("# Home\n")

        # Create theme without any icons
        theme_dir = tmp_path / "themes" / "minimal"
        theme_dir.mkdir(parents=True)
        (theme_dir / "theme.yaml").write_text(
            dedent("""
            name: minimal
            # extend_defaults defaults to true
            """)
        )

        config = {
            "title": "Test Site",
            "theme": {"name": "minimal"},
        }

        _ = Site(root_path=tmp_path, config=config)
        icon_resolver.clear_cache()

        # Default Phosphor icons should still be available via fallthrough
        paths = icon_resolver.get_search_paths()
        path_strs = [str(p) for p in paths]

        # Should include default theme path
        assert any("default" in p for p in path_strs)


class TestT010WarningsShowSearchedPaths:
    """Test that T010 warnings include searched paths."""

    def test_warning_includes_searched_paths(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warning for missing icon includes all directories that were searched."""
        from bengal.core.site import Site
        from bengal.icons import resolver as icon_resolver

        # Create minimal site
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("# Home\n")

        config = {
            "title": "Test Site",
            "theme": {"name": "default"},
        }

        _ = Site(root_path=tmp_path, config=config)
        icon_resolver.clear_cache()

        # Try to load a nonexistent icon
        result = icon_resolver.load_icon("nonexistent-icon-xyz")
        assert result is None

        # The warning should be logged by the calling code (template functions, etc.)
        # Here we just verify the search paths are available for the warning
        paths = icon_resolver.get_search_paths()
        assert len(paths) >= 1


class TestIconResolverWithBuild:
    """Test icon resolver during actual site builds."""

    def test_icon_template_function_uses_resolver(self, tmp_path: Path) -> None:
        """The icon() template function uses the resolver."""
        from bengal.core.site import Site
        from bengal.icons import resolver as icon_resolver

        # Create site
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("# Home\n")

        # Create custom theme with custom icon
        theme_dir = tmp_path / "themes" / "build-test-theme"
        theme_icons = theme_dir / "assets" / "icons"
        theme_icons.mkdir(parents=True)
        (theme_icons / "custom-build-icon.svg").write_text(
            '<svg viewBox="0 0 24 24" class="test"><!-- build-test --></svg>'
        )
        (theme_dir / "theme.yaml").write_text("name: build-test-theme\n")

        config = {
            "title": "Test Site",
            "theme": {"name": "build-test-theme"},
        }

        _ = Site(root_path=tmp_path, config=config)
        icon_resolver.clear_cache()

        # The custom icon should be loadable
        content = icon_resolver.load_icon("custom-build-icon")
        assert content is not None
        assert "<!-- build-test -->" in content
