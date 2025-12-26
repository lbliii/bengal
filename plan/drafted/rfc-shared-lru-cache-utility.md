# RFC: Shared LRU Cache Utility

**Status**: Implemented (Phase 1-3 Complete)  
**Created**: 2025-12-26  
**Updated**: 2025-12-26  
**Author**: AI Assistant  
**Effort**: Phase 1: ~2 hours | Phase 2: ~1 day | Phase 3: ~2 days  
**Impact**: Medium - Reduces duplication, enables consistent caching behavior  
**Category**: Utils / Performance / Architecture

---

## Executive Summary

Bengal has **6 independent cache implementations** with varying features and eviction strategies. Only 3 use true LRU; the rest use simpler FIFO eviction. This creates maintenance burden, inconsistent APIs, and missed optimization opportunities.

**The Opportunity**: Create a single, well-tested `LRUCache` utility in `bengal/utils/lru_cache.py` that all modules can adopt.

**Key Benefits**:
- Shared optimizations benefit all caches
- Consistent hit/miss tracking for performance analysis
- TTL support where beneficial (fragment caching, server responses)
- Upgrade FIFO caches to true LRU for better hit rates
- Future-proof: standalone utility with no internal Bengal dependencies

---

## Architecture Consideration: Kida Separation

Kida is planned to eventually become its own package outside Bengal. This RFC accounts for that:

**Current state**: Kida has the most complete LRU implementation in `rendering/kida/environment/core.py`.

