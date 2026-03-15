"""
Thread-safe cache for NavTree instances by version.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, ClassVar

from bengal.utils.cache_registry import InvalidationReason, register_cache
from bengal.utils.concurrency.concurrent_locks import PerKeyLockManager
from bengal.utils.primitives.lru_cache import LRUCache

from .tree import NavTree

if TYPE_CHECKING:
    from bengal.protocols import SiteLike


class NavTreeCache:
    """
    Thread-safe cache for NavTree instances with LRU eviction.

    Pre-computed trees (from SiteSnapshot) are checked first for lock-free O(1)
    lookups during parallel rendering. The lock-based build path remains as a
    fallback for contexts where no snapshot is available (tests, dev server).

    Memory leak prevention: Cache is limited to 20 entries. When limit is reached,
    least-recently-used entries are evicted (LRU). This prevents unbounded growth
    if many version_ids are created while keeping frequently-accessed versions cached.

    Thread Safety:
        - Pre-computed path: Lock-free dict lookup (set via set_precomputed)
        - Fallback path: shared LRUCache + per-version PerKeyLockManager locks

    Eviction Strategy:
        LRU (Least Recently Used) via shared bengal.utils.lru_cache.LRUCache.

    """

    _cache: LRUCache[str, NavTree] = LRUCache(maxsize=20, name="nav_tree")
    _lock = threading.Lock()
    _build_locks = PerKeyLockManager()  # Per-version build serialization
    _site: SiteLike | None = None
    # Pre-computed trees from SiteSnapshot — lock-free fast path
    _precomputed: ClassVar[dict[str, NavTree]] = {}

    @classmethod
    def set_precomputed(cls, trees: dict[str, NavTree] | None) -> None:
        """
        Install pre-computed NavTrees from the snapshot builder.

        Called once after create_site_snapshot() to enable lock-free lookups
        during parallel rendering. Pass None to clear pre-computed trees.

        Args:
            trees: Mapping of version_key → NavTree (or None to clear)
        """
        cls._precomputed = dict(trees) if trees else {}

    @classmethod
    def get(cls, site: SiteLike, version_id: str | None = None) -> NavTree:
        """
        Get a cached NavTree or build it if missing.

        Fast path (lock-free): If pre-computed trees are available (from
        SiteSnapshot), returns immediately via dict lookup — no locks acquired.

        Fallback path (thread-safe): Multiple threads requesting the same
        version will serialize on the build, with only one thread doing
        the actual work. Different versions can be built in parallel.
        """
        # Use string key for cache (None -> "__default__")
        cache_key = version_id if version_id is not None else "__default__"

        # Fast path: check pre-computed trees (lock-free O(1) lookup)
        precomputed = cls._precomputed.get(cache_key)
        if precomputed is not None:
            return precomputed

        # Fallback path: lock-based build-on-demand
        # 1. Quick cache check (includes site change detection)
        with cls._lock:
            # Full invalidation if site object changed (new build session)
            if cls._site is not site:
                cls._cache.clear()
                cls._build_locks.clear()
                cls._site = site

        # Check cache first (LRU update happens inside get)
        cached = cls._cache.get(cache_key)
        if cached is not None:
            return cached

        # 2. Serialize builds for SAME version (different versions build in parallel)
        with cls._build_locks.get_lock(cache_key):
            # Double-check: another thread may have built while we waited
            cached = cls._cache.get(cache_key)
            if cached is not None:
                return cached

            # 3. Build outside cache lock (expensive operation)
            tree = NavTree.build(site, version_id)

            # 4. Store result (LRU eviction handled by LRUCache)
            cls._cache.set(cache_key, tree)
            return tree

    @classmethod
    def invalidate(cls, version_id: str | None = None) -> None:
        """Invalidate the cache for a specific version or all."""
        if version_id is None:
            cls._cache.clear()
            cls._build_locks.clear()
            cls._precomputed.clear()
        else:
            cache_key = version_id if version_id is not None else "__default__"
            cls._cache.delete(cache_key)
            cls._precomputed.pop(cache_key, None)

    @classmethod
    def clear_locks(cls) -> None:
        """
        Clear all build locks and pre-computed trees.

        Call this at the end of a build session to reset lock state.
        Safe to call when no threads are actively building.
        """
        cls._build_locks.clear()
        cls._precomputed.clear()

    @classmethod
    def stats(cls) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics including hit/miss rates.
        """
        return cls._cache.stats()


# Register NavTreeCache with centralized cache registry
# Registered at module import time for automatic lifecycle management
register_cache(
    "nav_tree",
    NavTreeCache.invalidate,
    invalidate_on={
        InvalidationReason.CONFIG_CHANGED,
        InvalidationReason.STRUCTURAL_CHANGE,
        InvalidationReason.NAV_CHANGE,
        InvalidationReason.FULL_REBUILD,
        InvalidationReason.TEST_CLEANUP,
    },
)
