"""Tests for deferred highlighting (CodeBlockCollector, highlight_many path)."""

from __future__ import annotations

import pytest
import rosettes

from bengal.rendering.highlighting.cache import HighlightCache
from bengal.rendering.highlighting.deferred import (
    CodeBlockCollector,
    disable_deferred_highlighting,
    enable_deferred_highlighting,
    get_deferred_collector,
)


class TestCodeBlockCollectorFlush:
    """Test CodeBlockCollector.flush uses unified highlight_many path."""

    def test_flush_empty_returns_empty(self) -> None:
        """flush() with no blocks should return empty dict."""
        collector = CodeBlockCollector()
        assert collector.flush() == {}

    def test_flush_simple_blocks(self) -> None:
        """flush() should highlight simple blocks via highlight_many."""
        collector = CodeBlockCollector()
        collector.add("x = 1", "python")
        collector.add("const y = 2;", "javascript")

        results = collector.flush()

        assert len(results) == 2
        block_ids = list(results.keys())
        assert "x" in results[block_ids[0]]
        assert "const" in results[block_ids[1]]

    def test_flush_with_hl_lines(self) -> None:
        """flush() should process blocks with hl_lines via highlight_many."""
        collector = CodeBlockCollector()
        collector.add("a = 1\nb = 2\nc = 3", "python", hl_lines=[2])

        results = collector.flush()

        assert len(results) == 1
        html = next(iter(results.values()))
        assert '<span class="hll">' in html

    def test_flush_mixed_simple_and_hl_lines(self) -> None:
        """flush() should handle mixed simple and hl_lines blocks in one batch."""
        collector = CodeBlockCollector()
        collector.add("x = 1", "python")
        collector.add("a\nb\nc", "python", hl_lines=[2])
        collector.add("fn main() {}", "rust")

        results = collector.flush()

        assert len(results) == 3
        html_list = list(results.values())
        assert any("x" in h for h in html_list)
        assert any('<span class="hll">' in h for h in html_list)
        assert any("fn" in h for h in html_list)

    def test_flush_uses_cache_when_provided(self) -> None:
        """flush() should return cached HTML when cache hit."""
        pytest.importorskip("rosettes", reason="rosettes.content_hash required")
        if not hasattr(rosettes, "content_hash"):
            pytest.skip("rosettes.content_hash required (rosettes>=0.2.0)")
        cache = HighlightCache()
        key = rosettes.content_hash("x = 1", "python")
        cache.set(key, "<pre class=\"cached\">cached html</pre>")

        try:
            enable_deferred_highlighting(cache=cache)
            collector = get_deferred_collector()
            assert collector is not None
            collector.add("x = 1", "python")
            results = collector.flush()

            assert len(results) == 1
            html = next(iter(results.values()))
            assert "cached html" in html
        finally:
            disable_deferred_highlighting()

    def test_flush_cache_miss_populates_cache(self) -> None:
        """flush() should store highlighted HTML in cache on miss."""
        pytest.importorskip("rosettes", reason="rosettes.content_hash required")
        if not hasattr(rosettes, "content_hash"):
            pytest.skip("rosettes.content_hash required (rosettes>=0.2.0)")
        cache = HighlightCache()
        try:
            enable_deferred_highlighting(cache=cache)
            collector = get_deferred_collector()
            assert collector is not None
            collector.add("x = 1", "python")
            results = collector.flush()

            assert len(results) == 1
            key = rosettes.content_hash("x = 1", "python")
            cached = cache.get(key)
            assert cached is not None
            assert "x" in cached
        finally:
            disable_deferred_highlighting()

    def test_flush_cache_disabled_ignores_cache(self) -> None:
        """flush() should produce correct results when cache is disabled."""
        pytest.importorskip("rosettes", reason="rosettes.content_hash required")
        if not hasattr(rosettes, "content_hash"):
            pytest.skip("rosettes.content_hash required (rosettes>=0.2.0)")
        cache = HighlightCache(enabled=False)
        try:
            enable_deferred_highlighting(cache=cache)
            collector = get_deferred_collector()
            assert collector is not None
            collector.add("x = 1", "python")
            results = collector.flush()

            assert len(results) == 1
            html = next(iter(results.values()))
            assert "x" in html
        finally:
            disable_deferred_highlighting()
