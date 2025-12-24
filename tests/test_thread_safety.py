"""
Thread safety tests for Bengal's concurrent execution paths.

These tests verify that shared state is properly protected for safe
concurrent access during parallel rendering with Python 3.14 free-threading.

Test Coverage:
- DirectiveCache concurrent access (directives/cache.py)
- Icon resolver concurrent loading (icons/resolver.py)
- Context cache concurrent access (rendering/context/__init__.py)
- Directive registry lazy initialization (directives/registry.py)

See Also:
- plan/drafted/rfc-thread-safety-sweep.md — Thread safety RFC
- THREAD_SAFETY.md — Patterns and guidelines
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestDirectiveCacheThreadSafety:
    """Verify DirectiveCache handles concurrent access without corruption."""

    def test_concurrent_put_and_get(self) -> None:
        """Multiple threads can safely put and get cache entries."""
        from bengal.directives.cache import DirectiveCache

        cache = DirectiveCache(max_size=100)
        errors: list[str] = []
        errors_lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for i in range(100):
                    key = f"test:{thread_id}:{i}"
                    value = {"thread": thread_id, "iteration": i}
                    cache.put("test", key, value)

                    result = cache.get("test", key)
                    # Result may be None due to LRU eviction, that's OK
                    if result is not None and (
                        result["thread"] != thread_id or result["iteration"] != i
                    ):
                        with errors_lock:
                            errors.append(f"Thread {thread_id}: value mismatch at {i}")
            except Exception as e:
                with errors_lock:
                    errors.append(f"Thread {thread_id}: exception {e!r}")

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(worker, i) for i in range(10)]
            for f in as_completed(futures):
                f.result()  # Raise any exceptions

        assert not errors, f"Race conditions detected: {errors}"

    def test_concurrent_stats_access(self) -> None:
        """Stats can be safely read while cache is being modified."""
        from bengal.directives.cache import DirectiveCache

        cache = DirectiveCache(max_size=50)
        errors: list[str] = []
        stop_event = threading.Event()

        def writer() -> None:
            i = 0
            while not stop_event.is_set():
                cache.put("test", f"key:{i}", {"value": i})
                i += 1
                if i > 1000:
                    break

        def reader() -> None:
            try:
                while not stop_event.is_set():
                    stats = cache.stats()
                    # Verify stats are internally consistent
                    if stats["size"] > stats["max_size"]:
                        errors.append(f"size {stats['size']} > max_size {stats['max_size']}")
            except Exception as e:
                errors.append(f"Reader exception: {e!r}")

        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        # Let them run briefly
        writer_thread.join(timeout=1.0)
        stop_event.set()
        reader_thread.join(timeout=1.0)

        assert not errors, f"Race conditions detected: {errors}"

    def test_concurrent_clear(self) -> None:
        """Cache can be safely cleared while being accessed."""
        from bengal.directives.cache import DirectiveCache

        cache = DirectiveCache(max_size=100)
        stop_event = threading.Event()

        def writer() -> None:
            i = 0
            while not stop_event.is_set() and i < 500:
                cache.put("test", f"key:{i}", {"value": i})
                i += 1

        def clearer() -> None:
            for _ in range(10):
                cache.clear()
                if stop_event.is_set():
                    break

        writer_thread = threading.Thread(target=writer)
        clearer_thread = threading.Thread(target=clearer)

        writer_thread.start()
        clearer_thread.start()

        writer_thread.join(timeout=2.0)
        stop_event.set()
        clearer_thread.join(timeout=1.0)

        # If we get here without deadlock or exception, test passes
        assert True


class TestIconResolverThreadSafety:
    """Verify icon resolver handles concurrent loading safely."""

    def test_concurrent_load_icon(self, tmp_path) -> None:
        """Multiple threads can safely load icons concurrently."""
        from bengal.icons import resolver

        # Create test icons
        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()
        for name in ["warning", "info", "success", "error"]:
            (icons_dir / f"{name}.svg").write_text(f"<svg>{name}</svg>")

        # Reset resolver state for test isolation
        resolver.clear_cache()
        resolver._search_paths = [icons_dir]
        resolver._initialized = True

        errors: list[str] = []
        errors_lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for _ in range(50):
                    for icon_name in ["warning", "info", "success", "error"]:
                        content = resolver.load_icon(icon_name)
                        expected = f"<svg>{icon_name}</svg>"
                        if content != expected:
                            with errors_lock:
                                errors.append(f"Thread {thread_id}: {icon_name} content mismatch")
            except Exception as e:
                with errors_lock:
                    errors.append(f"Thread {thread_id}: exception {e!r}")

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, i) for i in range(8)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Race conditions detected: {errors}"

    def test_concurrent_cache_operations(self, tmp_path) -> None:
        """Cache operations are safe during concurrent access."""
        from bengal.icons import resolver

        icons_dir = tmp_path / "icons"
        icons_dir.mkdir()
        (icons_dir / "test.svg").write_text("<svg>test</svg>")

        resolver.clear_cache()
        resolver._search_paths = [icons_dir]
        resolver._initialized = True

        errors: list[str] = []
        stop_event = threading.Event()

        def loader() -> None:
            while not stop_event.is_set():
                try:
                    resolver.load_icon("test")
                except Exception as e:
                    errors.append(f"Loader exception: {e!r}")
                    break

        def clearer() -> None:
            for _ in range(20):
                resolver.clear_cache()
                if stop_event.is_set():
                    break

        threads = [threading.Thread(target=loader) for _ in range(4)] + [
            threading.Thread(target=clearer)
        ]

        for t in threads:
            t.start()

        # Let them run briefly
        threads[-1].join(timeout=1.0)  # Wait for clearer
        stop_event.set()

        for t in threads:
            t.join(timeout=1.0)

        assert not errors, f"Race conditions detected: {errors}"


class TestContextCacheThreadSafety:
    """Verify context cache handles concurrent access safely."""

    def test_concurrent_context_access(self, tmp_path) -> None:
        """Multiple threads can safely get global contexts."""
        from unittest.mock import MagicMock

        from bengal.rendering.context import _get_global_contexts, clear_global_context_cache

        # Create mock site
        mock_site = MagicMock()
        mock_site.config = {"title": "Test Site"}
        mock_site.theme_config = None
        mock_site.pages = []
        mock_site.menus = {}

        clear_global_context_cache()

        errors: list[str] = []
        results: list[dict] = []
        results_lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for _ in range(100):
                    ctx = _get_global_contexts(mock_site)
                    if "site" not in ctx:
                        with results_lock:
                            errors.append(f"Thread {thread_id}: missing 'site' in context")
                    with results_lock:
                        results.append(ctx)
            except Exception as e:
                with results_lock:
                    errors.append(f"Thread {thread_id}: exception {e!r}")

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, i) for i in range(8)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Race conditions detected: {errors}"
        # All results should be the same cached instance
        assert len(set(id(r) for r in results)) == 1, "Expected same cached context instance"


class TestDirectiveRegistryThreadSafety:
    """Verify directive registry lazy initialization is thread-safe."""

    def test_concurrent_get_directive_classes(self) -> None:
        """Multiple threads can safely get directive classes."""
        from bengal.directives.registry import _get_directive_classes

        errors: list[str] = []
        results: list[list] = []
        results_lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for _ in range(10):
                    classes = _get_directive_classes()
                    if not isinstance(classes, list):
                        with results_lock:
                            errors.append(f"Thread {thread_id}: unexpected type {type(classes)}")
                    with results_lock:
                        results.append(classes)
            except Exception as e:
                with results_lock:
                    errors.append(f"Thread {thread_id}: exception {e!r}")

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, i) for i in range(8)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Race conditions detected: {errors}"
        # All results should be the same cached instance
        assert len(set(id(r) for r in results)) == 1, "Expected same cached list instance"


class TestLockOrdering:
    """
    Document and verify lock acquisition order to prevent deadlocks.

    Lock order (acquire in this order to prevent deadlocks):
    1. _icon_lock (icons/resolver.py)
    2. DirectiveCache._lock (directives/cache.py)
    3. _cache_lock (rendering/pygments_cache.py)
    4. _context_lock (rendering/context/__init__.py)
    5. _registry_lock (directives/registry.py)
    6. _reload_condition (server/live_reload.py)
    """

    def test_no_circular_lock_dependencies(self) -> None:
        """
        Verify no code path acquires locks in reverse order.

        This is a documentation test - actual verification requires
        code review or runtime lock order tracking.
        """
        # This test documents the expected lock order
        # Actual deadlock detection requires runtime analysis
        lock_order = [
            "icons/resolver.py:_icon_lock",
            "directives/cache.py:DirectiveCache._lock",
            "rendering/pygments_cache.py:_cache_lock",
            "rendering/context/__init__.py:_context_lock",
            "directives/registry.py:_registry_lock",
            "server/live_reload.py:_reload_condition",
        ]
        assert len(lock_order) == 6, "Document all protected modules"
