"""
Tests for GeneratedPageCache.

RFC: Output Cache Architecture - Tests caching of generated page output
based on member content hashes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from bengal.cache.generated_page_cache import (
    GeneratedPageCache,
    GeneratedPageCacheEntry,
    GENERATED_PAGE_CACHE_VERSION,
)


def make_mock_page(source_path: str) -> MagicMock:
    """Create a mock Page with source_path."""
    page = MagicMock()
    page.source_path = Path(source_path)
    return page


class TestGeneratedPageCacheEntry:
    """Tests for GeneratedPageCacheEntry dataclass."""

    def test_to_dict_roundtrip(self) -> None:
        """Entry can be serialized and deserialized."""
        entry = GeneratedPageCacheEntry(
            page_type="tag",
            page_id="python",
            content_hash="abc123",
            template_hash="def456",
            member_hashes={"a.md": "hash1", "b.md": "hash2"},
            cached_html="<html>test</html>",
            last_generated="2026-01-14T12:00:00",
            generation_time_ms=100,
        )
        
        data = entry.to_dict()
        restored = GeneratedPageCacheEntry.from_dict(data)
        
        assert restored.page_type == entry.page_type
        assert restored.page_id == entry.page_id
        assert restored.content_hash == entry.content_hash
        assert restored.template_hash == entry.template_hash
        assert restored.member_hashes == entry.member_hashes
        assert restored.cached_html == entry.cached_html

    def test_from_dict_handles_missing_fields(self) -> None:
        """Handles missing optional fields gracefully."""
        data = {
            "page_type": "tag",
            "page_id": "python",
        }
        
        entry = GeneratedPageCacheEntry.from_dict(data)
        
        assert entry.page_type == "tag"
        assert entry.page_id == "python"
        assert entry.content_hash == ""
        assert entry.member_hashes == {}
        assert entry.cached_html is None


class TestGeneratedPageCache:
    """Tests for GeneratedPageCache class."""

    def test_get_cache_key(self, tmp_path: Path) -> None:
        """Cache key combines type and id."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        key = cache.get_cache_key("tag", "python")
        
        assert key == "tag:python"

    def test_compute_member_hash_deterministic(self, tmp_path: Path) -> None:
        """Member hash is deterministic for same inputs."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md"), make_mock_page("b.md")]
        hashes = {"a.md": "hash1", "b.md": "hash2"}
        
        hash1 = cache.compute_member_hash(pages, hashes)
        hash2 = cache.compute_member_hash(pages, hashes)
        
        assert hash1 == hash2

    def test_compute_member_hash_order_independent(self, tmp_path: Path) -> None:
        """Member hash is same regardless of page order."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages_forward = [make_mock_page("a.md"), make_mock_page("b.md")]
        pages_reverse = [make_mock_page("b.md"), make_mock_page("a.md")]
        hashes = {"a.md": "hash1", "b.md": "hash2"}
        
        hash1 = cache.compute_member_hash(pages_forward, hashes)
        hash2 = cache.compute_member_hash(pages_reverse, hashes)
        
        assert hash1 == hash2

    def test_should_regenerate_true_for_missing(self, tmp_path: Path) -> None:
        """Returns True when no cache entry exists."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md")]
        hashes = {"a.md": "hash1"}
        
        result = cache.should_regenerate("tag", "python", pages, hashes)
        
        assert result is True

    def test_should_regenerate_false_for_cached(self, tmp_path: Path) -> None:
        """Returns False when cache is valid."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md"), make_mock_page("b.md")]
        hashes = {"a.md": "hash1", "b.md": "hash2"}
        
        # First call: needs regeneration
        assert cache.should_regenerate("tag", "python", pages, hashes) is True
        
        # Update cache
        cache.update("tag", "python", pages, hashes, "<html>test</html>", 100)
        
        # Second call: cached
        assert cache.should_regenerate("tag", "python", pages, hashes) is False

    def test_should_regenerate_true_when_content_changed(self, tmp_path: Path) -> None:
        """Returns True when member content changed."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md")]
        
        # Initial cache
        cache.update("tag", "python", pages, {"a.md": "hash1"}, "<html>v1</html>", 100)
        
        # Content changed
        result = cache.should_regenerate("tag", "python", pages, {"a.md": "hash2"})
        
        assert result is True

    def test_should_regenerate_true_when_template_changed(self, tmp_path: Path) -> None:
        """Returns True when template hash changed."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md")]
        hashes = {"a.md": "hash1"}
        
        # Initial cache with template v1
        cache.update("tag", "python", pages, hashes, "<html>v1</html>", 100, "template_v1")
        
        # Same content, different template
        assert cache.should_regenerate("tag", "python", pages, hashes, "template_v1") is False
        assert cache.should_regenerate("tag", "python", pages, hashes, "template_v2") is True

    def test_get_cached_html_returns_cached(self, tmp_path: Path) -> None:
        """Returns cached HTML when available."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md")]
        hashes = {"a.md": "hash1"}
        html = "<html>cached content</html>"
        
        cache.update("tag", "python", pages, hashes, html, 100)
        
        result = cache.get_cached_html("tag", "python")
        
        assert result == html

    def test_get_cached_html_returns_none_for_missing(self, tmp_path: Path) -> None:
        """Returns None when no cache entry."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        result = cache.get_cached_html("tag", "nonexistent")
        
        assert result is None

    def test_large_html_not_cached(self, tmp_path: Path) -> None:
        """HTML over threshold is not cached."""
        cache = GeneratedPageCache(tmp_path / "cache.json", html_cache_threshold=100)
        
        pages = [make_mock_page("a.md")]
        hashes = {"a.md": "hash1"}
        large_html = "x" * 200  # Over threshold
        
        cache.update("tag", "python", pages, hashes, large_html, 100)
        
        result = cache.get_cached_html("tag", "python")
        
        assert result is None

    def test_invalidate_removes_entry(self, tmp_path: Path) -> None:
        """Invalidate removes specific entry."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md")]
        hashes = {"a.md": "hash1"}
        
        cache.update("tag", "python", pages, hashes, "<html>test</html>", 100)
        cache.update("tag", "rust", pages, hashes, "<html>test</html>", 100)
        
        result = cache.invalidate("tag", "python")
        
        assert result is True
        assert cache.get_cached_html("tag", "python") is None
        assert cache.get_cached_html("tag", "rust") is not None

    def test_clear_removes_all_entries(self, tmp_path: Path) -> None:
        """Clear removes all entries."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md")]
        hashes = {"a.md": "hash1"}
        
        cache.update("tag", "python", pages, hashes, "<html>test</html>", 100)
        cache.update("tag", "rust", pages, hashes, "<html>test</html>", 100)
        
        cache.clear()
        
        assert cache.get_cached_html("tag", "python") is None
        assert cache.get_cached_html("tag", "rust") is None

    def test_get_stats(self, tmp_path: Path) -> None:
        """Returns useful statistics."""
        cache = GeneratedPageCache(tmp_path / "cache.json")
        
        pages = [make_mock_page("a.md")]
        hashes = {"a.md": "hash1"}
        
        cache.update("tag", "python", pages, hashes, "<html>test</html>", 100)
        cache.update("tag", "rust", pages, hashes, "<html>test</html>", 100)
        
        stats = cache.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["entries_with_html"] == 2
        assert "by_type" in stats
        assert stats["by_type"]["tag"] == 2
