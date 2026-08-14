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
- Back pressure: Chunked submission (batch_size = max_workers * 2) bounds
  queue depth; expensive ops (highlighting, parsing) run in workers.

Related Modules:
- bengal.rendering.template_engine: Template rendering implementation
- bengal.rendering.renderer: Individual page rendering logic
- bengal.build.tracking: Dependency graph construction
- bengal.orchestration.render.parallel: Parallel rendering utilities
- bengal.orchestration.render.tracking: Active render tracking
- bengal.orchestration.render.ordering: PageLike ordering strategies
- bengal.orchestration.render.block_cache: Block cache management
- bengal.orchestration.render.sequential: Sequential rendering
- bengal.orchestration.render.coordinator: process() internals
- bengal.orchestration.render.parallel_render: Parallel dispatch mixin
- bengal.orchestration.render.parallel_batches: Shared executor loop

See Also:
- bengal/orchestration/render/orchestrator.py: RenderOrchestrator.process() entry point
- plan/active/rfc-template-performance-optimization.md: Performance RFC
- system-design-primer (back pressure, task queues): github.com/donnemartin/system-design-primer

"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

from .block_cache import BlockCacheMixin
from .coordinator import ProcessCoordinatorMixin
from .ordering import OrderingMixin
from .parallel import (
    is_free_threaded,
)
from .parallel_render import ParallelRenderMixin
from .sequential import SequentialRenderMixin
from .tracking import (
    clear_thread_local_pipelines,
)
from .tracking import (
    decrement_active_renders as _decrement_active_renders,
)
from .tracking import (
    increment_active_renders as _increment_active_renders,
)

logger = get_logger(__name__)


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


class RenderOrchestrator(
    OrderingMixin,
    BlockCacheMixin,
    SequentialRenderMixin,
    ProcessCoordinatorMixin,
    ParallelRenderMixin,
):
    """
    Orchestrates page rendering in sequential or parallel modes.

    Facade that composes ordering, block caching, sequential rendering,
    and parallel rendering. Handles page rendering with support for
    free-threaded Python for true parallelism.

    Mixins:
        OrderingMixin: PageLike ordering strategies (priority, complexity, track deps)
        BlockCacheMixin: Site-wide template block caching (Kida only)
        SequentialRenderMixin: Sequential rendering with optional progress
        ProcessCoordinatorMixin: process() internals (write-behind, dispatch)
        ParallelRenderMixin: Snapshot / live-progress / simple parallel paths

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
        orchestrator.process(pages, parallel=True, stats=stats)

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
        build_section = getattr(config, "build", None)
        if build_section is not None:
            return getattr(build_section, "max_workers", None)
        build_section = config.get("build", {})
        if isinstance(build_section, dict):
            return build_section.get("max_workers")
        return config.get("max_workers")

    def process(
        self,
        pages: Sequence[PageLike],
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
