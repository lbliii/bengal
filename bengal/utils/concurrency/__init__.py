"""
Concurrency and threading utilities for Bengal.

This sub-package provides thread-safe utilities for parallel builds,
including locks, caches, async support, retry mechanisms, and worker
pool management.

Modules:
    concurrent_locks: Per-key locking for parallel builds
    thread_local: Thread-local caching for expensive objects
    async_compat: uvloop integration for Rust-accelerated async I/O
    retry: Exponential backoff retry utilities
    gil: GIL detection utilities
    workers: Worker pool auto-tuning

Example:
    >>> from bengal.utils.concurrency import PerKeyLockManager, run_async, get_optimal_workers
    >>> locks = PerKeyLockManager()
    >>> with locks.get_lock("template.html"):
    ...     template = compile_template("template.html")
    >>> workers = get_optimal_workers(len(pages), workload_type=WorkloadType.MIXED)

"""

from bengal.utils.concurrency.async_compat import install_uvloop, run_async
from bengal.utils.concurrency.concurrent_locks import PerKeyLockManager
from bengal.utils.concurrency.gil import (
    format_gil_tip_for_cli,
    get_gil_status_message,
    has_free_threading_support,
    is_gil_disabled,
)
from bengal.utils.concurrency.retry import (
    async_retry_with_backoff,
    calculate_backoff,
    retry_with_backoff,
)
from bengal.utils.concurrency.thread_local import ThreadLocalCache, ThreadSafeSet
from bengal.utils.concurrency.workers import (
    Environment,
    WorkloadProfile,
    WorkloadType,
    detect_environment,
    estimate_page_weight,
    get_optimal_workers,
    get_profile,
    order_by_complexity,
    should_parallelize,
)

__all__ = [
    # concurrent_locks
    "PerKeyLockManager",
    # thread_local
    "ThreadLocalCache",
    "ThreadSafeSet",
    # async_compat
    "run_async",
    "install_uvloop",
    # retry
    "calculate_backoff",
    "retry_with_backoff",
    "async_retry_with_backoff",
    # gil
    "is_gil_disabled",
    "has_free_threading_support",
    "get_gil_status_message",
    "format_gil_tip_for_cli",
    # workers
    "WorkloadType",
    "Environment",
    "WorkloadProfile",
    "detect_environment",
    "get_optimal_workers",
    "should_parallelize",
    "estimate_page_weight",
    "order_by_complexity",
    "get_profile",
]
