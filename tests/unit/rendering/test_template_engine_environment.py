"""
Tests for bengal.rendering.template_engine.environment module.

Tests Jinja2 environment configuration including bytecode caching behavior.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.rendering.template_engine.environment import create_jinja_environment


class TestBytecodeCache:
    """Tests for bytecode cache configuration in different modes."""

    def test_bytecode_cache_disabled_in_dev_mode(self, tmp_path: Path) -> None:
        """Test that bytecode cache is disabled when dev_server=True."""
        # Create mock site with dev_server=True
        mock_site = MagicMock()
        mock_site.root_path = tmp_path
        mock_site.theme = "default"
        mock_site.theme_config = {}
        mock_site.output_dir = tmp_path / "public"
        mock_site.output_dir.mkdir()
        mock_site.config = {
            "dev_server": True,  # Dev mode enabled
            "cache_templates": True,  # Cache would be enabled normally
        }
        # Required Site attributes for template engine
        mock_site.dev_mode = True
        mock_site._bengal_template_dirs_cache = None
        mock_site._bengal_theme_chain_cache = None

        # Create mock template engine
        mock_engine = MagicMock()
        mock_engine._url_for = MagicMock(return_value="/")
        mock_engine._get_menu = MagicMock(return_value=[])
        mock_engine._get_menu_lang = MagicMock(return_value=[])
        mock_engine._asset_url = MagicMock(return_value="/assets/test.css")

        # Create environment
        env, _template_dirs = create_jinja_environment(mock_site, mock_engine)

        # Verify bytecode cache is None (disabled)
        assert env.bytecode_cache is None, (
            "Bytecode cache should be None in dev mode even when cache_templates=True"
        )

        # Verify auto_reload is enabled
        assert env.auto_reload is True, "auto_reload should be True in dev mode"

    def test_bytecode_cache_enabled_in_production(self, tmp_path: Path) -> None:
        """Test that bytecode cache is enabled when dev_server=False."""
        # Create mock site with dev_server=False
        mock_site = MagicMock()
        mock_site.root_path = tmp_path
        mock_site.theme = "default"
        mock_site.theme_config = {}
        mock_site.output_dir = tmp_path / "public"
        mock_site.output_dir.mkdir()
        mock_site.config = {
            "dev_server": False,  # Production mode
            "cache_templates": True,  # Cache enabled
        }
        # Required Site attributes for template engine
        mock_site.dev_mode = False
        mock_site._bengal_template_dirs_cache = None
        mock_site._bengal_theme_chain_cache = None

        # Create paths object for cache directory
        from bengal.cache.paths import BengalPaths

        mock_site.paths = BengalPaths(tmp_path)
        mock_site.paths.ensure_dirs()

        # Create mock template engine
        mock_engine = MagicMock()
        mock_engine._url_for = MagicMock(return_value="/")
        mock_engine._get_menu = MagicMock(return_value=[])
        mock_engine._get_menu_lang = MagicMock(return_value=[])
        mock_engine._asset_url = MagicMock(return_value="/assets/test.css")

        # Create environment
        env, _template_dirs = create_jinja_environment(mock_site, mock_engine)

        # Verify bytecode cache is enabled
        assert env.bytecode_cache is not None, (
            "Bytecode cache should be enabled in production mode with cache_templates=True"
        )

        # Verify auto_reload is disabled
        assert env.auto_reload is False, "auto_reload should be False in production mode"

    def test_bytecode_cache_disabled_when_cache_templates_false(self, tmp_path: Path) -> None:
        """Test that bytecode cache is disabled when cache_templates=False."""
        # Create mock site with cache_templates=False
        mock_site = MagicMock()
        mock_site.root_path = tmp_path
        mock_site.theme = "default"
        mock_site.theme_config = {}
        mock_site.output_dir = tmp_path / "public"
        mock_site.output_dir.mkdir()
        mock_site.config = {
            "dev_server": False,  # Production mode
            "cache_templates": False,  # Cache explicitly disabled
        }

        # Create mock template engine
        mock_engine = MagicMock()
        mock_engine._url_for = MagicMock(return_value="/")
        mock_engine._get_menu = MagicMock(return_value=[])
        mock_engine._get_menu_lang = MagicMock(return_value=[])
        mock_engine._asset_url = MagicMock(return_value="/assets/test.css")

        # Create environment
        env, _template_dirs = create_jinja_environment(mock_site, mock_engine)

        # Verify bytecode cache is None (disabled)
        assert env.bytecode_cache is None, (
            "Bytecode cache should be None when cache_templates=False"
        )
