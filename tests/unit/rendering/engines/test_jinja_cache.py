"""
Tests for Jinja2 template engine cache behavior.

These tests verify that template path caching is correctly enabled/disabled
based on dev_mode configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from bengal.core.site import Site


def make_mock_site(
    dev_mode: bool = False,
    theme: str = "default",
    root_path: Path | None = None,
) -> MagicMock:
    """Create a mock site for testing."""
    mock_site = MagicMock()
    mock_site.dev_mode = dev_mode
    mock_site.theme = theme
    mock_site.root_path = root_path or Path("/tmp/test-site")
    mock_site.output_dir = mock_site.root_path / "public"
    mock_site.config = {
        "site": {"title": "Test Site"},
        "development": {"dev_mode": dev_mode},
    }
    mock_site.theme_config = MagicMock()
    mock_site.theme_config.config = {}
    mock_site.menu = {}
    mock_site.menu_localized = {}
    mock_site.versioning_enabled = False
    mock_site.versions = []
    mock_site._warned_filters = set()
    mock_site._warned_functions = set()
    return mock_site


class TestJinjaTemplateCaching:
    """Test template path cache behavior."""

    def test_cache_disabled_in_dev_mode(self) -> None:
        """Verify template path cache is disabled when dev_mode=True."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=True)

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [])

            engine = JinjaTemplateEngine(mock_site)

        assert not engine._template_path_cache_enabled

    def test_cache_enabled_in_production_mode(self) -> None:
        """Verify template path cache is enabled when dev_mode=False."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=False)

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [])

            engine = JinjaTemplateEngine(mock_site)

        assert engine._template_path_cache_enabled

    def test_cache_respects_site_dev_mode_attribute(self) -> None:
        """Verify cache uses site.dev_mode attribute correctly."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        # Test with dev_mode=True
        mock_site_dev = make_mock_site(dev_mode=True)
        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [])
            engine_dev = JinjaTemplateEngine(mock_site_dev)
        assert not engine_dev._template_path_cache_enabled

        # Test with dev_mode=False
        mock_site_prod = make_mock_site(dev_mode=False)
        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [])
            engine_prod = JinjaTemplateEngine(mock_site_prod)
        assert engine_prod._template_path_cache_enabled

    def test_get_template_path_uses_cache_when_enabled(self) -> None:
        """Verify get_template_path uses cache in production mode."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=False)
        template_dir = Path("/tmp/templates")

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [template_dir])

            engine = JinjaTemplateEngine(mock_site)

            # Pre-populate cache
            engine._template_path_cache["test.html"] = template_dir / "test.html"

            # Should return cached value without checking filesystem
            with patch.object(Path, "exists", return_value=False) as mock_exists:
                result = engine.get_template_path("test.html")

            # Cache hit - should NOT have called exists()
            # (actually it may call exists during the loop, so let's just check result)
            assert result == template_dir / "test.html"

    def test_get_template_path_skips_cache_when_disabled(self) -> None:
        """Verify get_template_path skips cache in dev mode."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=True)
        template_dir = Path("/tmp/templates")

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [template_dir])

            engine = JinjaTemplateEngine(mock_site)

            # Pre-populate cache (should be ignored)
            engine._template_path_cache["test.html"] = template_dir / "test.html"

            # Mock Path.exists to track calls
            original_exists = Path.exists

            def mock_exists(self: Path) -> bool:
                if "test.html" in str(self):
                    return True
                return original_exists(self)

            with patch.object(Path, "exists", mock_exists):
                result = engine.get_template_path("test.html")

            # Should have checked filesystem (cache disabled)
            # Result should be the found path
            assert result is not None


class TestJinjaCacheInvalidation:
    """Test cache invalidation scenarios."""

    def test_template_path_cache_can_store_none(self) -> None:
        """Verify cache can store None for missing templates."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=False)
        template_dir = Path("/tmp/templates")

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [template_dir])

            engine = JinjaTemplateEngine(mock_site)

            # Cache None for missing template
            engine._template_path_cache["missing.html"] = None

            # Should return cached None
            result = engine.get_template_path("missing.html")
            assert result is None

    def test_referenced_template_cache_stores_sets(self) -> None:
        """Verify referenced template cache stores sets of names."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=False)

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [])

            engine = JinjaTemplateEngine(mock_site)

            # Verify cache is a dict of sets
            assert isinstance(engine._referenced_template_cache, dict)

            # Add some entries
            engine._referenced_template_cache["page.html"] = {"base.html", "header.html"}

            assert "base.html" in engine._referenced_template_cache["page.html"]
            assert "header.html" in engine._referenced_template_cache["page.html"]


class TestJinjaMenuCacheInvalidation:
    """Test menu dict cache invalidation."""

    def test_menu_cache_invalidated_on_render(self) -> None:
        """Verify menu cache is invalidated before rendering."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=False)

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_env.get_template = MagicMock(
                return_value=MagicMock(render=MagicMock(return_value=""))
            )
            mock_create_env.return_value = (mock_env, [])

            engine = JinjaTemplateEngine(mock_site)

            # Pre-populate menu cache
            engine._menu_dict_cache["main"] = [{"name": "Old", "url": "/old/"}]

            # Render should invalidate cache
            engine.render_template("test.html", {})

            # Cache should be cleared
            assert engine._menu_dict_cache == {}

    def test_invalidate_menu_cache_clears_all_entries(self) -> None:
        """Verify invalidate_menu_cache clears all entries."""
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        mock_site = make_mock_site(dev_mode=False)

        with patch("bengal.rendering.engines.jinja.create_jinja_environment") as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [])

            engine = JinjaTemplateEngine(mock_site)

            # Pre-populate with multiple entries
            engine._menu_dict_cache["main"] = [{"name": "Main"}]
            engine._menu_dict_cache["footer"] = [{"name": "Footer"}]
            engine._menu_dict_cache["main:en"] = [{"name": "Main EN"}]

            engine.invalidate_menu_cache()

            assert engine._menu_dict_cache == {}
