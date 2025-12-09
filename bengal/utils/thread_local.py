"""
Thread-local caching utilities.

Provides a generic thread-local cache for expensive-to-create objects
like parsers, database connections, or pipeline instances.

Example:

```python
from bengal.utils.thread_local import ThreadLocalCache

# Create a cache for markdown parsers
parser_cache = ThreadLocalCache(
    factory=lambda: create_markdown_parser(),
    name="markdown_parser",
)

# Get or create parser for current thread
parser = parser_cache.get()

# Get parser with a specific key (e.g., engine type)
mistune_parser = parser_cache.get("mistune")
```

Related Modules:
    - bengal.rendering.pipeline.thread_local: Uses for parser caching
    - bengal.orchestration.render: Uses for pipeline caching
    - bengal.core.site.core: Uses for rendering context caching
"""

from __future__ import annotations

import inspect
import threading
from collections.abc import Callable
from typing import Generic, TypeVar, cast

T = TypeVar("T")


class ThreadLocalCache(Generic[T]):
    """
    Generic thread-local cache with factory pattern.

    Creates one instance per thread per key, reusing it for subsequent calls.
    Useful for expensive objects like parsers that are not thread-safe but
    can be reused within a single thread.

    Thread Safety:
        Each thread gets its own instance(s), no locking required for access.
        The factory function should be thread-safe if it accesses shared state.

    Performance:
        - First access per thread/key: factory() cost (e.g., 10ms for parser)
        - Subsequent access: ~1µs (attribute lookup)

    Example:
        >>> cache = ThreadLocalCache(lambda: ExpensiveParser(), name="parser")
        >>> parser = cache.get()  # Creates parser for this thread
        >>> parser = cache.get()  # Reuses same parser
    """

    def __init__(
        self,
        factory: Callable[[], T] | Callable[[str], T],
        name: str = "default",
    ):
        """
        Initialize thread-local cache.

        Args:
            factory: Callable that creates new instances.
                     Can be no-arg or accept a key string.
            name: Name for this cache (used in attribute names)
        """
        self._local = threading.local()
        self._factory = factory
        self._name = name
        self._factory_accepts_key = self._check_factory_signature()

    def _check_factory_signature(self) -> bool:
        """Check if factory accepts a key argument."""
        sig = inspect.signature(self._factory)
        params = list(sig.parameters.values())
        return len(params) > 0

    def get(self, key: str | None = None) -> T:
        """
        Get or create cached instance for current thread.

        Args:
            key: Optional key for multiple instances per thread.
                 Use when caching different variants (e.g., parser engines).

        Returns:
            Cached or newly created instance
        """
        cache_key = f"_cache_{self._name}_{key or 'default'}"

        if not hasattr(self._local, cache_key):
            if self._factory_accepts_key and key:
                instance = self._factory(key)  # type: ignore[call-arg]
            else:
                instance = self._factory()  # type: ignore[call-arg]
            setattr(self._local, cache_key, instance)

        return cast(T, getattr(self._local, cache_key))

    def clear(self, key: str | None = None) -> None:
        """
        Clear cached instance for current thread.

        Args:
            key: Specific key to clear, or None to clear default
        """
        cache_key = f"_cache_{self._name}_{key or 'default'}"
        if hasattr(self._local, cache_key):
            delattr(self._local, cache_key)

    def clear_all(self) -> None:
        """Clear all cached instances for current thread."""
        # Find all cache keys for this cache name
        to_delete = [attr for attr in dir(self._local) if attr.startswith(f"_cache_{self._name}_")]
        for attr in to_delete:
            delattr(self._local, attr)


class ThreadSafeSet:
    """
    Thread-safe set for tracking created resources (e.g., directories).

    Example:
        >>> created_dirs = ThreadSafeSet()
        >>> if created_dirs.add_if_new("/path/to/dir"):
        ...     os.makedirs("/path/to/dir")  # Only if not already created
    """

    def __init__(self) -> None:
        self._set: set[str] = set()
        self._lock = threading.Lock()

    def add_if_new(self, item: str) -> bool:
        """
        Add item if not present, return True if added.

        Thread-safe check-and-add operation.

        Args:
            item: Item to add

        Returns:
            True if item was new (added), False if already present
        """
        with self._lock:
            if item in self._set:
                return False
            self._set.add(item)
            return True

    def __contains__(self, item: str) -> bool:
        with self._lock:
            return item in self._set

    def clear(self) -> None:
        with self._lock:
            self._set.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._set)
