"""
Tests for file locking utilities.

Tests concurrent access safety for the build cache.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from bengal.utils.file_lock import (
    LockAcquisitionError,
    file_lock,
    is_locked,
    remove_stale_lock,
)


class TestFileLock:
    """Tests for the file_lock context manager."""

    def test_basic_lock_acquire_release(self, tmp_path: Path) -> None:
        """Test basic lock acquisition and release."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        # Lock should acquire and release cleanly
        with file_lock(test_file, exclusive=True):
            assert True  # Lock acquired

        # Lock file should exist but be unlocked
        lock_file = test_file.with_suffix(".json.lock")
        assert lock_file.exists()

    def test_shared_lock_allows_concurrent_reads(self, tmp_path: Path) -> None:
        """Test that multiple shared locks can be acquired simultaneously."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        acquired_locks = []
        errors = []

        def acquire_shared():
            try:
                with file_lock(test_file, exclusive=False, timeout=5):
                    acquired_locks.append(True)
                    time.sleep(0.2)  # Hold lock briefly
            except Exception as e:
                errors.append(e)

        # Start multiple threads with shared locks
        threads = [threading.Thread(target=acquire_shared) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should acquire successfully
        assert len(acquired_locks) == 3
        assert len(errors) == 0

    def test_exclusive_lock_blocks_others(self, tmp_path: Path) -> None:
        """Test that exclusive lock blocks other exclusive locks."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        results = []
        errors = []
        lock_order = []

        def acquire_exclusive(thread_id: int, delay: float = 0):
            try:
                time.sleep(delay)  # Stagger starts
                with file_lock(test_file, exclusive=True, timeout=5):
                    lock_order.append(thread_id)
                    results.append(thread_id)
                    time.sleep(0.3)  # Hold lock
            except Exception as e:
                errors.append((thread_id, e))

        # Start threads at slightly different times
        t1 = threading.Thread(target=acquire_exclusive, args=(1, 0))
        t2 = threading.Thread(target=acquire_exclusive, args=(2, 0.1))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both should eventually acquire
        assert len(results) == 2
        assert len(errors) == 0
        # First should be 1 (started earlier)
        assert lock_order[0] == 1

    def test_lock_timeout(self, tmp_path: Path) -> None:
        """Test that lock acquisition times out correctly."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        lock_held = threading.Event()
        can_release = threading.Event()

        def hold_lock():
            with file_lock(test_file, exclusive=True):
                lock_held.set()
                can_release.wait(timeout=10)

        # Start a thread that holds the lock
        holder = threading.Thread(target=hold_lock)
        holder.start()

        # Wait for lock to be acquired
        lock_held.wait(timeout=5)

        # Try to acquire with short timeout - should fail
        with (
            pytest.raises(LockAcquisitionError) as exc_info,
            file_lock(test_file, exclusive=True, timeout=0.5),
        ):
            pass

        assert "Could not acquire lock" in str(exc_info.value)

        # Release the holder
        can_release.set()
        holder.join()

    def test_lock_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that lock file parent directory is created if needed."""
        test_file = tmp_path / "subdir" / "nested" / "test.json"

        # Directory shouldn't exist yet
        assert not test_file.parent.exists()

        with file_lock(test_file, exclusive=True):
            # Lock file parent should now exist
            lock_file = test_file.with_suffix(".json.lock")
            assert lock_file.parent.exists()


class TestIsLocked:
    """Tests for the is_locked function."""

    def test_returns_false_for_unlocked_file(self, tmp_path: Path) -> None:
        """Test that is_locked returns False for unlocked file."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        assert is_locked(test_file) is False

    def test_returns_true_for_locked_file(self, tmp_path: Path) -> None:
        """Test that is_locked returns True for locked file."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        lock_acquired = threading.Event()
        can_release = threading.Event()

        def hold_lock():
            with file_lock(test_file, exclusive=True):
                lock_acquired.set()
                can_release.wait(timeout=10)

        holder = threading.Thread(target=hold_lock)
        holder.start()
        lock_acquired.wait(timeout=5)

        try:
            assert is_locked(test_file) is True
        finally:
            can_release.set()
            holder.join()

    def test_returns_false_for_nonexistent_lock(self, tmp_path: Path) -> None:
        """Test that is_locked returns False when lock file doesn't exist."""
        test_file = tmp_path / "nonexistent.json"
        assert is_locked(test_file) is False


