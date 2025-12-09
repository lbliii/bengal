"""
Directive content caching for performance optimization.

Caches parsed directive content by content hash to avoid expensive
re-parsing of identical directive blocks.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from bengal.utils.hashing import hash_str


class DirectiveCache:
    """
    LRU cache for parsed directive content.

    Uses content hash to detect changes and reuse parsed AST.
    Implements LRU eviction to limit memory usage.

    Expected impact: 30-50% speedup on pages with repeated directive patterns.
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize directive cache.

        Args:
            max_size: Maximum number of cached items (default 1000)
        """
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._enabled = True

    def _make_key(self, directive_type: str, content: str) -> str:
        """
        Generate cache key from directive type and content.

        Uses SHA256 hash for deterministic, collision-resistant keys.

        Args:
            directive_type: Type of directive (tabs, note, etc.)
            content: Directive content

        Returns:
            Cache key string
        """
        # Create combined string
        combined = f"{directive_type}:{content}"

        # Hash it and use key format: type:hash
        return f"{directive_type}:{hash_str(combined, truncate=16)}"

    def get(self, directive_type: str, content: str) -> Any | None:
        """
        Get cached parsed content.

        Args:
            directive_type: Type of directive
            content: Directive content

        Returns:
            Cached parsed result or None if not found
        """
        if not self._enabled:
            return None

        cache_key = self._make_key(directive_type, content)

        if cache_key in self._cache:
            self._hits += 1
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        self._misses += 1
        return None

    def put(self, directive_type: str, content: str, parsed: Any) -> None:
        """
        Cache parsed content.

        Args:
            directive_type: Type of directive
            content: Directive content
            parsed: Parsed result to cache
        """
        if not self._enabled:
            return

        cache_key = self._make_key(directive_type, content)

        # Add to cache
        self._cache[cache_key] = parsed

        # Move to end (most recently used)
        self._cache.move_to_end(cache_key)

        # Evict oldest if over size limit
        if len(self._cache) > self._max_size:
            # Remove oldest (first item)
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def enable(self) -> None:
        """Enable caching."""
        self._enabled = True

    def disable(self) -> None:
        """Disable caching."""
        self._enabled = False

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Cache hit rate (0.0 to 1.0)
            - size: Current cache size
            - max_size: Maximum cache size
            - enabled: Whether caching is enabled
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "max_size": self._max_size,
            "enabled": self._enabled,
        }

    def reset_stats(self) -> None:
        """Reset hit/miss statistics without clearing cache."""
        self._hits = 0
        self._misses = 0

    def __repr__(self) -> str:
        """String representation."""
        stats = self.stats()
        size = stats["size"]
        max_size = stats["max_size"]
        hit_rate = stats["hit_rate"]
        return f"<DirectiveCache: {size}/{max_size} items, {hit_rate:.1%} hit rate>"


# Global cache instance (shared across all threads)
# Thread-safe: Only stores immutable parsed results
_directive_cache = DirectiveCache(max_size=1000)


def get_cache() -> DirectiveCache:
    """
    Get the global directive cache instance.

    Returns:
        Global DirectiveCache instance
    """
    return _directive_cache


def configure_cache(max_size: int | None = None, enabled: bool | None = None) -> None:
    """
    Configure the global directive cache.

    Args:
        max_size: Maximum cache size (None to keep current)
        enabled: Whether to enable caching (None to keep current)
    """
    global _directive_cache

    if max_size is not None:
        _directive_cache._max_size = max_size

    if enabled is not None:
        if enabled:
            _directive_cache.enable()
        else:
            _directive_cache.disable()


def clear_cache() -> None:
    """Clear the global directive cache."""
    _directive_cache.clear()


def get_cache_stats() -> dict[str, Any]:
    """
    Get statistics from the global directive cache.

    Returns:
        Cache statistics dictionary
    """
    return _directive_cache.stats()
