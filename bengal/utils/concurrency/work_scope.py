"""Structured concurrency for Bengal's build pipeline.

WorkScope is the single way to do parallel work in Bengal. It wraps
ThreadPoolExecutor with correct shutdown semantics, context propagation,
cancellation, and timeout enforcement.

Every thread spawned within a WorkScope is bounded by that scope's lifetime.
When the scope exits (normally or via exception), all threads are cancelled
and joined. No thread outlives its scope.

Example:
    >>> from bengal.utils.concurrency.work_scope import WorkScope
    >>> with WorkScope("render", max_workers=8, timeout=300) as scope:
    ...     results = scope.map(render_page, pages)
    ...     for r in results:
    ...         if r.error:
    ...             handle_error(r.error)
    ...         else:
    ...             use(r.value)

"""

from __future__ import annotations

import concurrent.futures
import contextvars
import time
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from bengal.utils.concurrency.workers import WorkloadType

T = TypeVar("T")
R = TypeVar("R")

logger = get_logger(__name__)


def _is_shutdown_error(e: Exception) -> bool:
    """Check if exception is due to interpreter shutdown."""
    return "interpreter shutdown" in str(e)


@dataclass(frozen=True, slots=True)
class WorkResult(Generic[R]):  # noqa: UP046
    """Immutable result from a parallel work item.

    Attributes:
        value: The return value if successful, None on error.
        error: The exception if failed, None on success.
        elapsed_ms: Wall-clock time for this item in milliseconds.
    """

    value: R | None
    error: Exception | None
    elapsed_ms: float

    @property
    def ok(self) -> bool:
        """True if the work item completed without error."""
        return self.error is None


