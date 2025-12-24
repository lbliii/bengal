"""
Unit tests for bengal.icons.resolver module.

Tests the theme-aware icon resolution system.
See: plan/drafted/rfc-theme-aware-icons.md
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.icons import resolver as icon_resolver


class TestIconResolutionOrder:
    """Test icon search path ordering."""

    def test_icon_resolution_uses_search_paths(self, tmp_path: Path) -> None:
        """Icons are loaded from configured search paths."""
        # Create a mock icons directory
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()
        (icons_dir / "test-icon.svg").write_text('<svg id="test"><!-- test --></svg>')

        # Manually set search paths (simulating initialization)
        icon_resolver._search_paths = [icons_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        # Load the icon
        content = icon_resolver.load_icon("test-icon")
        assert content is not None
        assert "<!-- test -->" in content

    def test_icon_fallthrough_to_later_paths(self, tmp_path: Path) -> None:
        """Missing icons fall through to later paths in search chain."""
        # Create two directories - first empty, second with icon
        first_dir = tmp_path / "first" / "icons"
        first_dir.mkdir(parents=True)

        second_dir = tmp_path / "second" / "icons"
        second_dir.mkdir(parents=True)
        (second_dir / "fallback.svg").write_text('<svg id="fallback"><!-- fallback --></svg>')

        # Set up search paths with fallthrough
        icon_resolver._search_paths = [first_dir, second_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        # Should find icon in second directory
        content = icon_resolver.load_icon("fallback")
        assert content is not None
        assert "<!-- fallback -->" in content

    def test_icon_first_match_wins(self, tmp_path: Path) -> None:
        """First matching icon in search chain wins."""
        # Create two directories with same icon name
        first_dir = tmp_path / "first" / "icons"
        first_dir.mkdir(parents=True)
        (first_dir / "shared.svg").write_text("<svg><!-- first-version --></svg>")

        second_dir = tmp_path / "second" / "icons"
        second_dir.mkdir(parents=True)
        (second_dir / "shared.svg").write_text("<svg><!-- second-version --></svg>")

        # Set up search paths
        icon_resolver._search_paths = [first_dir, second_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        # Should load first directory's version
        content = icon_resolver.load_icon("shared")
        assert content is not None
        assert "<!-- first-version -->" in content
        assert "<!-- second-version -->" not in content


class TestIconCaching:
    """Test caching behavior."""

    def test_icon_cache_hit(self, tmp_path: Path) -> None:
        """Second load uses cache, no disk I/O."""
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()
        icon_path = icons_dir / "cached.svg"
        icon_path.write_text("<svg><!-- original --></svg>")

        icon_resolver._search_paths = [icons_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        # First load
        content1 = icon_resolver.load_icon("cached")
        assert content1 is not None

        # Modify file on disk
        icon_path.write_text("<svg><!-- modified --></svg>")

        # Second load should return cached version
        content2 = icon_resolver.load_icon("cached")
        assert content2 == content1
        assert "<!-- original -->" in content2

    def test_icon_not_found_cache(self, tmp_path: Path) -> None:
        """Not-found icons are cached to avoid repeated disk checks."""
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()

        icon_resolver._search_paths = [icons_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        # First miss
        assert icon_resolver.load_icon("nonexistent") is None

        # Verify it's in the not-found cache
        assert "nonexistent" in icon_resolver._not_found_cache

        # Second miss should not hit disk again
        assert icon_resolver.load_icon("nonexistent") is None

    def test_clear_cache(self, tmp_path: Path) -> None:
        """clear_cache() allows reloading modified icons."""
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()
        icon_path = icons_dir / "reload.svg"
        icon_path.write_text("<svg><!-- v1 --></svg>")

        icon_resolver._search_paths = [icons_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        # Load first version
        content1 = icon_resolver.load_icon("reload")
        assert "<!-- v1 -->" in content1

        # Modify file
        icon_path.write_text("<svg><!-- v2 --></svg>")

        # Clear cache
        icon_resolver.clear_cache()

        # Should get new version
        content2 = icon_resolver.load_icon("reload")
        assert "<!-- v2 -->" in content2


class TestGetSearchPaths:
    """Test get_search_paths() function."""

    def test_get_search_paths_returns_copy(self, tmp_path: Path) -> None:
        """get_search_paths() returns a copy, not the original list."""
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()

        icon_resolver._search_paths = [icons_dir]
        icon_resolver._initialized = True

        paths = icon_resolver.get_search_paths()
        assert paths == [icons_dir]

        # Modifying returned list shouldn't affect internal state
        paths.append(tmp_path / "other")
        assert len(icon_resolver.get_search_paths()) == 1


class TestGetAvailableIcons:
    """Test get_available_icons() function."""

    def test_get_available_icons(self, tmp_path: Path) -> None:
        """get_available_icons() returns all icon names from search paths."""
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()
        (icons_dir / "alpha.svg").write_text("<svg></svg>")
        (icons_dir / "beta.svg").write_text("<svg></svg>")
        (icons_dir / "gamma.svg").write_text("<svg></svg>")

        icon_resolver._search_paths = [icons_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        icons = icon_resolver.get_available_icons()
        assert "alpha" in icons
        assert "beta" in icons
        assert "gamma" in icons

    def test_get_available_icons_deduplicates(self, tmp_path: Path) -> None:
        """Icons present in multiple paths appear only once."""
        first_dir = tmp_path / "first" / "icons"
        first_dir.mkdir(parents=True)
        (first_dir / "shared.svg").write_text("<svg></svg>")
        (first_dir / "first-only.svg").write_text("<svg></svg>")

        second_dir = tmp_path / "second" / "icons"
        second_dir.mkdir(parents=True)
        (second_dir / "shared.svg").write_text("<svg></svg>")
        (second_dir / "second-only.svg").write_text("<svg></svg>")

        icon_resolver._search_paths = [first_dir, second_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        icons = icon_resolver.get_available_icons()
        # Should have 3 unique icons
        assert len(icons) == 3
        assert "shared" in icons
        assert "first-only" in icons
        assert "second-only" in icons


class TestFallbackBehavior:
    """Test behavior when resolver is not initialized."""

    def test_fallback_to_default_path(self) -> None:
        """When not initialized, falls back to default theme path."""
        # Reset to uninitialized state
        icon_resolver._initialized = False
        icon_resolver._search_paths = []
        icon_resolver.clear_cache()

        # Should use fallback path
        paths = icon_resolver.get_search_paths()
        assert len(paths) == 1
        assert "themes" in str(paths[0])
        assert "default" in str(paths[0])

    def test_load_icon_works_without_initialization(self) -> None:
        """load_icon() works even without explicit initialization."""
        icon_resolver._initialized = False
        icon_resolver._search_paths = []
        icon_resolver.clear_cache()

        # Should be able to load icons from default path
        # (assuming default theme exists)
        content = icon_resolver.load_icon("warning")
        # Either returns content or None, but shouldn't raise
        assert content is None or isinstance(content, str)


class TestPreloading:
    """Test preloading functionality."""

    def test_preload_all_icons(self, tmp_path: Path) -> None:
        """_preload_all_icons() loads all icons into cache."""
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()
        (icons_dir / "icon1.svg").write_text("<svg>1</svg>")
        (icons_dir / "icon2.svg").write_text("<svg>2</svg>")
        (icons_dir / "icon3.svg").write_text("<svg>3</svg>")

        icon_resolver._search_paths = [icons_dir]
        icon_resolver._initialized = True
        icon_resolver.clear_cache()

        # Preload
        icon_resolver._preload_all_icons()

        # All icons should be in cache
        assert "icon1" in icon_resolver._icon_cache
        assert "icon2" in icon_resolver._icon_cache
        assert "icon3" in icon_resolver._icon_cache


class TestIsInitialized:
    """Test is_initialized() function."""

    def test_is_initialized_before_init(self) -> None:
        """is_initialized() returns False before initialization."""
        icon_resolver._initialized = False
        assert not icon_resolver.is_initialized()

    def test_is_initialized_after_init(self, tmp_path: Path) -> None:
        """is_initialized() returns True after initialization."""
        icon_resolver._search_paths = [tmp_path]
        icon_resolver._initialized = True
        assert icon_resolver.is_initialized()


class TestInitializeWithSite:
    """Test initialize() with mock Site object."""

    def test_initialize_with_mock_site(self, tmp_path: Path) -> None:
        """initialize() sets up search paths from Site."""
        icons_dir = tmp_path / "theme" / "assets" / "icons"
        icons_dir.mkdir(parents=True)

        # Create mock site
        mock_site = MagicMock()
        mock_site._get_theme_assets_chain.return_value = [tmp_path / "theme" / "assets"]
        mock_site.theme_config = MagicMock()
        mock_site.theme_config.icons = MagicMock()
        mock_site.theme_config.icons.extend_defaults = False

        # Clear state
        icon_resolver._initialized = False
        icon_resolver._search_paths = []
        icon_resolver.clear_cache()

        # Initialize
        icon_resolver.initialize(mock_site)

        # Check state
        assert icon_resolver.is_initialized()
        assert icons_dir in icon_resolver.get_search_paths()

    def test_initialize_with_extend_defaults(self, tmp_path: Path) -> None:
        """initialize() includes default theme when extend_defaults=True."""
        icons_dir = tmp_path / "theme" / "assets" / "icons"
        icons_dir.mkdir(parents=True)

        # Create mock site with extend_defaults=True
        mock_site = MagicMock()
        mock_site._get_theme_assets_chain.return_value = [tmp_path / "theme" / "assets"]
        mock_site.theme_config = MagicMock()
        mock_site.theme_config.icons = MagicMock()
        mock_site.theme_config.icons.extend_defaults = True

        # Clear state
        icon_resolver._initialized = False
        icon_resolver._search_paths = []
        icon_resolver.clear_cache()

        # Initialize
        icon_resolver.initialize(mock_site)

        # Should have theme icons + default icons
        paths = icon_resolver.get_search_paths()
        assert len(paths) >= 1
        # Default path should be included
        path_strs = [str(p) for p in paths]
        assert any("default" in p for p in path_strs)
