"""
Async parallel fetching utilities.

Provides a unified pattern for fetching items in parallel with:
- Semaphore-based concurrency limiting
- Automatic retry with exponential backoff
- Streaming results as they complete
- Error tracking and logging
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TypeVar

from bengal.errors import BengalContentError, ErrorCode, record_error
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


async def fetch_parallel[T, R](
    items: list[T],
    fetch_fn: Callable[[T], Awaitable[R | None]],
    *,
    max_concurrent: int = 10,
    max_retries: int = 3,
    retry_backoff_base: float = 1.0,
    retry_on_status: tuple[int, ...] = (429, 403),
    item_name: str = "item",
) -> AsyncIterator[R]:
    """
    Fetch items in parallel with concurrency limiting and retry logic.

    Streams results as they complete (order is non-deterministic). Failed
    items are logged and counted but don't stop processing of other items.

    Args:
        items: List of items to fetch
        fetch_fn: Async function that fetches a single item. Should return
            the result or None. May raise exceptions.
        max_concurrent: Maximum concurrent requests (default: 10)
        max_retries: Maximum retry attempts for rate-limited requests
        retry_backoff_base: Base delay for exponential backoff (seconds)
        retry_on_status: HTTP status codes that trigger retry. Only applies
            if fetch_fn raises aiohttp.ClientResponseError.
        item_name: Name for logging (e.g., "file", "page")

    Yields:
        Successfully fetched results (non-None values from fetch_fn)

    Example:
        >>> async def fetch_file(path: str) -> ContentEntry | None:
        ...     # fetch logic here
        ...     return entry
        ...
        >>> async for entry in fetch_parallel(
        ...     paths,
        ...     fetch_file,
        ...     max_concurrent=5,
        ...     item_name="file",
        ... ):
        ...     process(entry)

    """
    if not items:
        return

    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_retry(item: T) -> R | None:
        """Fetch item with semaphore and retry on rate limit."""
        async with semaphore:
            for attempt in range(max_retries):
                try:
                    return await fetch_fn(item)
                except Exception as e:
                    # Check if this is a retryable HTTP error
                    status = getattr(e, "status", None)
                    if status in retry_on_status and attempt < max_retries - 1:
                        delay = retry_backoff_base * (2**attempt)
                        logger.warning(
                            f"Rate limited (HTTP {status}), retrying in {delay}s: {item}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
            return None  # All retries exhausted

    # Create tasks for all items
    tasks = [fetch_with_retry(item) for item in items]

    # Track failures for summary logging
    failed_count = 0

    # Stream results as they complete (order not guaranteed)
    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            if result is not None:
                yield result
        except Exception as e:
            failed_count += 1
            error = BengalContentError(
                f"Failed to fetch {item_name}: {e}",
                code=ErrorCode.N016,
                suggestion=f"Check {item_name} exists and is accessible",
                original_error=e,
            )
            record_error(error)
            logger.error(f"Failed to fetch {item_name}: {e}")

    if failed_count > 0:
        logger.warning(f"Failed to fetch {failed_count}/{len(items)} {item_name}s")
