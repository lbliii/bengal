"""Parallel rendering mixin for RenderOrchestrator.

Dispatches snapshot / live-progress / simple ThreadPoolExecutor paths.
Worker selection and parallel-vs-sequential choice stay with the caller
(``process()`` / ``phase_render``). Free-threading detection is unchanged.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers
from bengal.utils.observability.logger import get_logger

from .output_collector_diagnostics import diagnose_missing_output_collector
from .parallel_batches import run_parallel_page_batches
from .pipeline_runner import process_page_with_pipeline as _process_page_with_pipeline
from .tracking import (
    get_current_generation as _get_current_generation,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.orchestration.types import ProgressManagerProtocol
    from bengal.protocols.core import PageLike
    from bengal.utils.observability.cli_progress import LiveProgressManager

logger = get_logger(__name__)


class ParallelRenderMixin:
    """
    Mixin providing parallel rendering for RenderOrchestrator.

    Expects from host class:
        site: Site instance
        _block_cache / _highlight_cache
        _get_max_workers()
        _maybe_sort_by_complexity()
    """

    site: Site
    _block_cache: Any
    _highlight_cache: Any

    def _get_max_workers(self) -> int | None:
        """Expected from host. RenderOrchestrator overrides with config lookup."""
        return None

    def _render_parallel(
        self,
        pages: Sequence[PageLike],
        quiet: bool,
        stats: BuildStats | None,
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None = None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """
        Build pages in parallel for better performance.

        Threading Model:
            - Creates ThreadPoolExecutor with max_workers threads
            - max_workers comes from config (default: 4)
            - Each thread gets its own RenderingPipeline instance (cached)
            - Each pipeline gets its own MarkdownParser instance (cached)

        Free-Threaded Python Support (PEP 703):
            - Automatically detects Python 3.13t+ with GIL disabled
            - ThreadPoolExecutor gets true parallelism (no GIL contention)
            - ~1.5-2x faster rendering on multi-core machines
            - No code changes needed - works automatically

        Snapshot Engine (RFC: rfc-bengal-snapshot-engine):
            - If snapshot is available in build_context, uses WaveScheduler
            - Topological wave-based rendering for cache locality
            - Scout thread for predictive cache warming
            - Zero lock contention (frozen snapshots)

        Caching Strategy:
            Thread-local caching at two levels:
            1. RenderingPipeline: One per thread (Jinja2 environment is expensive)
            2. MarkdownParser: One per thread (parser setup is expensive)

            This means with max_workers=N:
            - N RenderingPipeline instances created
            - N MarkdownParser instances created
            - Both are reused for all pages processed by that thread

        Performance Example:
            With 200 pages and max_workers=10:
            - 10 threads created
            - 10 pipelines created (one-time cost: ~50ms)
            - 10 parsers created (one-time cost: ~100ms)
            - Each thread processes ~20 pages
            - Per-page savings: ~5ms (pipeline) + ~10ms (parser) = ~15ms
            - Total savings: ~3 seconds vs creating fresh for each page

            On free-threaded Python (3.14t):
            - Same setup but ~1.78x faster due to true parallelism
            - 1000 pages in 1.94s vs 3.46s with GIL (515 vs 289 pages/sec)

        Args:
            pages: Pages to render
            quiet: Whether to suppress verbose output
            stats: Build statistics tracker
            progress_manager: Live progress manager (optional)

        Raises:
            Exception: Errors during page rendering are logged but don't fail the build

        Note:
            If you're profiling and see N parser/pipeline instances created,
            where N = max_workers, this is OPTIMAL behavior.
        """
        # Single aggregated warning when output_collector missing (affects all worker threads)
        output_collector = build_context.output_collector if build_context else None
        if output_collector is None:
            dev_mode = getattr(self.site, "dev_mode", False)
            if dev_mode:
                max_workers = get_optimal_workers(
                    len(pages),
                    workload_type=WorkloadType.MIXED,
                    config_override=self._get_max_workers(),
                )
                diagnostic = diagnose_missing_output_collector(
                    build_context=build_context,
                    caller="_render_parallel",
                    worker_threads=max_workers,
                )
                logger.warning(
                    "output_collector_missing_in_pipeline",
                    **diagnostic.to_log_context(),
                )

        # Check if snapshot is available (RFC: rfc-bengal-snapshot-engine)
        if build_context and build_context.snapshot:
            # Use WaveScheduler for topological wave-based rendering
            self._render_with_snapshot(
                build_context.snapshot,
                pages,
                quiet,
                stats,
                progress_manager,
                build_context,
            )
            return

        # If we have a progress manager, use it with parallel rendering
        if progress_manager:
            self._render_parallel_with_live_progress(
                pages, quiet, stats, progress_manager, build_context, changed_sources
            )
            return

        self._render_parallel_simple(pages, quiet, stats, build_context, changed_sources)

    def _render_with_snapshot(
        self,
        snapshot: Any,  # SiteSnapshot
        pages: Sequence[PageLike],
        quiet: bool,
        stats: BuildStats | None,
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None = None,
        build_context: BuildContext | None = None,
    ) -> None:
        """
        Render pages using snapshot-based WaveScheduler.

        Uses topological wave-based rendering for cache locality and includes
        scout thread for predictive cache warming.

        Args:
            snapshot: SiteSnapshot from build context
            pages: Pages to render (filtered to pages in snapshot)
            quiet: Whether to suppress verbose output
            stats: Build statistics tracker
            progress_manager: Live progress manager (optional)
            build_context: Build context
        """
        from bengal.snapshots import WaveScheduler

        # Get max workers
        max_workers = get_optimal_workers(
            len(pages),
            workload_type=WorkloadType.MIXED,
            config_override=self._get_max_workers(),
        )

        # Create wave scheduler (pass output_collector explicitly for hot reload)
        output_collector = build_context.output_collector if build_context else None
        scheduler = WaveScheduler(
            snapshot=snapshot,
            site=self.site,
            quiet=quiet,
            stats=stats,
            build_context=build_context,
            output_collector=output_collector,
            max_workers=max_workers,
        )

        # Render using wave scheduler
        render_stats = scheduler.render_all(pages)

        # Update build stats
        if stats:
            stats.pages_rendered = render_stats.pages_rendered
            if render_stats.errors:
                for page_path, error in render_stats.errors:
                    logger.error(
                        "page_rendering_error",
                        page=str(page_path),
                        error=str(error),
                    )

        # Update progress manager if provided
        if progress_manager:
            progress_manager.update_phase(
                "rendering",
                current=render_stats.pages_rendered,
                current_item="",
            )

    def _render_parallel_simple(
        self,
        pages: Sequence[PageLike],
        quiet: bool,
        stats: BuildStats | None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """Parallel rendering without progress (traditional)."""
        max_workers = get_optimal_workers(
            len(pages),
            workload_type=WorkloadType.MIXED,
            config_override=self._get_max_workers(),
        )

        # Sort heavy pages first to avoid straggler workers (LPT scheduling)
        sorted_pages = self._maybe_sort_by_complexity(pages, max_workers)

        # Capture current generation for staleness check
        current_gen = _get_current_generation()

        def process_page_with_pipeline(page: PageLike) -> None:
            _process_page_with_pipeline(
                page,
                site=self.site,
                quiet=quiet,
                stats=stats,
                build_context=build_context,
                changed_sources=changed_sources,
                block_cache=self._block_cache,
                highlight_cache=self._highlight_cache,
                output_collector=build_context.output_collector if build_context else None,
                current_generation=current_gen,
            )

        token = build_context.cancellation_token if build_context else None
        run_parallel_page_batches(
            sorted_pages,
            process_page_with_pipeline,
            max_workers=max_workers,
            cancellation_token=token,
        )

    def _render_parallel_with_live_progress(
        self,
        pages: Sequence[PageLike],
        quiet: bool,
        stats: BuildStats | None,
        progress_manager: LiveProgressManager | ProgressManagerProtocol,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """Render pages in parallel with live progress manager."""
        import time

        max_workers = get_optimal_workers(
            len(pages),
            workload_type=WorkloadType.MIXED,
            config_override=self._get_max_workers(),
        )

        # Sort heavy pages first to avoid straggler workers (LPT scheduling)
        sorted_pages = self._maybe_sort_by_complexity(pages, max_workers)

        completed_count = 0
        lock = threading.Lock()
        last_update_time = time.time()
        update_interval = 0.1  # Update every 100ms (10 Hz max)
        batch_size = 10  # Or every 10 pages, whichever comes first

        # Capture current generation for staleness check
        current_gen = _get_current_generation()

        def process_page_with_pipeline(page: PageLike) -> None:
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            nonlocal completed_count, last_update_time

            _process_page_with_pipeline(
                page,
                site=self.site,
                quiet=True,  # Always True when progress_manager is active
                stats=stats,
                build_context=build_context,
                changed_sources=changed_sources,
                block_cache=self._block_cache,
                highlight_cache=self._highlight_cache,
                output_collector=build_context.output_collector if build_context else None,
                current_generation=current_gen,
            )

            # Pre-compute current_item outside lock (PERFORMANCE OPTIMIZATION)
            if page.output_path:
                current_item = str(page.output_path.relative_to(self.site.output_dir))
            else:
                current_item = page.source_path.name

            # Update progress with batched/throttled updates (PERFORMANCE OPTIMIZATION)
            now = time.time()
            should_update = False
            current_count = 0

            with lock:
                completed_count += 1
                current_count = completed_count
                # Update if: batch size reached OR time interval exceeded
                if current_count % batch_size == 0 or (now - last_update_time) >= update_interval:
                    should_update = True
                    last_update_time = now

            # Update progress outside lock to minimize lock hold time
            if should_update:
                progress_manager.update_phase(
                    "rendering",
                    current=current_count,
                    current_item=current_item,
                    threads=max_workers,
                )

        token = build_context.cancellation_token if build_context else None
        run_parallel_page_batches(
            sorted_pages,
            process_page_with_pipeline,
            max_workers=max_workers,
            cancellation_token=token,
        )

        if progress_manager:
            progress_manager.update_phase(
                "rendering",
                current=len(sorted_pages),
                current_item="",
                threads=max_workers,
            )
