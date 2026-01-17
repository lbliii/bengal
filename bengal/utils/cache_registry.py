"""
Centralized cache registry for cache lifecycle management.

Provides a registry pattern where caches can register themselves with metadata
for automatic cleanup, dependency tracking, and coordinated invalidation.
This prevents memory leaks in tests and ensures correct cache invalidation
order during builds.

Key Features:
- Reason-based invalidation: Caches declare which events should trigger them
- Dependency tracking: Caches can depend on other caches (cascade invalidation)
- Topological sorting: Ensures correct invalidation order
- Invalidation logging: Track what was invalidated and why

Usage:

```python
from bengal.utils.cache_registry import (
    register_cache,
    invalidate_for_reason,
    InvalidationReason,
)

# Register a cache with lifecycle metadata
register_cache(
    "nav_tree",
    NavTreeCache.invalidate,
    invalidate_on={InvalidationReason.CONFIG_CHANGED, InvalidationReason.STRUCTURAL_CHANGE},
    depends_on={"build_cache"},
)

# Invalidate all caches that should respond to a config change
invalidated = invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
logger.debug("caches_invalidated", caches=invalidated)
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
- bengal.core.nav_tree: Registers NavTreeCache

"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from graphlib import TopologicalSorter

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class InvalidationReason(Enum):
    """
    Why a cache was invalidated.
    
    Used to declare which events should trigger cache invalidation.
    Caches register which reasons they respond to, enabling coordinated
    invalidation without scattered manual calls.
        
    """

    CONFIG_CHANGED = auto()  # Site configuration changed
    STRUCTURAL_CHANGE = auto()  # Pages added/deleted/moved
    NAV_CHANGE = auto()  # Navigation-affecting metadata (title, weight, icon)
    TEMPLATE_CHANGE = auto()  # Template files modified
    FULL_REBUILD = auto()  # Full rebuild requested
    BUILD_START = auto()  # New build starting
    BUILD_END = auto()  # Build completed
    TEST_CLEANUP = auto()  # Test cleanup (clear_all_caches)


@dataclass
class CacheEntry:
    """
    Registered cache with metadata.
    
    Stores cache clear function along with lifecycle metadata for
    coordinated invalidation and dependency tracking.
    
    Attributes:
        name: Unique cache name (for debugging and dependency tracking)
        clear_fn: Callable that clears the cache (e.g., lambda: cache.clear())
        invalidate_on: Set of reasons that should trigger invalidation
        depends_on: Set of cache names this cache depends on
        
    """

    name: str
    clear_fn: Callable[[], None]
    invalidate_on: set[InvalidationReason] = field(
        default_factory=lambda: {InvalidationReason.FULL_REBUILD}
    )
    depends_on: set[str] = field(default_factory=set)


# Registry of cache entries with metadata
_registered_caches: dict[str, CacheEntry] = {}
_registry_lock = threading.Lock()

# Invalidation log for debugging (keeps last 100 entries)
_invalidation_log: list[tuple[str, InvalidationReason, float]] = []
_INVALIDATION_LOG_MAX = 100


def register_cache(
    name: str,
    clear_fn: Callable[[], None],
    invalidate_on: set[InvalidationReason] | None = None,
    depends_on: set[str] | None = None,
) -> None:
    """
    Register a cache with lifecycle metadata.
    
    Caches should register themselves at module import time (standard pattern).
    This ensures all caches are registered before any build operations.
    
    Args:
        name: Unique cache name (for debugging and dependency tracking)
        clear_fn: Callable that clears the cache (e.g., lambda: cache.clear())
        invalidate_on: Set of reasons that should trigger invalidation.
                       Defaults to {FULL_REBUILD} if not specified.
        depends_on: Set of cache names this cache depends on (for cascade invalidation).
                    Dependencies must already be registered.
    
    Raises:
        ValueError: If dependency cycle detected or dependencies don't exist
    
    Example:
        register_cache(
            "nav_tree",
            NavTreeCache.invalidate,
            invalidate_on={InvalidationReason.CONFIG_CHANGED, InvalidationReason.STRUCTURAL_CHANGE},
            depends_on={"build_cache"},
        )
    
    Note:
        If you want the cache cleared on test cleanup, include TEST_CLEANUP
        in invalidate_on, or just use FULL_REBUILD which is the default.
        
    """
    effective_invalidate_on = (
        invalidate_on if invalidate_on is not None else {InvalidationReason.FULL_REBUILD}
    )
    effective_depends_on = depends_on if depends_on is not None else set()

    with _registry_lock:
        # Validate dependencies exist (if not empty)
        if effective_depends_on:
            missing = effective_depends_on - _registered_caches.keys()
            if missing:
                # Log warning but allow registration (dependencies may be registered later)
                # This allows for flexible registration order
                logger.debug(
                    "cache_registration_missing_deps",
                    cache=name,
                    missing_deps=list(missing),
                )

        # Check for cycles (defensive - shouldn't happen with proper design)
        _validate_no_cycles(name, effective_depends_on)

        _registered_caches[name] = CacheEntry(
            name=name,
            clear_fn=clear_fn,
            invalidate_on=effective_invalidate_on,
            depends_on=effective_depends_on,
        )


def _validate_no_cycles(new_cache: str, new_deps: set[str]) -> None:
    """
    Validate that adding new_cache with new_deps doesn't create a cycle.
    
    Uses DFS to detect cycles in dependency graph.
    
    Args:
        new_cache: Name of cache being registered
        new_deps: Dependencies of the new cache
    
    Raises:
        ValueError: If adding this cache would create a dependency cycle
        
    """
    # Build dependency graph including new cache
    graph: dict[str, set[str]] = {}
    for name, entry in _registered_caches.items():
        graph[name] = entry.depends_on.copy()
    graph[new_cache] = new_deps.copy()

    # Check for cycles using DFS
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for dep in graph.get(node, set()):
            if dep not in visited:
                if has_cycle(dep):
                    return True
            elif dep in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited and has_cycle(node):
            raise ValueError(
                f"Cache dependency cycle detected involving '{new_cache}'. Dependencies: {new_deps}"
            )


def _topological_sort(cache_names: set[str]) -> list[str]:
    """
    Topologically sort cache names by dependency order.
    
    Uses graphlib.TopologicalSorter (Python 3.9+) for reliable ordering.
    Ensures dependencies are invalidated before dependents.
    
    Args:
        cache_names: Set of cache names to sort
    
    Returns:
        List of cache names in dependency order (dependencies first)
        
    """
    # Handle empty or single-item case
    if len(cache_names) <= 1:
        return list(cache_names)

    # Build dependency graph for selected caches
    # TopologicalSorter expects {node: set(predecessors)}
    graph: dict[str, set[str]] = {}
    for name in cache_names:
        if name in _registered_caches:
            # Only include dependencies that are also in cache_names
            entry = _registered_caches[name]
            graph[name] = entry.depends_on & cache_names
        else:
            graph[name] = set()

    # Use TopologicalSorter for reliable ordering
    try:
        sorter = TopologicalSorter(graph)
        return list(sorter.static_order())
    except ValueError as e:
        # Shouldn't happen if cycle detection works, but defensive
        logger.warning(
            "topological_sort_failed",
            error=str(e),
            cache_names=list(cache_names),
        )
        return list(cache_names)


def invalidate_for_reason(reason: InvalidationReason) -> list[str]:
    """
    Invalidate all caches that should be cleared for this reason.
    
    This is the primary API for triggering cache invalidation. Instead of
    calling individual cache invalidation functions, call this with the
    appropriate reason and let caches self-select.
    
    Args:
        reason: Why invalidation is occurring
    
    Returns:
        List of invalidated cache names (for logging)
    
    Thread-safe: Uses registry lock for consistency.
    
    Example:
        # When config changes:
        invalidated = invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
        logger.debug("caches_invalidated", reason="config_changed", caches=invalidated)
        
    """
    to_invalidate: set[str] = set()
    timestamp = time.time()

    with _registry_lock:
        # Find all caches that should be invalidated for this reason
        for name, entry in _registered_caches.items():
            if reason in entry.invalidate_on:
                to_invalidate.add(name)

        # Sort by dependency order
        sorted_caches = _topological_sort(to_invalidate)

        # Invalidate in order
        invalidated: list[str] = []
        for name in sorted_caches:
            if name in _registered_caches:
                try:
                    _registered_caches[name].clear_fn()
                    invalidated.append(name)
                    _log_invalidation(name, reason, timestamp)
                except Exception as e:
                    # Log but don't fail - one cache failure shouldn't break invalidation
                    logger.warning(
                        "cache_invalidation_failed",
                        cache=name,
                        error=str(e),
                    )

    return invalidated


def invalidate_with_dependents(cache_name: str, reason: InvalidationReason) -> list[str]:
    """
    Invalidate a specific cache and all caches that depend on it.
    
    Uses topological sort to ensure correct order (dependencies before dependents).
    
    Args:
        cache_name: Name of cache to invalidate
        reason: Reason for invalidation (for logging)
    
    Returns:
        List of invalidated cache names in dependency order
    
    Raises:
        KeyError: If cache_name not registered
    
    Example:
        # When nav tree changes, invalidate it and dependents:
        invalidated = invalidate_with_dependents("nav_tree", InvalidationReason.STRUCTURAL_CHANGE)
        
    """
    timestamp = time.time()

    with _registry_lock:
        if cache_name not in _registered_caches:
            raise KeyError(f"Cache '{cache_name}' not registered")

        # Find all dependents (transitive closure)
        to_invalidate = {cache_name}
        changed = True
        while changed:
            changed = False
            for name, entry in _registered_caches.items():
                if entry.depends_on & to_invalidate and name not in to_invalidate:
                    to_invalidate.add(name)
                    changed = True

        # Invalidate in dependency order
        sorted_caches = _topological_sort(to_invalidate)
        invalidated: list[str] = []

        for name in sorted_caches:
            if name in _registered_caches:
                try:
                    _registered_caches[name].clear_fn()
                    invalidated.append(name)
                    _log_invalidation(name, reason, timestamp)
                except Exception as e:
                    logger.warning(
                        "cache_invalidation_failed",
                        cache=name,
                        error=str(e),
                    )

    return invalidated


def _log_invalidation(name: str, reason: InvalidationReason, timestamp: float) -> None:
    """Log an invalidation event (internal helper)."""
    global _invalidation_log
    _invalidation_log.append((name, reason, timestamp))

    # Trim to max size
    if len(_invalidation_log) > _INVALIDATION_LOG_MAX:
        _invalidation_log = _invalidation_log[-_INVALIDATION_LOG_MAX:]


def unregister_cache(name: str) -> None:
    """
    Unregister a cache (rarely needed).
    
    Args:
        name: Name of cache to unregister
        
    """
    with _registry_lock:
        _registered_caches.pop(name, None)


def clear_all_caches() -> None:
    """
    Clear all registered caches.
    
    This is the main function to call in test fixtures or between builds
    to prevent memory leaks. Equivalent to invalidate_for_reason(FULL_REBUILD)
    but clears ALL caches regardless of their invalidate_on settings.
    
    Thread Safety:
        Thread-safe - clears all caches under lock.
        
    """
    with _registry_lock:
        for name, entry in _registered_caches.items():
            try:
                entry.clear_fn()
            except Exception as e:
                # Log but don't fail - one cache failure shouldn't break cleanup
                logger.warning(f"Failed to clear cache '{name}': {e}")


def list_registered_caches() -> list[str]:
    """
    List all registered cache names (for debugging).
    
    Returns:
        List of cache names
        
    """
    with _registry_lock:
        return list(_registered_caches.keys())


def get_cache_info(name: str) -> dict | None:
    """
    Get information about a registered cache.
    
    Args:
        name: Cache name
    
    Returns:
        Dict with cache info or None if not registered
        
    """
    with _registry_lock:
        if name not in _registered_caches:
            return None
        entry = _registered_caches[name]
        return {
            "name": entry.name,
            "invalidate_on": [r.name for r in entry.invalidate_on],
            "depends_on": list(entry.depends_on),
        }


def get_invalidation_log() -> list[tuple[str, str, float]]:
    """
    Get log of recent invalidations (for debugging).
    
    Returns:
        List of (cache_name, reason_name, timestamp) tuples
        
    """
    with _registry_lock:
        return [(name, reason.name, ts) for name, reason, ts in _invalidation_log]


def clear_invalidation_log() -> None:
    """Clear invalidation log."""
    global _invalidation_log
    with _registry_lock:
        _invalidation_log = []
