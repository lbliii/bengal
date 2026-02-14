"""
Tests for bengal.utils.thread_local module.

Verifies thread-local caching utilities for expensive objects.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from bengal.utils.concurrency.thread_local import ThreadLocalCache, ThreadSafeSet


class TestThreadLocalCache:
    """Tests for ThreadLocalCache class."""

    def test_basic_caching(self) -> None:
        """Test basic get/cache behavior."""
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        cache: ThreadLocalCache[str] = ThreadLocalCache(factory, name="test")

        # First call creates instance
        result1 = cache.get()
        assert result1 == "instance_1"
        assert call_count == 1

        # Second call returns cached instance
        result2 = cache.get()
        assert result2 == "instance_1"
        assert call_count == 1  # No new call

    def test_keyed_caching(self) -> None:
        """Test caching with different keys."""
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        cache: ThreadLocalCache[str] = ThreadLocalCache(factory, name="test")

        # Different keys get different instances
        result1 = cache.get("key1")
        result2 = cache.get("key2")
        result3 = cache.get("key1")  # Same as first

        assert result1 == "instance_1"
        assert result2 == "instance_2"
        assert result3 == "instance_1"  # Cached
        assert call_count == 2

    def test_factory_with_key(self) -> None:
        """Test factory that accepts key argument."""

        def factory(key: str) -> str:
            return f"created_for_{key}"

        cache: ThreadLocalCache[str] = ThreadLocalCache(factory, name="test")

        result = cache.get("mykey")
        assert result == "created_for_mykey"

    def test_thread_isolation(self) -> None:
        """Test that each thread gets its own instance."""
        creation_count = 0
        creation_lock = threading.Lock()
        results: list[tuple[str, str]] = []
        results_lock = threading.Lock()

        def factory() -> str:
            nonlocal creation_count
            with creation_lock:
                creation_count += 1
                count = creation_count
            return f"instance_{count}"

        # Use unique name to avoid cache pollution from other tests
        cache: ThreadLocalCache[str] = ThreadLocalCache(factory, name="test_isolation")

        def worker(thread_name: str) -> None:
            # Get instance twice to verify caching within thread
            instance1 = cache.get()
            instance2 = cache.get()
            with results_lock:
                results.append((thread_name, instance1))
            # Both calls should return same instance
            assert instance1 == instance2

        # Run in multiple threads
        threads = [threading.Thread(target=worker, args=(f"t{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Each thread should create exactly one instance
        assert creation_count == 5
        assert len(results) == 5
        # Each thread should have a different instance
        instance_names = [r[1] for r in results]
        assert len(set(instance_names)) == 5

    def test_clear_specific_key(self) -> None:
        """Test clearing specific key."""
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        cache: ThreadLocalCache[str] = ThreadLocalCache(factory, name="test")

        cache.get("key1")
        cache.get("key2")
        assert call_count == 2

        # Clear key1
        cache.clear("key1")

        # key1 should recreate, key2 should be cached
        cache.get("key1")
        cache.get("key2")
        assert call_count == 3

    def test_clear_all(self) -> None:
        """Test clearing all cached instances."""
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        cache: ThreadLocalCache[str] = ThreadLocalCache(factory, name="test")

        cache.get("key1")
        cache.get("key2")
        assert call_count == 2

        # Clear all
        cache.clear_all()

        # Both should recreate
        cache.get("key1")
        cache.get("key2")
        assert call_count == 4

    def test_multiple_caches_independent(self) -> None:
        """Test that multiple caches with different names are independent."""

        def factory1() -> str:
            return "cache1_instance"

        def factory2() -> str:
            return "cache2_instance"

        cache1: ThreadLocalCache[str] = ThreadLocalCache(factory1, name="cache1")
        cache2: ThreadLocalCache[str] = ThreadLocalCache(factory2, name="cache2")

        result1 = cache1.get()
        result2 = cache2.get()

        assert result1 == "cache1_instance"
        assert result2 == "cache2_instance"


class TestThreadSafeSet:
    """Tests for ThreadSafeSet class."""

    def test_add_if_new_returns_true_for_new(self) -> None:
        """Test add_if_new returns True for new items."""
        s = ThreadSafeSet()
        assert s.add_if_new("item1") is True

    def test_add_if_new_returns_false_for_existing(self) -> None:
        """Test add_if_new returns False for existing items."""
        s = ThreadSafeSet()
        s.add_if_new("item1")
        assert s.add_if_new("item1") is False

    def test_contains(self) -> None:
        """Test __contains__ check."""
        s = ThreadSafeSet()
        assert "item1" not in s
        s.add_if_new("item1")
        assert "item1" in s

    def test_clear(self) -> None:
        """Test clearing the set."""
        s = ThreadSafeSet()
        s.add_if_new("item1")
        s.add_if_new("item2")

        s.clear()

        assert "item1" not in s
        assert "item2" not in s

    def test_len(self) -> None:
        """Test __len__."""
        s = ThreadSafeSet()
        assert len(s) == 0

        s.add_if_new("item1")
        assert len(s) == 1

        s.add_if_new("item2")
        assert len(s) == 2

        s.add_if_new("item1")  # Duplicate
        assert len(s) == 2

    def test_thread_safety(self) -> None:
        """Test thread safety under concurrent access."""
        s = ThreadSafeSet()
        add_results: list[bool] = []
        lock = threading.Lock()

        def worker(item: str) -> None:
            result = s.add_if_new(item)
            with lock:
                add_results.append(result)

        # Multiple threads trying to add same items
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Each item submitted 5 times across threads
            for i in range(10):
                for _j in range(5):
                    executor.submit(worker, f"item_{i}")

        # Should have exactly 10 True results (one per unique item)
        assert sum(add_results) == 10
        assert len(s) == 10

    def test_atomic_check_and_add(self) -> None:
        """Test that add_if_new is atomic (no race conditions)."""
        s = ThreadSafeSet()
        success_count = 0
        lock = threading.Lock()

        def worker() -> None:
            nonlocal success_count
            if s.add_if_new("shared_item"):
                with lock:
                    success_count += 1

        # Many threads trying to add same item
        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Exactly one thread should succeed
        assert success_count == 1
        assert len(s) == 1


class TestThreadLocalCacheWithExpensiveObjects:
    """Integration tests simulating real-world usage."""

    def test_parser_cache_pattern(self) -> None:
        """Test pattern similar to parser caching in rendering pipeline."""
        parser_creation_count = 0

        class FakeParser:
            def __init__(self, engine: str) -> None:
                self.engine = engine
                nonlocal parser_creation_count
                parser_creation_count += 1

            def parse(self, content: str) -> str:
                return f"parsed by {self.engine}: {content}"

        def create_parser(engine: str = "default") -> FakeParser:
            return FakeParser(engine)

        parser_cache: ThreadLocalCache[FakeParser] = ThreadLocalCache(create_parser, name="parser")

        # Simulate parsing multiple documents
        parser = parser_cache.get("mistune")
        result1 = parser.parse("doc1")

        parser = parser_cache.get("mistune")  # Should reuse
        result2 = parser.parse("doc2")

        assert "mistune" in result1
        assert "mistune" in result2
        assert parser_creation_count == 1  # Only one parser created

    def test_parallel_rendering_simulation(self) -> None:
        """Test pattern similar to parallel page rendering."""
        creation_counts: dict[int, int] = {}
        lock = threading.Lock()

        def factory() -> dict[str, Any]:
            thread_id = threading.current_thread().ident
            with lock:
                creation_counts[thread_id] = creation_counts.get(thread_id, 0) + 1  # type: ignore[index]
            return {"thread_id": thread_id}

        cache: ThreadLocalCache[dict[str, Any]] = ThreadLocalCache(factory, name="ctx")

        def render_page(page_id: int) -> tuple[int, dict[str, Any]]:
            # Each render gets context from cache
            ctx = cache.get()
            # Simulate some work
            time.sleep(0.001)
            return page_id, ctx

        # Simulate rendering 20 pages across 4 threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(render_page, range(20)))

        # Should have results for all pages
        assert len(results) == 20

        # Each thread should have created exactly one context
        assert all(count == 1 for count in creation_counts.values())

        # Should have at most 4 unique contexts (one per worker)
        unique_thread_ids = {r[1]["thread_id"] for r in results}
        assert len(unique_thread_ids) <= 4
