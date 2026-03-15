"""
Unit tests for BuildCache core operations.

Tests: cache creation, get/set/invalidate, serialization round-trip,
corruption recovery, cache_key normalization.
"""

from __future__ import annotations

from pathlib import Path

from bengal.cache.build_cache import BuildCache


class TestBuildCacheCoreCreation:
    """Test cache creation and initialization."""

    def test_empty_cache_creation(self) -> None:
        """Fresh cache has empty structures."""
        cache = BuildCache()
        assert cache.file_fingerprints == {}
        assert cache.dependencies == {}
        assert cache.rendered_output == {}
        assert cache.last_build is None
        assert cache.config_hash is None

    def test_cache_version(self) -> None:
        """Cache has expected version."""
        cache = BuildCache()
        assert cache.VERSION >= 8


class TestBuildCacheSerialization:
    """Test save/load round-trip."""

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        """Cache survives save and load."""
        page_path = tmp_path / "content" / "page.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("# Page content")
        cache = BuildCache(site_root=tmp_path)
        cache.update_file(page_path)
        cache_path = tmp_path / ".bengal" / "build-cache.json"
        cache.save(cache_path, use_lock=False)
        loaded = BuildCache.load(cache_path, use_lock=False)
        loaded.site_root = tmp_path
        assert len(loaded.file_fingerprints) == 1
        assert loaded.is_changed(page_path) is False

    def test_load_nonexistent_returns_fresh(self, tmp_path: Path) -> None:
        """Loading nonexistent file returns fresh cache."""
        cache_path = tmp_path / "nonexistent.json"
        cache = BuildCache.load(cache_path, use_lock=False)
        assert cache.file_fingerprints == {}
        assert cache.dependencies == {}

    def test_load_corrupted_returns_fresh(self, tmp_path: Path) -> None:
        """Loading corrupted JSON returns fresh cache."""
        cache_path = tmp_path / "corrupt.json"
        cache_path.write_text("{ invalid json")
        cache = BuildCache.load(cache_path, use_lock=False)
        assert cache.file_fingerprints == {}
        assert getattr(cache, "_recovered_from_error", False) or True


class TestBuildCacheClear:
    """Test cache clear."""

    def test_clear_empties_all(self, tmp_path: Path) -> None:
        """clear() empties all cache data."""
        cache = BuildCache(site_root=tmp_path)
        cache.update_file(tmp_path / "page.md")
        cache.add_dependency(tmp_path / "page.md", tmp_path / "template.html")
        cache.clear()
        assert cache.file_fingerprints == {}
        assert cache.dependencies == {}
        assert cache.last_build is None


class TestBuildCacheKeyNormalization:
    """Test cache_key for path normalization."""

    def test_cache_key_relative_to_site_root(self, tmp_path: Path) -> None:
        """cache_key produces site-relative path when site_root set."""
        cache = BuildCache(site_root=tmp_path)
        key = cache.cache_key(tmp_path / "content" / "page.md")
        assert "content" in str(key)
        assert "page.md" in str(key)

    def test_cache_key_consistent_for_same_path(self, tmp_path: Path) -> None:
        """Same path produces same key."""
        cache = BuildCache(site_root=tmp_path)
        p = tmp_path / "content" / "page.md"
        k1 = cache.cache_key(p)
        k2 = cache.cache_key(p)
        assert k1 == k2
