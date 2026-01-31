"""
Thread-safe cache mixin.

Provides a common pattern for caches that need thread safety:
- RLock for reentrant locking
- Context manager for locked operations

Usage:
    class MyCache(ThreadSafeCacheMixin):
        def __init__(self):
            super().__init__()
            self.data: dict[str, str] = {}

        def get(self, key: str) -> str | None:
            with self._lock:
                return self.data.get(key)

        def set(self, key: str, value: str) -> None:
            with self._lock:
                self.data[key] = value

"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager


class ThreadSafeCacheMixin:
    """
    Mixin providing thread-safe operations with RLock.

    RLock (reentrant lock) allows the same thread to acquire the lock
    multiple times, which is useful for nested method calls.

    Usage:
        class MyCache(ThreadSafeCacheMixin):
            def __init__(self):
                super().__init__()  # Initializes _lock
                self.data = {}

            def update(self, key: str, value: str) -> None:
                with self._lock:
                    self.data[key] = value

    Attributes:
        _lock: threading.RLock instance

    """

    _lock: threading.RLock

    def __init__(self) -> None:
        """Initialize the RLock."""
        self._lock = threading.RLock()

    @contextmanager
    def locked(self) -> Iterator[None]:
        """
        Context manager for explicit locked sections.

        Convenience method for when you want to be explicit about locking.

        Example:
            with cache.locked():
                # Multiple operations atomically
                cache.data[key1] = value1
                cache.data[key2] = value2
        """
        with self._lock:
            yield

    def acquire_lock(self, blocking: bool = True, timeout: float = -1) -> bool:
        """
        Acquire the lock (low-level API).

        Most code should use `with self._lock:` instead.

        Args:
            blocking: If True, block until lock acquired. If False, return immediately.
            timeout: Timeout in seconds (-1 = infinite)

        Returns:
            True if lock acquired, False if timeout/non-blocking failed

        """
        return self._lock.acquire(blocking=blocking, timeout=timeout)

    def release_lock(self) -> None:
        """
        Release the lock (low-level API).

        Most code should use `with self._lock:` instead.
        """
        self._lock.release()
