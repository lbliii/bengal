"""
Disk caching for reactive pipeline streams.

This module provides persistent caching for stream items, enabling:
- Fast incremental builds (skip unchanged items)
- Cross-build cache persistence
- Version-based cache invalidation

Key Components:
    - StreamCache: Disk-backed cache storage for stream items
    - DiskCachedStream: Stream wrapper that adds persistent caching
    - StreamCacheEntry: Cacheable entry for stream items

Architecture:
    Stream items are cached by their StreamKey, which includes:
    - source: Which stream produced the item
    - id: Unique identifier within the stream
    - version: Content hash for invalidation

    When a stream runs, cached items with matching key+version are
    returned without recomputing. Changed items (different version)
    are recomputed and the cache is updated.

Related:
    - bengal/cache/cacheable.py - Cacheable protocol
    - bengal/cache/cache_store.py - Generic cache storage
    - bengal/pipeline/core.py - StreamKey, StreamItem
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from bengal.cache.cacheable import Cacheable
from bengal.pipeline.core import Stream, StreamItem, StreamKey
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class StreamCacheEntry(Cacheable):
    """
    A single cached stream item entry.

    Implements Cacheable protocol for JSON serialization.

    Attributes:
        source: Stream name that produced this item
        id: Unique identifier within the stream
        version: Content version (hash) for invalidation
        value_json: JSON-serialized value
        cached_at: Timestamp when cached
    """

    source: str
    id: str
    version: str
    value_json: str
    cached_at: float = field(default_factory=time.time)

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "source": self.source,
            "id": self.id,
            "version": self.version,
            "value_json": self.value_json,
            "cached_at": self.cached_at,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> StreamCacheEntry:
        """Deserialize from dict."""
        return cls(
            source=data["source"],
            id=data["id"],
            version=data["version"],
            value_json=data["value_json"],
            cached_at=data.get("cached_at", 0.0),
        )

    @property
    def key(self) -> StreamKey:
        """Reconstruct StreamKey from entry."""
        return StreamKey(source=self.source, id=self.id, version=self.version)


class StreamCache:
    """
    Disk-backed cache for stream items.

    Stores stream items as JSON in the .bengal/ directory, enabling
    persistence across builds.

    Cache Structure:
        .bengal/pipeline/
        ├── streams.json          # Cache index and metadata
        └── items/
            ├── {source}_{id}.json  # Individual item caches

    Usage:
        >>> cache = StreamCache(Path(".bengal/pipeline"))
        >>> cache.get(key)  # Returns cached value or None
        >>> cache.put(key, value, serialize_fn)  # Store value
        >>> cache.save()  # Persist to disk

    Thread Safety:
        Not thread-safe. Use separate cache instances per thread
        or synchronize access externally.
    """

    VERSION = 1

    def __init__(self, cache_dir: Path) -> None:
        """
        Initialize stream cache.

        Args:
            cache_dir: Directory for cache files (.bengal/pipeline)
        """
        self.cache_dir = cache_dir
        self._entries: dict[str, StreamCacheEntry] = {}
        self._dirty = False
        self._load()

    def _cache_key(self, key: StreamKey) -> str:
        """Generate internal cache key from StreamKey."""
        return f"{key.source}:{key.id}"

    def get(
        self,
        key: StreamKey,
        deserialize_fn: Callable[[str], T] | None = None,
    ) -> T | None:
        """
        Get cached value for a stream key.

        Returns None if:
        - Key not in cache
        - Cached version doesn't match key version

        Args:
            key: StreamKey to look up
            deserialize_fn: Function to deserialize JSON value

        Returns:
            Cached value or None if cache miss
        """
        cache_key = self._cache_key(key)
        entry = self._entries.get(cache_key)

        if entry is None:
            return None

        # Version mismatch = cache miss
        if entry.version != key.version:
            logger.debug(
                "cache_version_mismatch",
                key=str(key),
                cached_version=entry.version,
                requested_version=key.version,
            )
            return None

        # Deserialize value
        if deserialize_fn:
            try:
                return deserialize_fn(entry.value_json)
            except Exception as e:
                logger.warning(
                    "cache_deserialize_error",
                    key=str(key),
                    error=str(e),
                )
                return None
        else:
            # Return raw JSON string
            return entry.value_json  # type: ignore

    def put(
        self,
        key: StreamKey,
        value: Any,
        serialize_fn: Callable[[Any], str] | None = None,
    ) -> None:
        """
        Store value in cache.

        Args:
            key: StreamKey for this item
            value: Value to cache
            serialize_fn: Function to serialize value to JSON string
        """
        value_json = serialize_fn(value) if serialize_fn else json.dumps(value, default=str)

        entry = StreamCacheEntry(
            source=key.source,
            id=key.id,
            version=key.version,
            value_json=value_json,
        )

        cache_key = self._cache_key(key)
        self._entries[cache_key] = entry
        self._dirty = True

    def invalidate(self, key: StreamKey) -> bool:
        """
        Remove entry from cache.

        Args:
            key: StreamKey to invalidate

        Returns:
            True if entry was removed, False if not found
        """
        cache_key = self._cache_key(key)
        if cache_key in self._entries:
            del self._entries[cache_key]
            self._dirty = True
            return True
        return False

    def invalidate_source(self, source: str) -> int:
        """
        Remove all entries from a specific source stream.

        Args:
            source: Stream name to invalidate

        Returns:
            Number of entries removed
        """
        to_remove = [k for k, e in self._entries.items() if e.source == source]
        for cache_key in to_remove:
            del self._entries[cache_key]
        if to_remove:
            self._dirty = True
        return len(to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries.clear()
        self._dirty = True

    def save(self) -> None:
        """
        Persist cache to disk.

        Only writes if cache has been modified since last save.
        """
        if not self._dirty:
            return

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / "streams.json"

        data = {
            "version": self.VERSION,
            "entries": [e.to_cache_dict() for e in self._entries.values()],
        }

        try:
            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self._dirty = False
            logger.debug(
                "stream_cache_saved",
                entries=len(self._entries),
                path=str(cache_file),
            )
        except Exception as e:
            logger.warning("stream_cache_save_error", error=str(e))

    def _load(self) -> None:
        """Load cache from disk."""
        cache_file = self.cache_dir / "streams.json"

        if not cache_file.exists():
            return

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))

            # Version check
            if data.get("version") != self.VERSION:
                logger.debug(
                    "stream_cache_version_mismatch",
                    cached=data.get("version"),
                    expected=self.VERSION,
                )
                return  # Start fresh

            for entry_data in data.get("entries", []):
                entry = StreamCacheEntry.from_cache_dict(entry_data)
                cache_key = self._cache_key(entry.key)
                self._entries[cache_key] = entry

            logger.debug(
                "stream_cache_loaded",
                entries=len(self._entries),
            )
        except Exception as e:
            logger.warning("stream_cache_load_error", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        sources: dict[str, int] = {}
        for entry in self._entries.values():
            sources[entry.source] = sources.get(entry.source, 0) + 1

        return {
            "total_entries": len(self._entries),
            "entries_by_source": sources,
            "dirty": self._dirty,
        }


class DiskCachedStream(Stream[T]):
    """
    Stream wrapper that adds persistent disk caching.

    Cached items are stored to disk and reused across builds.
    Only items with changed versions are recomputed.

    Example:
        >>> cache = StreamCache(Path(".bengal/pipeline"))
        >>> stream = content_stream.disk_cache(cache)
        >>> result = stream.materialize()  # Uses cache for unchanged items

    Serialization:
        Values must be JSON-serializable or provide custom serialize/deserialize
        functions. For complex types, implement the Cacheable protocol.

    Cache Behavior:
        - Cache hit: Return cached value, skip upstream computation
        - Cache miss: Compute value, store in cache
        - Version change: Recompute, update cache

    Related:
        - StreamCache: The underlying cache storage
        - bengal/cache/cacheable.py: Protocol for complex types
    """

    def __init__(
        self,
        upstream: Stream[T],
        cache: StreamCache,
        *,
        serialize_fn: Callable[[T], str] | None = None,
        deserialize_fn: Callable[[str], T] | None = None,
    ) -> None:
        """
        Initialize disk-cached stream.

        Args:
            upstream: Source stream to cache
            cache: StreamCache instance for storage
            serialize_fn: Custom serialization function (default: json.dumps)
            deserialize_fn: Custom deserialization function (default: json.loads)
        """
        super().__init__(f"{upstream.name}.disk_cached")
        self._upstream = upstream
        self._disk_cache = cache  # Renamed to avoid collision with parent's _cache
        self._serialize_fn = serialize_fn or (lambda v: json.dumps(v, default=str))
        self._deserialize_fn = deserialize_fn or json.loads

        # Disable parent's in-memory cache (we use disk cache instead)
        self._cache_enabled = False

        # Statistics
        self._hits = 0
        self._misses = 0

    def _produce(self) -> Iterator[StreamItem[T]]:
        """
        Produce items with disk caching.

        For each upstream item:
        1. Check cache for matching key+version
        2. If hit: yield cached value
        3. If miss: yield computed value, update cache
        """
        for item in self._upstream.iterate():
            # Try cache lookup
            cached_value = self._disk_cache.get(item.key, self._deserialize_fn)

            if cached_value is not None:
                # Cache hit
                self._hits += 1
                yield StreamItem(
                    key=item.key,
                    value=cached_value,
                    produced_at=item.produced_at,
                )
            else:
                # Cache miss - use upstream value and store
                self._misses += 1
                self._disk_cache.put(item.key, item.value, self._serialize_fn)
                yield item

    def get_cache_stats(self) -> dict[str, Any]:
        """Get caching statistics for this stream."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "total": total,
        }


def add_disk_cache_method() -> None:
    """
    Add disk_cache() method to Stream class.

    This is called at module import to extend Stream with caching support.
    """

    def disk_cache(
        self: Stream[T],
        cache: StreamCache,
        *,
        serialize_fn: Callable[[T], str] | None = None,
        deserialize_fn: Callable[[str], T] | None = None,
    ) -> DiskCachedStream[T]:
        """
        Add persistent disk caching to this stream.

        Args:
            cache: StreamCache instance for storage
            serialize_fn: Custom serialization function
            deserialize_fn: Custom deserialization function

        Returns:
            DiskCachedStream wrapping this stream

        Example:
            >>> cache = StreamCache(Path(".bengal/pipeline"))
            >>> cached_stream = stream.disk_cache(cache)
        """
        return DiskCachedStream(
            self,
            cache,
            serialize_fn=serialize_fn,
            deserialize_fn=deserialize_fn,
        )

    # Attach method to Stream class
    Stream.disk_cache = disk_cache  # type: ignore


# Extend Stream class with disk_cache method
add_disk_cache_method()
