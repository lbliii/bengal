"""
Concurrent lock utilities for preventing duplicate work in parallel builds.

This module provides the PerKeyLockManager pattern for serializing access
to resources by key while allowing parallel access to different keys.

Problem Solved:
    When multiple threads need the same resource simultaneously (e.g., compiling
    the same template, building the same NavTree), without per-key locking:
    - All threads see "cache miss"
    - All threads start expensive work
    - All threads write to cache (race condition)
    - Result: Wasted CPU + file system contention

Solution:
    Per-key locks serialize work for a SPECIFIC resource while allowing
    parallel work on DIFFERENT resources.

Example:
    >>> from bengal.utils.concurrent_locks import PerKeyLockManager
    >>>
    >>> _build_locks = PerKeyLockManager()
    >>>
    >>> def get_or_build(key: str, cache: dict) -> Result:
    ...     # Quick cache check (no lock)
    ...     if key in cache:
    ...         return cache[key]
    ...
    ...     # Serialize builds for SAME key (different keys build in parallel)
    ...     with _build_locks.get_lock(key):
    ...         # Double-check: another thread may have built while we waited
    ...         if key in cache:
    ...             return cache[key]
    ...         result = expensive_build(key)
    ...         cache[key] = result
    ...         return result

Design Decisions:
    - Uses RLock (reentrant) to prevent deadlock if nested acquisition occurs
    - No automatic eviction — lock objects are tiny (~100 bytes each)
    - Explicit clear() for session boundaries (call between builds)
    - Thread-safe lock dictionary access via meta-lock

Related Modules:
    - bengal/rendering/engines/jinja.py: Template compilation uses this pattern
    - bengal/core/nav_tree.py: NavTreeCache uses PerKeyLockManager
    - bengal/rendering/template_functions/navigation/scaffold.py: Uses PerKeyLockManager

See Also:
    - plan/drafted/rfc-concurrent-compilation-locks.md: Design rationale
"""

from __future__ import annotations

import threading
from collections.abc import Hashable


class PerKeyLockManager:
    """
    Thread-safe manager for per-key locks.

    Prevents duplicate work when multiple threads need the same resource.
    Each key gets its own lock, allowing parallel work on different keys.

    Attributes:
        _locks: Dictionary mapping keys to their RLock instances
        _meta_lock: Lock protecting the _locks dictionary itself

    Thread Safety:
        Fully thread-safe. The meta-lock ensures atomic get-or-create
        semantics for individual key locks.

    Memory:
        Lock objects are tiny (~100 bytes). Even 1000 unique keys only
        consume ~100KB. Use clear() between build sessions to reset.

    Example:
        >>> manager = PerKeyLockManager()
        >>> with manager.get_lock("base.html"):
        ...     template = compile_template("base.html")
    """

    __slots__ = ("_locks", "_meta_lock")

    def __init__(self) -> None:
        """Initialize lock manager with empty lock dictionary."""
        self._locks: dict[Hashable, threading.RLock] = {}
        self._meta_lock = threading.Lock()

    def get_lock(self, key: Hashable) -> threading.RLock:
        """
        Get or create a lock for the given key.

        Thread-safe: Creates lock if missing, returns existing if present.
        Uses RLock to allow safe nested acquisition within same thread.

        Args:
            key: Any hashable key (string, tuple, etc.)

        Returns:
            RLock instance for the given key

        Example:
            >>> manager = PerKeyLockManager()
            >>> lock = manager.get_lock("my-resource")
            >>> with lock:
            ...     # Critical section for "my-resource"
            ...     pass
        """
        with self._meta_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]

    def clear(self) -> None:
        """
        Clear all locks.

        Call this between build sessions to prevent unbounded growth.
        Safe to call when no threads are actively using locks.

        Warning:
            Do NOT call while threads may be waiting on locks.
            This should only be called at session boundaries (e.g., after
            a build completes, before starting a new build).
        """
        with self._meta_lock:
            self._locks.clear()

    def __len__(self) -> int:
        """
        Return number of active locks.

        Useful for monitoring and debugging lock accumulation.
        """
        with self._meta_lock:
            return len(self._locks)

    def __repr__(self) -> str:
        """Return string representation showing lock count."""
        return f"PerKeyLockManager(locks={len(self)})"
