"""Generic thread-local instance pool.

Provides a reusable pattern for thread-local instance pooling.
Eliminates duplication between ParserPool and RendererPool.

Thread Safety:
    Uses threading.local() for per-thread pool isolation.
    No locks needed - each thread has its own pool.

Usage:
    class MyPool(ThreadLocalPool[MyClass]):
        @classmethod
        def _create(cls, *args, **kwargs) -> MyClass:
            return MyClass(*args, **kwargs)

        @classmethod
        def _reinit(cls, instance: MyClass, *args, **kwargs) -> None:
            instance._reinit(*args, **kwargs)

"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from threading import local
from typing import Any, ClassVar

# Default pool size (configurable via subclass)
_DEFAULT_POOL_SIZE = 8


class ThreadLocalPool[T](ABC):
    """Abstract base class for thread-local instance pools.

    Provides the common pooling infrastructure:
    - Thread-local storage via threading.local()
    - _get_pool() to get/create pool for current thread
    - acquire() context manager for borrow/return semantics
    - clear() and size() utility methods

    Subclasses must implement:
    - _create(*args, **kwargs) -> T: Create a new instance
    - _reinit(instance, *args, **kwargs): Reset an existing instance

    Type Parameters:
        T: The type of pooled instances

    Thread Safety:
        Each thread has its own pool. No locks needed.
    """

    _local: ClassVar[local]
    _max_pool_size: ClassVar[int]
    _env_var_name: ClassVar[str] = ""  # Override in subclass for custom env var

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with its own thread-local storage."""
        super().__init_subclass__(**kwargs)
        cls._local = local()

        # Get pool size from environment variable if specified
        if cls._env_var_name:
            cls._max_pool_size = int(os.environ.get(cls._env_var_name, _DEFAULT_POOL_SIZE))
        else:
            cls._max_pool_size = _DEFAULT_POOL_SIZE

    @classmethod
    def _get_pool(cls) -> deque[T]:
        """Get or create thread-local pool."""
        if not hasattr(cls._local, "pool"):
            cls._local.pool: deque[T] = deque(maxlen=cls._max_pool_size)
        return cls._local.pool

    @classmethod
    @abstractmethod
    def _create(cls, *args: Any, **kwargs: Any) -> T:
        """Create a new instance.

        Args:
            *args: Positional arguments for instance creation
            **kwargs: Keyword arguments for instance creation

        Returns:
            New instance of type T
        """
        ...

    @classmethod
    @abstractmethod
    def _reinit(cls, instance: T, *args: Any, **kwargs: Any) -> None:
        """Reinitialize an existing instance for reuse.

        Args:
            instance: Instance to reinitialize
            *args: Positional arguments for reinitialization
            **kwargs: Keyword arguments for reinitialization
        """
        ...

    @classmethod
    @contextmanager
    def acquire(cls, *args: Any, **kwargs: Any) -> Iterator[T]:
        """Acquire an instance from pool or create new one.

        Args:
            *args: Arguments passed to _create() or _reinit()
            **kwargs: Keyword arguments passed to _create() or _reinit()

        Yields:
            Instance ready for use

        Note:
            Instance is returned to pool on context exit if pool is not full.
        """
        pool = cls._get_pool()

        if pool:
            # Reuse existing instance from pool
            instance = pool.pop()
            cls._reinit(instance, *args, **kwargs)
        else:
            # Create new instance if pool is empty
            instance = cls._create(*args, **kwargs)

        try:
            yield instance
        finally:
            # Return to pool if not full
            if len(pool) < cls._max_pool_size:
                pool.append(instance)

    @classmethod
    def clear(cls) -> None:
        """Clear the pool for current thread.

        Useful for testing or memory cleanup.
        """
        if hasattr(cls._local, "pool"):
            cls._local.pool.clear()

    @classmethod
    def size(cls) -> int:
        """Get current pool size for this thread."""
        if hasattr(cls._local, "pool"):
            return len(cls._local.pool)
        return 0
