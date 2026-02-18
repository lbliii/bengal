"""
Unit tests for PerKeyLockManager.

Tests thread safety, lock creation, and cleanup behavior for the per-key
lock pattern used to prevent duplicate work in parallel builds.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from bengal.utils.concurrency.concurrent_locks import PerKeyLockManager

pytestmark = pytest.mark.parallel_unsafe


class TestPerKeyLockManager:
    """Tests for PerKeyLockManager class."""

    def test_get_lock_creates_new_lock(self) -> None:
        """get_lock should create a new lock for a new key."""
        manager = PerKeyLockManager()
        lock = manager.get_lock("key1")

        assert lock is not None
        assert isinstance(lock, type(threading.RLock()))
        assert len(manager) == 1

    def test_get_lock_returns_same_lock_for_same_key(self) -> None:
        """get_lock should return the same lock for the same key."""
        manager = PerKeyLockManager()
        lock1 = manager.get_lock("key1")
        lock2 = manager.get_lock("key1")

        assert lock1 is lock2
        assert len(manager) == 1

    def test_get_lock_returns_different_locks_for_different_keys(self) -> None:
        """get_lock should return different locks for different keys."""
        manager = PerKeyLockManager()
        lock1 = manager.get_lock("key1")
        lock2 = manager.get_lock("key2")

        assert lock1 is not lock2
        assert len(manager) == 2

    def test_get_lock_supports_hashable_keys(self) -> None:
        """get_lock should support various hashable key types."""
        manager = PerKeyLockManager()

        # String key
        lock_str = manager.get_lock("string_key")
        assert lock_str is not None

        # Tuple key (like NavScaffoldCache uses)
        lock_tuple = manager.get_lock(("version", "/docs/"))
        assert lock_tuple is not None

        # Integer key
        lock_int = manager.get_lock(42)
        assert lock_int is not None

        # None as key (edge case)
        lock_none = manager.get_lock(None)
        assert lock_none is not None

        assert len(manager) == 4

    def test_clear_removes_all_locks(self) -> None:
        """clear should remove all locks."""
        manager = PerKeyLockManager()
        manager.get_lock("key1")
        manager.get_lock("key2")
        manager.get_lock("key3")

        assert len(manager) == 3

        manager.clear()

        assert len(manager) == 0

    def test_clear_allows_new_locks_after(self) -> None:
        """After clear, new locks can be created."""
        manager = PerKeyLockManager()
        lock_before = manager.get_lock("key1")
        manager.clear()
        lock_after = manager.get_lock("key1")

        # New lock should be created (not the same object)
        assert lock_before is not lock_after
        assert len(manager) == 1

    def test_len_returns_lock_count(self) -> None:
        """__len__ should return the number of locks."""
        manager = PerKeyLockManager()

        assert len(manager) == 0

        manager.get_lock("key1")
        assert len(manager) == 1

        manager.get_lock("key2")
        assert len(manager) == 2

        manager.get_lock("key1")  # Same key
        assert len(manager) == 2  # Still 2

    def test_repr(self) -> None:
        """__repr__ should show lock count."""
        manager = PerKeyLockManager()
        assert repr(manager) == "PerKeyLockManager(locks=0)"

        manager.get_lock("key1")
        manager.get_lock("key2")
        assert repr(manager) == "PerKeyLockManager(locks=2)"

    def test_rlock_allows_nested_acquisition(self) -> None:
        """RLock should allow nested acquisition in same thread."""
        manager = PerKeyLockManager()
        lock = manager.get_lock("key1")

        # Should not deadlock
        with lock, lock:
            pass  # Nested acquisition should work

    def test_thread_safety_concurrent_get_lock(self) -> None:
        """Multiple threads getting same lock should get the same lock object."""
        manager = PerKeyLockManager()
        locks_obtained: list[threading.RLock] = []
        lock_for_results = threading.Lock()

        def get_lock() -> None:
            lock = manager.get_lock("shared_key")
            with lock_for_results:
                locks_obtained.append(lock)

        # 10 threads all request the same key
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_lock) for _ in range(10)]
            for f in futures:
                f.result()

        # All threads should have gotten the same lock
        assert len(locks_obtained) == 10
        first_lock = locks_obtained[0]
        assert all(lock is first_lock for lock in locks_obtained)
        assert len(manager) == 1

    def test_per_key_lock_prevents_duplicate_work(self) -> None:
        """Multiple threads requesting same key should serialize work."""
        manager = PerKeyLockManager()
        build_count = 0
        results: dict[str, str] = {}
        results_lock = threading.Lock()

        def build_if_missing(key: str) -> str:
            nonlocal build_count

            with manager.get_lock(key):
                # Check cache
                with results_lock:
                    if key in results:
                        return results[key]

                # Simulate expensive build
                build_count += 1
                time.sleep(0.01)  # 10ms work

                # Store result
                result = f"built-{key}-{build_count}"
                with results_lock:
                    results[key] = result
                return result

        # 10 threads all request the same key
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(build_if_missing, "same-key") for _ in range(10)]
            outcomes = [f.result() for f in futures]

        # Only one build should have occurred
        assert build_count == 1
        # All threads should get the same result
        assert all(r == "built-same-key-1" for r in outcomes)

    def test_different_keys_run_in_parallel(self) -> None:
        """Different keys should not block each other."""
        manager = PerKeyLockManager()
        execution_times: dict[str, float] = {}
        lock_for_times = threading.Lock()

        def work(key: str) -> None:
            start = time.time()
            with manager.get_lock(key):
                time.sleep(0.02)  # 20ms work
            end = time.time()
            with lock_for_times:
                execution_times[key] = end - start

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 4 different keys should run in parallel
            futures = [executor.submit(work, f"key-{i}") for i in range(4)]
            for f in futures:
                f.result()
        total_time = time.time() - start_time

        # If serialized, would take ~80ms (4 × 20ms)
        # If parallel, should take ~20-30ms (just one work unit + overhead)
        # Allow some tolerance for thread scheduling
        assert total_time < 0.06, f"Expected parallel execution but took {total_time:.3f}s"

    def test_same_key_serializes(self) -> None:
        """Same key should serialize, taking longer."""
        manager = PerKeyLockManager()
        work_per_key = 0.01  # 10ms per work unit

        def work(key: str) -> None:
            with manager.get_lock(key):
                time.sleep(work_per_key)

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 4 threads all with SAME key should serialize
            futures = [executor.submit(work, "same-key") for _ in range(4)]
            for f in futures:
                f.result()
        total_time = time.time() - start_time

        # Should take ~40ms (4 × 10ms serialized) plus overhead
        # Definitely more than 30ms if properly serialized
        assert total_time >= 0.03, f"Expected serialization but took only {total_time:.3f}s"


class TestPerKeyLockManagerEdgeCases:
    """Edge case tests for PerKeyLockManager."""

    def test_empty_string_key(self) -> None:
        """Empty string is a valid key."""
        manager = PerKeyLockManager()
        lock = manager.get_lock("")
        assert lock is not None
        assert len(manager) == 1

    def test_frozen_set_key(self) -> None:
        """Frozen set is hashable and can be used as key."""
        manager = PerKeyLockManager()
        key = frozenset(["a", "b", "c"])
        lock = manager.get_lock(key)
        assert lock is not None
        assert manager.get_lock(key) is lock

    def test_many_keys_memory_usage(self) -> None:
        """Creating many locks should be memory-efficient."""
        manager = PerKeyLockManager()

        # Create 1000 locks
        for i in range(1000):
            manager.get_lock(f"key-{i}")

        assert len(manager) == 1000

        # Clear should release all
        manager.clear()
        assert len(manager) == 0

    def test_concurrent_clear_and_get(self) -> None:
        """clear() during get_lock() should not cause errors."""
        manager = PerKeyLockManager()
        errors: list[Exception] = []

        def get_locks() -> None:
            try:
                for i in range(100):
                    manager.get_lock(f"key-{i}")
            except Exception as e:
                errors.append(e)

        def clear_locks() -> None:
            try:
                for _ in range(10):
                    time.sleep(0.001)
                    manager.clear()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(get_locks),
                executor.submit(get_locks),
                executor.submit(clear_locks),
            ]
            for f in futures:
                f.result()

        # No errors should have occurred
        assert len(errors) == 0, f"Got errors: {errors}"
