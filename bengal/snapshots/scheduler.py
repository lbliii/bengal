"""
Wave scheduler for optimized parallel rendering.

Supports two rendering strategies:
1. Template-first batching (default) - Groups pages by template for CPU cache locality
2. Topological waves - Renders in section order for content-based locality

All data access is from frozen snapshot (lock-free).

"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.snapshots.scout import ScoutThread
    from bengal.snapshots.types import SiteSnapshot

from bengal.snapshots.utils import (
    ProgressManagerProtocol,
    RenderProgressTracker,
    resolve_template_name,
)
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class RenderStats:
    """Statistics from rendering."""

    def __init__(self) -> None:
        self.pages_rendered = 0
        self.files_written = 0
        self.errors: list[tuple[Path, Exception]] = []
        self.template_batches: dict[str, int] = {}  # template -> page count
        self.batch_times_ms: dict[str, float] = {}  # template -> render time


class WaveScheduler:
    """
    Optimized parallel renderer with template-first batching.

    Default strategy groups pages by template to maximize cache locality.
    When all pages using the same template are rendered together:

    1. Kida's template cache returns the same compiled Template object
    2. The compiled Python code object stays in CPU instruction cache
    3. Filter/test lookups hit warm dict caches

    Uses snapshot for pre-computed data, renders actual Page objects.
    """

    def __init__(
        self,
        snapshot: SiteSnapshot,
        site: Any,  # Site type
        tracker: Any | None,  # DependencyTracker type
        quiet: bool,
        stats: Any | None,  # BuildStats type
        build_context: Any | None,  # BuildContext type
        max_workers: int = 4,
        write_behind: Any | None = None,  # WriteBehindCollector type
        strategy: str = "template_first",  # "template_first" or "topological"
        progress_manager: ProgressManagerProtocol | None = None,
    ):
        self.snapshot = snapshot
        self.site = site
        self.tracker = tracker
        self.quiet = quiet
        self.stats = stats
        self.build_context = build_context
        self.max_workers = max_workers
        self._write_behind = write_behind
        self._strategy = strategy
        self._progress_manager = progress_manager

        # Create mapping from snapshot pages to actual pages
        self._page_map: dict[Path, Page] = {}
        for page in site.pages:
            self._page_map[page.source_path] = page

        # Pre-build shared context (same for all pages) - major optimization
        self._shared_context: dict[str, Any] | None = None

        # Progress tracking (created per-render to reset count)
        self._progress_tracker: RenderProgressTracker | None = None

    def _build_shared_context(self) -> dict[str, Any]:
        """
        Pre-build context that's identical for all pages.

        This includes site, config, menus, theme - values that don't change
        between pages. Building once and reusing saves ~10-15% render time.
        """
        if self._shared_context is not None:
            return self._shared_context

        from bengal.rendering.context import _get_global_contexts

        # Get cached global contexts (site, config, theme wrappers)
        self._shared_context = _get_global_contexts(self.site)

        # Add snapshot reference if available
        if self.snapshot:
            self._shared_context["_snapshot"] = self.snapshot

        return self._shared_context

    def render_all(self, pages_to_build: list[Page]) -> RenderStats:
        """
        Render pages using the configured strategy.

        Default is template-first batching for CPU cache optimization.

        Args:
            pages_to_build: List of actual Page objects to render

        Returns:
            RenderStats with rendering statistics
        """
        if self._strategy == "template_first":
            return self._render_template_first(pages_to_build)
        return self._render_topological_waves(pages_to_build)

    def _render_template_first(self, pages_to_build: list[Page]) -> RenderStats:
        """
        Render pages grouped by template for cache locality.

        This strategy maximizes cache efficiency by rendering all pages
        using the same template together before moving to the next:

        - Kida's template cache hits (same Template object reused)
        - Python bytecode stays in CPU instruction cache
        - Filter/test dict lookups hit warm caches

        Performance: ~20-30% faster than random order on template-heavy sites.
        """
        from bengal.rendering.pipeline import RenderingPipeline
        from bengal.rendering.pipeline.thread_local import thread_local
        from bengal.utils.paths.url_strategy import URLStrategy

        stats = RenderStats()

        # Filter to pages we can render
        pages_to_render = [p for p in pages_to_build if p.source_path in self._page_map]

        if not pages_to_render:
            if pages_to_build:
                logger.warning(
                    "no_pages_in_snapshot",
                    pages_requested=len(pages_to_build),
                    pages_in_snapshot=len(self._page_map),
                )
            return stats

        # Initialize progress tracker
        total_pages = len(pages_to_render)
        self._progress_tracker = RenderProgressTracker(self._progress_manager, self.site)

        # Pre-process: Set output paths
        for page in pages_to_render:
            if not page.output_path:
                page.output_path = URLStrategy.compute_regular_page_output_path(page, self.site)

        # Build shared context once (caches in self._shared_context)
        self._build_shared_context()

        # Create template engine
        from bengal.rendering.engines import create_engine

        profile_templates = (
            getattr(self.build_context, "profile_templates", False) if self.build_context else False
        )
        template_engine = create_engine(self.site, profile=profile_templates)

        # Precompile templates used by pages we're about to render
        # This warms Kida's bytecode cache before parallel rendering begins
        if hasattr(template_engine, "precompile_templates"):
            templates_to_precompile = {resolve_template_name(p) for p in pages_to_render}

            # Type guard: hasattr check ensures precompile_templates exists
            precompile_method = template_engine.precompile_templates
            precompiled = precompile_method(list(templates_to_precompile))
            logger.debug(
                "templates_precompiled",
                count=precompiled,
                templates=len(templates_to_precompile),
            )

        # Start scout thread
        scout: ScoutThread | None = None
        from bengal.snapshots.scout import ScoutThread

        scout = ScoutThread(self.snapshot, template_engine)
        scout.start()

        try:
            # Group pages by template using snapshot's pre-computed groups
            template_to_pages: dict[str, list[Page]] = {}

            # Build attention lookup from snapshot
            attention_by_path: dict[Path, float] = {}
            for page_snap in self.snapshot.pages:
                attention_by_path[page_snap.source_path] = page_snap.attention_score

            for page in pages_to_render:
                template_name = resolve_template_name(page)
                if template_name not in template_to_pages:
                    template_to_pages[template_name] = []
                template_to_pages[template_name].append(page)

            # Sort pages within each template group by attention (high-value first)
            # This renders index pages, featured content, and recent pages first
            for template_name in template_to_pages:
                template_to_pages[template_name].sort(
                    key=lambda p: -attention_by_path.get(p.source_path, 0.0)
                )

            # Sort templates by page count (most-used first for better cache warming)
            sorted_templates = sorted(
                template_to_pages.keys(), key=lambda t: -len(template_to_pages[t])
            )

            logger.debug(
                "template_first_batching",
                templates=len(sorted_templates),
                pages=len(pages_to_render),
                distribution={t: len(template_to_pages[t]) for t in sorted_templates[:5]},
            )

            # Render by template batch
            with ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="Bengal-Render",
            ) as executor:
                for template_idx, template_name in enumerate(sorted_templates):
                    batch_pages = template_to_pages[template_name]
                    if not batch_pages:
                        continue

                    batch_start = time.perf_counter()

                    # Signal scout to warm this template
                    if scout:
                        scout._worker_wave = template_idx + 1

                    def process_page(page: Page) -> Page:
                        """Process page with thread-local pipeline."""
                        if not hasattr(thread_local, "pipeline"):
                            thread_local.pipeline = RenderingPipeline(
                                self.site,
                                self.tracker,
                                quiet=self.quiet,
                                build_stats=self.stats,
                                build_context=self.build_context,
                                block_cache=None,
                                write_behind=self._write_behind,
                            )
                        thread_local.pipeline.process_page(page)
                        return page

                    # Submit all pages in this template batch
                    futures = {executor.submit(process_page, page): page for page in batch_pages}

                    # Collect results and update progress
                    for future in as_completed(futures):
                        page = futures[future]
                        try:
                            rendered_page = future.result()
                            stats.pages_rendered += 1
                            self._progress_tracker.increment(rendered_page)
                        except Exception as e:
                            stats.errors.append((page.source_path, e))

                    batch_time = (time.perf_counter() - batch_start) * 1000
                    stats.template_batches[template_name] = len(batch_pages)
                    stats.batch_times_ms[template_name] = batch_time

            # Final progress update to ensure 100%
            self._progress_tracker.finalize(total_pages)

        finally:
            if scout:
                scout.stop()
                scout.join(timeout=1.0)

            if self._write_behind:
                stats.files_written = self._write_behind.flush_and_close()

        return stats

    def _render_topological_waves(self, pages_to_build: list[Page]) -> RenderStats:
        """
        Render pages using topological waves (section order).

        This strategy groups pages by section for content-based locality,
        useful when sections have interdependencies.
        """
        from bengal.rendering.pipeline import RenderingPipeline
        from bengal.rendering.pipeline.thread_local import thread_local
        from bengal.utils.paths.url_strategy import URLStrategy

        stats = RenderStats()

        pages_to_render = [p for p in pages_to_build if p.source_path in self._page_map]

        if not pages_to_render and pages_to_build:
            logger.warning(
                "no_pages_in_snapshot",
                pages_requested=len(pages_to_build),
                pages_in_snapshot=len(self._page_map),
            )

        # Initialize progress tracker
        total_pages = len(pages_to_render)
        self._progress_tracker = RenderProgressTracker(self._progress_manager, self.site)

        for page in pages_to_render:
            if not page.output_path:
                page.output_path = URLStrategy.compute_regular_page_output_path(page, self.site)

        from bengal.rendering.engines import create_engine

        profile_templates = (
            getattr(self.build_context, "profile_templates", False) if self.build_context else False
        )
        template_engine = create_engine(self.site, profile=profile_templates)

        scout: ScoutThread | None = None
        from bengal.snapshots.scout import ScoutThread

        scout = ScoutThread(self.snapshot, template_engine)
        scout.start()

        try:
            page_to_wave: dict[Path, int] = {}
            for wave_idx, wave in enumerate(self.snapshot.topological_order):
                for page_snapshot in wave:
                    page_to_wave[page_snapshot.source_path] = wave_idx

            waves: dict[int, list[Page]] = {}
            orphan_pages: list[Page] = []

            for page in pages_to_render:
                wave_idx = page_to_wave.get(page.source_path)
                if wave_idx is not None:
                    if wave_idx not in waves:
                        waves[wave_idx] = []
                    waves[wave_idx].append(page)
                else:
                    orphan_pages.append(page)

            if orphan_pages:
                max_wave = max(waves.keys()) if waves else -1
                waves[max_wave + 1] = orphan_pages

            with ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="Bengal-Render",
            ) as executor:
                wave_num = 0

                for wave_idx in sorted(waves.keys()):
                    wave_pages = waves[wave_idx]
                    if not wave_pages:
                        continue

                    wave_num += 1
                    if scout:
                        scout._worker_wave = wave_num

                    def process_page_with_pipeline(page: Page) -> Page:
                        if not hasattr(thread_local, "pipeline"):
                            thread_local.pipeline = RenderingPipeline(
                                self.site,
                                self.tracker,
                                quiet=self.quiet,
                                build_stats=self.stats,
                                build_context=self.build_context,
                                block_cache=None,
                                write_behind=self._write_behind,
                            )
                        thread_local.pipeline.process_page(page)
                        return page

                    futures = {
                        executor.submit(process_page_with_pipeline, page): page
                        for page in wave_pages
                    }

                    for future in as_completed(futures):
                        page = futures[future]
                        try:
                            rendered_page = future.result()
                            stats.pages_rendered += 1
                            self._progress_tracker.increment(rendered_page)
                        except Exception as e:
                            stats.errors.append((page.source_path, e))

            # Final progress update to ensure 100%
            self._progress_tracker.finalize(total_pages)

        finally:
            if scout:
                scout.stop()
                scout.join(timeout=1.0)

            if self._write_behind:
                stats.files_written = self._write_behind.flush_and_close()

        return stats
