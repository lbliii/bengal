"""
Tests for get_engine_globals() - the engine-agnostic context layer.

This module tests the centralized template context infrastructure that
ensures consistent globals across all template engines (Jinja2, Kida).

Related RFC: plan/drafted/rfc-engine-agnostic-context-layer.md
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.rendering.context import (
    ConfigContext,
    MenusContext,
    SiteContext,
    ThemeContext,
    get_engine_globals,
)


@pytest.fixture
def mock_site():
    """Create a minimal mock site for testing get_engine_globals()."""
    site = MagicMock()
    site.config = {"title": "Test Site", "baseurl": "/"}
    site.root_path = Path("/tmp/test-site")
    site.output_dir = Path("/tmp/test-output")
    site.theme = "default"
    site.theme_config = MagicMock()
    site.theme_config.name = "default"
    site.versioning_enabled = False
    site.versions = []
    site.menu = {}
    site.menu_localized = {}
    return site


class TestGetEngineGlobals:
    """Unit tests for get_engine_globals() function."""

    def test_returns_dict(self, mock_site):
        """Function returns a dictionary."""
        result = get_engine_globals(mock_site)
        assert isinstance(result, dict)

    def test_includes_site_context(self, mock_site):
        """Includes SiteContext wrapper for safe template access."""
        result = get_engine_globals(mock_site)
        assert "site" in result
        assert isinstance(result["site"], SiteContext)

    def test_includes_config_context(self, mock_site):
        """Includes ConfigContext wrapper for safe config access."""
        result = get_engine_globals(mock_site)
        assert "config" in result
        assert isinstance(result["config"], ConfigContext)

    def test_includes_theme_context(self, mock_site):
        """Includes ThemeContext wrapper for theme access."""
        result = get_engine_globals(mock_site)
        assert "theme" in result
        assert isinstance(result["theme"], ThemeContext)

    def test_includes_menus_context(self, mock_site):
        """Includes MenusContext wrapper for menu access."""
        result = get_engine_globals(mock_site)
        assert "menus" in result
        assert isinstance(result["menus"], MenusContext)

    def test_includes_raw_site(self, mock_site):
        """Includes raw site reference for internal use."""
        result = get_engine_globals(mock_site)
        assert "_raw_site" in result
        assert result["_raw_site"] is mock_site

    def test_includes_bengal_metadata(self, mock_site):
        """Includes bengal metadata dict."""
        result = get_engine_globals(mock_site)
        assert "bengal" in result
        assert isinstance(result["bengal"], dict)

    def test_bengal_metadata_has_engine_info(self, mock_site):
        """Bengal metadata includes engine information."""
        result = get_engine_globals(mock_site)
        # Should have at least engine info (even fallback)
        assert "engine" in result["bengal"]

    def test_includes_versioning_enabled(self, mock_site):
        """Includes versioning_enabled flag."""
        result = get_engine_globals(mock_site)
        assert "versioning_enabled" in result
        assert result["versioning_enabled"] is False

    def test_includes_versions_list(self, mock_site):
        """Includes versions list."""
        result = get_engine_globals(mock_site)
        assert "versions" in result
        assert result["versions"] == []

    def test_versioning_enabled_true(self, mock_site):
        """Correctly reflects versioning_enabled when True."""
        mock_site.versioning_enabled = True
        mock_site.versions = [{"name": "v1.0"}]
        result = get_engine_globals(mock_site)
        assert result["versioning_enabled"] is True
        assert result["versions"] == [{"name": "v1.0"}]

    def test_includes_getattr(self, mock_site):
        """Includes Python's getattr builtin."""
        result = get_engine_globals(mock_site)
        assert "getattr" in result
        assert result["getattr"] is getattr

    def test_theme_context_empty_when_no_theme_config(self):
        """Returns empty ThemeContext when site has no theme_config."""
        from bengal.rendering.context import clear_global_context_cache

        clear_global_context_cache()

        # Create fresh site with no theme_config
        site = MagicMock()
        site.config = {"title": "Test Site"}
        site.theme_config = None
        site.versioning_enabled = False
        site.versions = []
        site.menu = {}
        site.menu_localized = {}

        result = get_engine_globals(site)
        assert "theme" in result
        assert isinstance(result["theme"], ThemeContext)
        # Empty theme returns "default" as fallback name
        assert result["theme"].name == "default"
        # Empty theme is falsy
        assert not result["theme"]

    def test_all_expected_keys_present(self, mock_site):
        """All documented keys are present in result."""
        result = get_engine_globals(mock_site)
        expected_keys = {
            "site",
            "config",
            "theme",
            "menus",
            "_raw_site",
            "bengal",
            "versioning_enabled",
            "versions",
            "getattr",
        }
        assert expected_keys <= set(result.keys())


class TestGetEngineGlobalsCaching:
    """Tests for caching behavior of get_engine_globals()."""

    def test_same_site_returns_cached_wrappers(self, mock_site):
        """Multiple calls with same site return cached wrappers."""
        result1 = get_engine_globals(mock_site)
        result2 = get_engine_globals(mock_site)

        # Context wrappers should be same object (cached)
        assert result1["site"] is result2["site"]
        assert result1["config"] is result2["config"]
        assert result1["theme"] is result2["theme"]
        assert result1["menus"] is result2["menus"]

    def test_different_sites_get_different_wrappers(self):
        """Different site instances get different wrappers."""
        from bengal.rendering.context import clear_global_context_cache

        clear_global_context_cache()

        site1 = MagicMock()
        site1.config = {"title": "Site 1"}
        site1.theme_config = None
        site1.versioning_enabled = False
        site1.versions = []
        site1.menu = {}
        site1.menu_localized = {}

        site2 = MagicMock()
        site2.config = {"title": "Site 2"}
        site2.theme_config = None
        site2.versioning_enabled = False
        site2.versions = []
        site2.menu = {}
        site2.menu_localized = {}

        result1 = get_engine_globals(site1)
        result2 = get_engine_globals(site2)

        # Different sites should have different wrappers
        assert result1["site"] is not result2["site"]
        assert result1["config"] is not result2["config"]


class TestGetEngineGlobalsThreadSafety:
    """Tests for thread safety of get_engine_globals()."""

    def test_concurrent_access_same_site(self, mock_site):
        """Concurrent calls with same site don't cause issues."""
        import concurrent.futures

        from bengal.rendering.context import clear_global_context_cache

        clear_global_context_cache()

        def get_globals():
            return get_engine_globals(mock_site)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(get_globals) for _ in range(10)]
            results = [f.result() for f in futures]

        # All should have same cached wrappers
        for result in results[1:]:
            assert result["site"] is results[0]["site"]
