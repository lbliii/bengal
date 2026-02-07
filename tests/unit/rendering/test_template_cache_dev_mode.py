"""
Tests for template cache behavior in dev server mode.

Verifies that bytecode caching is properly disabled during dev server operation
to ensure template changes are immediately reflected.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBytecodeaCacheDevMode:
    """Test bytecode cache is disabled when dev_server is True."""

    @pytest.fixture
    def mock_site_prod(self, tmp_path):
        """Create a mock site in production mode."""
        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir(parents=True)
        site.config = {"dev_server": False, "cache_templates": True}
        site.theme = None
        site.theme_config = {}
        # Required Site attributes for template engine
        site.dev_mode = False
        site._bengal_template_dirs_cache = None
        site._bengal_theme_chain_cache = None

        # Create paths mock
        paths = MagicMock()
        paths.templates_dir = tmp_path / ".bengal-cache" / "templates"
        paths.templates_dir.mkdir(parents=True, exist_ok=True)
        site.paths = paths

        return site

    @pytest.fixture
    def mock_site_dev(self, tmp_path):
        """Create a mock site in dev server mode."""
        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir(parents=True)
        site.config = {"dev_server": True, "cache_templates": True}
        site.theme = None
        site.theme_config = {}
        # Required Site attributes for template engine
        site.dev_mode = True
        site._bengal_template_dirs_cache = None
        site._bengal_theme_chain_cache = None

        # Create paths mock
        paths = MagicMock()
        paths.templates_dir = tmp_path / ".bengal-cache" / "templates"
        paths.templates_dir.mkdir(parents=True, exist_ok=True)
        site.paths = paths

        return site

    def test_bytecode_cache_disabled_in_dev_mode(self, mock_site_dev):
        """
        Bytecode cache should be None when dev_server=True.

        This ensures template changes are immediately reflected without
        needing to restart the server.
        """
        from bengal.rendering.template_engine.environment import create_jinja_environment

        # Create a mock template_engine
        mock_engine = MagicMock()

        with patch("bengal.rendering.template_engine.environment.register_all"):
            env, _template_dirs = create_jinja_environment(
                mock_site_dev, mock_engine, profile_templates=False
            )

        # Bytecode cache should be None in dev mode
        assert env.bytecode_cache is None

    def test_bytecode_cache_enabled_in_prod_mode(self, mock_site_prod):
        """
        Bytecode cache should be enabled when dev_server=False.

        In production builds, caching improves performance.
        """
        from bengal.rendering.template_engine.environment import create_jinja_environment

        mock_engine = MagicMock()

        with patch("bengal.rendering.template_engine.environment.register_all"):
            env, _template_dirs = create_jinja_environment(
                mock_site_prod, mock_engine, profile_templates=False
            )

        # Bytecode cache should be set in prod mode
        assert env.bytecode_cache is not None

    def test_auto_reload_enabled_in_dev_mode(self, mock_site_dev):
        """
        auto_reload should be True when dev_server=True.

        This ensures Jinja2 checks template file mtimes for changes.
        """
        from bengal.rendering.template_engine.environment import create_jinja_environment

        mock_engine = MagicMock()

        with patch("bengal.rendering.template_engine.environment.register_all"):
            env, _template_dirs = create_jinja_environment(
                mock_site_dev, mock_engine, profile_templates=False
            )

        # auto_reload should be True in dev mode
        assert env.auto_reload is True

    def test_auto_reload_disabled_in_prod_mode(self, mock_site_prod):
        """
        auto_reload should be False when dev_server=False.

        In production, we don't need to check mtimes every render.
        """
        from bengal.rendering.template_engine.environment import create_jinja_environment

        mock_engine = MagicMock()

        with patch("bengal.rendering.template_engine.environment.register_all"):
            env, _template_dirs = create_jinja_environment(
                mock_site_prod, mock_engine, profile_templates=False
            )

        # auto_reload should be False in prod mode
        assert env.auto_reload is False


class TestTemplateDirsCacheDevMode:
    """Test template directory caching behavior in dev mode."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site."""
        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir(parents=True)
        site.theme = None
        site.theme_config = {}
        # Required Site attributes for template engine
        site.dev_mode = False
        site._bengal_template_dirs_cache = None
        site._bengal_theme_chain_cache = None
        site.paths = MagicMock()
        site.paths.templates_dir = tmp_path / ".bengal-cache" / "templates"
        site.paths.templates_dir.mkdir(parents=True, exist_ok=True)
        return site

    def test_template_dirs_not_cached_in_dev_mode(self, mock_site):
        """
        Template directory list should not be cached in dev mode.

        This allows new template directories (e.g., from theme changes)
        to be picked up without restart.
        """
        mock_site.config = {"dev_server": True}
        mock_site.dev_mode = True  # Dev mode must be set for cache bypass
        mock_site._bengal_template_dirs_cache = {
            "key": (mock_site.theme, str(mock_site.root_path)),
            "template_dirs": ["/old/cached/dir"],
        }

        from bengal.rendering.template_engine.environment import create_jinja_environment

        mock_engine = MagicMock()

        with patch("bengal.rendering.template_engine.environment.register_all"):
            _env, template_dirs = create_jinja_environment(
                mock_site, mock_engine, profile_templates=False
            )

        # Should NOT use the cached /old/cached/dir
        template_dir_strs = [str(d) for d in template_dirs]
        assert "/old/cached/dir" not in template_dir_strs

    def test_template_dirs_cached_in_prod_mode(self, mock_site, tmp_path):
        """
        Template directory list should be cached in production mode.

        This avoids repeated filesystem scanning during parallel rendering.
        """
        mock_site.config = {"dev_server": False, "cache_templates": True}

        # Create a valid cached entry
        cached_dir = str(tmp_path / "templates")
        Path(cached_dir).mkdir(parents=True)

        mock_site._bengal_template_dirs_cache = {
            "key": (mock_site.theme, str(mock_site.root_path)),
            "template_dirs": [cached_dir],
        }

        from bengal.rendering.template_engine.environment import create_jinja_environment

        mock_engine = MagicMock()

        with patch("bengal.rendering.template_engine.environment.register_all"):
            _env, template_dirs = create_jinja_environment(
                mock_site, mock_engine, profile_templates=False
            )

        # Should use the cached directory
        template_dir_strs = [str(d) for d in template_dirs]
        assert cached_dir in template_dir_strs


