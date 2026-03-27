"""Managed ThreadPoolExecutor with safe shutdown and cancellation support.

Provides a context manager that handles KeyboardInterrupt, SystemExit,
and interpreter shutdown correctly — cancelling pending futures on interrupt
and waiting gracefully on normal exit.

Also provides CancellationToken for cooperative cancellation of long-running
parallel work, with bounded waits on future.result().

Example:
    >>> from bengal.utils.concurrency.executor import managed_executor, CancellationToken
    >>> token = CancellationToken(timeout=30.0)
    >>> with managed_executor(4) as executor:
    ...     futures = {executor.submit(render, page): page for page in pages}
    ...     for future in as_completed(futures):
    ...         result = token.result(future)  # bounded wait

"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from collections.abc import Generator
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import contextmanager

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def _is_shutdown_error(e: Exception) -> bool:
    """Check if exception is due to interpreter shutdown."""
    return "interpreter shutdown" in str(e)


@contextmanager
def managed_executor(
    max_workers: int,
    *,
    thread_name_prefix: str = "",
) -> Generator[concurrent.futures.ThreadPoolExecutor]:
    """Context manager that shuts down a ThreadPoolExecutor correctly on error.

    On normal exit or RuntimeError from interpreter shutdown, shuts down
    gracefully.  On KeyboardInterrupt/SystemExit, cancels pending futures
    and re-raises.

    Args:
        max_workers: Maximum number of worker threads.
        thread_name_prefix: Optional prefix for thread names.

    Yields:
        Configured ThreadPoolExecutor.
    """
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix=thread_name_prefix,
    )
    try:
        yield executor
    except KeyboardInterrupt, SystemExit:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    except RuntimeError as e:
        if _is_shutdown_error(e):
            logger.debug("executor_shutdown_detected")
            executor.shutdown(wait=False, cancel_futures=True)
            return
        executor.shutdown(wait=True)
        raise
    else:
        executor.shutdown(wait=True)


class CancellationToken:
    """Cooperative cancellation token for bounded parallel work.

    Create one per build, pass it through the pipeline. Workers and
    result-collection loops use it to enforce time limits.

    Thread-safe: can be checked from any thread, cancelled from any thread.

    Example:
        >>> token = CancellationToken(timeout=120.0)
        >>> # In result collection loop:
        >>> result = token.result(future)  # raises on timeout or cancel
        >>> # In worker (optional cooperative check):
        >>> if token.is_cancelled:
        ...     return  # stop early
    """

    __slots__ = ("_cancelled", "_deadline", "_event", "_timeout")

    def __init__(self, timeout: float = 300.0) -> None:
        """Initialize with a timeout in seconds from now.

        Args:
            timeout: Maximum seconds before cancellation. Default 300s (5 min).
        """
        self._timeout = timeout
        self._deadline = time.monotonic() + timeout
        self._cancelled = False
        self._event = threading.Event()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancelled or timed out."""
        return self._cancelled or time.monotonic() > self._deadline

    @property
    def remaining(self) -> float:
        """Seconds remaining before deadline. Returns 0.0 if expired."""
        if self._cancelled:
            return 0.0
        return max(0.0, self._deadline - time.monotonic())

    def cancel(self) -> None:
        """Cancel all work using this token."""
        self._cancelled = True
        self._event.set()

    def result(
        self,
        future: Future,
        *,
        per_item_timeout: float = 60.0,
    ) -> object:
        """Get a future's result with bounded wait.

        Uses the smaller of per_item_timeout and remaining token time.
        Raises TimeoutError if the wait exceeds the limit.

        Args:
            future: Future to wait on.
            per_item_timeout: Max seconds to wait for this single result.

        Returns:
            The future's result.

        Raises:
            TimeoutError: If wait exceeds timeout.
            CancellationError: If token was cancelled.
            Exception: Any exception from the future's callable.
        """
        if self._cancelled:
            raise CancellationError("Build cancelled")

        timeout = min(per_item_timeout, self.remaining)
        if timeout <= 0:
            raise CancellationError("Build timeout expired")

        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            self.cancel()  # cancel remaining work
            raise CancellationError(
                f"Future timed out after {per_item_timeout:.0f}s "
                f"(token remaining: {self.remaining:.0f}s)"
            ) from None

    def check(self) -> None:
        """Raise CancellationError if cancelled or timed out.

        Call this periodically in long-running worker loops for
        cooperative cancellation.
        """
        if self.is_cancelled:
            raise CancellationError("Build cancelled")


class CancellationError(Exception):
    """Raised when a CancellationToken is cancelled or expires."""
