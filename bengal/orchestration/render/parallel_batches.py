"""Shared ThreadPoolExecutor batch runner for parallel page rendering.

Simple and live-progress paths share one submission/error-aggregation loop.
Semantics match the previous inline loops:

- Chunked submit (``batch_size = max_workers * 2``) bounds queue depth
- Each task runs under ``contextvars.copy_context()``
- Token timeout 60s; untokened ``future.result`` timeout 90s
- ``CancellationError`` breaks the current batch's ``as_completed`` loop
- Shutdown errors are skipped; other errors go through ``ErrorAggregator``
"""

from __future__ import annotations

import concurrent.futures
import contextvars
from itertools import batched
from typing import TYPE_CHECKING, Any

from bengal.errors import ErrorAggregator, extract_error_context
from bengal.orchestration.utils.errors import is_shutdown_error
from bengal.utils.concurrency.executor import CancellationError, managed_executor
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from bengal.protocols.core import PageLike

logger = get_logger(__name__)


def managed_render_executor(max_workers: int):
    """Context manager that shuts down a ThreadPoolExecutor correctly on error."""
    return managed_executor(max_workers, thread_name_prefix="Bengal-Render")


def run_parallel_page_batches(
    pages: Sequence[PageLike],
    process_page: Callable[[PageLike], None],
    *,
    max_workers: int,
    cancellation_token: Any | None,
) -> None:
    """Submit pages in batches and collect per-page render errors.

    Args:
        pages: Pages to render (already ordered)
        process_page: Per-page worker callable
        max_workers: Thread pool size
        cancellation_token: Optional build cancellation token
    """
    with managed_render_executor(max_workers) as executor:
        batch_size = max(max_workers * 2, 1)
        aggregator = ErrorAggregator(total_items=len(pages))
        threshold = 5

        for batch in batched(pages, batch_size, strict=False):
            future_to_page = {
                executor.submit(
                    contextvars.copy_context().run,
                    process_page,
                    page,
                ): page
                for page in batch
            }
            for future in concurrent.futures.as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    if cancellation_token:
                        cancellation_token.result(future, per_item_timeout=60.0)
                    else:
                        future.result(timeout=90)
                except CancellationError:
                    logger.warning("render_cancelled", page=page.source_path.name)
                    break
                except Exception as e:
                    if is_shutdown_error(e):
                        logger.debug("render_shutdown", page=page.source_path.name)
                        continue
                    context = extract_error_context(e, page)
                    if aggregator.should_log_individual(
                        e, context, threshold=threshold, max_samples=3
                    ):
                        logger.error("page_rendering_error", **context)
                    aggregator.add_error(e, context=context)

        aggregator.log_summary(logger, threshold=threshold, error_type="rendering")