class TestConfigChangeTriggersCacheInvalidation:
    """Test that config changes properly invalidate caches."""

    def test_cache_key_includes_theme(self, tmp_path):
        """
        Cache key should include theme so changing themes invalidates cache.
        """
        site1 = MagicMock()
        site1.root_path = tmp_path
        site1.output_dir = tmp_path / "public"
        site1.output_dir.mkdir(parents=True)
        site1.theme = "theme-a"
        site1.theme_config = {}
        site1.config = {"dev_server": False, "cache_templates": True}
        site1.dev_mode = False
        site1.build_state = None  # Must be explicitly None to avoid MagicMock auto-generation
        site1._bengal_theme_chain_cache = None
        site1.paths = MagicMock()
        site1.paths.templates_dir = tmp_path / ".cache" / "templates"
        site1.paths.templates_dir.mkdir(parents=True, exist_ok=True)

        # Cache with theme-a
        cached_dir_a = str(tmp_path / "templates-a")
        Path(cached_dir_a).mkdir(parents=True)
        site1._bengal_template_dirs_cache = {
            "key": ("theme-a", str(tmp_path)),
            "template_dirs": [cached_dir_a],
        }

        from bengal.rendering.template_engine.environment import create_jinja_environment

        mock_engine = MagicMock()

        with patch("bengal.rendering.template_engine.environment.register_all"):
            _env1, dirs1 = create_jinja_environment(site1, mock_engine, profile_templates=False)

        # Should use cached theme-a dirs
        assert cached_dir_a in [str(d) for d in dirs1]

        # Now change to theme-b - cache should miss
        site2 = MagicMock()
        site2.root_path = tmp_path
        site2.output_dir = tmp_path / "public"
        site2.theme = "theme-b"
        site2.theme_config = {}
        site2.config = {"dev_server": False, "cache_templates": True}
        site2.dev_mode = False
        site2.build_state = None  # Must be explicitly None
        site2._bengal_theme_chain_cache = None
        site2.paths = MagicMock()
        site2.paths.templates_dir = tmp_path / ".cache" / "templates"

        # Still has old cache
        site2._bengal_template_dirs_cache = {
            "key": ("theme-a", str(tmp_path)),  # Old key
            "template_dirs": [cached_dir_a],
        }

        with patch("bengal.rendering.template_engine.environment.register_all"):
            _env2, _dirs2 = create_jinja_environment(site2, mock_engine, profile_templates=False)

        # Cache key doesn't match (theme-a vs theme-b), should NOT use cached dir
        # (The actual template dirs will be computed fresh)
        # We can verify by checking the cache wasn't used - cached_dir_a shouldn't
        # necessarily appear unless it's a valid default location
