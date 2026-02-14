"""Tests for HighlightCache."""

from __future__ import annotations

from bengal.rendering.highlighting.cache import HighlightCache


class TestHighlightCache:
    """Test HighlightCache get/set behavior."""

    def test_get_miss_returns_none(self) -> None:
        """get() should return None for unknown key."""
        cache = HighlightCache()
        assert cache.get("unknown") is None

    def test_set_and_get(self) -> None:
        """set() and get() should store and retrieve HTML."""
        cache = HighlightCache()
        cache.set("key1", "<pre>html</pre>")
        assert cache.get("key1") == "<pre>html</pre>"

    def test_disabled_get_returns_none(self) -> None:
        """get() should return None when cache is disabled."""
        cache = HighlightCache(enabled=False)
        cache.set("key1", "<pre>html</pre>")
        assert cache.get("key1") is None
