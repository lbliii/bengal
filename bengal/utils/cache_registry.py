"""
Centralized cache registry for test cleanup and memory leak prevention.

Provides a registry pattern where caches can register themselves for automatic
cleanup. This prevents memory leaks in tests and long-running processes.

Usage:

```python
from bengal.utils.cache_registry import register_cache, clear_all_caches

# Register a cache with a cleanup function
_my_cache: dict[str, Any] = {}
register_cache("my_cache", lambda: _my_cache.clear())

# In tests, clear all registered caches
clear_all_caches()
```

For caches keyed by object IDs (like Site objects), use WeakKeyDictionary
instead of regular dict to prevent memory leaks:

```python
from weakref import WeakKeyDictionary

_my_cache: WeakKeyDictionary[Site, Any] = WeakKeyDictionary()
# No registration needed - automatically cleaned up when objects are GC'd
```

Related Modules:
    - bengal.tests.conftest: Uses clear_all_caches() in test fixtures
    - bengal.rendering.context: Registers global context cache
    - bengal.rendering.pipeline.thread_local: Registers parser cache
"""

from __future__ import annotations

import threading
from collections.abc import Callable

# Registry of cache cleanup functions
_cache_registry: dict[str, Callable[[], None]] = {}
_registry_lock = threading.Lock()


def register_cache(name: str, cleanup_func: Callable[[], None]) -> None:
    """
    Register a cache for centralized cleanup.

    Args:
        name: Unique name for the cache (for debugging)
        cleanup_func: Callable that clears the cache (e.g., lambda: cache.clear())

    Thread Safety:
        Thread-safe registration and cleanup.
    """
    with _registry_lock:
        _cache_registry[name] = cleanup_func


def unregister_cache(name: str) -> None:
    """
    Unregister a cache (rarely needed).

    Args:
        name: Name of cache to unregister
    """
    with _registry_lock:
        _cache_registry.pop(name, None)


def clear_all_caches() -> None:
    """
    Clear all registered caches.

    This is the main function to call in test fixtures or between builds
    to prevent memory leaks. All registered caches will be cleared.

    Thread Safety:
        Thread-safe - clears all caches under lock.
    """
    with _registry_lock:
        for name, cleanup_func in _cache_registry.items():
            try:
                cleanup_func()
            except Exception as e:
                # Log but don't fail - one cache failure shouldn't break cleanup
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to clear cache '{name}': {e}")


def list_registered_caches() -> list[str]:
    """
    List all registered cache names (for debugging).

    Returns:
        List of cache names
    """
    with _registry_lock:
        return list(_cache_registry.keys())
