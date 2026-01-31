"""
Thread-safe LRU cache with optional TTL and statistics.

This is Bengal's standard LRU cache implementation. Use it for any
in-memory caching with size limits and optional time-based expiry.

Design Goals:
- Zero dependencies on Bengal internals (portable to Kida or elsewhere)
- Generic type parameters for type safety
- Full-featured: stats, TTL, enable/disable, get_or_set
- Thread-safe with RLock for reentrant access

Example:
    >>> from bengal.utils.primitives import LRUCache
    >>> cache: LRUCache[str, Template] = LRUCache(maxsize=400, ttl=300)
    >>> cache.set("key", value)
    >>> cache.get("key")
    >>> template = cache.get_or_set("other", lambda: compile_template())
    >>> cache.stats()
{'hits': 10, 'misses': 2, 'hit_rate': 0.83, ...}

"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, overload


class LRUCache[K, V]:
    """Thread-safe LRU cache with optional TTL support.

    Uses OrderedDict + RLock for O(1) operations with thread safety.

    Eviction Strategy:
        True LRU - move_to_end() on every access, popitem(last=False) for eviction.
        This provides better hit rates than FIFO for workloads with temporal locality.

    Args:
        maxsize: Maximum number of entries (0 = unlimited)
        ttl: Time-to-live in seconds (None = no expiry)
        name: Optional name for debugging/logging

    Thread-Safety:
        All operations are protected by an RLock (reentrant).
        Safe for concurrent access from multiple threads.

    Complexity:
        - get: O(1) average
        - set: O(1) average
        - get_or_set: O(1) + factory cost on miss
        - clear: O(n)

    """

    __slots__ = (
        "_cache",
        "_enabled",
        "_hits",
        "_lock",
        "_maxsize",
        "_misses",
        "_name",
        "_timestamps",
        "_ttl",
    )

    def __init__(
        self,
        maxsize: int = 128,
        ttl: float | None = None,
        *,
        name: str | None = None,
    ) -> None:
        """Initialize LRU cache.

        Args:
            maxsize: Maximum entries (0 = unlimited, default 128)
            ttl: Time-to-live in seconds (None = no expiry)
            name: Optional name for debugging (shown in repr)
        """
        self._cache: OrderedDict[K, V] = OrderedDict()
        self._timestamps: dict[K, float] = {}
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._enabled = True
        self._name = name

    def get(self, key: K) -> V | None:
        """Get value by key, returning None if not found or expired.

        Updates LRU order on hit. Counts as miss if disabled.
        """
        with self._lock:
            if not self._enabled:
                self._misses += 1
                return None

            if key not in self._cache:
                self._misses += 1
                return None

            # Check TTL expiry
            if self._ttl is not None:
                ts = self._timestamps.get(key, 0)
                if time.monotonic() - ts > self._ttl:
                    del self._cache[key]
                    del self._timestamps[key]
                    self._misses += 1
                    return None

            # LRU: Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    @overload
    def get_or_set(self, key: K, factory: Callable[[], V]) -> V: ...
    @overload
    def get_or_set(self, key: K, factory: Callable[[K], V], *, pass_key: bool) -> V: ...

    def get_or_set(
        self,
        key: K,
        factory: Callable[[], V] | Callable[[K], V],
        *,
        pass_key: bool = False,
    ) -> V:
        """Get value or compute and cache it.

        This is the preferred pattern for cache usage - avoids the
        check-then-set race condition and reduces boilerplate.

        Args:
            key: Cache key
            factory: Callable that returns the value to cache on miss
            pass_key: If True, passes key to factory as argument

        Returns:
            Cached or newly computed value

        Example:
            >>> cache = LRUCache[str, Template](maxsize=100)
            >>> template = cache.get_or_set("base.html", lambda: compile("base.html"))
            >>> # Or with key passed to factory:
            >>> template = cache.get_or_set("base.html", compile, pass_key=True)
        """
        with self._lock:
            if not self._enabled:
                self._misses += 1
                if pass_key:
                    return factory(key)  # type: ignore[call-arg]
                return factory()  # type: ignore[call-arg]

            if key in self._cache:
                # Check TTL
                if self._ttl is not None:
                    ts = self._timestamps.get(key, 0)
                    if time.monotonic() - ts > self._ttl:
                        del self._cache[key]
                        del self._timestamps[key]
                        # Fall through to compute
                    else:
                        self._cache.move_to_end(key)
                        self._hits += 1
                        return self._cache[key]
                else:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return self._cache[key]

            # Miss - compute value
            self._misses += 1

        # Compute outside lock to avoid blocking other threads
        value = factory(key) if pass_key else factory()  # type: ignore[call-arg]

        # Store result
        with self._lock:
            if not self._enabled:
                return value

            # Another thread may have set it while we computed
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]

            self._cache[key] = value
            self._timestamps[key] = time.monotonic()

            # Evict if over capacity
            if self._maxsize > 0:
                while len(self._cache) > self._maxsize:
                    oldest_key, _ = self._cache.popitem(last=False)
                    self._timestamps.pop(oldest_key, None)

            return value

    def set(self, key: K, value: V) -> None:
        """Set value, evicting LRU entries if at capacity."""
        with self._lock:
            if not self._enabled:
                return

            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = value
                self._timestamps[key] = time.monotonic()
                return

            self._cache[key] = value
            self._timestamps[key] = time.monotonic()

            # Evict if over capacity
            if self._maxsize > 0:
                while len(self._cache) > self._maxsize:
                    oldest_key, _ = self._cache.popitem(last=False)
                    self._timestamps.pop(oldest_key, None)

    def delete(self, key: K) -> bool:
        """Delete a key from the cache.

        Returns:
            True if key was present and deleted, False otherwise.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._timestamps.pop(key, None)
                return True
            return False

    def clear(self) -> None:
        """Clear all entries and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._hits = 0
            self._misses = 0

    def enable(self) -> None:
        """Enable caching."""
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        """Disable caching (get returns None, set is no-op)."""
        with self._lock:
            self._enabled = False

    @property
    def enabled(self) -> bool:
        """Whether caching is enabled."""
        return self._enabled

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Cache hit rate (0.0 to 1.0)
            - size: Current cache size
            - max_size: Maximum cache size
            - ttl: Time-to-live in seconds (None if disabled)
            - enabled: Whether caching is enabled
            - name: Cache name (if set)
        """
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "size": len(self._cache),
                "max_size": self._maxsize,
                "ttl": self._ttl,
                "enabled": self._enabled,
                "name": self._name,
            }

    def reset_stats(self) -> None:
        """Reset hit/miss statistics without clearing cache."""
        with self._lock:
            self._hits = 0
            self._misses = 0

    def __contains__(self, key: K) -> bool:
        """Check if key exists and is not expired.

        Does NOT update LRU order or stats. Use for existence checks only.
        """
        with self._lock:
            if key not in self._cache:
                return False
            if self._ttl is not None:
                ts = self._timestamps.get(key, 0)
                if time.monotonic() - ts > self._ttl:
                    return False
            return True

    def __len__(self) -> int:
        """Return number of entries (may include expired if TTL set)."""
        return len(self._cache)

    @property
    def maxsize(self) -> int:
        """Maximum cache size."""
        return self._maxsize

    def keys(self) -> list[K]:
        """Return list of all keys (snapshot, may include expired)."""
        with self._lock:
            return list(self._cache.keys())

    def __repr__(self) -> str:
        stats = self.stats()
        name = f" '{self._name}'" if self._name else ""
        return (
            f"<LRUCache{name}: {stats['size']}/{stats['max_size']} items, "
            f"{stats['hit_rate']:.1%} hit rate>"
        )
