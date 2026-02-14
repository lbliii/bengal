"""
Rendering orchestration for Bengal SSG.

Handles page rendering in both sequential and parallel modes. Supports
free-threaded Python for true parallelism and falls back to sequential
rendering on standard Python. Integrates with dependency tracking for
incremental builds.

Key Concepts:
- Parallel rendering: ThreadPoolExecutor for concurrent page rendering
- Free-threaded detection: Automatic detection of GIL-disabled Python
- Dependency tracking: Template dependency tracking for incremental builds
- Error handling: Graceful error handling with page-level isolation

Related Modules:
- bengal.rendering.template_engine: Template rendering implementation
- bengal.rendering.renderer: Individual page rendering logic
- bengal.build.tracking: Dependency graph construction
- bengal.orchestration.render.parallel: Parallel rendering utilities
- bengal.orchestration.render.tracking: Active render tracking

See Also:
- bengal/orchestration/render/orchestrator.py: RenderOrchestrator.process() entry point
- plan/active/rfc-template-performance-optimization.md: Performance RFC

"""

from __future__ import annotations

import concurrent.futures
import contextvars
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors import ErrorAggregator, extract_error_context
from bengal.orchestration.utils.errors import is_shutdown_error
from bengal.protocols import ProgressReporter
from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.url_strategy import URLStrategy

