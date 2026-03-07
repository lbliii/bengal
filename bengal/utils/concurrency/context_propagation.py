"""
Context propagation for thread pool executors.

When submitting work to ThreadPoolExecutor, the default behavior does not copy
contextvars from the submitting thread to worker threads. This causes
get_asset_manifest() and similar ContextVar lookups to return None in workers.

Use submit_with_context() when the task needs access to build-scoped context
(e.g., asset manifest for fingerprinting in templates).

RFC: rfc-global-build-state-dependencies.md
Plan: asset-manifest-context-refactor
"""

from __future__ import annotations

import contextvars
from concurrent.futures import Executor
from typing import Any


def submit_with_context(executor: Executor, fn: Any, *args: Any) -> Any:
    """
    Submit fn(*args) to executor with context propagation.

    Copies the current context (ContextVars) to the worker thread so that
    asset_manifest_context, build_context, and similar state are available
    during task execution.

    Args:
        executor: ThreadPoolExecutor (or compatible)
        fn: Callable to run in worker
        *args: Positional arguments for fn

    Returns:
        Future from executor.submit()

    Example:
        >>> def process_page(page):
        ...     # get_asset_manifest() works here - context was copied
        ...     return render(page)
        >>> future = submit_with_context(executor, process_page, page)
    """
    return executor.submit(contextvars.copy_context().run, fn, *args)
