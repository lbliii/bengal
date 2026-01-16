"""Tests for bengal.utils.lru_cache.LRUCache."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from bengal.utils.primitives.lru_cache import LRUCache


class TestLRUEviction:
    """Test LRU eviction behavior (not FIFO)."""

    def test_evicts_lru_not_fifo(self) -> None:
        """Verify true LRU behavior - accessed items stay longer."""
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # Access "a" to make it recently used
        cache.get("a")

        # Add "d" - should evict "b" (LRU), not "a" (would be FIFO)
        cache.set("d", 4)

        assert "a" in cache  # Recently accessed, kept
        assert "b" not in cache  # Least recently used, evicted
        assert "c" in cache
        assert "d" in cache

    def test_evicts_oldest_on_capacity(self) -> None:
        """Items are evicted when capacity is reached."""
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Evicts "a"

        assert "a" not in cache
        assert cache.get("b") == 2

    def test_update_moves_to_end(self) -> None:
        """Updating existing key makes it most recently used."""
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # Update "a" - should move to end
        cache.set("a", 10)

        # Add "d" - should evict "b", not "a"
        cache.set("d", 4)

        assert "a" in cache  # Updated, moved to end
        assert cache.get("a") == 10
        assert "b" not in cache  # Now LRU

    def test_unlimited_size(self) -> None:
        """maxsize=0 means unlimited."""
        cache: LRUCache[int, int] = LRUCache(maxsize=0)
        for i in range(1000):
            cache.set(i, i)
        assert len(cache) == 1000


class TestTTL:
    """Test TTL expiration behavior."""

    def test_expires_after_ttl(self) -> None:
        """Items expire after TTL."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10, ttl=0.1)
        cache.set("key", 42)
        assert cache.get("key") == 42

        time.sleep(0.15)
        assert cache.get("key") is None

    def test_contains_respects_ttl(self) -> None:
        """__contains__ respects TTL expiration."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10, ttl=0.1)
        cache.set("key", 42)
        assert "key" in cache

        time.sleep(0.15)
        assert "key" not in cache

    def test_get_or_set_respects_ttl(self) -> None:
        """get_or_set recomputes after TTL expiry."""
        call_count = 0

        def factory() -> int:
            nonlocal call_count
            call_count += 1
            return call_count * 10

        cache: LRUCache[str, int] = LRUCache(maxsize=10, ttl=0.1)

        result1 = cache.get_or_set("key", factory)
        assert result1 == 10
        assert call_count == 1

        # Should return cached value
        result2 = cache.get_or_set("key", factory)
        assert result2 == 10
        assert call_count == 1

        # Wait for expiry
        time.sleep(0.15)

        # Should recompute
        result3 = cache.get_or_set("key", factory)
        assert result3 == 20
        assert call_count == 2

    def test_no_ttl_never_expires(self) -> None:
        """Without TTL, items never expire."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("key", 42)

        time.sleep(0.05)
        assert cache.get("key") == 42
        assert "key" in cache


class TestGetOrSet:
    """Test get_or_set pattern."""

    def test_returns_cached_value(self) -> None:
        """get_or_set returns cached value without calling factory."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("key", 42)

        call_count = 0

        def factory() -> int:
            nonlocal call_count
            call_count += 1
            return 100

        result = cache.get_or_set("key", factory)
        assert result == 42
        assert call_count == 0  # Factory not called

    def test_computes_on_miss(self) -> None:
        """get_or_set computes and caches on miss."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)

        result = cache.get_or_set("key", lambda: 42)
        assert result == 42
        assert cache.get("key") == 42

    def test_passes_key_to_factory(self) -> None:
        """get_or_set passes key when pass_key=True."""
        cache: LRUCache[str, str] = LRUCache(maxsize=10)

        result = cache.get_or_set("hello", lambda k: k.upper(), pass_key=True)
        assert result == "HELLO"

    def test_factory_exception_not_cached(self) -> None:
        """If factory raises, nothing is cached."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)

        def bad_factory() -> int:
            raise ValueError("oops")

        with pytest.raises(ValueError, match="oops"):
            cache.get_or_set("key", bad_factory)

        assert "key" not in cache


class TestStats:
    """Test statistics tracking."""

    def test_tracks_hits_and_misses(self) -> None:
        """Stats track hits and misses correctly."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        cache.get("a")  # hit

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(2 / 3)

    def test_reset_stats(self) -> None:
        """reset_stats clears counters but not cache."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.get("a")
        cache.get("b")

        cache.reset_stats()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 1  # Cache not cleared

    def test_stats_includes_metadata(self) -> None:
        """Stats include all metadata."""
        cache: LRUCache[str, int] = LRUCache(maxsize=100, ttl=60, name="test_cache")
        cache.set("a", 1)

        stats = cache.stats()
        assert stats["max_size"] == 100
        assert stats["ttl"] == 60
        assert stats["name"] == "test_cache"
        assert stats["enabled"] is True
        assert stats["size"] == 1

    def test_hit_rate_zero_when_empty(self) -> None:
        """Hit rate is 0 when no accesses."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        assert cache.stats()["hit_rate"] == 0.0


