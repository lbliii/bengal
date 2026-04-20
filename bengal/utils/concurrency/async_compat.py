"""
Async utilities using uvloop for Rust-accelerated event loop.

Provides utilities for running async code with uvloop, which offers
20-30% faster async I/O operations than stdlib asyncio.

Performance:
- HTTP requests: 20-30% faster
- File watching: 15-25% faster
- General async operations: 10-20% faster

Usage:
    >>> from bengal.utils.concurrency.async_compat import run_async
    >>>
    >>> async def main():
    ...     return await fetch_data()
    >>>
    >>> result = run_async(main())

Note:
uvloop is only available on Linux and macOS (not Windows).
Import is lazy - uvloop only loads when run_async() is actually called.

See Also:
- bengal/health/linkcheck/async_checker.py - Uses run_async for link checking
- bengal/content/sources/manager.py - Uses run_async for content fetching
- https://github.com/MagicStack/uvloop - uvloop documentation

"""

from __future__ import annotations

import asyncio
from functools import cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Coroutine


@cache
def _get_uvloop():
    """
    Lazily import uvloop on first use.

    Cached via ``functools.cache`` so the import attempt happens exactly
    once across all threads (avoids the ~200ms uvloop import overhead on
    every call, and avoids a check-then-act race under Python 3.14t
    free-threading).
    """
    try:
        import uvloop
    except ImportError:
        return None
    return uvloop


def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine with uvloop (if available).

    This is the recommended way to run async code in Bengal. It uses uvloop
    for 20-30% better performance on Linux/macOS when available.

    Falls back to standard asyncio on Windows or when uvloop is unavailable
    (e.g., Python 3.14t where uvloop is not yet compatible).

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine

    Example:
            >>> async def fetch_links():
            ...     async with httpx.AsyncClient() as client:
            ...         return await client.get("https://example.com")
            >>>
            >>> response = run_async(fetch_links())

    """
    uvloop = _get_uvloop()
    if uvloop is not None:
        return uvloop.run(coro)
    return asyncio.run(coro)


def install_uvloop() -> None:
    """
    Install uvloop as the global event loop policy.

    Call this once at application startup to make all subsequent
    asyncio.run() calls use uvloop automatically.

    Does nothing on Windows or when uvloop is unavailable
    (e.g., Python 3.14t where uvloop is not yet compatible).

    Example:
            >>> from bengal.utils.concurrency.async_compat import install_uvloop
            >>> install_uvloop()
            >>> # Now all asyncio.run() calls use uvloop (if available)

    """
    uvloop = _get_uvloop()
    if uvloop is not None:
        uvloop.install()


__all__ = [
    "install_uvloop",
    "run_async",
]
