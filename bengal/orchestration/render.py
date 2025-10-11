"""
Rendering orchestration for Bengal SSG.

Handles page rendering in both sequential and parallel modes.
"""

from __future__ import annotations

import concurrent.futures
import threading
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger
from bengal.utils.url_strategy import URLStrategy

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.cache import DependencyTracker
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.utils.build_stats import BuildStats

# Thread-local storage for pipelines (reuse per thread, not per page!)
_thread_local = threading.local()


class RenderOrchestrator:
    """
    Handles page rendering.

    Responsibilities:
        - Sequential page rendering
        - Parallel page rendering with thread-local pipelines
        - Pipeline creation and management
    """

    def __init__(self, site: Site):
        """
        Initialize render orchestrator.

        Args:
            site: Site instance containing pages and configuration
        """
        self.site = site

    def process(self, pages: list[Page], parallel: bool = True,
                quiet: bool = False,
                tracker: DependencyTracker | None = None,
                stats: BuildStats | None = None,
                progress_manager: Any | None = None) -> None:
        """
        Render pages (parallel or sequential).

        Args:
            pages: List of pages to render
            parallel: Whether to use parallel rendering
            quiet: Whether to suppress progress output (minimal output mode)
            tracker: Dependency tracker for incremental builds
            stats: Build statistics tracker
            progress_manager: Live progress manager (optional)
        """

        # PRE-PROCESS: Set output paths for pages being rendered
        # Note: This only sets paths for pages we're actually rendering.
        # Other pages should already have paths from previous builds or will get them when needed.
        self._set_output_paths_for_pages(pages)

        # Use parallel rendering only for 5+ pages (avoid thread overhead for small batches)
        PARALLEL_THRESHOLD = 5
        if parallel and len(pages) >= PARALLEL_THRESHOLD:
            self._render_parallel(pages, tracker, quiet, stats, progress_manager)
        else:
            self._render_sequential(pages, tracker, quiet, stats, progress_manager)

    def _render_sequential(self, pages: list[Page],
                          tracker: DependencyTracker | None,
                          quiet: bool,
                          stats: BuildStats | None,
                          progress_manager: Any | None = None) -> None:
        """
        Build pages sequentially.

        Args:
            pages: Pages to render
            tracker: Dependency tracker
            quiet: Whether to suppress verbose output
            stats: Build statistics tracker
            progress_manager: Live progress manager (optional)
        """
        from bengal.rendering.pipeline import RenderingPipeline

        # If we have a progress manager, use it (and suppress individual page output)
        if progress_manager:
            pipeline = RenderingPipeline(self.site, tracker, quiet=True, build_stats=stats)
            for i, page in enumerate(pages):
                pipeline.process_page(page)
                # Update progress with current page
                if page.output_path:
                    current_item = str(page.output_path.relative_to(self.site.output_dir))
                else:
                    current_item = page.source_path.name
                progress_manager.update_phase('rendering', current=i+1, current_item=current_item)
            return

        # Try to use rich progress if available
        try:
            from bengal.utils.rich_console import get_console, should_use_rich
            use_rich = should_use_rich() and not quiet and len(pages) > 5
        except ImportError:
            use_rich = False

        if use_rich:
            self._render_sequential_with_progress(pages, tracker, quiet, stats)
        else:
            # Traditional rendering without progress
            pipeline = RenderingPipeline(self.site, tracker, quiet=quiet, build_stats=stats)
            for page in pages:
                pipeline.process_page(page)

    def _render_parallel(self, pages: list[Page],
                        tracker: DependencyTracker | None,
                        quiet: bool,
                        stats: BuildStats | None,
                        progress_manager: Any | None = None) -> None:
        """
        Build pages in parallel for better performance.

        Threading Model:
            - Creates ThreadPoolExecutor with max_workers threads
            - max_workers comes from config (default: 4)
            - Each thread gets its own RenderingPipeline instance (cached)
            - Each pipeline gets its own MarkdownParser instance (cached)

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

        Args:
            pages: Pages to render
            tracker: Dependency tracker for incremental builds
            quiet: Whether to suppress verbose output
            stats: Build statistics tracker
            progress_manager: Live progress manager (optional)

        Raises:
            Exception: Errors during page rendering are logged but don't fail the build

        Note:
            If you're profiling and see N parser/pipeline instances created,
            where N = max_workers, this is OPTIMAL behavior.
        """
        # If we have a progress manager, use it with parallel rendering
        if progress_manager:
            self._render_parallel_with_live_progress(pages, tracker, quiet, stats, progress_manager)
            return

        # Try to use rich progress if available
        try:
            from bengal.utils.rich_console import get_console, should_use_rich
            use_rich = should_use_rich() and not quiet and len(pages) > 5
        except ImportError:
            use_rich = False

        if use_rich:
            self._render_parallel_with_progress(pages, tracker, quiet, stats)
        else:
            self._render_parallel_simple(pages, tracker, quiet, stats)

    def _render_parallel_simple(self, pages: list[Page],
                               tracker: DependencyTracker | None,
                               quiet: bool,
                               stats: BuildStats | None) -> None:
        """Parallel rendering without progress (traditional)."""
        from bengal.rendering.pipeline import RenderingPipeline

        max_workers = self.site.config.get("max_workers", 4)

        def process_page_with_pipeline(page):
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            if not hasattr(_thread_local, 'pipeline'):
                _thread_local.pipeline = RenderingPipeline(
                    self.site, tracker, quiet=quiet, build_stats=stats
                )
            _thread_local.pipeline.process_page(page)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_page_with_pipeline, page)
                for page in pages
            ]

            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error("page_rendering_error",
                                error=str(e),
                                error_type=type(e).__name__)

    def _render_sequential_with_progress(self, pages: list[Page],
                                        tracker: DependencyTracker | None,
                                        quiet: bool,
                                        stats: BuildStats | None) -> None:
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
        from bengal.utils.rich_console import get_console

        console = get_console()
        pipeline = RenderingPipeline(self.site, tracker, quiet=quiet, build_stats=stats)

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
            transient=False
        ) as progress:
            task = progress.add_task("[cyan]Rendering pages...", total=len(pages))

            for page in pages:
                try:
                    pipeline.process_page(page)
                except Exception as e:
                    logger.error("page_rendering_error", error=str(e), error_type=type(e).__name__)
                progress.update(task, advance=1)

    def _render_parallel_with_live_progress(self, pages: list[Page],
                                           tracker: DependencyTracker | None,
                                           quiet: bool,
                                           stats: BuildStats | None,
                                           progress_manager: Any) -> None:
        """Render pages in parallel with live progress manager."""
        from bengal.rendering.pipeline import RenderingPipeline

        max_workers = self.site.config.get("max_workers", 4)
        completed_count = 0
        lock = threading.Lock()

        def process_page_with_pipeline(page):
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            nonlocal completed_count

            if not hasattr(_thread_local, 'pipeline'):
                # When using progress manager, suppress individual page output
                _thread_local.pipeline = RenderingPipeline(
                    self.site, tracker, quiet=True, build_stats=stats
                )
            _thread_local.pipeline.process_page(page)

            # Update progress (thread-safe)
            with lock:
                completed_count += 1
                if page.output_path:
                    current_item = str(page.output_path.relative_to(self.site.output_dir))
                else:
                    current_item = page.source_path.name

                # Add thread count to metadata for dev profile
                progress_manager.update_phase(
                    'rendering',
                    current=completed_count,
                    current_item=current_item,
                    threads=max_workers
                )

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_page_with_pipeline, page)
                for page in pages
            ]

            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error("page_rendering_error", error=str(e), error_type=type(e).__name__)

    def _render_parallel_with_progress(self, pages: list[Page],
                                      tracker: DependencyTracker | None,
                                      quiet: bool,
                                      stats: BuildStats | None) -> None:
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
        from bengal.utils.rich_console import get_console

        console = get_console()
        max_workers = self.site.config.get("max_workers", 4)

        def process_page_with_pipeline(page):
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            if not hasattr(_thread_local, 'pipeline'):
                _thread_local.pipeline = RenderingPipeline(
                    self.site, tracker, quiet=quiet, build_stats=stats
                )
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
            transient=False
        ) as progress:
            task = progress.add_task("[cyan]Rendering pages...", total=len(pages))

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(process_page_with_pipeline, page)
                    for page in pages
                ]

                # Wait for all to complete and update progress
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error("page_rendering_error", error=str(e), error_type=type(e).__name__)
                    progress.update(task, advance=1)

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