from .parallel import (
    is_free_threaded,
)
from .parallel import (
    thread_local as _thread_local,
)
from .tracking import (
    clear_thread_local_pipelines,
)
from .tracking import (
    decrement_active_renders as _decrement_active_renders,
)
from .tracking import (
    get_current_generation as _get_current_generation,
)
from .tracking import (
    increment_active_renders as _increment_active_renders,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.orchestration.types import ProgressManagerProtocol
    from bengal.utils.observability.cli_progress import LiveProgressManager

class RenderOrchestrator:
    """
    Orchestrates page rendering in sequential or parallel modes.

    Handles page rendering with support for free-threaded Python for true
    parallelism. Manages thread-local rendering pipelines and integrates
    with dependency tracking for incremental builds.

    Creation:
        Direct instantiation: RenderOrchestrator(site)
            - Created by BuildOrchestrator during build
            - Requires Site instance with pages populated

    Attributes:
        site: Site instance containing pages and configuration
        _free_threaded: Whether running on free-threaded Python (GIL disabled)
        _block_cache: Cache for site-wide template blocks (Kida only)

    Relationships:
        - Uses: RenderingPipeline for individual page rendering
        - Uses: EffectTracer for dependency tracking
        - Uses: BuildStats for build statistics collection
        - Uses: BlockCache for site-wide block caching
        - Used by: BuildOrchestrator for rendering phase

    Thread Safety:
        Thread-safe for parallel rendering. Uses thread-local pipelines
        to avoid contention. Detects free-threaded Python automatically.

    Examples:
        orchestrator = RenderOrchestrator(site)
        orchestrator.process(pages, parallel=True,
 stats=stats)

    """

    def __init__(self, site: Site):
        """
        Initialize render orchestrator.

        Args:
            site: Site instance containing pages and configuration
        """
        self.site = site
        self._free_threaded = is_free_threaded()
        self._block_cache = None  # Lazy initialized for Kida only
        from bengal.rendering.highlighting.cache import HighlightCache

        self._highlight_cache = HighlightCache(enabled=True)

        # Log free-threaded detection once
        if self._free_threaded:
            logger.info(
                "Using ThreadPoolExecutor with true parallelism (no GIL)",
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            )

    def _get_max_workers(self) -> int | None:
        """Get max_workers from config, supporting both Config and dict."""
        config = self.site.config
        if hasattr(config, "build"):
            return config.build.max_workers  # type: ignore[union-attr]
        build_section = config.get("build", {})
        if isinstance(build_section, dict):
            return build_section.get("max_workers")
        return config.get("max_workers")

    def _warm_block_cache(self) -> None:
        """Pre-warm block cache with site-wide blocks (Kida only).

        Identifies blocks that only depend on site context and pre-renders
        them once. These cached blocks are reused for all pages, avoiding
        redundant rendering of nav, footer, etc.

        RFC: kida-template-introspection
        """
        try:
            from bengal.protocols import EngineCapability
            from bengal.rendering.block_cache import BlockCache
            from bengal.rendering.context import get_engine_globals
            from bengal.rendering.engines import create_engine

            engine = create_engine(self.site)

            # Check if engine supports block caching via capability detection
            if not engine.has_capability(EngineCapability.BLOCK_CACHING):
                return

            # Initialize block cache
            self._block_cache = BlockCache(enabled=True)

            # Build site context for block rendering
            site_context = get_engine_globals(self.site)  # type: ignore[arg-type]

            # Warm cache for key templates
            templates_to_warm = ["base.html", "page.html", "single.html", "list.html"]
            total_cached = 0

            for template_name in templates_to_warm:
                try:
                    cached = self._block_cache.warm_site_blocks(engine, template_name, site_context)  # type: ignore[arg-type]
                    total_cached += cached
                except Exception:
                    pass  # Skip templates that don't exist or fail to warm

            if total_cached > 0:
                logger.info(
                    "block_cache_ready",
                    total_blocks_cached=total_cached,
                    templates_analyzed=len(templates_to_warm),
                )

        except Exception as e:
            # Don't fail build if cache warming fails
            logger.debug("block_cache_warm_failed", error=str(e))

    def get_cached_block(self, template_name: str, block_name: str) -> str | None:
        """Get a cached block if available.

        Args:
            template_name: Template containing the block
            block_name: Block to retrieve

        Returns:
            Cached HTML string, or None if not cached
        """
        if self._block_cache is None:
            return None
        return self._block_cache.get(template_name, block_name)

    def get_block_cache_stats(self) -> dict | None:
        """Get block cache statistics.

        Returns:
            Dict with hits, misses, and cached block count, or None if no cache
        """
        if self._block_cache is None:
            return None
        return self._block_cache.get_stats()

    def process(
        self,
        pages: list[Page],
        parallel: bool = True,
        quiet: bool = False,
        stats: BuildStats | None = None,
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None = None,
        reporter: ProgressReporter | None = None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """
        Render pages (parallel or sequential).

        Args:
            pages: List of pages to render
            parallel: Whether to use parallel rendering
            quiet: Whether to suppress progress output (minimal output mode)
            stats: Build statistics tracker
            progress_manager: Live progress manager (optional)
        """
        # Clear stale thread-local pipelines from previous builds BEFORE tracking
        # CRITICAL: Without this, template changes may not be reflected because
        # the old Jinja2 environment with its internal cache would be reused.
        # Must happen BEFORE _increment_active_renders() to avoid warning.
        clear_thread_local_pipelines()

        # Track active render for cache lifecycle management (RFC: Phase 4)
        _increment_active_renders()

        try:
            self._process_impl(
                pages=pages,
                parallel=parallel,
                quiet=quiet,
                stats=stats,
                progress_manager=progress_manager,
                reporter=reporter,
                build_context=build_context,
                changed_sources=changed_sources,
            )
        finally:
            _decrement_active_renders()

    def _process_impl(
        self,
        pages: list[Page],
        parallel: bool,
        quiet: bool,
        stats: BuildStats | None,
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None,
        reporter: ProgressReporter | None,
        build_context: BuildContext | None,
        changed_sources: set[Path] | None,
    ) -> None:
        """
        Internal implementation of process() wrapped with render tracking.

        Note: clear_thread_local_pipelines() is called in process() BEFORE
        _increment_active_renders() to avoid "clear during active render" warnings.
        """
        # Use centralized cache registry for build-start invalidation
        # This replaces manual clear_global_context_cache() call and ensures
        # all BUILD_START caches are invalidated in correct order
        from bengal.utils.cache_registry import InvalidationReason, invalidate_for_reason

        invalidate_for_reason(InvalidationReason.BUILD_START)

        # Set build context for template function memoization (RFC: template-function-memoization)
        # This enables site-scoped memoization for functions like get_auto_nav()
        from bengal.rendering.template_functions.memo import set_build_context

        set_build_context(build_context)

        # Warm block cache before parallel rendering (Kida only)
        self._warm_block_cache()

        # Resolve progress manager from context if not provided
        if (
            not progress_manager
            and build_context
            and getattr(build_context, "progress_manager", None)
        ):
            progress_manager = build_context.progress_manager

        # PRE-PROCESS: Set output paths for pages being rendered
        # (done first so we can pre-create directories)
        self._set_output_paths_for_pages(pages)

        # Initialize write-behind I/O for all builds
        # PERF: Overlaps I/O with CPU rendering by queueing writes to a dedicated thread.
        # WriteBehindCollector is thread-safe - multiple render workers can enqueue
        # simultaneously while the writer threads drain to disk.
        # This provides 15-25% speedup by eliminating I/O blocking in render workers.
        #
        # Optimizations:
        # - 8 writer threads for SSD parallelism
        # - Auto-enables fast_writes in dev server mode
        # - Pre-creates directories to reduce lock contention
        # - Uses atomic counter instead of uuid4 for temp files
        write_behind = None
        use_parallel = parallel  # Already computed in phase_render based on force_sequential
        if build_context:
            from bengal.rendering.pipeline.write_behind import WriteBehindCollector

            write_behind = WriteBehindCollector(site=self.site)
            build_context.write_behind = write_behind

            # Pre-create all output directories in a single pass
            # Eliminates lock contention during parallel writes
            output_paths = [p.output_path for p in pages if p.output_path]
            if output_paths:
                write_behind.precreate_directories(output_paths)

            logger.debug(
                "write_behind_enabled",
                parallel=use_parallel,
                writers=write_behind._num_writers,
                fast_writes=write_behind._fast_writes,
            )

        # RFC: Autodoc Incremental Caching Enhancement
        # Prioritize pages that were explicitly changed (forced_changed_sources)
        # to ensure the most important content renders first.
        pages = self._priority_sort(pages, changed_sources)

        try:
            # Use parallel rendering only when worthwhile (avoid thread overhead for small batches)
            # WorkloadType.MIXED because rendering involves both I/O (templates) and CPU (parsing)
            if use_parallel:
                self._render_parallel(
                    pages, quiet, stats, progress_manager, build_context, changed_sources
                )
            else:
                self._render_sequential(
                    pages, quiet, stats, progress_manager, build_context, changed_sources
                )
        finally:
            # Flush write-behind queue and wait for all writes to complete
            if write_behind:
                try:
                    written = write_behind.flush_and_close()
                    logger.debug("write_behind_flushed", files_written=written)
                except Exception as e:
                    logger.error("write_behind_flush_error", error=str(e))

            # Clear build context for memoization (cleanup)
            set_build_context(None)

    def _render_sequential(
        self,
        pages: list[Page],
        quiet: bool,
        stats: BuildStats | None,
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None = None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """
        Build pages sequentially.

        Args:
            pages: Pages to render
            quiet: Whether to suppress verbose output
            stats: Build statistics tracker
            progress_manager: Live progress manager (optional)
        """
        from bengal.rendering.pipeline import RenderingPipeline

        # If we have a progress manager, use it (and suppress individual page output)
        if progress_manager:
            import time

            pipeline = RenderingPipeline(
                self.site,
                quiet=True,
                build_stats=stats,
                build_context=build_context,
                changed_sources=changed_sources,
                block_cache=self._block_cache,
                highlight_cache=self._highlight_cache,
            )
            last_update_time = time.time()
            update_interval = 0.1  # Update every 100ms (throttled for performance)

            for i, page in enumerate(pages):
                pipeline.process_page(page)
                # Throttle progress updates to reduce Rich rendering overhead
                now = time.time()
                if (i + 1) % 10 == 0 or (now - last_update_time) >= update_interval:
                    # Pre-compute current_item once
                    if page.output_path:
                        current_item = str(page.output_path.relative_to(self.site.output_dir))
                    else:
                        current_item = page.source_path.name
                    progress_manager.update_phase(
                        "rendering", current=i + 1, current_item=current_item
                    )
                    last_update_time = now

            # Final update to ensure progress shows 100%
            progress_manager.update_phase("rendering", current=len(pages), current_item="")
            return

        # Try to use rich progress if available (but not if Live display already active)
        try:
            from bengal.utils.observability.rich_console import (
                is_live_display_active,
                should_use_rich,
            )

            # Don't create Progress if there's already a Live display (e.g., LiveProgressManager)
            use_rich = (
                should_use_rich() and not quiet and len(pages) > 5 and not is_live_display_active()
            )
        except ImportError:
            use_rich = False

        if use_rich:
            self._render_sequential_with_progress(pages, quiet, stats, build_context)
        else:
            # Traditional rendering without progress
            pipeline = RenderingPipeline(
                self.site,
                quiet=quiet,
                build_stats=stats,
                build_context=build_context,
                changed_sources=changed_sources,
                block_cache=self._block_cache,
                highlight_cache=self._highlight_cache,
            )
            for page in pages:
                pipeline.process_page(page)

    def _render_parallel(
        self,
        pages: list[Page],
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
        # Check if snapshot is available (RFC: rfc-bengal-snapshot-engine)
        if build_context and hasattr(build_context, "snapshot") and build_context.snapshot:
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

        # Try to use rich progress if available (but not if Live display already active)
        try:
            from bengal.utils.observability.rich_console import (
                is_live_display_active,
                should_use_rich,
            )

            # Don't create Progress if there's already a Live display (e.g., LiveProgressManager)
            use_rich = (
                should_use_rich() and not quiet and len(pages) > 5 and not is_live_display_active()
            )
        except ImportError:
            use_rich = False

        if use_rich:
            self._render_parallel_with_progress(
                pages, quiet, stats, build_context, changed_sources
            )
        else:
            self._render_parallel_simple(
                pages, quiet, stats, build_context, changed_sources
            )

    def _render_with_snapshot(
        self,
        snapshot: Any,  # SiteSnapshot
        pages: list[Page],
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

        # Create wave scheduler
        scheduler = WaveScheduler(
            snapshot=snapshot,
            site=self.site,
            quiet=quiet,
            stats=stats,
            build_context=build_context,
            max_workers=max_workers,
        )

        # Render using wave scheduler
        render_stats = scheduler.render_all(pages)

        # Update build stats
        if stats:
            stats.pages_rendered = render_stats.pages_rendered  # type: ignore[assignment]
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

    def _should_use_complexity_ordering(self) -> bool:
        """Check if complexity-based ordering is enabled."""
        return self.site.config.get("build", {}).get("complexity_ordering", True)

    def _maybe_sort_by_complexity(self, pages: list[Page], max_workers: int) -> list[Page]:
        """Sort pages by complexity if enabled and beneficial.

        Only sorts if:
        1. Complexity ordering is enabled in config (default: True)
        2. We have more pages than workers (otherwise no benefit)

        Heavy pages are sorted first to minimize straggler workers.
        """
        if not self._should_use_complexity_ordering():
            return pages

        if len(pages) <= max_workers:
            # No benefit from sorting if we have fewer pages than workers
            return pages

        from bengal.orchestration.complexity import get_complexity_stats, sort_by_complexity

        sorted_pages = sort_by_complexity(pages, descending=True)

        # Log complexity distribution at debug level
        complexity_stats = get_complexity_stats(sorted_pages)
        mean_score = float(complexity_stats["mean"])  # type: ignore[arg-type]
        variance_ratio = float(complexity_stats["variance_ratio"])  # type: ignore[arg-type]
        logger.debug(
            "complexity_distribution",
            page_count=complexity_stats["count"],
            min_score=complexity_stats["min"],
            max_score=complexity_stats["max"],
            mean_score=round(mean_score, 1),
            variance_ratio=round(variance_ratio, 1),
        )
        # Log ordering effectiveness (high variance = big benefit)
        if variance_ratio > 10:
            logger.debug(
                "complexity_ordering_beneficial",
                reason="high variance detected",
                top_5=complexity_stats["top_5_scores"],
                bottom_5=complexity_stats["bottom_5_scores"],
            )

        return sorted_pages

    def _render_parallel_simple(
        self,
        pages: list[Page],
        quiet: bool,
        stats: BuildStats | None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """Parallel rendering without progress (traditional)."""
        from bengal.rendering.pipeline import RenderingPipeline

        max_workers = get_optimal_workers(
            len(pages),
            workload_type=WorkloadType.MIXED,
            config_override=self._get_max_workers(),
        )

        # Sort heavy pages first to avoid straggler workers (LPT scheduling)
        sorted_pages = self._maybe_sort_by_complexity(pages, max_workers)

        # Capture current generation for staleness check
        current_gen = _get_current_generation()

        def process_page_with_pipeline(page: Page) -> None:
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            # Check if pipeline exists AND is from current build generation.
            # If generation has changed (new build), recreate the pipeline
            # to get a fresh TemplateEngine with updated templates.
            needs_new_pipeline = (
                not hasattr(_thread_local, "pipeline")
                or getattr(_thread_local, "pipeline_generation", -1) != current_gen
            )
            if needs_new_pipeline:
                _thread_local.pipeline = RenderingPipeline(
                    self.site,
                    quiet=quiet,
                    build_stats=stats,
                    build_context=build_context,
                    changed_sources=changed_sources,
                    block_cache=self._block_cache,
                    highlight_cache=self._highlight_cache,
                )
                _thread_local.pipeline_generation = current_gen
            _thread_local.pipeline.process_page(page)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Map futures to pages for error reporting
                # Uses sorted_pages (heavy first) for optimal parallel scheduling
                #
                # CRITICAL: Copy parent context for each task to propagate ContextVars
                # (e.g., asset_manifest_context) to worker threads. Without this,
                # workers start with empty context in free-threaded Python (PEP 703).
                # fmt: off
                future_to_page = {
                    executor.submit(
                        contextvars.copy_context().run,  # type: ignore[arg-type]
                        process_page_with_pipeline,  # type: ignore[arg-type]
                        page,
                    ): page
                    for page in sorted_pages
                }
                # fmt: on

                # Track errors for aggregation
                aggregator = ErrorAggregator(total_items=len(sorted_pages))
                threshold = 5

                # Wait for all to complete
                for future in concurrent.futures.as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        future.result()
                    except Exception as e:
                        # Handle graceful shutdown
                        if is_shutdown_error(e):
                            logger.debug("render_shutdown", page=page.source_path.name)
                            continue
                        context = extract_error_context(e, page)

                        # Only log individual error if below threshold or first samples
                        if aggregator.should_log_individual(
                            e, context, threshold=threshold, max_samples=3
                        ):
                            logger.error("page_rendering_error", **context)

                        aggregator.add_error(e, context=context)

                # Log aggregated summary if threshold exceeded
                aggregator.log_summary(logger, threshold=threshold, error_type="rendering")
        except RuntimeError as e:
            # Handle graceful shutdown at executor level
            if is_shutdown_error(e):
                logger.debug("render_executor_shutdown")
                return
            raise

    def _render_sequential_with_progress(
        self,
        pages: list[Page],
        quiet: bool,
        stats: BuildStats | None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """Render pages sequentially with rich progress bar."""
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
        )

        from bengal.rendering.pipeline import RenderingPipeline
        from bengal.utils.observability.rich_console import get_console

        console = get_console()
        pipeline = RenderingPipeline(
            self.site,
            quiet=quiet,
            build_stats=stats,
            build_context=build_context,
            changed_sources=changed_sources,
            block_cache=self._block_cache,
            highlight_cache=self._highlight_cache,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total} pages"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task("[cyan]Rendering pages...", total=len(pages))

            # Track errors for aggregation
            aggregator = ErrorAggregator(total_items=len(pages))
            threshold = 5

            for page in pages:
                try:
                    pipeline.process_page(page)
                except Exception as e:
                    context = extract_error_context(e, page)

                    # Only log individual error if below threshold or first samples
                    if aggregator.should_log_individual(
                        e, context, threshold=threshold, max_samples=3
                    ):
                        logger.error("page_rendering_error", **context)

                    aggregator.add_error(e, context=context)
                progress.update(task, advance=1)

            # Log aggregated summary if threshold exceeded
            aggregator.log_summary(logger, threshold=threshold, error_type="rendering")

    def _render_parallel_with_live_progress(
        self,
        pages: list[Page],
        quiet: bool,
        stats: BuildStats | None,
        progress_manager: LiveProgressManager | ProgressManagerProtocol,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """Render pages in parallel with live progress manager."""
        import time

        from bengal.rendering.pipeline import RenderingPipeline

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

        def process_page_with_pipeline(page: Page) -> None:
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            nonlocal completed_count, last_update_time

            # Check if pipeline exists AND is from current build generation.
            needs_new_pipeline = (
                not hasattr(_thread_local, "pipeline")
                or getattr(_thread_local, "pipeline_generation", -1) != current_gen
            )
            if needs_new_pipeline:
                # When using progress manager, always suppress individual page output
                # (quiet=True) because progress_manager handles display. The `quiet`
                # parameter from the caller is intentionally ignored here.
                _thread_local.pipeline = RenderingPipeline(
                    self.site,
                    quiet=True,  # Always True when progress_manager is active
                    build_stats=stats,
                    build_context=build_context,
                    changed_sources=changed_sources,
                    block_cache=self._block_cache,
                    highlight_cache=self._highlight_cache,
                )
                _thread_local.pipeline_generation = current_gen
            _thread_local.pipeline.process_page(page)

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

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Map futures to pages for error reporting
                # Uses sorted_pages (heavy first) for optimal parallel scheduling
                #
                # CRITICAL: Copy parent context for each task to propagate ContextVars
                # (e.g., asset_manifest_context) to worker threads. Without this,
                # workers start with empty context in free-threaded Python (PEP 703).
                # fmt: off
                future_to_page = {
                    executor.submit(
                        contextvars.copy_context().run,  # type: ignore[arg-type]
                        process_page_with_pipeline,  # type: ignore[arg-type]
                        page,
                    ): page
                    for page in sorted_pages
                }
                # fmt: on

                # Track errors for aggregation
                aggregator = ErrorAggregator(total_items=len(sorted_pages))
                threshold = 5

                # Wait for all to complete
                for future in concurrent.futures.as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        future.result()
                    except Exception as e:
                        # Handle graceful shutdown
                        if is_shutdown_error(e):
                            logger.debug("render_shutdown", page=page.source_path.name)
                            continue
                        context = extract_error_context(e, page)

                        # Only log individual error if below threshold or first samples
                        if aggregator.should_log_individual(
                            e, context, threshold=threshold, max_samples=3
                        ):
                            logger.error("page_rendering_error", **context)

                        aggregator.add_error(e, context=context)

                # Log aggregated summary if threshold exceeded
                aggregator.log_summary(logger, threshold=threshold, error_type="rendering")

                # Final update to ensure progress shows 100%
                if progress_manager:
                    progress_manager.update_phase(
                        "rendering",
                        current=len(sorted_pages),
                        current_item="",
                        threads=max_workers,
                    )
        except RuntimeError as e:
            # Handle graceful shutdown at executor level
            if is_shutdown_error(e):
                logger.debug("render_executor_shutdown")
                return
            raise

    def _render_parallel_with_progress(
        self,
        pages: list[Page],
        quiet: bool,
        stats: BuildStats | None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """Render pages in parallel with rich progress bar."""
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
        )

        from bengal.rendering.pipeline import RenderingPipeline
        from bengal.utils.observability.rich_console import get_console

        console = get_console()
        max_workers = get_optimal_workers(
            len(pages),
            workload_type=WorkloadType.MIXED,
            config_override=self._get_max_workers(),
        )

        # Sort heavy pages first to avoid straggler workers (LPT scheduling)
        sorted_pages = self._maybe_sort_by_complexity(pages, max_workers)

        # Capture current generation for staleness check
        current_gen = _get_current_generation()

        def process_page_with_pipeline(page: Page) -> None:
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            # Check if pipeline exists AND is from current build generation.
            needs_new_pipeline = (
                not hasattr(_thread_local, "pipeline")
                or getattr(_thread_local, "pipeline_generation", -1) != current_gen
            )
            if needs_new_pipeline:
                _thread_local.pipeline = RenderingPipeline(
                    self.site,
                    quiet=quiet,
                    build_stats=stats,
                    build_context=build_context,
                    changed_sources=changed_sources,
                    block_cache=self._block_cache,
                    highlight_cache=self._highlight_cache,
                )
                _thread_local.pipeline_generation = current_gen
            _thread_local.pipeline.process_page(page)

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total} pages"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task("[cyan]Rendering pages...", total=len(sorted_pages))

            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Uses sorted_pages (heavy first) for optimal parallel scheduling
                    #
                    # CRITICAL: Copy parent context for each task to propagate ContextVars
                    # (e.g., asset_manifest_context) to worker threads. Without this,
                    # workers start with empty context in free-threaded Python (PEP 703).
                    # fmt: off
                    futures = [
                        executor.submit(
                            contextvars.copy_context().run,  # type: ignore[arg-type]
                            process_page_with_pipeline,  # type: ignore[arg-type]
                            page,
                        )
                        for page in sorted_pages
                    ]
                    # fmt: on

                    # Track errors for aggregation
                    aggregator = ErrorAggregator(total_items=len(sorted_pages))

                    # Wait for all to complete and update progress
                    threshold = 5
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            # Handle graceful shutdown
                            if is_shutdown_error(e):
                                logger.debug("render_shutdown")
                                continue
                            # Get page from future if possible (may not be available)
                            page = None
                            context = extract_error_context(e, page)

                            # Only log individual error if below threshold or first samples
                            if aggregator.should_log_individual(
                                e, context, threshold=threshold, max_samples=3
                            ):
                                logger.error("page_rendering_error", **context)

                            aggregator.add_error(e, context=context)
                        progress.update(task, advance=1)

                    # Log aggregated summary if threshold exceeded
                    aggregator.log_summary(logger, threshold=5, error_type="rendering")
            except RuntimeError as e:
                # Handle graceful shutdown at executor level
                if is_shutdown_error(e):
                    logger.debug("render_executor_shutdown")
                    return
                raise

    def _set_output_paths_for_pages(self, pages: list[Page]) -> None:
        """
        Pre-set output paths for specific pages before rendering.

        Only processes pages that are being rendered, not all pages in the site.
        This is an optimization for incremental builds where we only render a subset.
        """

        for page in pages:
            # Skip if already set (e.g., generated pages)
            if page.output_path:
                continue

            # Determine output path using centralized strategy (kept in sync with pipeline)
            page.output_path = URLStrategy.compute_regular_page_output_path(page, self.site)

    def _priority_sort(self, pages: list[Page], changed_sources: set[Path] | None) -> list[Page]:
        """
        Sort pages so that explicitly changed files are at the front.

        Args:
            pages: Pages to sort
            changed_sources: Set of paths that were explicitly changed

        Returns:
            Prioritized list of pages
        """
        if not changed_sources:
            return pages

        priority_pages: list[Page] = []
        normal_pages: list[Page] = []

        # Convert to resolved absolute paths for reliable matching
        resolved_changed = set()
        for p in changed_sources:
            try:
                resolved_changed.add(p.resolve())
            except (OSError, ValueError):
                resolved_changed.add(p)

        for page in pages:
            is_priority = False
            try:
                # Regular pages have a source_path
                if page.source_path and page.source_path.resolve() in resolved_changed:
                    is_priority = True

                # Autodoc pages might have source_path pointing to the python file
                # If the python file is in changed_sources, it's a priority
                if not is_priority and page.metadata.get("is_autodoc") and page.source_path:
                    if page.source_path.resolve() in resolved_changed:
                        is_priority = True
            except (OSError, ValueError):
                if page.source_path in changed_sources:
                    is_priority = True

            if is_priority:
                priority_pages.append(page)
            else:
                normal_pages.append(page)

        if priority_pages:
            logger.debug(
                "rendering_prioritization",
                priority_count=len(priority_pages),
                normal_count=len(normal_pages),
            )
            # Maintain complexity sorting within each group if enabled
            max_workers = self._get_max_workers() or 4
            priority_pages = self._maybe_sort_by_complexity(priority_pages, max_workers)
            normal_pages = self._maybe_sort_by_complexity(normal_pages, max_workers)

            return priority_pages + normal_pages

        return pages
