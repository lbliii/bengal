"""
Directive content caching for performance optimization.

Caches parsed directive content by content hash to avoid expensive
re-parsing of identical directive blocks.

Thread Safety (Free-Threading / PEP 703):
    DirectiveCache uses LRUCache internally which is already thread-safe.
    configure_cache() uses a lock to protect the global instance replacement.
"""

from __future__ import annotations

import threading
from typing import Any

from bengal.utils.primitives.hashing import hash_str
from bengal.utils.primitives.lru_cache import LRUCache


class DirectiveCache:
    """
    LRU cache for parsed directive content.

    Uses content hash to detect changes and reuse parsed AST.
    Implements LRU eviction to limit memory usage.

    Thread-safe: Uses shared LRUCache with RLock for safe concurrent access.

    Expected impact: 30-50% speedup on pages with repeated directive patterns.

    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize directive cache.

        Args:
            max_size: Maximum number of cached items (default 1000)
        """
        self._cache: LRUCache[str, Any] = LRUCache(
            maxsize=max_size,
            name="directive",
        )

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
        combined = f"{directive_type}:{content}"
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
        return self._cache.get(self._make_key(directive_type, content))

    def put(self, directive_type: str, content: str, parsed: Any) -> None:
        """
        Cache parsed content.

        Args:
            directive_type: Type of directive
            content: Directive content
            parsed: Parsed result to cache
        """
        self._cache.set(self._make_key(directive_type, content), parsed)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()

    def enable(self) -> None:
        """Enable caching."""
        self._cache.enable()

    def disable(self) -> None:
        """Disable caching."""
        self._cache.disable()

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
        return self._cache.stats()

    def reset_stats(self) -> None:
        """Reset hit/miss statistics without clearing cache."""
        self._cache.reset_stats()

    def __repr__(self) -> str:
        """String representation."""
        stats = self.stats()
        size = stats["size"]
        max_size = stats["max_size"]
        hit_rate = stats["hit_rate"]
        return f"<DirectiveCache: {size}/{max_size} items, {hit_rate:.1%} hit rate>"


# Global cache instance (shared across all threads)
# Thread-safe: Uses LRUCache with internal RLock
_directive_cache = DirectiveCache(max_size=1000)
_config_lock = threading.Lock()  # Protects _directive_cache replacement in configure_cache


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

    Thread-safe: Uses lock to protect global instance replacement under
    free-threading (PEP 703).

    Args:
        max_size: Maximum cache size (None to keep current)
        enabled: Whether to enable caching (None to keep current)

    Note:
        max_size changes require recreating the cache. This clears existing entries.

    """
    global _directive_cache

    with _config_lock:
        if max_size is not None:
            # Recreate cache with new size
            was_enabled = _directive_cache._cache.enabled
            _directive_cache = DirectiveCache(max_size=max_size)
            if not was_enabled:
                _directive_cache.disable()

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


def configure_for_site(site: Any) -> None:
    """
    Auto-configure directive cache based on site configuration.

    Versioned sites benefit from directive caching because identical
    directive blocks appear across multiple versions. Cache provides
    3-5x speedup for repeated directive content.

    Single-version sites skip caching (no benefit, adds overhead).

    Args:
        site: Site instance with version_config and config attributes

    """
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)

    version_config = getattr(site, "version_config", None)
    if not version_config:
        return

    # Check for explicit config override
    build_config = site.config.get("build", {}) or {}
    cache_override = build_config.get("directive_cache")

    if cache_override is not None:
        # Explicit config: respect user preference
        configure_cache(enabled=bool(cache_override))
        logger.debug(
            "directive_cache_configured",
            enabled=bool(cache_override),
            reason="explicit_config",
        )
        return

    # Auto-detect: enable if multiple versions
    if version_config.enabled and len(version_config.versions) > 1:
        configure_cache(enabled=True)
        logger.debug(
            "directive_cache_auto_enabled",
            versions=len(version_config.versions),
            reason="multiple_versions_detected",
        )
    else:
        # Single version or no versioning: disable (avoid overhead)
        configure_cache(enabled=False)
