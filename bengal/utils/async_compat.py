"""
Async utilities using uvloop for Rust-accelerated event loop.

Provides utilities for running async code with uvloop, which offers
20-30% faster async I/O operations than stdlib asyncio.

Performance:
    - HTTP requests: 20-30% faster
    - File watching: 15-25% faster
    - General async operations: 10-20% faster

Usage:
    >>> from bengal.utils.async_compat import run_async
    >>>
    >>> async def main():
    ...     return await fetch_data()
    >>>
    >>> result = run_async(main())

Note:
    uvloop is only available on Linux and macOS (not Windows).

See Also:
    - bengal/health/linkcheck/async_checker.py - Uses run_async for link checking
    - bengal/content_layer/manager.py - Uses run_async for content fetching
    - https://github.com/MagicStack/uvloop - uvloop documentation
"""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any

import uvloop


def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine with uvloop.

    This is the recommended way to run async code in Bengal. It uses uvloop
    for 20-30% better performance on Linux/macOS.

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
    return uvloop.run(coro)


def install_uvloop() -> None:
    """
    Install uvloop as the global event loop policy.

    Call this once at application startup to make all subsequent
    asyncio.run() calls use uvloop automatically.

    Example:
        >>> from bengal.utils.async_compat import install_uvloop
        >>> install_uvloop()
        >>> # Now all asyncio.run() calls use uvloop
    """
    uvloop.install()


__all__ = [
    "run_async",
    "install_uvloop",
]