class WorkScope:
    """Structured concurrency scope for parallel work.

    All threads spawned via .map() are bounded by this scope's lifetime.
    On normal exit, waits for completion. On any exception, cancels pending
    futures and shuts down without waiting for hung threads.

    Supports multiple .map() calls within a single scope (the executor
    is reused across calls).

    Args:
        name: Human-readable name for logging and thread prefixes.
        max_workers: Maximum worker threads. None = auto-tune.
        workload_type: Workload characteristics for auto-tuning.
        timeout: Scope-level deadline in seconds (0 = no deadline).
        on_progress: Optional callback(completed_count, total_count)
            fired after each item completes.
    """

    __slots__ = (
        "_deadline",
        "_executor",
        "_max_workers",
        "_name",
        "_on_progress",
        "_timed_out",
        "_timeout",
        "_workload_type",
    )

    def __init__(
        self,
        name: str,
        *,
        max_workers: int | None = None,
        workload_type: WorkloadType | None = None,
        timeout: float = 300.0,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        self._name = name
        self._max_workers = max_workers
        self._workload_type = workload_type
        self._timeout = timeout
        self._on_progress = on_progress
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None
        self._deadline: float = 0.0
        self._timed_out: bool = False

    def __enter__(self) -> WorkScope:
        if self._timeout > 0:
            self._deadline = time.monotonic() + self._timeout
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._executor is not None:
            if exc_type is not None or self._timed_out:
                # Any exception or internal timeout: cancel pending and don't wait
                self._executor.shutdown(wait=False, cancel_futures=True)
            else:
                self._executor.shutdown(wait=True)
            self._executor = None
        return False

    @property
    def remaining(self) -> float:
        """Seconds remaining before scope deadline. float('inf') if no deadline."""
        if self._deadline <= 0:
            return float("inf")
        return max(0.0, self._deadline - time.monotonic())

    def _resolve_workers(self, task_count: int) -> int:
        """Determine worker count, auto-tuning if needed."""
        if self._max_workers is not None:
            return self._max_workers

        from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers

        wt = self._workload_type or WorkloadType.CPU_BOUND
        return get_optimal_workers(task_count, workload_type=wt)

    def _should_parallelize(self, task_count: int) -> bool:
        """Check if parallelization is worthwhile."""
        if self._max_workers is not None:
            # Explicit worker count: trust the caller, but not for 0-1 items
            return task_count > 1 and self._max_workers > 1

        from bengal.utils.concurrency.workers import WorkloadType, should_parallelize

        wt = self._workload_type or WorkloadType.CPU_BOUND
        return should_parallelize(task_count, workload_type=wt)

    def _ensure_executor(self, task_count: int) -> concurrent.futures.ThreadPoolExecutor:
        """Lazily create executor on first .map() call, reuse thereafter."""
        if self._executor is None:
            workers = self._resolve_workers(task_count)
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix=f"Bengal-{self._name}",
            )
        return self._executor

    def map(
        self,
        fn: Callable[[T], R],
        items: Iterable[T],
    ) -> list[WorkResult[R]]:
        """Process items in parallel, returning results for all items.

        Context variables are automatically propagated to worker threads.
        Each item's result is bounded by the scope deadline. Errors are
        captured per-item (never raises for individual item failures).

        Args:
            fn: Function to apply to each item.
            items: Items to process.

        Returns:
            List of WorkResult in completion order. Check .ok or .error
            on each result.

        Raises:
            KeyboardInterrupt: Re-raised after executor cleanup.
            SystemExit: Re-raised after executor cleanup.
        """
        items_list = list(items)
        if not items_list:
            return []

        total = len(items_list)

        # Sequential fast path for small workloads
        if not self._should_parallelize(total):
            return self._map_sequential(fn, items_list)

        return self._map_parallel(fn, items_list, total)

    def _map_sequential(
        self,
        fn: Callable[[T], R],
        items: list[T],
    ) -> list[WorkResult[R]]:
        """Sequential fallback for small workloads."""
        results: list[WorkResult[R]] = []
        total = len(items)
        for i, item in enumerate(items):
            start = time.perf_counter()
            try:
                value = fn(item)
                elapsed = (time.perf_counter() - start) * 1000
                results.append(WorkResult(value=value, error=None, elapsed_ms=elapsed))
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                results.append(WorkResult(value=None, error=e, elapsed_ms=elapsed))
            if self._on_progress:
                self._on_progress(i + 1, total)
        return results

    def _map_parallel(
        self,
        fn: Callable[[T], R],
        items: list[T],
        total: int,
    ) -> list[WorkResult[R]]:
        """Parallel execution with context propagation and bounded waits."""
        executor = self._ensure_executor(total)
        results: list[WorkResult[R]] = []
        completed = 0

        def _timed_call(item: T) -> tuple[R, float]:
            start = time.perf_counter()
            result = fn(item)
            elapsed = (time.perf_counter() - start) * 1000
            return result, elapsed

        # Submit all items with context propagation.
        # Each submit gets a fresh copy_context() so workers have independent
        # context snapshots (required for thread-safety).
        future_to_item: dict[Future[tuple[R, float]], T] = {
            executor.submit(contextvars.copy_context().run, _timed_call, item): item
            for item in items
        }

        try:
            # Use as_completed with a timeout to enforce the scope deadline.
            # This is the only reliable way to bound total wall-clock time —
            # future.result(timeout=N) only bounds the *wait*, not execution.
            iter_timeout = self.remaining if self._deadline > 0 else None
            done_iter = concurrent.futures.as_completed(future_to_item, timeout=iter_timeout)

            for future in done_iter:
                try:
                    value, elapsed_ms = future.result()
                    results.append(WorkResult(value=value, error=None, elapsed_ms=elapsed_ms))
                except KeyboardInterrupt, SystemExit:
                    for f in future_to_item:
                        f.cancel()
                    raise
                except RuntimeError as e:
                    if _is_shutdown_error(e):
                        logger.debug("work_scope_shutdown", scope=self._name)
                        break
                    results.append(WorkResult(value=None, error=e, elapsed_ms=0.0))
                except Exception as e:
                    results.append(WorkResult(value=None, error=e, elapsed_ms=0.0))

                completed += 1
                if self._on_progress:
                    self._on_progress(completed, total)

        except FuturesTimeoutError:
            # as_completed timed out — scope deadline expired
            self._timed_out = True
            remaining_count = total - completed
            logger.warning(
                "work_scope_deadline_expired",
                scope=self._name,
                completed=completed,
                remaining=remaining_count,
            )
            for f in future_to_item:
                f.cancel()
            # Record timeout errors for uncompleted items
            timeout_error = TimeoutError(
                f"Scope '{self._name}' deadline expired after {self._timeout:.0f}s"
            )
            results.extend(
                WorkResult(value=None, error=timeout_error, elapsed_ms=0.0)
                for _ in range(remaining_count)
            )
        except KeyboardInterrupt, SystemExit:
            if self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = None
            raise

        return results