class TestEnableDisable:
    """Test enable/disable functionality."""

    def test_disable_returns_none(self) -> None:
        """Disabled cache returns None on get."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("key", 42)

        cache.disable()
        assert cache.get("key") is None  # Disabled

        cache.enable()
        assert cache.get("key") == 42  # Re-enabled

    def test_disable_prevents_set(self) -> None:
        """Disabled cache ignores set."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.disable()
        cache.set("key", 42)

        cache.enable()
        assert cache.get("key") is None  # Was not set

    def test_get_or_set_when_disabled(self) -> None:
        """get_or_set still computes when disabled."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.disable()

        result = cache.get_or_set("key", lambda: 42)
        assert result == 42

        cache.enable()
        assert cache.get("key") is None  # Not cached while disabled

    def test_enabled_property(self) -> None:
        """enabled property reflects state."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        assert cache.enabled is True

        cache.disable()
        assert cache.enabled is False

        cache.enable()
        assert cache.enabled is True


class TestDelete:
    """Test delete functionality."""

    def test_delete_existing(self) -> None:
        """delete returns True and removes existing key."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("key", 42)

        assert cache.delete("key") is True
        assert "key" not in cache

    def test_delete_nonexistent(self) -> None:
        """delete returns False for missing key."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        assert cache.delete("missing") is False


class TestClear:
    """Test clear functionality."""

    def test_clear_removes_all(self) -> None:
        """clear removes all entries."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        cache.clear()
        assert len(cache) == 0
        assert cache.get("a") is None

    def test_clear_resets_stats(self) -> None:
        """clear also resets stats."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.get("a")  # hit

        cache.clear()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestThreadSafety:
    """Test concurrent access patterns."""

    def test_concurrent_access(self) -> None:
        """Cache handles concurrent reads and writes."""
        cache: LRUCache[int, int] = LRUCache(maxsize=100)

        def writer(start: int) -> None:
            for i in range(start, start + 100):
                cache.set(i, i * 2)

        def reader(start: int) -> None:
            for i in range(start, start + 100):
                cache.get(i)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(4):
                futures.append(executor.submit(writer, i * 100))
                futures.append(executor.submit(reader, i * 100))
            for f in futures:
                f.result()  # Raises if any thread failed

        assert len(cache) <= 100

    def test_get_or_set_concurrent(self) -> None:
        """get_or_set handles concurrent computation."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        call_count = 0

        def slow_factory() -> int:
            nonlocal call_count
            call_count += 1
            time.sleep(0.05)
            return 42

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cache.get_or_set, "key", slow_factory) for _ in range(4)]
            results = [f.result() for f in futures]

        assert all(r == 42 for r in results)
        # Due to RLock, at least one thread computes; others may get cached
        assert call_count >= 1


class TestMiscellaneous:
    """Test other functionality."""

    def test_len(self) -> None:
        """__len__ returns cache size."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        assert len(cache) == 0

        cache.set("a", 1)
        cache.set("b", 2)
        assert len(cache) == 2

    def test_contains(self) -> None:
        """__contains__ checks key existence."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)

        assert "a" in cache
        assert "b" not in cache

    def test_keys(self) -> None:
        """keys returns snapshot of all keys."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        keys = cache.keys()
        assert sorted(keys) == ["a", "b", "c"]

    def test_maxsize_property(self) -> None:
        """maxsize property returns configured max."""
        cache: LRUCache[str, int] = LRUCache(maxsize=42)
        assert cache.maxsize == 42

    def test_repr(self) -> None:
        """__repr__ shows useful info."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10, name="my_cache")
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss

        repr_str = repr(cache)
        assert "my_cache" in repr_str
        assert "1/10" in repr_str
        assert "50.0%" in repr_str

    def test_repr_no_name(self) -> None:
        """__repr__ works without name."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        repr_str = repr(cache)
        assert "<LRUCache:" in repr_str

    def test_default_maxsize(self) -> None:
        """Default maxsize is 128."""
        cache: LRUCache[str, int] = LRUCache()
        assert cache.maxsize == 128

    def test_generic_types(self) -> None:
        """Cache works with various key/value types."""
        # Tuple keys
        cache1: LRUCache[tuple[str, int], list[str]] = LRUCache(maxsize=10)
        cache1.set(("a", 1), ["x", "y"])
        assert cache1.get(("a", 1)) == ["x", "y"]

        # Complex values
        cache2: LRUCache[str, dict[str, int]] = LRUCache(maxsize=10)
        cache2.set("key", {"count": 42})
        assert cache2.get("key") == {"count": 42}
