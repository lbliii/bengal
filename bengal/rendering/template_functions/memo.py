"""
Build-scoped memoization for template functions.

Provides memoization for expensive template functions that return the same
result across all pages in a build. Results are cached per-build and
automatically cleared when the build completes.

Architecture:
    Uses BuildContext.get_cached() for build-scoped caching when available,
    falling back to thread-local cache when BuildContext is not available.

    ```
    @build_memoize("auto_nav")
    def get_auto_nav(site: SiteLike) -> list[dict]:
        # Expensive computation...
        return nav_items
    ```

Thread Safety:
    - BuildContext.get_cached() uses thread-safe locking
    - Thread-local fallback is inherently thread-safe
    - Safe for parallel rendering with free-threaded Python

Performance:
    Functions like get_auto_nav() are called once per page (~225 times for
    a 225-page site) but return identical results. Memoization reduces
    this to 1 computation per build.

RFC: rfc-template-function-memoization

"""

from __future__ import annotations

import functools
import hashlib
import threading
from collections.abc import Callable
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext

# Type variables for generic memoization
P = ParamSpec("P")
R = TypeVar("R")

# ContextVar for build context (set by rendering phase)
_build_context_var: ContextVar[BuildContext | None] = ContextVar("build_context", default=None)

# Thread-local fallback cache (when BuildContext not available)
_fallback_cache = threading.local()


def set_build_context(ctx: BuildContext | None) -> None:
    """Set the current build context for memoization.

    Called at the start of rendering to enable build-scoped caching.

    Args:
        ctx: BuildContext instance or None to clear
    """
    _build_context_var.set(ctx)


def get_build_context() -> BuildContext | None:
    """Get the current build context.

    Returns:
        BuildContext if set, None otherwise
    """
    return _build_context_var.get()


def clear_fallback_cache() -> None:
    """Clear the thread-local fallback cache.

    Called between builds when BuildContext is not available.
    """
    if hasattr(_fallback_cache, "cache"):
        _fallback_cache.cache.clear()


def _get_fallback_cache() -> dict[str, Any]:
    """Get or create the thread-local fallback cache."""
    if not hasattr(_fallback_cache, "cache"):
        _fallback_cache.cache = {}
    return _fallback_cache.cache


def _hash_args(*args: Any, **kwargs: Any) -> str:
    """Create a stable hash key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        16-character hex hash of arguments
    """
    # Simple approach: repr of args/kwargs
    # For complex objects, use id() as part of key
    parts = []
    for arg in args:
        if hasattr(arg, "__hash__") and arg.__hash__ is not None:
            try:
                parts.append(repr(arg))
            except Exception:
                parts.append(str(id(arg)))
        else:
            parts.append(str(id(arg)))

    for k, v in sorted(kwargs.items()):
        if hasattr(v, "__hash__") and v.__hash__ is not None:
            try:
                parts.append(f"{k}={v!r}")
            except Exception:
                parts.append(f"{k}={id(v)}")
        else:
            parts.append(f"{k}={id(v)}")

    key_str = "|".join(parts)
    return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def build_memoize(cache_key: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for build-scoped memoization.

    Caches function results per-build. The cache is automatically cleared
    when the build completes (via BuildContext lifecycle).

    Args:
        cache_key: Unique key prefix for this function's cache entries

    Returns:
        Decorator that adds memoization to a function

    Example:
        @build_memoize("auto_nav")
        def get_auto_nav(site: SiteLike) -> list[dict]:
            return expensive_computation()

    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Build full cache key from function name and args
            args_hash = _hash_args(*args, **kwargs)
            full_key = f"memo:{cache_key}:{args_hash}"

            # Try BuildContext cache first (preferred)
            build_ctx = get_build_context()
            if build_ctx is not None:
                return build_ctx.get_cached(full_key, lambda: func(*args, **kwargs))

            # Fallback to thread-local cache
            fallback = _get_fallback_cache()
            if full_key in fallback:
                return fallback[full_key]

            result = func(*args, **kwargs)
            fallback[full_key] = result
            return result

        # Mark as memoized for introspection
        wrapper._memoized = True  # type: ignore[attr-defined]
        wrapper._cache_key = cache_key  # type: ignore[attr-defined]

        return wrapper

    return decorator


def site_scoped_memoize(cache_key: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for site-scoped memoization (ignores arguments).

    Like build_memoize, but only uses the cache_key (ignores function arguments).
    Use for functions that take `site` but return the same result regardless.

    Args:
        cache_key: Unique key for this function's cache entry

    Returns:
        Decorator that adds site-scoped memoization

    Example:
        @site_scoped_memoize("auto_nav")
        def get_auto_nav(site: SiteLike) -> list[dict]:
            # Result is same for all pages in a build
            return expensive_site_wide_computation()

    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            full_key = f"memo:{cache_key}"

            # Try BuildContext cache first (preferred)
            build_ctx = get_build_context()
            if build_ctx is not None:
                return build_ctx.get_cached(full_key, lambda: func(*args, **kwargs))

            # Fallback to thread-local cache
            fallback = _get_fallback_cache()
            if full_key in fallback:
                return fallback[full_key]

            result = func(*args, **kwargs)
            fallback[full_key] = result
            return result

        wrapper._memoized = True  # type: ignore[attr-defined]
        wrapper._cache_key = cache_key  # type: ignore[attr-defined]
        wrapper._site_scoped = True  # type: ignore[attr-defined]

        return wrapper

    return decorator


# Register cache cleanup
try:
    from bengal.utils.cache_registry import InvalidationReason, register_cache

    register_cache(
        "template_function_memo",
        clear_fallback_cache,
        invalidate_on={
            InvalidationReason.BUILD_START,
            InvalidationReason.FULL_REBUILD,
            InvalidationReason.TEST_CLEANUP,
        },
    )
except ImportError:
    pass


__all__ = [
    "build_memoize",
    "clear_fallback_cache",
    "get_build_context",
    "set_build_context",
    "site_scoped_memoize",
]
