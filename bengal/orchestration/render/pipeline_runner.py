"""
Shared pipeline runner for parallel page rendering.

Provides process_page_with_pipeline() — a thread-safe helper that gets or creates
a thread-local RenderingPipeline and processes a page. Used by RenderOrchestrator
and WaveScheduler to eliminate duplicated pipeline creation logic.

Thread Safety:
- Uses thread_local from orchestration/render/parallel.py
- When current_generation is provided, recreates pipeline when generation changes
- When current_generation is None (WaveScheduler), uses simple hasattr check
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.rendering.pipeline import RenderingPipeline

from .parallel import thread_local as _thread_local

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats


def process_page_with_pipeline(
    page: Page,
    *,
    site: Site,
    quiet: bool,
    stats: BuildStats | None,
    build_context: BuildContext | None,
    changed_sources: set[Path] | None,
    block_cache: Any,
    highlight_cache: Any,
    output_collector: Any = None,
    write_behind: Any = None,
    current_generation: int | None = None,
) -> None:
    """
    Get or create thread-local pipeline, process page. Thread-safe.

    Args:
        page: Page to render
        site: Site instance
        quiet: Suppress per-page output
        stats: Build statistics tracker
        build_context: Build context for dependency injection
        changed_sources: Set of changed source paths
        block_cache: Block cache for template blocks (or None)
        highlight_cache: Highlight cache
        output_collector: Output collector for hot reload
        write_behind: WriteBehindCollector (WaveScheduler only)
        current_generation: Build generation for staleness check. When provided,
            recreates pipeline when generation changes. When None (WaveScheduler),
            uses simple hasattr check.
    """
    if current_generation is not None:
        needs_new_pipeline = (
            not hasattr(_thread_local, "pipeline")
            or getattr(_thread_local, "pipeline_generation", -1) != current_generation
        )
    else:
        needs_new_pipeline = not hasattr(_thread_local, "pipeline")

    if needs_new_pipeline:
        out_collector = output_collector or (
            build_context.output_collector if build_context else None
        )
        _thread_local.pipeline = RenderingPipeline(
            site,
            quiet=quiet,
            build_stats=stats,
            build_context=build_context,
            output_collector=out_collector,
            changed_sources=changed_sources,
            block_cache=block_cache,
            highlight_cache=highlight_cache,
            write_behind=write_behind,
        )
        if current_generation is not None:
            _thread_local.pipeline_generation = current_generation

    _start = time.perf_counter()
    _thread_local.pipeline.process_page(page)
    page.render_time_ms = (time.perf_counter() - _start) * 1000
