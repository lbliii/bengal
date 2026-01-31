"""
Parallel processing utilities for orchestrators.

Provides generic parallel processing infrastructure with:
- Error aggregation and batch logging
- Progress update throttling
- Shutdown error handling
- Thread-local state management

These utilities consolidate common patterns from AssetOrchestrator,
TaxonomyOrchestrator, RenderOrchestrator, and PostprocessOrchestrator.

Example:
    >>> processor = ParallelProcessor(
    ...     workload_type=WorkloadType.IO_BOUND,
    ...     error_type="assets",
    ... )
    >>> results = processor.process(
    ...     items=assets,
    ...     process_fn=process_asset,
    ...     progress_callback=lambda i, a: progress.update("assets", current=i),
    ... )

"""

from __future__ import annotations

import concurrent.futures
import contextvars
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from bengal.errors import ErrorAggregator, extract_error_context
from bengal.orchestration.utils.errors import is_shutdown_error
from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.orchestration.types import ProgressManagerProtocol

logger = get_logger(__name__)

T = TypeVar("T")  # Input item type
R = TypeVar("R")  # Result type


@dataclass
class ProcessResult(Generic[R]):
    """Result of parallel processing."""

    results: list[R] = field(default_factory=list)
    errors: list[tuple[Any, Exception]] = field(default_factory=list)
    total_processed: int = 0
    total_errors: int = 0


class BatchProgressUpdater:
    """
    Throttled progress updates for parallel processing.

    Batches progress updates to reduce Rich rendering overhead.
    Updates are sent when either:
    - batch_size items have been processed
    - update_interval has elapsed since last update

    Thread-safe for use in parallel processing.

    Example:
        >>> updater = BatchProgressUpdater(progress_manager, phase="rendering")
        >>> for item in items:
        ...     process(item)
        ...     updater.increment(item.name)
        >>> updater.finalize()

    """

    def __init__(
        self,
        progress_manager: ProgressManagerProtocol | None,
        phase: str,
        batch_size: int = 10,
        update_interval_s: float = 0.1,
    ) -> None:
        """
        Initialize progress updater.

        Args:
            progress_manager: Progress manager to update (can be None for no-op)
            phase: Phase name for progress updates (e.g., "rendering", "assets")
            batch_size: Number of items before forcing an update
            update_interval_s: Maximum seconds between updates
        """
        self._progress_manager = progress_manager
        self._phase = phase
        self._batch_size = batch_size
        self._update_interval = update_interval_s

        self._lock = threading.Lock()
        self._completed_count = 0
        self._pending_updates = 0
        self._last_update_time = time.time()
        self._last_item: str = ""

    def increment(self, current_item: str = "", **metadata: Any) -> None:
        """
        Increment progress counter and potentially send update.

        Args:
            current_item: Name/description of current item being processed
            **metadata: Additional metadata to pass to progress update
        """
        if self._progress_manager is None:
            return

        now = time.time()
        should_update = False
        current_count = 0

        with self._lock:
            self._pending_updates += 1
            self._last_item = current_item

            # Check if update needed
            if (
                self._pending_updates >= self._batch_size
                or (now - self._last_update_time) >= self._update_interval
            ):
                should_update = True
                self._completed_count += self._pending_updates
                current_count = self._completed_count
                self._pending_updates = 0
                self._last_update_time = now

        # Update outside lock to minimize hold time
        if should_update:
            self._progress_manager.update_phase(
                self._phase,
                current=current_count,
                current_item=current_item,
                **metadata,
            )

    def finalize(self, total: int | None = None) -> None:
        """
        Send final progress update with any remaining pending updates.

        Args:
            total: Optional total count for final update (uses completed_count if None)
        """
        if self._progress_manager is None:
            return

        with self._lock:
            if self._pending_updates > 0:
                self._completed_count += self._pending_updates
                self._pending_updates = 0

            final_count = total if total is not None else self._completed_count

        self._progress_manager.update_phase(
            self._phase,
            current=final_count,
            current_item="",
        )

    @property
    def completed_count(self) -> int:
        """Get current completed count (thread-safe)."""
        with self._lock:
            return self._completed_count + self._pending_updates