class TestRemoveStaleLock:
    """Tests for the remove_stale_lock function."""

    def test_removes_old_lock_file(self, tmp_path: Path) -> None:
        """Test that stale lock file is removed."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")
        lock_file = test_file.with_suffix(".json.lock")

        # Create an old lock file
        lock_file.write_text("")
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(lock_file, (old_time, old_time))

        result = remove_stale_lock(test_file, max_age_seconds=3600)

        assert result is True
        assert not lock_file.exists()

    def test_keeps_fresh_lock_file(self, tmp_path: Path) -> None:
        """Test that fresh lock file is not removed."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")
        lock_file = test_file.with_suffix(".json.lock")

        # Create a fresh lock file
        lock_file.write_text("")

        result = remove_stale_lock(test_file, max_age_seconds=3600)

        assert result is False
        assert lock_file.exists()

    def test_returns_false_for_no_lock(self, tmp_path: Path) -> None:
        """Test that function returns False when no lock file exists."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        result = remove_stale_lock(test_file)

        assert result is False


class TestBuildCacheWithLocking:
    """Integration tests for BuildCache with file locking."""

    def test_cache_save_with_lock(self, tmp_path: Path) -> None:
        """Test that cache save acquires exclusive lock."""
        from bengal.cache.build_cache import BuildCache

        cache = BuildCache()
        cache.file_hashes["test.md"] = "abc123"

        cache_path = tmp_path / ".bengal" / "cache.json"
        cache.save(cache_path, use_lock=True)

        # Verify cache was saved
        assert cache_path.exists()

        # Verify lock file was created
        lock_file = cache_path.with_suffix(".json.lock")
        assert lock_file.exists()

    def test_cache_load_with_lock(self, tmp_path: Path) -> None:
        """Test that cache load acquires shared lock."""
        from bengal.cache.build_cache import BuildCache

        cache_path = tmp_path / ".bengal" / "cache.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Save initial cache
        cache = BuildCache()
        cache.file_hashes["test.md"] = "abc123"
        cache.save(cache_path, use_lock=True)

        # Load with lock
        loaded = BuildCache.load(cache_path, use_lock=True)

        assert loaded.file_hashes.get("test.md") == "abc123"

    def test_concurrent_cache_writes(self, tmp_path: Path) -> None:
        """Test that concurrent cache writes don't corrupt data."""
        from bengal.cache.build_cache import BuildCache

        cache_path = tmp_path / ".bengal" / "cache.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        results = []
        errors = []

        def write_cache(writer_id: int):
            try:
                cache = BuildCache()
                # Each writer adds a unique file
                cache.file_hashes[f"file_{writer_id}.md"] = f"hash_{writer_id}"
                cache.save(cache_path, use_lock=True)
                results.append(writer_id)
            except Exception as e:
                errors.append((writer_id, e))

        # Start multiple concurrent writers
        threads = [threading.Thread(target=write_cache, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should complete without errors
        assert len(errors) == 0
        assert len(results) == 5

        # Final cache should be valid JSON
        loaded = BuildCache.load(cache_path, use_lock=True)
        assert loaded is not None
        # Last writer's data should be present
        assert any(f"file_{i}.md" in loaded.file_hashes for i in range(5)), (
            "At least one write should persist"
        )

    def test_cache_lock_prevents_corruption_during_read(self, tmp_path: Path) -> None:
        """Test that reads during writes get consistent data."""
        from bengal.cache.build_cache import BuildCache

        cache_path = tmp_path / ".bengal" / "cache.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Create initial cache
        initial_cache = BuildCache()
        initial_cache.file_hashes["initial.md"] = "initial_hash"
        initial_cache.save(cache_path, use_lock=True)

        write_started = threading.Event()
        read_results = []
        errors = []

        def slow_write():
            """Simulates a slow write operation."""
            cache = BuildCache()
            cache.file_hashes["new.md"] = "new_hash"
            write_started.set()
            cache.save(cache_path, use_lock=True)

        def read_during_write():
            """Tries to read during the write."""
            write_started.wait(timeout=5)
            time.sleep(0.01)  # Small delay to let write lock be acquired
            try:
                loaded = BuildCache.load(cache_path, use_lock=True)
                read_results.append(loaded)
            except Exception as e:
                errors.append(e)

        writer = threading.Thread(target=slow_write)
        reader = threading.Thread(target=read_during_write)

        writer.start()
        reader.start()
        writer.join()
        reader.join()

        # Read should complete without errors
        assert len(errors) == 0
        assert len(read_results) == 1

        # Result should be valid (either old or new, not corrupted)
        result = read_results[0]
        assert isinstance(result, BuildCache)
