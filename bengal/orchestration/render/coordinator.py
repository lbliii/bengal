"""Process-impl coordinator for render orchestration.

Owns write-behind setup, cache invalidation, output-path pre-set, and
parallel-vs-sequential dispatch. Mixed into RenderOrchestrator. Does not
change worker selection or parallel/sequential semantics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.url_strategy import URLStrategy

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.orchestration.types import ProgressManagerProtocol
    from bengal.protocols import ProgressReporter
    from bengal.protocols.core import PageLike
    from bengal.utils.observability.cli_progress import LiveProgressManager

logger = get_logger(__name__)


class ProcessCoordinatorMixin:
    """
    Mixin providing process() internals for RenderOrchestrator.

    Expects from host class:
        site: Site instance
        _warm_block_cache()
        _priority_sort()
        _render_parallel()
        _render_sequential()
    """

    site: Site

    def _process_impl(
        self,
        pages: Sequence[PageLike],
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
        from bengal.icons import resolver as icon_resolver
        from bengal.rendering.template_functions.memo import set_build_context

        set_build_context(build_context)

        # Pre-initialize thread-safe resolver accumulator before threads start
        # (avoids TOCTOU race in per-thread RenderingPipeline.__init__)
        if not hasattr(self.site, "_external_ref_resolvers"):
            self.site._external_ref_resolvers = []
        if not hasattr(self.site, "_external_ref_resolvers_lock"):
            import threading

            self.site._external_ref_resolvers_lock = threading.Lock()

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

        # Initialize write-behind I/O for parallel builds only.
        # Overlaps CPU (rendering) with I/O (writing) via a dedicated thread pool,
        # providing 15-25% speedup on parallel renders.  Sequential builds write
        # inline — spawning 8 daemon threads for a handful of pages adds latency
        # and deadlock surface under free-threaded Python with no benefit.
        write_behind = None
        use_parallel = parallel  # Already computed in phase_render based on force_sequential
        if use_parallel and build_context:
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
            with icon_resolver.site_context(self.site):
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

    def _set_output_paths_for_pages(self, pages: Sequence[PageLike]) -> None:
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
