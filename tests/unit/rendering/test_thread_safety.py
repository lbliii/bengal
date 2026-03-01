"""
Thread-safety tests for rendering components under free-threading (PEP 703).

These tests verify that rendering components are safe for concurrent access,
which is critical for Python 3.14t free-threading support.

RFC: rfc-free-threading-hardening.md
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bengal.rendering.block_cache import BlockCache

pytestmark = pytest.mark.parallel_unsafe

if TYPE_CHECKING:
    pass


class TestBlockCacheThreadSafety:
    """Test BlockCache under concurrent access."""

    def test_concurrent_set_same_block(self) -> None:
        """Verify setting the same block from multiple threads is safe."""
        cache = BlockCache()
        errors: list[Exception] = []
        set_count = 0
        count_lock = threading.Lock()

        def set_block(thread_id: int) -> None:
            nonlocal set_count
            try:
                cache.set("base.html", "nav", f"<nav>content-{thread_id}</nav>")
                with count_lock:
                    set_count += 1
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=set_block, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        # Block should exist (content from whichever thread won)
        assert cache.get("base.html", "nav") is not None
        # Should only be counted once despite multiple set attempts
        assert cache.get_stats()["site_blocks_cached"] == 1

    def test_concurrent_get_and_set(self) -> None:
        """Verify concurrent reads and writes don't cause issues."""
        cache = BlockCache()
        cache.set("base.html", "footer", "<footer>initial</footer>")
        errors: list[Exception] = []
        results: list[str | None] = []
        results_lock = threading.Lock()

        def reader() -> None:
            try:
                for _ in range(100):
                    result = cache.get("base.html", "footer")
                    with results_lock:
                        results.append(result)
            except Exception as e:
                errors.append(e)

        def writer(thread_id: int) -> None:
            try:
                cache.set("base.html", f"block_{thread_id}", f"<div>{thread_id}</div>")
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            # Mix readers and writers
            for i in range(5):
                futures.append(executor.submit(reader))
                futures.append(executor.submit(writer, i))

            for _f in as_completed(futures):
                pass

        assert not errors, f"Thread safety errors: {errors}"
        # All reads should return valid content
        assert all(r is not None for r in results)

    def test_stats_thread_safety(self) -> None:
        """Verify stats updates are thread-safe."""
        cache = BlockCache()
        # Pre-populate some blocks
        for i in range(5):
            cache.set("base.html", f"block_{i}", f"<div>{i}</div>")

        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(100):
                    cache.get("base.html", "block_0")  # Hit
                    cache.get("base.html", "nonexistent")  # Miss
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        stats = cache.get_stats()
        # Should have tracked all hits and misses
        assert stats["hits"] == 10 * 100  # 10 threads × 100 hits each
        assert stats["misses"] == 10 * 100  # 10 threads × 100 misses each

    def test_clear_is_safe_when_no_readers(self) -> None:
        """Verify clear() is safe when called between build phases.

        Note: BlockCache is designed for the pattern:
        1. Populate cache (warm_site_blocks)
        2. Read during parallel rendering
        3. Clear between builds

        clear() is NOT designed to be called while readers are active.
        This test verifies the safe pattern works correctly.
        """
        cache = BlockCache()

        # Phase 1: Populate
        for i in range(10):
            cache.set("base.html", f"block_{i}", f"<div>{i}</div>")

        # Phase 2: Concurrent reads (no clear)
        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(100):
                    cache.get("base.html", "block_0")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors during reads: {errors}"

        # Phase 3: Clear between builds (no readers)
        cache.clear()

        assert cache.get("base.html", "block_0") is None
        assert cache.get_stats()["site_blocks_cached"] == 0


