"""
Thread-safety stress tests for free-threading (PEP 703).

These tests verify that Bengal's critical subsystems are thread-safe
when running with PYTHON_GIL=0 (free-threaded Python 3.14+).

RFC: rfc-free-threading-hardening.md

Run with:
    pytest tests/test_thread_safety.py -v -x

Run with GIL disabled (requires Python 3.14t):
    PYTHON_GIL=0 pytest tests/test_thread_safety.py -v -x
"""

from __future__ import annotations

import threading
from typing import Any


class TestLRUCacheThreadSafety:
    """Verify LRUCache replacements are thread-safe."""

    def test_param_info_cache_concurrent_access(self) -> None:
        """Test autodoc param_info cache under concurrent access."""
        from bengal.autodoc.base import _cached_param_info, _param_info_cache

        errors: list[Exception] = []
        results: list[Any] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for i in range(100):
                    # Each thread creates param infos with overlapping names
                    result = _cached_param_info(
                        name=f"param_{i % 10}",
                        type_hint=f"str | int" if i % 2 == 0 else None,
                        default=f"default_{i % 5}" if i % 3 == 0 else None,
                        description=f"Description for param {i}",
                    )
                    with lock:
                        results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        assert len(results) == 1000  # 10 threads * 100 iterations

        # Verify cache is working (should have hits)
        stats = _param_info_cache.stats()
        assert stats["hits"] > 0, "Cache should have hits from repeated calls"

    def test_icon_render_cache_concurrent_access(self) -> None:
        """Test icon render cache under concurrent access."""
        from bengal.rendering.template_functions.icons import (
            _icon_render_cache,
            _render_icon_cached,
            clear_icon_cache,
        )

        # Clear cache before test
        clear_icon_cache()

        errors: list[Exception] = []
        results: list[str] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    # Each thread renders icons with overlapping names
                    result = _render_icon_cached(
                        name=f"icon_{i % 5}",
                        size=20 + (i % 3),
                        css_class=f"class_{i % 2}",
                        aria_label="",
                    )
                    with lock:
                        results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        assert len(results) == 500  # 10 threads * 50 iterations

    def test_directive_icon_cache_concurrent_access(self) -> None:
        """Test directive icon cache under concurrent access."""
        from bengal.icons.svg import _svg_icon_cache, clear_icon_cache, render_svg_icon

        # Clear cache before test
        clear_icon_cache()

        errors: list[Exception] = []
        results: list[str] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    result = render_svg_icon(
                        name=f"icon_{i % 5}",
                        size=16 + (i % 3),
                        css_class="",
                        aria_label="",
                    )
                    with lock:
                        results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        assert len(results) == 500

    def test_theme_cache_concurrent_access(self) -> None:
        """Test theme discovery cache under concurrent access."""
        from bengal.core.theme.registry import _installed_themes_cache, get_installed_themes

        errors: list[Exception] = []
        results: list[dict] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for _ in range(20):
                    result = get_installed_themes()
                    with lock:
                        results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        assert len(results) == 200

        # All results should be the same dict (singleton pattern)
        if results:
            first_id = id(results[0])
            assert all(id(r) == first_id for r in results), "All results should be same instance"


class TestScaffoldRegistryThreadSafety:
    """Verify scaffold registry singleton is thread-safe."""

    def test_singleton_initialization_race(self) -> None:
        """Verify scaffold registry singleton handles concurrent initialization."""
        from bengal.scaffolds import registry

        # Reset to test initialization race
        registry._registry = None

        instances: list[int] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker() -> None:
            try:
                instance = registry._get_registry()
                with lock:
                    instances.append(id(instance))
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
        # All threads should get the same singleton instance
        assert len(set(instances)) == 1, f"Multiple instances created: {set(instances)}"

    def test_concurrent_template_access(self) -> None:
        """Verify concurrent template lookups work correctly."""
        from bengal.scaffolds import registry

        errors: list[Exception] = []
        results: list[Any] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for _ in range(20):
                    # Attempt various operations
                    templates = registry.list_templates()
                    for tid, _ in templates[:3]:  # Limit to first 3
                        template = registry.get_template(tid)
                        with lock:
                            results.append(template)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"


class TestLoggerRegistryThreadSafety:
    """Verify logger registry handles concurrent get_logger calls."""

    def test_get_logger_concurrent_access(self) -> None:
        """Test concurrent get_logger calls with overlapping names."""
        from bengal.utils.observability.logger import get_logger, reset_loggers

        reset_loggers()
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    # Each thread creates loggers with overlapping names
                    logger = get_logger(f"test.module.{i % 10}")
                    logger.debug("test", thread_id=thread_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"

    def test_reset_during_concurrent_access(self) -> None:
        """Test reset_loggers while other threads are accessing loggers."""
        from bengal.utils.observability.logger import get_logger, reset_loggers

        reset_loggers()
        errors: list[Exception] = []
        stop_flag = threading.Event()

        def worker(thread_id: int) -> None:
            try:
                while not stop_flag.is_set():
                    logger = get_logger(f"test.reset.{thread_id}")
                    logger.debug("test", thread_id=thread_id)
            except Exception as e:
                errors.append(e)

        def resetter() -> None:
            try:
                for _ in range(5):
                    reset_loggers()
            except Exception as e:
                errors.append(e)

        workers = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        reset_thread = threading.Thread(target=resetter)

        for w in workers:
            w.start()
        reset_thread.start()

        reset_thread.join(timeout=10)
        stop_flag.set()

        for w in workers:
            w.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"


class TestThreadSafeSetUsage:
    """Verify ThreadSafeSet usage in asset fallback warnings."""

    def test_fallback_warned_concurrent_access(self) -> None:
        """Test concurrent access to _fallback_warned set."""
        from bengal.rendering.assets import _fallback_warned

        _fallback_warned.clear()
        added_paths: list[tuple[str, bool]] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    path = f"assets/test_{i % 10}.css"
                    was_new = _fallback_warned.add_if_new(path)
                    with lock:
                        added_paths.append((path, was_new))
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"

        # Each unique path should only be "new" once across all threads
        unique_paths = set(path for path, _ in added_paths)
        new_counts = {}
        for path, was_new in added_paths:
            if was_new:
                new_counts[path] = new_counts.get(path, 0) + 1

        # Each path should have been new exactly once
        for path, count in new_counts.items():
            assert count == 1, f"Path {path} was marked new {count} times (should be 1)"


class TestDirectiveCacheConfiguration:
    """Verify directive cache configuration is thread-safe."""

    def test_configure_cache_concurrent(self) -> None:
        """Test concurrent cache configuration changes."""
        from bengal.cache.directive_cache import configure_cache, get_cache

        errors: list[Exception] = []

        def config_worker(enabled: bool) -> None:
            try:
                for _ in range(20):
                    configure_cache(enabled=enabled)
            except Exception as e:
                errors.append(e)

        def use_worker() -> None:
            try:
                cache = get_cache()
                for _ in range(50):
                    cache.get("test", "content")
                    cache.put("test", "content", {"parsed": True})
            except Exception as e:
                errors.append(e)

        config_threads = [
            threading.Thread(target=config_worker, args=(True,)),
            threading.Thread(target=config_worker, args=(False,)),
        ]
        use_threads = [threading.Thread(target=use_worker) for _ in range(5)]

        all_threads = config_threads + use_threads
        for t in all_threads:
            t.start()
        for t in all_threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety errors: {errors}"
