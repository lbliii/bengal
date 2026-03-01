"""
Sequential rendering for render orchestration.

Provides sequential (single-threaded) page rendering with optional rich
progress bars. Used as fallback when parallel rendering is not beneficial
or when running on systems without free-threaded Python.

Mixed into RenderOrchestrator via SequentialRenderMixin.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors import ErrorAggregator, extract_error_context
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.orchestration.types import ProgressManagerProtocol
    from bengal.utils.observability.cli_progress import LiveProgressManager

logger = get_logger(__name__)


class SequentialRenderMixin:
    """
    Mixin providing sequential rendering for RenderOrchestrator.

    Expects from host class:
        site: Site instance
        _block_cache: BlockCache | None
        _highlight_cache: HighlightCache
    """

    site: Site
    _block_cache: Any
    _highlight_cache: Any

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
            update_interval = 0.1

            for i, page in enumerate(pages):
                pipeline.process_page(page)
                now = time.time()
                if (i + 1) % 10 == 0 or (now - last_update_time) >= update_interval:
                    if page.output_path:
                        current_item = str(page.output_path.relative_to(self.site.output_dir))
                    else:
                        current_item = page.source_path.name
                    progress_manager.update_phase(
                        "rendering", current=i + 1, current_item=current_item
                    )
                    last_update_time = now

            progress_manager.update_phase("rendering", current=len(pages), current_item="")
            return

        try:
            from bengal.utils.observability.rich_console import (
                is_live_display_active,
                should_use_rich,
            )

            use_rich = (
                should_use_rich() and not quiet and len(pages) > 5 and not is_live_display_active()
            )
        except ImportError:
            use_rich = False

        if use_rich:
            self._render_sequential_with_progress(pages, quiet, stats, build_context)
        else:
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

            aggregator = ErrorAggregator(total_items=len(pages))
            threshold = 5

            for page in pages:
                try:
                    pipeline.process_page(page)
                except Exception as e:
                    context = extract_error_context(e, page)

                    if aggregator.should_log_individual(
                        e, context, threshold=threshold, max_samples=3
                    ):
                        logger.error("page_rendering_error", **context)

                    aggregator.add_error(e, context=context)
                progress.update(task, advance=1)

            aggregator.log_summary(logger, threshold=threshold, error_type="rendering")