class TestIconThreadSafety:
    """Test icon() function under concurrent access."""

    def test_icon_concurrent_rendering(self) -> None:
        """Verify icon() is safe when called from multiple threads."""
        from bengal.rendering.template_functions.icons import icon

        errors: list[Exception] = []
        results: list[str] = []
        results_lock = threading.Lock()

        def render_icons() -> None:
            try:
                for name in ["search", "menu", "close", "arrow-up"]:
                    result = icon(name, size=24)
                    with results_lock:
                        results.append(str(result))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=render_icons) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        # All threads should have rendered icons (40 total = 10 threads × 4 icons)
        assert len(results) == 40

    def test_icon_cache_thread_safety(self) -> None:
        """Verify icon render cache is thread-safe."""
        from bengal.rendering.template_functions.icons import (
            _icon_render_cache,
            clear_icon_cache,
            icon,
        )

        clear_icon_cache()
        errors: list[Exception] = []

        def render_same_icon() -> None:
            try:
                for _ in range(50):
                    icon("search", size=24, css_class="test")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=render_same_icon) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        # Cache should have been used (high hit rate after initial miss)
        stats = _icon_render_cache.stats()
        assert stats["hits"] > 0


class TestAssetTrackerThreadSafety:
    """Test AssetTracker under concurrent access."""

    def test_concurrent_tracking(self) -> None:
        """Verify concurrent asset tracking is safe."""
        from bengal.rendering.asset_tracking import AssetTracker

        tracker = AssetTracker()
        errors: list[Exception] = []

        def track_assets(thread_id: int) -> None:
            try:
                for i in range(100):
                    tracker.track(f"/assets/thread_{thread_id}/file_{i}.css")
            except Exception as e:
                errors.append(e)

        with tracker:
            threads = [threading.Thread(target=track_assets, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        assert not errors
        assets = tracker.get_assets()
        # Should have all 1000 unique assets (10 threads × 100 files each)
        assert len(assets) == 1000

    def test_nested_trackers_thread_safety(self) -> None:
        """Verify nested trackers work correctly across threads."""
        from bengal.rendering.asset_tracking import AssetTracker, get_current_tracker

        errors: list[Exception] = []

        def use_nested_trackers(thread_id: int) -> None:
            try:
                outer = AssetTracker()
                with outer:
                    outer.track(f"/outer/{thread_id}.css")
                    assert get_current_tracker() is outer

                    inner = AssetTracker()
                    with inner:
                        inner.track(f"/inner/{thread_id}.css")
                        assert get_current_tracker() is inner

                    # Outer should be restored
                    assert get_current_tracker() is outer

                # Should be None outside
                assert get_current_tracker() is None

                # Verify correct tracking
                assert f"/outer/{thread_id}.css" in outer.get_assets()
                assert f"/inner/{thread_id}.css" in inner.get_assets()
                assert f"/inner/{thread_id}.css" not in outer.get_assets()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=use_nested_trackers, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"


class TestRendererCacheThreadSafety:
    """Test Renderer cache initialization under concurrent access."""

    def test_tag_pages_cache_initialization(self) -> None:
        """Verify tag pages cache initializes safely under concurrent access."""
        from unittest.mock import MagicMock

        from bengal.rendering.renderer import Renderer

        # Create mock template engine and site
        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_site.taxonomies = {
            "tags": {
                "python": {"name": "Python", "slug": "python", "pages": []},
                "rust": {"name": "Rust", "slug": "rust", "pages": []},
            }
        }
        mock_site.get_page_path_map.return_value = {}
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)
        errors: list[Exception] = []
        results: list[list] = []
        results_lock = threading.Lock()

        def get_tag_pages() -> None:
            try:
                result = renderer._get_resolved_tag_pages("python")
                with results_lock:
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Spawn many threads that all try to initialize the cache simultaneously
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_tag_pages) for _ in range(50)]
            for _future in as_completed(futures):
                pass

        assert not errors, f"Thread safety errors: {errors}"
        # All results should be the same list object (same cache)
        assert len(results) == 50
        # Cache should be built exactly once
        assert renderer._tag_pages_cache is not None

    def test_top_level_cache_thread_safety(self) -> None:
        """Verify top-level content cache is thread-safe."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_site.sections = []
        mock_site.regular_pages = []
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)
        errors: list[Exception] = []

        def get_top_level() -> None:
            try:
                for _ in range(100):
                    renderer._get_top_level_content()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_top_level) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
