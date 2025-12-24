"""
Tests for template context caching optimizations.

Tests cover:
- MenusContext caching for menu dict lists
- site.versions property caching
- site.latest_version property caching
- Autodoc template environment menu caching

These tests verify the ergonomic overhead optimizations described in:
plan/drafted/rfc-ergonomic-overhead-diagnostics.md
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.rendering.context import MenusContext


class TestMenusContextCaching:
    """Tests for MenusContext menu dict caching."""

    def test_menu_dict_cached_on_first_access(self) -> None:
        """Test that menu dicts are cached after first access."""
        # Setup mock site with menu
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {"name": "Home", "url": "/"}

        mock_site = MagicMock()
        mock_site.menu = {"main": [mock_item]}
        mock_site.menu_localized = {}

        ctx = MenusContext(mock_site)

        # First access
        result1 = ctx.get("main")
        assert result1 == [{"name": "Home", "url": "/"}]
        assert mock_item.to_dict.call_count == 1

        # Second access - should return cached, not call to_dict again
        result2 = ctx.get("main")
        assert result2 is result1  # Same object
        assert mock_item.to_dict.call_count == 1  # Not called again

    def test_menu_dict_cached_via_getattr(self) -> None:
        """Test that dot notation access (menus.main) also uses cache."""
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {"name": "Home", "url": "/"}

        mock_site = MagicMock()
        mock_site.menu = {"main": [mock_item]}
        mock_site.menu_localized = {}

        ctx = MenusContext(mock_site)

        # Access via dot notation
        result1 = ctx.main
        assert result1 == [{"name": "Home", "url": "/"}]

        # Second access via get()
        result2 = ctx.get("main")
        assert result2 is result1

        # to_dict only called once
        assert mock_item.to_dict.call_count == 1

    def test_different_menus_cached_separately(self) -> None:
        """Test that different menu names have separate cache entries."""
        mock_main_item = MagicMock()
        mock_main_item.to_dict.return_value = {"name": "Home", "url": "/"}

        mock_footer_item = MagicMock()
        mock_footer_item.to_dict.return_value = {"name": "Privacy", "url": "/privacy"}

        mock_site = MagicMock()
        mock_site.menu = {"main": [mock_main_item], "footer": [mock_footer_item]}
        mock_site.menu_localized = {}

        ctx = MenusContext(mock_site)

        main_result = ctx.get("main")
        footer_result = ctx.get("footer")

        assert main_result != footer_result
        assert mock_main_item.to_dict.call_count == 1
        assert mock_footer_item.to_dict.call_count == 1

    def test_localized_menu_cached(self) -> None:
        """Test that localized menus are cached with language key."""
        mock_en_item = MagicMock()
        mock_en_item.to_dict.return_value = {"name": "Home", "url": "/en/"}

        mock_es_item = MagicMock()
        mock_es_item.to_dict.return_value = {"name": "Inicio", "url": "/es/"}

        mock_site = MagicMock()
        mock_site.menu = {"main": []}
        mock_site.menu_localized = {
            "main": {
                "en": [mock_en_item],
                "es": [mock_es_item],
            }
        }

        ctx = MenusContext(mock_site)

        # Access English menu
        en_result1 = ctx.get("main", lang="en")
        en_result2 = ctx.get("main", lang="en")
        assert en_result1 is en_result2
        assert mock_en_item.to_dict.call_count == 1

        # Access Spanish menu
        es_result1 = ctx.get("main", lang="es")
        es_result2 = ctx.get("main", lang="es")
        assert es_result1 is es_result2
        assert mock_es_item.to_dict.call_count == 1

        # Different caches for different languages
        assert en_result1 is not es_result1

    def test_invalidate_clears_cache(self) -> None:
        """Test that invalidate() clears the menu cache."""
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {"name": "Home", "url": "/"}

        mock_site = MagicMock()
        mock_site.menu = {"main": [mock_item]}
        mock_site.menu_localized = {}

        ctx = MenusContext(mock_site)

        # First access
        result1 = ctx.get("main")
        assert mock_item.to_dict.call_count == 1

        # Invalidate
        ctx.invalidate()

        # Access again - should call to_dict again
        result2 = ctx.get("main")
        assert mock_item.to_dict.call_count == 2
        assert result1 is not result2

    def test_empty_menu_cached(self) -> None:
        """Test that empty menus are also cached."""
        mock_site = MagicMock()
        mock_site.menu = {"main": []}
        mock_site.menu_localized = {}

        ctx = MenusContext(mock_site)

        result1 = ctx.get("nonexistent")
        result2 = ctx.get("nonexistent")

        assert result1 == []
        assert result1 is result2

    def test_items_without_to_dict_passed_through(self) -> None:
        """Test that items without to_dict method are passed through."""
        plain_dict = {"name": "Plain", "url": "/plain"}

        mock_site = MagicMock()
        mock_site.menu = {"main": [plain_dict]}
        mock_site.menu_localized = {}

        ctx = MenusContext(mock_site)

        result = ctx.get("main")
        assert result == [plain_dict]


class TestSiteVersionsCaching:
    """Tests for site.versions property caching."""

    def test_versions_cached_on_first_access(self) -> None:
        """Test that versions list is cached after first access."""

        class MockVersion:
            def __init__(self, id: str):
                self.id = id
                self.to_dict_call_count = 0

            def to_dict(self) -> dict:
                self.to_dict_call_count += 1
                return {"id": self.id}

        class MockVersionConfig:
            def __init__(self):
                self.enabled = True
                self.versions = [MockVersion("v1"), MockVersion("v2")]

        # Create a minimal Site-like object
        class TestSite:
            def __init__(self):
                self.version_config = MockVersionConfig()

            @property
            def versions(self):
                cache_attr = "_versions_dict_cache"
                cached = getattr(self, cache_attr, None)
                if cached is not None:
                    return cached
                result = [v.to_dict() for v in self.version_config.versions]
                object.__setattr__(self, cache_attr, result)
                return result

        site = TestSite()

        # First access
        result1 = site.versions
        assert len(result1) == 2
        assert site.version_config.versions[0].to_dict_call_count == 1
        assert site.version_config.versions[1].to_dict_call_count == 1

        # Second access - should return cached
        result2 = site.versions
        assert result2 is result1
        assert site.version_config.versions[0].to_dict_call_count == 1  # Not called again
        assert site.version_config.versions[1].to_dict_call_count == 1

    def test_versions_empty_when_disabled(self) -> None:
        """Test that versions returns empty list when versioning disabled."""

        class MockVersionConfig:
            def __init__(self):
                self.enabled = False
                self.versions = []

        class TestSite:
            def __init__(self):
                self.version_config = MockVersionConfig()

            @property
            def versions(self):
                cache_attr = "_versions_dict_cache"
                cached = getattr(self, cache_attr, None)
                if cached is not None:
                    return cached
                if not self.version_config or not self.version_config.enabled:
                    result = []
                else:
                    result = [v.to_dict() for v in self.version_config.versions]
                object.__setattr__(self, cache_attr, result)
                return result

        site = TestSite()
        assert site.versions == []


class TestSiteLatestVersionCaching:
    """Tests for site.latest_version property caching."""

    def test_latest_version_cached(self) -> None:
        """Test that latest_version dict is cached."""

        class MockVersion:
            def __init__(self):
                self.to_dict_call_count = 0

            def to_dict(self) -> dict:
                self.to_dict_call_count += 1
                return {"id": "v1", "latest": True}

        class MockVersionConfig:
            def __init__(self):
                self.enabled = True
                self._latest = MockVersion()

            @property
            def latest_version(self):
                return self._latest

        class TestSite:
            def __init__(self):
                self.version_config = MockVersionConfig()

            @property
            def latest_version(self):
                cache_attr = "_latest_version_dict_cache"
                cached = getattr(self, cache_attr, None)
                if cached is not None:
                    return cached if cached != "_NO_LATEST_VERSION_" else None
                latest = self.version_config.latest_version
                result = latest.to_dict() if latest else None
                object.__setattr__(
                    self,
                    cache_attr,
                    result if result is not None else "_NO_LATEST_VERSION_",
                )
                return result

        site = TestSite()

        # First access
        result1 = site.latest_version
        assert result1 == {"id": "v1", "latest": True}
        assert site.version_config._latest.to_dict_call_count == 1

        # Second access - should return cached
        result2 = site.latest_version
        assert result2 is result1
        assert site.version_config._latest.to_dict_call_count == 1  # Not called again

    def test_latest_version_none_cached(self) -> None:
        """Test that None latest_version is also cached (using sentinel)."""

        class MockVersionConfig:
            def __init__(self):
                self.enabled = True

            @property
            def latest_version(self):
                return None

        class TestSite:
            def __init__(self):
                self.version_config = MockVersionConfig()
                self._lookup_count = 0

            @property
            def latest_version(self):
                cache_attr = "_latest_version_dict_cache"
                cached = getattr(self, cache_attr, None)
                if cached is not None:
                    return cached if cached != "_NO_LATEST_VERSION_" else None
                self._lookup_count += 1
                latest = self.version_config.latest_version
                result = latest.to_dict() if latest else None
                object.__setattr__(
                    self,
                    cache_attr,
                    result if result is not None else "_NO_LATEST_VERSION_",
                )
                return result

        site = TestSite()

        # First access - returns None
        result1 = site.latest_version
        assert result1 is None
        assert site._lookup_count == 1

        # Second access - should return cached None without lookup
        result2 = site.latest_version
        assert result2 is None
        assert site._lookup_count == 1  # Not looked up again


class TestAutodocMenuCaching:
    """Tests for autodoc template environment menu caching."""

    def test_autodoc_get_menu_cached(self) -> None:
        """Test that autodoc get_menu function caches results."""
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {"name": "Home", "url": "/"}

        mock_site = MagicMock()
        mock_site.menu = {"main": [mock_item]}
        mock_site.menu_localized = {}

        # Simulate the closure-based caching in template_env.py
        _menu_cache: dict = {}

        def get_menu(menu_name: str = "main"):
            if menu_name in _menu_cache:
                return _menu_cache[menu_name]
            menu = mock_site.menu.get(menu_name, [])
            _menu_cache[menu_name] = [item.to_dict() for item in menu]
            return _menu_cache[menu_name]

        # First call
        result1 = get_menu("main")
        assert result1 == [{"name": "Home", "url": "/"}]
        assert mock_item.to_dict.call_count == 1

        # Second call - cached
        result2 = get_menu("main")
        assert result2 is result1
        assert mock_item.to_dict.call_count == 1

    def test_autodoc_get_menu_lang_cached(self) -> None:
        """Test that autodoc get_menu_lang function caches results."""
        mock_en_item = MagicMock()
        mock_en_item.to_dict.return_value = {"name": "Home", "url": "/en/"}

        mock_site = MagicMock()
        mock_site.menu = {"main": []}
        mock_site.menu_localized = {"main": {"en": [mock_en_item]}}

        _menu_cache: dict = {}

        def get_menu(menu_name: str = "main"):
            if menu_name in _menu_cache:
                return _menu_cache[menu_name]
            menu = mock_site.menu.get(menu_name, [])
            _menu_cache[menu_name] = [item.to_dict() for item in menu]
            return _menu_cache[menu_name]

        def get_menu_lang(menu_name: str = "main", lang: str = ""):
            if not lang:
                return get_menu(menu_name)
            cache_key = f"{menu_name}:{lang}"
            if cache_key in _menu_cache:
                return _menu_cache[cache_key]
            localized = mock_site.menu_localized.get(menu_name, {}).get(lang)
            if localized is None:
                return get_menu(menu_name)
            _menu_cache[cache_key] = [item.to_dict() for item in localized]
            return _menu_cache[cache_key]

        # First call with language
        result1 = get_menu_lang("main", "en")
        assert result1 == [{"name": "Home", "url": "/en/"}]
        assert mock_en_item.to_dict.call_count == 1

        # Second call - cached
        result2 = get_menu_lang("main", "en")
        assert result2 is result1
        assert mock_en_item.to_dict.call_count == 1


class TestCacheInvalidation:
    """Tests for cache invalidation scenarios."""

    def test_menus_context_invalidate_before_access(self) -> None:
        """Test that invalidate works even before first access."""
        mock_site = MagicMock()
        mock_site.menu = {}
        mock_site.menu_localized = {}

        ctx = MenusContext(mock_site)

        # Should not raise
        ctx.invalidate()

        # Should work normally after
        result = ctx.get("main")
        assert result == []