**Strategy**: Create a new `LRUCache` in `bengal/utils/` with zero dependencies on Kida internals. When Kida separates:
- **Option A**: Kida copies the LRUCache (it's ~200 lines, self-contained)
- **Option B**: Both depend on a tiny shared package (e.g., `lru-cache-py`)
- **Option C**: Kida uses Python's `functools.lru_cache` or `cachetools` instead

The utility is designed to be copy-paste portable with no Bengal-specific imports.

---

## Current State Analysis

### Existing Implementations

| Cache | Location | Eviction | Stats | TTL | Thread-Safe | Lines |
|-------|----------|----------|-------|-----|-------------|-------|
| `DirectiveCache` | `directives/cache.py` | **LRU** | ✅ | ❌ | ✅ | ~155 |
| `NavTreeCache` | `core/nav_tree.py` | **LRU** | ❌ | ❌ | ✅ | ~96 |
| `LRUCache` (Kida) | `rendering/kida/environment/core.py` | **LRU** | ✅ | ✅ | ✅ | ~170 |
| `NavScaffoldCache` | `template_functions/navigation/scaffold.py` | FIFO | ❌ | ❌ | ✅ | ~80 |
| Server HTML cache | `server/request_handler.py` | FIFO | ❌ | ❌ | ✅ | ~40 |
| Ignore filter cache | `server/ignore_filter.py` | FIFO | ❌ | ❌ | ❌ | ~30 |

**Total**: ~571 lines of cache logic across 6 locations.

### Eviction Strategy Comparison

**True LRU** (3 implementations):
- Uses `OrderedDict.move_to_end()` on every access
- Evicts least-recently-used entries
- Better hit rates for access patterns with temporal locality

**FIFO** (3 implementations):
- Uses `next(iter())` to find oldest entry
- Evicts first-inserted entries regardless of access
- Simpler but lower hit rates

```python
# True LRU pattern (DirectiveCache, NavTreeCache, Kida)
def get(self, key):
    if key in self._cache:
        self._cache.move_to_end(key)  # ← LRU update
        return self._cache[key]

# FIFO pattern (NavScaffoldCache, Server HTML, IgnoreFilter)  
def set(self, key, value):
    if len(self._cache) >= self._max_size:
        first_key = next(iter(self._cache))  # ← No LRU, just oldest
        del self._cache[first_key]
```

---

## Problem Statement

### 1. Inconsistent Features

| Feature | DirectiveCache | NavTreeCache | NavScaffoldCache | Kida LRU | Server HTML | IgnoreFilter |
|---------|---------------|--------------|------------------|----------|-------------|--------------|
| True LRU eviction | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| `stats()` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `enable()/disable()` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `reset_stats()` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| TTL support | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `get_or_set()` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Generic types | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Developers can't uniformly debug or control caches.

### 2. Maintenance Burden

- Bug fixes must be applied 3-6 times
- Performance optimizations aren't shared
- Tests are duplicated or missing
- FIFO caches could benefit from LRU but nobody upgrades them

### 3. Missed Optimizations

Without stats, we can't identify:
- Which caches have low hit rates (wasted memory)
- Which caches are undersized (too many evictions)
- Which caches would benefit from TTL

---

## Proposed Solution

### Phase 1: Create Shared Utility (~2 hours)

Create `bengal/utils/lru_cache.py` as a standalone, zero-dependency utility.

```python
# bengal/utils/lru_cache.py
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
    >>> from bengal.utils.lru_cache import LRUCache
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
from typing import Any, Generic, TypeVar, overload

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
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
        "_maxsize",
        "_ttl",
        "_lock",
        "_timestamps",
        "_hits",
        "_misses",
        "_enabled",
        "_name",
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
                    return factory(key)  # type: ignore
                return factory()  # type: ignore

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
        if pass_key:
            value = factory(key)  # type: ignore
        else:
            value = factory()  # type: ignore

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
```

### Phase 2: Integrate and Test (~1 day)

**2a. Add to utils exports**:

```python
# bengal/utils/__init__.py
from bengal.utils.lru_cache import LRUCache

__all__ = [
    # ... existing exports
    "LRUCache",
]
```

**2b. Update Kida to use shared utility**:

```python
# bengal/rendering/kida/environment/core.py
# BEFORE:
class LRUCache:
    """Thread-safe LRU cache with optional TTL support..."""
    # 170 lines of implementation

# AFTER:
from bengal.utils.lru_cache import LRUCache
# Delete local implementation
```

**2c. Add comprehensive tests**:

```python
# tests/utils/test_lru_cache.py
import time
from concurrent.futures import ThreadPoolExecutor
from bengal.utils.lru_cache import LRUCache


class TestLRUEviction:
    def test_evicts_lru_not_fifo(self):
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

    def test_evicts_oldest_on_capacity(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Evicts "a"

        assert "a" not in cache
        assert cache.get("b") == 2


class TestTTL:
    def test_expires_after_ttl(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10, ttl=0.1)
        cache.set("key", 42)
        assert cache.get("key") == 42

        time.sleep(0.15)
        assert cache.get("key") is None

    def test_contains_respects_ttl(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10, ttl=0.1)
        cache.set("key", 42)
        assert "key" in cache

        time.sleep(0.15)
        assert "key" not in cache


class TestGetOrSet:
    def test_returns_cached_value(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("key", 42)

        call_count = 0
        def factory():
            nonlocal call_count
            call_count += 1
            return 100

        result = cache.get_or_set("key", factory)
        assert result == 42
        assert call_count == 0  # Factory not called

    def test_computes_on_miss(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10)

        result = cache.get_or_set("key", lambda: 42)
        assert result == 42
        assert cache.get("key") == 42

    def test_passes_key_to_factory(self):
        cache: LRUCache[str, str] = LRUCache(maxsize=10)

        result = cache.get_or_set("hello", lambda k: k.upper(), pass_key=True)
        assert result == "HELLO"


class TestStats:
    def test_tracks_hits_and_misses(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        cache.get("a")  # hit

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2/3

    def test_reset_stats(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.get("a")
        cache.get("b")

        cache.reset_stats()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 1  # Cache not cleared


class TestEnableDisable:
    def test_disable_returns_none(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.set("key", 42)

        cache.disable()
        assert cache.get("key") is None  # Disabled

        cache.enable()
        assert cache.get("key") == 42  # Re-enabled

    def test_disable_prevents_set(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        cache.disable()
        cache.set("key", 42)

        cache.enable()
        assert cache.get("key") is None  # Was not set


class TestThreadSafety:
    def test_concurrent_access(self):
        cache: LRUCache[int, int] = LRUCache(maxsize=100)

        def writer(start: int):
            for i in range(start, start + 100):
                cache.set(i, i * 2)

        def reader(start: int):
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

    def test_get_or_set_concurrent(self):
        """Ensure get_or_set doesn't compute twice for same key."""
        cache: LRUCache[str, int] = LRUCache(maxsize=10)
        call_count = 0

        def slow_factory():
            nonlocal call_count
            call_count += 1
            time.sleep(0.05)
            return 42

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cache.get_or_set, "key", slow_factory) for _ in range(4)]
            results = [f.result() for f in futures]

        assert all(r == 42 for r in results)
        # Due to RLock, only one thread computes; others wait or get cached
        assert call_count >= 1  # At least one computed
```

### Phase 3: Opportunistic Migration (~2 days)

Migrate existing caches when touched. Prioritize by benefit:

#### Migration Priority Tiers

**Tier 1 - High Value (already use LRU pattern)**:
1. `DirectiveCache` - Direct swap, ~130 lines saved
2. `NavTreeCache` - Gains stats/enable/disable, ~60 lines saved

**Tier 2 - Upgrade Benefit (currently FIFO → LRU)**:
3. `NavScaffoldCache` - Gains true LRU + stats
4. Server HTML cache - Gains true LRU + TTL for auto-expire
5. `IgnoreFilter` cache - Gains true LRU + thread safety

**Tier 3 - Keep Specialized**:
- `BuildCache` - Disk-persistent, different pattern
- `PageDiscoveryCache` - JSON-serialized, different pattern
- `ThreadLocalCache` - Per-thread, different pattern

#### Example: DirectiveCache Migration

```python
# BEFORE: ~155 lines in directives/cache.py
class DirectiveCache:
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._enabled = True

    def get(self, directive_type: str, content: str) -> Any | None:
        if not self._enabled:
            return None
        cache_key = self._make_key(directive_type, content)
        with self._lock:
            if cache_key in self._cache:
                self._hits += 1
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]
            self._misses += 1
        return None

    # ... 100+ more lines of LRU logic, stats, enable/disable ...


# AFTER: ~35 lines
from bengal.utils.lru_cache import LRUCache

class DirectiveCache:
    """LRU cache for parsed directive content."""

    def __init__(self, max_size: int = 1000):
        self._cache: LRUCache[str, Any] = LRUCache(
            maxsize=max_size,
            name="directive"
        )

    def _make_key(self, directive_type: str, content: str) -> str:
        combined = f"{directive_type}:{content}"
        return f"{directive_type}:{hash_str(combined, truncate=16)}"

    def get(self, directive_type: str, content: str) -> Any | None:
        return self._cache.get(self._make_key(directive_type, content))

    def put(self, directive_type: str, content: str, parsed: Any) -> None:
        self._cache.set(self._make_key(directive_type, content), parsed)

    def clear(self) -> None:
        self._cache.clear()

    def enable(self) -> None:
        self._cache.enable()

    def disable(self) -> None:
        self._cache.disable()

    def stats(self) -> dict[str, Any]:
        return self._cache.stats()

    def __repr__(self) -> str:
        return repr(self._cache)
```

**Reduction**: ~155 lines → ~35 lines (77% less code)

#### Example: NavTreeCache Migration

```python
# BEFORE: ~96 lines using OrderedDict + manual LRU
class NavTreeCache:
    _trees: OrderedDict[str | None, NavTree] = OrderedDict()
    _lock = threading.Lock()
    _MAX_CACHE_SIZE = 20

    @classmethod
    def get(cls, site: Site, version_id: str | None = None) -> NavTree:
        with cls._lock:
            if version_id in cls._trees:
                cls._trees.move_to_end(version_id)
                return cls._trees[version_id]
        # ... build logic ...


# AFTER: ~50 lines using get_or_set pattern
from bengal.utils.lru_cache import LRUCache

class NavTreeCache:
    _cache: LRUCache[tuple[int, str | None], NavTree] = LRUCache(
        maxsize=20,
        name="nav_tree"
    )
    _build_locks = PerKeyLockManager()

    @classmethod
    def get(cls, site: Site, version_id: str | None = None) -> NavTree:
        # Use site id + version as key
        cache_key = (id(site), version_id)

        # Check if site changed (full invalidation)
        # ... site change detection ...

        def build_tree() -> NavTree:
            # Serialize builds for same version
            with cls._build_locks.get_lock(version_id or "__default__"):
                # Double-check after acquiring lock
                cached = cls._cache.get(cache_key)
                if cached is not None:
                    return cached
                return NavTree.build(site, version_id)

        return cls._cache.get_or_set(cache_key, build_tree)
```

---

## Performance Benefits

### 1. FIFO → LRU Upgrade

Caches currently using FIFO get true LRU for better hit rates:

| Cache | Current | After | Expected Improvement |
|-------|---------|-------|---------------------|
| NavScaffoldCache | FIFO | LRU | 10-20% better hit rate |
| Server HTML | FIFO | LRU | 15-25% better hit rate |
| IgnoreFilter | FIFO | LRU | 5-10% better hit rate |

### 2. Consistent Observability

```python
# Debug ALL caches uniformly
def report_cache_health():
    caches = [
        directive_cache._cache,
        nav_tree_cache._cache,
        env._template_cache,
        env._fragment_cache,
    ]

    for cache in caches:
        stats = cache.stats()
        name = stats.get("name", "unnamed")
        if stats["hit_rate"] < 0.5:
            logger.warning(f"{name} cache: low hit rate {stats['hit_rate']:.1%}")
        if stats["size"] == stats["max_size"]:
            logger.warning(f"{name} cache: at capacity, consider increasing maxsize")
```

### 3. TTL Where Beneficial

| Cache | Current | With TTL | Benefit |
|-------|---------|----------|---------|
| Fragment cache | Manual invalidation | 5min auto-expire | Stale content protection |
| Server HTML cache | Never expires | 30s auto-expire | Memory control in dev |
| Ignore filter | Never expires | 60s auto-expire | Pick up new ignores |

---

## Migration Checklist (Per Cache)

- [ ] Replace `OrderedDict` + manual logic with `LRUCache`
- [ ] Use `get_or_set()` where applicable
- [ ] Remove duplicate hit/miss tracking code
- [ ] Remove duplicate enable/disable code
- [ ] Add `name` parameter for debugging
- [ ] Update tests to verify behavior unchanged
- [ ] Consider adding TTL if beneficial
- [ ] Verify thread safety preserved

---

## Risks and Mitigations

### Risk 1: Regression in Migrated Caches

**Mitigation**:
- Keep existing tests, add LRU-specific tests
- Migrate one cache at a time
- Verify behavior in integration tests

### Risk 2: Performance Regression

**Mitigation**:
- `LRUCache` uses same O(1) operations
- `get_or_set()` reduces lock contention vs check-then-set
- Benchmark before/after for critical paths

### Risk 3: Kida Separation Complexity

**Mitigation**:
- `LRUCache` has zero Bengal dependencies
- Can be copy-pasted to Kida or extracted to shared package
- Clear documentation of portability design

### Risk 4: Breaking API Changes

**Mitigation**:
- Existing cache classes keep their public API
- `LRUCache` is an implementation detail
- Wrapper methods preserve existing signatures

---

## Success Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Cache implementation count | 6 | 1 | 1 |
| Lines of cache code | ~571 | ~200 + thin wrappers | 60% reduction |
| Caches with stats | 2/6 | 6/6 | 100% |
| Caches with true LRU | 3/6 | 6/6 | 100% |
| Caches with TTL option | 1/6 | 6/6 | 100% |

---

## Implementation Timeline

| Phase | Effort | Scope |
|-------|--------|-------|
| Phase 1 | 2 hours | Create `bengal/utils/lru_cache.py` |
| Phase 2 | 1 day | Add tests, update Kida to import from utils |
| Phase 3 | 2 days | Migrate Tier 1 caches (DirectiveCache, NavTreeCache) |
| Future | Opportunistic | Migrate Tier 2 caches when touched |

---

## Decision

### Proceed if:
- ✅ Performance debugging is difficult without stats (true - 4/6 have no stats)
- ✅ Multiple caches need TTL (true - server/fragment caches)
- ✅ FIFO caches would benefit from LRU (true - 3 caches)
- ✅ Kida separation needs portable utilities (true - planned)
- ✅ Reducing duplication is valued (true - ~370 lines saved)

### Defer if:
- ❌ Current caches work well enough
- ❌ No resources for migration
- ❌ Kida separation timeline is imminent (extract there instead)

---

## Related RFCs

- `rfc-cache-algorithm-optimization.md` - Broader cache optimization
- `rfc-performance-optimizations.md` - Overall performance improvements
- `rfc-kida-python-compatibility.md` - Kida portability considerations

---

## Appendix A: Cache Inventory

### Tier 1: Direct Migration Candidates

| Cache | Location | Current Lines | After Lines | Savings |
|-------|----------|--------------|-------------|---------|
| DirectiveCache | `directives/cache.py` | ~155 | ~35 | 77% |
| NavTreeCache | `core/nav_tree.py` | ~96 | ~50 | 48% |
| Kida LRUCache | `rendering/kida/environment/core.py` | ~170 | import | 100% |

### Tier 2: Upgrade Candidates (FIFO → LRU)

| Cache | Location | Current Lines | Benefit |
|-------|----------|--------------|---------|
| NavScaffoldCache | `template_functions/navigation/scaffold.py` | ~80 | +LRU, +stats |
| Server HTML cache | `server/request_handler.py` | ~40 | +LRU, +TTL |
| IgnoreFilter cache | `server/ignore_filter.py` | ~30 | +LRU, +thread-safe |

### Tier 3: Keep Specialized

| Cache | Location | Reason |
|-------|----------|--------|
| BuildCache | `cache/build_cache/` | Disk-persistent |
| PageDiscoveryCache | `cache/page_discovery_cache.py` | JSON-serialized |
| ThreadLocalCache | `utils/thread_local.py` | Per-thread semantics |

---

## Appendix B: Kida Separation Options

When Kida becomes its own package:

**Option A: Copy LRUCache**
- Pros: Zero dependencies, complete control
- Cons: Divergent implementations over time
- Best if: Kida wants to customize behavior

**Option B: Shared micro-package**
- Pros: Single source of truth
- Cons: Additional dependency to manage
- Best if: Multiple projects need it

**Option C: Use `cachetools`**
- Pros: Well-tested, feature-rich
- Cons: External dependency, different API
- Best if: Want to reduce code ownership

**Recommendation**: Start with Option A (copy). It's ~200 lines of self-contained code. Consider Option B if Bengal and Kida both actively develop cache features.
