"""
Retry utilities with exponential backoff.

Provides both synchronous and asynchronous retry decorators and functions
with configurable backoff strategies and jitter.

Example:

```python
from bengal.utils.retry import retry_with_backoff, calculate_backoff

# Retry function with backoff
result = retry_with_backoff(
    fetch_data,
    retries=3,
    base_delay=0.5,
    exceptions=(ConnectionError, TimeoutError),
)

# Calculate backoff for custom retry loop
delay = calculate_backoff(attempt=2, base=0.5, max_delay=10.0)
```

Related Modules:
    - bengal.health.linkcheck.async_checker: Uses for HTTP retry
    - bengal.utils.file_lock: Uses for lock acquisition retry
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


def calculate_backoff(
    attempt: int,
    base: float = 0.5,
    max_delay: float = 10.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Uses formula: base * (2 ^ attempt) with ±25% jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Delay in seconds

    Examples:
        >>> calculate_backoff(0, base=0.5)  # ~0.5s
        >>> calculate_backoff(1, base=0.5)  # ~1.0s
        >>> calculate_backoff(2, base=0.5)  # ~2.0s
    """
    delay = base * (2**attempt)
    delay = min(delay, max_delay)

    if jitter:
        # ±25% jitter
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return float(max(0.1, delay))  # Minimum 100ms


def retry_with_backoff(
    func: Callable[[], T],
    retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    """
    Execute function with retry and exponential backoff.

    Args:
        func: Function to execute (no arguments)
        retries: Maximum retry attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay cap
        jitter: Add jitter to prevent thundering herd
        exceptions: Exception types to catch and retry
        on_retry: Optional callback(attempt, exception) on each retry

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries exhausted

    Example:
        >>> result = retry_with_backoff(
        ...     lambda: requests.get(url),
        ...     retries=3,
        ...     exceptions=(ConnectionError,),
        ... )
    """
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            return func()
        except exceptions as e:
            last_error = e

            if attempt < retries:
                delay = calculate_backoff(attempt, base_delay, max_delay, jitter)

                if on_retry:
                    on_retry(attempt, e)

                time.sleep(delay)
            else:
                raise

    # Should never reach here, but satisfies type checker
    raise last_error  # type: ignore[misc]


async def async_retry_with_backoff(
    coro_func: Callable[[], Awaitable[T]],
    retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    """
    Execute async function with retry and exponential backoff.

    Args:
        coro_func: Async function to execute (no arguments, returns awaitable)
        retries: Maximum retry attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay cap
        jitter: Add jitter to prevent thundering herd
        exceptions: Exception types to catch and retry
        on_retry: Optional callback(attempt, exception) on each retry

    Returns:
        Result of successful coroutine

    Raises:
        Last exception if all retries exhausted

    Example:
        >>> result = await async_retry_with_backoff(
        ...     lambda: client.get(url),
        ...     retries=3,
        ...     exceptions=(httpx.TimeoutException,),
        ... )
    """
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            return await coro_func()
        except exceptions as e:
            last_error = e

            if attempt < retries:
                delay = calculate_backoff(attempt, base_delay, max_delay, jitter)

                if on_retry:
                    on_retry(attempt, e)

                await asyncio.sleep(delay)
            else:
                raise

    raise last_error  # type: ignore[misc]