class ParallelProcessor(Generic[T, R]):
    """
    Generic parallel processor with error aggregation and progress tracking.

    Consolidates the common parallel processing pattern used across orchestrators:
    - ThreadPoolExecutor with optimal workers
    - Error aggregation with threshold-based logging
    - Progress update batching
    - Shutdown error handling
    - Context variable propagation

    Example:
        >>> processor = ParallelProcessor[Asset, None](
        ...     workload_type=WorkloadType.IO_BOUND,
        ...     error_type="assets",
        ... )
        >>> result = processor.process(
        ...     items=assets,
        ...     process_fn=lambda a: a.copy_to_output(output_dir),
        ...     context_extractor=lambda e, a: {"asset": str(a.source_path)},
        ... )
        >>> if result.errors:
        ...     logger.error("Some assets failed", count=result.total_errors)

    """

    def __init__(
        self,
        workload_type: WorkloadType = WorkloadType.MIXED,
        config_override: int | None = None,
        error_type: str = "items",
        error_threshold: int = 5,
        max_error_samples: int = 3,
        propagate_context: bool = True,
    ) -> None:
        """
        Initialize parallel processor.

        Args:
            workload_type: Type of workload (IO_BOUND, CPU_BOUND, MIXED)
            config_override: Optional max_workers override from config
            error_type: Name for error aggregation logging (e.g., "assets", "rendering")
            error_threshold: Number of errors before switching to summary mode
            max_error_samples: Maximum individual errors to log before threshold
            propagate_context: Whether to propagate ContextVars to worker threads
        """
        self._workload_type = workload_type
        self._config_override = config_override
        self._error_type = error_type
        self._error_threshold = error_threshold
        self._max_error_samples = max_error_samples
        self._propagate_context = propagate_context

    def process(
        self,
        items: list[T],
        process_fn: Callable[[T], R],
        progress_callback: Callable[[int, T], None] | None = None,
        context_extractor: Callable[[Exception, T], dict[str, Any]] | None = None,
        progress_updater: BatchProgressUpdater | None = None,
    ) -> ProcessResult[R]:
        """
        Process items in parallel with error handling.

        Args:
            items: Items to process
            process_fn: Function to process each item
            progress_callback: Optional callback(completed_count, item) after each item
            context_extractor: Optional function to extract error context from (exception, item)
            progress_updater: Optional BatchProgressUpdater for throttled progress updates

        Returns:
            ProcessResult with results, errors, and counts
        """
        if not items:
            return ProcessResult()

        max_workers = get_optimal_workers(
            len(items),
            workload_type=self._workload_type,
            config_override=self._config_override,
        )

        result = ProcessResult[R]()
        aggregator = ErrorAggregator(total_items=len(items))
        completed_count = 0
        lock = threading.Lock()

        def process_item(item: T) -> R:
            """Process single item with context propagation."""
            return process_fn(item)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit tasks with optional context propagation
                if self._propagate_context:
                    future_to_item = {
                        executor.submit(
                            contextvars.copy_context().run,
                            process_item,
                            item,
                        ): item
                        for item in items
                    }
                else:
                    future_to_item = {
                        executor.submit(process_fn, item): item for item in items
                    }

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        item_result = future.result()
                        result.results.append(item_result)
                        result.total_processed += 1

                        # Progress update
                        if progress_updater:
                            progress_updater.increment(str(item))
                        elif progress_callback:
                            with lock:
                                completed_count += 1
                                progress_callback(completed_count, item)

                    except Exception as e:
                        # Handle shutdown errors gracefully
                        if is_shutdown_error(e):
                            logger.debug(f"{self._error_type}_shutdown", item=str(item))
                            continue

                        result.errors.append((item, e))
                        result.total_errors += 1

                        # Extract context for logging
                        if context_extractor:
                            context = context_extractor(e, item)
                        else:
                            context = extract_error_context(e, item)

                        # Log individual errors until threshold
                        if aggregator.should_log_individual(
                            e, context, threshold=self._error_threshold, max_samples=self._max_error_samples
                        ):
                            logger.error(f"{self._error_type}_processing_failed", **context)

                        aggregator.add_error(e, context=context)

                # Final progress update
                if progress_updater:
                    progress_updater.finalize(len(items))

                # Log aggregated summary if threshold exceeded
                aggregator.log_summary(
                    logger, threshold=self._error_threshold, error_type=self._error_type
                )

        except RuntimeError as e:
            if is_shutdown_error(e):
                logger.debug(f"{self._error_type}_executor_shutdown")
            else:
                raise

        return result

    def process_with_thread_local(
        self,
        items: list[T],
        process_fn: Callable[[T, Any], R],
        thread_local_factory: Callable[[], Any],
        thread_local: threading.local,
        thread_local_attr: str = "instance",
        generation: int | None = None,
        progress_updater: BatchProgressUpdater | None = None,
        context_extractor: Callable[[Exception, T], dict[str, Any]] | None = None,
    ) -> ProcessResult[R]:
        """
        Process items with thread-local state (e.g., RenderingPipeline per thread).

        Args:
            items: Items to process
            process_fn: Function(item, thread_local_instance) -> result
            thread_local_factory: Factory to create thread-local instance
            thread_local: threading.local object to store instances
            thread_local_attr: Attribute name on thread_local for instance
            generation: Optional generation number for cache invalidation
            progress_updater: Optional BatchProgressUpdater for throttled progress
            context_extractor: Optional function to extract error context

        Returns:
            ProcessResult with results, errors, and counts
        """
        if not items:
            return ProcessResult()

        max_workers = get_optimal_workers(
            len(items),
            workload_type=self._workload_type,
            config_override=self._config_override,
        )

        result = ProcessResult[R]()
        aggregator = ErrorAggregator(total_items=len(items))
        generation_attr = f"{thread_local_attr}_generation"

        def process_with_local(item: T) -> R:
            """Process item with thread-local instance."""
            # Check if instance exists and is current generation
            needs_new = (
                not hasattr(thread_local, thread_local_attr)
                or (generation is not None and getattr(thread_local, generation_attr, -1) != generation)
            )
            if needs_new:
                setattr(thread_local, thread_local_attr, thread_local_factory())
                if generation is not None:
                    setattr(thread_local, generation_attr, generation)

            instance = getattr(thread_local, thread_local_attr)
            return process_fn(item, instance)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                if self._propagate_context:
                    future_to_item = {
                        executor.submit(
                            contextvars.copy_context().run,
                            process_with_local,
                            item,
                        ): item
                        for item in items
                    }
                else:
                    future_to_item = {
                        executor.submit(process_with_local, item): item for item in items
                    }

                for future in concurrent.futures.as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        item_result = future.result()
                        result.results.append(item_result)
                        result.total_processed += 1

                        if progress_updater:
                            progress_updater.increment(str(item))

                    except Exception as e:
                        if is_shutdown_error(e):
                            logger.debug(f"{self._error_type}_shutdown", item=str(item))
                            continue

                        result.errors.append((item, e))
                        result.total_errors += 1

                        if context_extractor:
                            context = context_extractor(e, item)
                        else:
                            context = extract_error_context(e, item)

                        if aggregator.should_log_individual(
                            e, context, threshold=self._error_threshold, max_samples=self._max_error_samples
                        ):
                            logger.error(f"{self._error_type}_processing_failed", **context)

                        aggregator.add_error(e, context=context)

                if progress_updater:
                    progress_updater.finalize(len(items))

                aggregator.log_summary(
                    logger, threshold=self._error_threshold, error_type=self._error_type
                )

        except RuntimeError as e:
            if is_shutdown_error(e):
                logger.debug(f"{self._error_type}_executor_shutdown")
            else:
                raise

        return result
