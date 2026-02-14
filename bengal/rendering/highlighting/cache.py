"""Site-wide cache for syntax-highlighted code blocks.

Uses rosettes.content_hash() as cache key. Thread-safe for parallel page
rendering. Per-build scope; cache is cleared between builds.
"""

from __future__ import annotations

import threading


class HighlightCache:
    """Site-wide cache for highlighted code blocks. Thread-safe for parallel page rendering."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        """Return cached HTML if present. Thread-safe for parallel rendering."""
        if not self._enabled:
            return None
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, html: str) -> None:
        """Store highlighted HTML. Uses lock for thread-safe writes."""
        if not self._enabled:
            return
        with self._lock:
            self._cache[key] = html
