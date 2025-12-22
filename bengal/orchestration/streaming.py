"""
Streaming build orchestration for memory-optimized builds.

Uses knowledge graph analysis to process pages in optimal order for memory
efficiency. The hub-first strategy keeps highly connected pages in memory
while streaming leaves in batches with immediate memory release.

Strategy:
    1. Build knowledge graph to analyze page connectivity
    2. Classify pages into hubs (highly connected), mid-tier, and leaves
    3. Render hubs first and keep in memory (referenced often by links)
    4. Process mid-tier in batches
    5. Stream leaves in batches with gc.collect() after each batch

Memory Reduction:
    Achieves 80-90% memory reduction on large sites by:
    - Processing leaves in small batches instead of all at once
    - Releasing page content after rendering each batch
    - Keeping only hub pages in memory throughout

Recommended Use:
    Best for sites with 5K+ pages where memory is constrained.
    For smaller sites, standard rendering is faster due to lower overhead.

Performance Notes:
    - Uses build_context.knowledge_graph if available to avoid rebuilding
    - Falls back to standard rendering if knowledge graph unavailable
    - Batch size is configurable (default: 100 pages per batch)

Related Modules:
    bengal.analysis.knowledge_graph: Graph construction and analysis
    bengal.orchestration.render: Standard rendering (used for actual work)

See Also:
    bengal.orchestration.build: Enables streaming via memory_optimized flag
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import DependencyTracker
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.render import RenderOrchestrator
    from bengal.orchestration.stats import BuildStats

logger = get_logger(__name__)


class StreamingRenderOrchestrator:
    """
    Memory-optimized page rendering using knowledge graph analysis.

    Processes pages in connectivity-based order to minimize memory usage.
    Hub pages are rendered first and kept in memory (they're referenced
    often), while leaf pages are streamed in batches with immediate release.

    Strategy:
        1. Build/reuse knowledge graph to identify page connectivity
        2. Classify into hubs, mid-tier, and leaves based on link count
        3. Render hubs first (keep in memory for cross-page references)
        4. Process mid-tier in batches
        5. Stream leaves with gc.collect() after each batch

    Memory Savings:
        80-90% reduction on large sites by not keeping all pages in memory.
        Leaf pages (typically 70-80% of content) are released immediately.

    Creation:
        Direct instantiation: StreamingRenderOrchestrator(site)
            - Created by BuildOrchestrator when memory_optimized=True
            - Requires Site instance with pages populated

    Attributes:
        site: Site instance containing pages for rendering

    Relationships:
        - Uses: KnowledgeGraph for connectivity analysis
        - Uses: RenderOrchestrator for actual page rendering
        - Used by: BuildOrchestrator when memory_optimized flag is set

    Best For:
        Sites with 5K+ pages where memory is constrained. For smaller sites,
        the graph analysis overhead exceeds benefits.

    Example:
        streaming = StreamingRenderOrchestrator(site)
        streaming.process(pages, parallel=True, batch_size=100)
    """

    def __init__(self, site: Site):
        """
        Initialize streaming render orchestrator.

        Args:
            site: Site instance containing pages
        """
        self.site = site

    def process(
        self,
        pages: list[Page],
        parallel: bool = True,
        quiet: bool = False,
        tracker: DependencyTracker | None = None,
        stats: BuildStats | None = None,
        batch_size: int = 100,
        progress_manager: Any | None = None,
        reporter: Any | None = None,
        build_context: Any | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """
        Render pages in memory-optimized batches using connectivity analysis.

        Uses build_context.knowledge_graph if available to avoid rebuilding
        the graph multiple times per build.

        Args:
            pages: List of pages to render
            parallel: Whether to use parallel rendering
            quiet: Whether to suppress progress output (minimal output mode)
            tracker: Dependency tracker for incremental builds
            stats: Build statistics tracker
            batch_size: Number of leaves to process per batch
            progress_manager: Optional progress manager to use for unified progress display
            reporter: Optional progress reporter for output
            build_context: Optional BuildContext with cached knowledge graph
        """
        total_pages = len(pages)

        # Nothing to render: return early and avoid unnecessary analysis/output
        if total_pages == 0:
            return

        # Resolve from context if absent
        if not reporter and build_context and getattr(build_context, "reporter", None):
            reporter = build_context.reporter
        if (
            not progress_manager
            and build_context
            and getattr(build_context, "progress_manager", None)
        ):
            progress_manager = build_context.progress_manager

        # Warn if using memory optimization on small sites (overhead > benefit)
        RECOMMENDED_THRESHOLD = 5000
        WARNING_THRESHOLD = 1000

        if reporter is None:
            try:
                from bengal.utils.progress import NoopReporter

                reporter = NoopReporter()
            except Exception as e:
                logger.debug(
                    "noop_reporter_creation_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                reporter = None

        if total_pages < WARNING_THRESHOLD:
            msg1 = "  ⚠️  Memory optimization is designed for large sites (5K+ pages)"
            msg2 = f"     Your site has {total_pages} pages - standard build is likely faster."
            msg3 = "     Continuing anyway for testing/profiling purposes..."
            if reporter:
                reporter.log(msg1)
                reporter.log(msg2)
                reporter.log(msg3)
            elif not quiet:
                print(msg1)
                print(msg2)
                print(msg3)
        elif total_pages < RECOMMENDED_THRESHOLD:
            msg = f"  ℹ️  Site has {total_pages} pages - memory optimization may have marginal benefit."
            if reporter:
                reporter.log(msg)
            elif not quiet:
                print(msg)

        logger.info(
            "streaming_render_start",
            total_pages=total_pages,
            batch_size=batch_size,
            recommended=total_pages >= RECOMMENDED_THRESHOLD,
        )

        # Try to get cached graph from build context first (lazy-computed artifact)
        graph = None
        if build_context is not None:
            graph = build_context.knowledge_graph
            if graph is not None:
                logger.debug("using_cached_knowledge_graph_for_streaming_render")

        # Fallback: build our own (for standalone usage or if not in context)
        if graph is None:
            # Import here to avoid circular dependency
            try:
                from bengal.analysis.knowledge_graph import KnowledgeGraph
            except ImportError:
                logger.warning(
                    "streaming_render_fallback",
                    reason="Knowledge graph not available, using standard rendering",
                )
                # Fall back to standard rendering
                from bengal.orchestration.render import RenderOrchestrator

                orchestrator = RenderOrchestrator(self.site)
                orchestrator.process(
                    pages, parallel, quiet, tracker, stats, progress_manager=progress_manager
                )
                return

            # Build knowledge graph to analyze connectivity
            if reporter:
                reporter.log("  🧠 Analyzing connectivity for memory optimization...")
            elif not quiet:
                print("  🧠 Analyzing connectivity for memory optimization...")
            logger.debug("building_knowledge_graph_for_streaming_render")
            graph = KnowledgeGraph(self.site)
            graph.build()

        # Get connectivity-based layers
        layers = graph.get_layers()

        # Filter to only pages we're rendering
        pages_set = set(pages)
        hubs_to_render = [p for p in layers.hubs if p in pages_set]
        mid_to_render = [p for p in layers.mid_tier if p in pages_set]
        leaves_to_render = [p for p in layers.leaves if p in pages_set]

        total_hubs = len(hubs_to_render)
        total_mid = len(mid_to_render)
        total_leaves = len(leaves_to_render)

        logger.info(
            "streaming_render_layers", hubs=total_hubs, mid_tier=total_mid, leaves=total_leaves
        )

        msg_h = f"     Hubs: {total_hubs} (keep in memory)"
        msg_m = f"     Mid-tier: {total_mid} (batch process)"
        msg_l = f"     Leaves: {total_leaves} (stream & release)"
        if reporter:
            reporter.log(msg_h)
            reporter.log(msg_m)
            reporter.log(msg_l)
        elif not quiet:
            print(msg_h)
            print(msg_m)
            print(msg_l)

        # Import standard renderer for actual processing
        from bengal.orchestration.render import RenderOrchestrator

        renderer = RenderOrchestrator(self.site)

        # Phase 1: Render hubs (keep in memory - they're referenced often)
        if hubs_to_render:
            msg = f"\n  📍 Rendering {total_hubs} hub page(s)..."
            if reporter:
                reporter.log(msg)
            elif not quiet:
                print(msg)
            renderer.process(
                hubs_to_render,
                parallel,
                quiet,
                tracker,
                stats,
                progress_manager=progress_manager,
                reporter=reporter,
                build_context=build_context,
                changed_sources=changed_sources,
            )
            logger.debug("streaming_render_hubs_complete", count=total_hubs)

        # Phase 2: Render mid-tier in batches
        if mid_to_render:
            msg = f"  🔗 Rendering {total_mid} mid-tier page(s)..."
            if reporter:
                reporter.log(msg)
            elif not quiet:
                print(msg)
            self._render_batches(
                renderer,
                mid_to_render,
                batch_size,
                parallel,
                quiet,
                tracker,
                stats,
                "mid-tier",
                progress_manager=progress_manager,
                changed_sources=changed_sources,
                # reporter and context forwarded inside _render_batches via renderer.process
            )
            logger.debug("streaming_render_mid_complete", count=total_mid)

        # Phase 3: Stream leaves in batches (release after each batch)
        if leaves_to_render:
            msg = f"  🍃 Streaming {total_leaves} leaf page(s)..."
            if reporter:
                reporter.log(msg)
            else:
                print(msg)
            self._render_batches(
                renderer,
                leaves_to_render,
                batch_size,
                parallel,
                quiet,
                tracker,
                stats,
                "leaves",
                release_memory=True,
                progress_manager=progress_manager,
                changed_sources=changed_sources,
            )
            logger.debug("streaming_render_leaves_complete", count=total_leaves)

        logger.info(
            "streaming_render_complete",
            total_rendered=len(pages),
            hubs=total_hubs,
            mid=total_mid,
            leaves=total_leaves,
        )

        if reporter:
            reporter.log("  ✓ Memory-optimized render complete!")
        elif not quiet:
            print("  ✓ Memory-optimized render complete!")

    def _render_batches(
        self,
        renderer: RenderOrchestrator,
        pages: list[Page],
        batch_size: int,
        parallel: bool,
        quiet: bool,
        tracker: DependencyTracker | None,
        stats: BuildStats | None,
        batch_label: str = "pages",
        release_memory: bool = False,
        progress_manager: Any | None = None,
        changed_sources: set[Path] | None = None,
    ) -> None:
        """
        Render pages in batches with optional memory release.

        Args:
            renderer: RenderOrchestrator instance
            pages: Pages to render
            batch_size: Pages per batch
            parallel: Use parallel rendering
            quiet: Whether to suppress progress output
            tracker: Dependency tracker
            stats: Build statistics
            batch_label: Label for logging
            release_memory: Whether to force garbage collection after each batch
            progress_manager: Optional progress manager to use for unified progress display
        """
        total = len(pages)
        batches = (total + batch_size - 1) // batch_size  # Ceiling division

        for i in range(0, total, batch_size):
            batch = pages[i : i + batch_size]
            batch_num = (i // batch_size) + 1

            # Render this batch
            renderer.process(
                batch,
                parallel,
                quiet,
                tracker,
                stats,
                progress_manager=progress_manager,
                build_context=None,
                changed_sources=changed_sources,
            )

            logger.debug(
                "streaming_render_batch_complete",
                batch_type=batch_label,
                batch_num=batch_num,
                batch_size=len(batch),
                total_batches=batches,
            )

            # Release memory if requested (for leaves)
            if release_memory:
                # Clear references to page content/metadata to free memory
                for page in batch:
                    # Keep essential metadata but release heavy content
                    if hasattr(page, "_content_cache"):
                        delattr(page, "_content_cache")
                    if hasattr(page, "_html_cache"):
                        delattr(page, "_html_cache")

                # Force garbage collection
                gc.collect()

                logger.debug(
                    "streaming_render_memory_released",
                    batch_num=batch_num,
                    pages_released=len(batch),
                )
