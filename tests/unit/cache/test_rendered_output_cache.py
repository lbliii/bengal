"""
Unit tests for RenderedOutputCacheMixin (rendered output caching).

Tests: cache hit/miss, invalidation on content change, metadata hash change,
template change, stale entry detection.
"""

from __future__ import annotations

from pathlib import Path

from bengal.cache.build_cache import BuildCache
from bengal.utils.primitives.sentinel import MISSING


class TestRenderedOutputCacheStoreGet:
    """Test store and get rendered output."""

    def test_store_and_get_hit(self, tmp_path: Path) -> None:
        """Stored output is returned on get."""
        cache = BuildCache(site_root=tmp_path)
        page_path = tmp_path / "content" / "page.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("# Page")
        cache.update_file(page_path)
        cache.store_rendered_output(
            page_path,
            html="<html><body>Hello</body></html>",
            template="page.html",
            metadata={"title": "Test"},
        )
        result = cache.get_rendered_output(
            page_path,
            template="page.html",
            metadata={"title": "Test"},
        )
        assert result == "<html><body>Hello</body></html>"

    def test_get_miss_when_not_cached(self, tmp_path: Path) -> None:
        """Uncached page returns MISSING."""
        cache = BuildCache(site_root=tmp_path)
        page_path = tmp_path / "content" / "page.md"
        result = cache.get_rendered_output(
            page_path,
            template="page.html",
            metadata={"title": "Test"},
        )
        assert result is MISSING

    def test_get_miss_when_metadata_changed(self, tmp_path: Path) -> None:
        """Metadata change invalidates cache."""
        cache = BuildCache(site_root=tmp_path)
        page_path = tmp_path / "content" / "page.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("# Page")
        cache.update_file(page_path)
        cache.store_rendered_output(
            page_path,
            html="<html>Original</html>",
            template="page.html",
            metadata={"title": "Original"},
        )
        result = cache.get_rendered_output(
            page_path,
            template="page.html",
            metadata={"title": "Changed"},
        )
        assert result is MISSING

    def test_get_miss_when_template_changed(self, tmp_path: Path) -> None:
        """Template name change invalidates cache."""
        cache = BuildCache(site_root=tmp_path)
        page_path = tmp_path / "content" / "page.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("# Page")
        cache.update_file(page_path)
        cache.store_rendered_output(
            page_path,
            html="<html>Content</html>",
            template="page.html",
            metadata={"title": "Test"},
        )
        result = cache.get_rendered_output(
            page_path,
            template="other.html",
            metadata={"title": "Test"},
        )
        assert result is MISSING


class TestRenderedOutputCacheInvalidate:
    """Test invalidation."""

    def test_invalidate_removes_entry(self, tmp_path: Path) -> None:
        """invalidate_rendered_output removes cached entry."""
        cache = BuildCache(site_root=tmp_path)
        page_path = tmp_path / "content" / "page.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("# Page")
        cache.update_file(page_path)
        cache.store_rendered_output(
            page_path,
            html="<html>x</html>",
            template="page.html",
            metadata={},
        )
        removed = cache.invalidate_rendered_output(page_path)
        assert removed is True
        result = cache.get_rendered_output(page_path, template="page.html", metadata={})
        assert result is MISSING

    def test_invalidate_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """invalidate_rendered_output returns False when not present."""
        cache = BuildCache(site_root=tmp_path)
        page_path = tmp_path / "content" / "nonexistent.md"
        removed = cache.invalidate_rendered_output(page_path)
        assert removed is False


class TestRenderedOutputCacheStats:
    """Test get_rendered_output_stats."""

    def test_stats_empty_cache(self) -> None:
        """Empty cache returns zero stats."""
        cache = BuildCache()
        stats = cache.get_rendered_output_stats()
        assert stats["cached_pages"] == 0
        assert stats["total_size_mb"] == 0

    def test_stats_with_entries(self, tmp_path: Path) -> None:
        """Stats reflect cached entries."""
        cache = BuildCache(site_root=tmp_path)
        page_path = tmp_path / "content" / "page.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("# Page")
        cache.update_file(page_path)
        html = "<html><body>Hello World</body></html>"
        cache.store_rendered_output(
            page_path,
            html=html,
            template="page.html",
            metadata={},
        )
        stats = cache.get_rendered_output_stats()
        assert stats["cached_pages"] == 1
        assert stats["total_size_mb"] > 0
