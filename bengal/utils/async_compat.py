"""
Async compatibility layer with uvloop acceleration.

Provides utilities for running async code with uvloop (Rust-based event loop,
20-30% faster) when available on Linux/macOS, with automatic fallback to
stdlib asyncio on Windows or when uvloop is unavailable.

Performance:
    uvloop provides significant speedups for async I/O operations:
    - HTTP requests: 20-30% faster
    - File watching: 15-25% faster
    - General async operations: 10-20% faster

Usage:
    >>> from bengal.utils.async_compat import run_async
    >>>
    >>> async def main():
    ...     return await fetch_data()
    >>>
    >>> result = run_async(main())  # Uses uvloop if available

    Or for explicit event loop policy:
    >>> from bengal.utils.async_compat import install_uvloop
    >>> install_uvloop()  # Install globally for all asyncio.run() calls

API:
    - run_async(coro): Run coroutine with uvloop if available
    - install_uvloop(): Install uvloop as the global event loop policy
    - UVLOOP_AVAILABLE: Boolean indicating uvloop availability

Note:
    uvloop is only available on Linux and macOS. On Windows, these functions
    gracefully fall back to stdlib asyncio.

See Also:
    - bengal/health/linkcheck/async_checker.py - Uses run_async for link checking
    - bengal/content_layer/manager.py - Uses run_async for content fetching
    - https://github.com/MagicStack/uvloop - uvloop documentation
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Coroutine, TypeVar

# Type variable for coroutine return type
T = TypeVar("T")

# Try to import uvloop for Rust-accelerated event loop
# Only available on Linux and macOS
UVLOOP_AVAILABLE = False
if sys.platform != "win32":
    try:
        import uvloop

        UVLOOP_AVAILABLE = True
    except ImportError:
        uvloop = None  # type: ignore[assignment]


def install_uvloop() -> bool:
    """
    Install uvloop as the global event loop policy.

    Call this once at application startup to make all subsequent
    asyncio.run() calls use uvloop automatically.

    Returns:
        True if uvloop was installed, False if unavailable

    Example:
        >>> from bengal.utils.async_compat import install_uvloop
        >>> install_uvloop()
        True
        >>> # Now all asyncio.run() calls use uvloop
        >>> asyncio.run(some_coroutine())
    """
    if UVLOOP_AVAILABLE:
        uvloop.install()
        return True
    return False


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine with uvloop if available.

    This is the recommended way to run async code in Bengal. It automatically
    uses uvloop on Linux/macOS for 20-30% better performance, falling back
    to stdlib asyncio on Windows or when uvloop is unavailable.

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

    Performance:
        On Linux/macOS with uvloop:
        - HTTP requests: ~25% faster
        - Concurrent operations: ~20% more throughput
    """
    if UVLOOP_AVAILABLE:
        # Use uvloop's run function for optimal performance
        return uvloop.run(coro)
    else:
        # Fall back to stdlib asyncio
        return asyncio.run(coro)


def get_event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """
    Get the appropriate event loop policy.

    Returns uvloop policy if available, otherwise default asyncio policy.

    Returns:
        Event loop policy

    Example:
        >>> policy = get_event_loop_policy()
        >>> asyncio.set_event_loop_policy(policy)
    """
    if UVLOOP_AVAILABLE:
        return uvloop.EventLoopPolicy()
    else:
        return asyncio.DefaultEventLoopPolicy()


__all__ = [
    "run_async",
    "install_uvloop",
    "get_event_loop_policy",
    "UVLOOP_AVAILABLE",
]

