"""
Sequential rendering for render orchestration.

Provides sequential (single-threaded) page rendering with optional rich
progress bars. Used as fallback when parallel rendering is not beneficial
or when running on systems without free-threaded Python.

Mixed into RenderOrchestrator via SequentialRenderMixin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

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
        pages: Sequence[PageLike],
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

        token = build_context.cancellation_token if build_context else None

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
                if token and token.is_cancelled:
                    logger.warning("render_cancelled_sequential", pages_completed=i)
                    break
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

        pipeline = RenderingPipeline(
            self.site,
            quiet=quiet,
            build_stats=stats,
            build_context=build_context,
            changed_sources=changed_sources,
            block_cache=self._block_cache,
            highlight_cache=self._highlight_cache,
        )
        for i, page in enumerate(pages):
            if token and token.is_cancelled:
                logger.warning("render_cancelled_sequential", pages_completed=i)
                break
            pipeline.process_page(page)
