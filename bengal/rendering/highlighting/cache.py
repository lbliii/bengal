"""Site-wide cache for syntax-highlighted code blocks.

Uses rosettes.content_hash() as cache key. Thread-safe for parallel page
rendering. Per-build scope; cache is cleared between builds.

Sharded design: 16 shards with separate locks reduce contention under
parallel rendering. Workers hitting different shards proceed without blocking.
"""

from __future__ import annotations

import threading

_NUM_SHARDS = 16


def _shard_index(key: str) -> int:
    """Pick shard from key. Uses hash for even distribution."""
    return hash(key) % _NUM_SHARDS


class HighlightCache:
    """Site-wide cache for highlighted code blocks. Sharded for low lock contention."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._shards: list[tuple[dict[str, str], threading.Lock]] = [
            ({}, threading.Lock()) for _ in range(_NUM_SHARDS)
        ]

    def get(self, key: str) -> str | None:
        """Return cached HTML if present. Thread-safe for parallel rendering."""
        if not self._enabled:
            return None
        cache, lock = self._shards[_shard_index(key)]
        with lock:
            return cache.get(key)

    def set(self, key: str, html: str) -> None:
        """Store highlighted HTML. Uses per-shard lock for thread-safe writes."""
        if not self._enabled:
            return
        cache, lock = self._shards[_shard_index(key)]
        with lock:
            cache[key] = html
