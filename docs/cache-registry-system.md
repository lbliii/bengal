# Cache Registry System

## Problem

Bengal uses several module-level caches for performance optimization:
- `_global_context_cache`: Caches SiteContext wrappers keyed by `id(site)`
- `_parser_cache`: Thread-local cache for markdown parsers
- `_created_dirs`: Thread-safe set tracking created directories
- Theme discovery cache: LRU cache for installed themes

These caches can cause memory leaks in tests when Site objects are created and destroyed frequently, as the cache entries persist even after objects are garbage collected.

## Solution

A centralized **Cache Registry** system where caches register themselves for automatic cleanup:

1. **Cache Registry** (`bengal/utils/cache_registry.py`): Central registry of cache cleanup functions
2. **Automatic Registration**: Caches register themselves at module import time
3. **Centralized Cleanup**: Single `clear_all_caches()` function clears all registered caches

## Usage

### Registering a New Cache

When creating a new module-level cache, register it for automatic cleanup:

```python
from bengal.utils.cache_registry import register_cache

_my_cache: dict[str, Any] = {}

def _clear_my_cache() -> None:
    """Clear my cache."""
    _my_cache.clear()

# Register at module import time
try:
    register_cache("my_cache", _clear_my_cache)
except ImportError:
    # Cache registry not available (shouldn't happen in normal usage)
    pass
```

### Using Weak References for Object-Keyed Caches

For caches keyed by object IDs (like `id(site)`), consider using `WeakKeyDictionary` to automatically clean up when objects are garbage collected:

```python
from weakref import WeakKeyDictionary

# Instead of: dict[int, Any] = {}
_my_cache: WeakKeyDictionary[Site, Any] = WeakKeyDictionary()
# No registration needed - automatically cleaned up when Site objects are GC'd
```

**Note**: The current `_global_context_cache` uses `id(site)` as keys, which prevents using WeakKeyDictionary directly. Consider refactoring to use Site objects directly as keys if possible.

### Clearing Caches

In tests, caches are automatically cleared via the `reset_bengal_state` fixture:

```python
# In tests/conftest.py
from bengal.utils.cache_registry import clear_all_caches

clear_all_caches()  # Clears all registered caches
```

In production code, clear caches between builds:

```python
from bengal.utils.cache_registry import clear_all_caches

# Between builds or when configuration changes
clear_all_caches()
```

## Currently Registered Caches

- `global_context_cache`: Site context wrappers cache
- `parser_cache`: Thread-local markdown parser cache
- `created_dirs_cache`: Thread-safe directory tracking cache
- `theme_cache`: Theme discovery LRU cache

## Benefits

1. **Prevents Memory Leaks**: All caches are automatically cleared in tests
2. **Maintainable**: New caches just need to register themselves
3. **Discoverable**: `list_registered_caches()` shows all registered caches
4. **Fail-Safe**: Cache cleanup failures don't break the entire cleanup process

## Future Improvements

1. **Weak References**: Refactor `_global_context_cache` to use `WeakKeyDictionary` with Site objects as keys
2. **Cache Size Limits**: Add size limits to prevent unbounded growth (like `_version_page_index_cache` does)
3. **Metrics**: Add cache hit/miss metrics for performance monitoring
