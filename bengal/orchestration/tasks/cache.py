"""Task: save_cache -- persist build cache and provenance."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip in dry-run mode."""
    opts = ctx._build_options
    return bool(opts and opts.dry_run)


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.finalization import (
        phase_collect_stats,
        phase_finalize,
    )
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)
    orchestrator = ctx._orchestrator
    pages_to_build = ctx.pages_to_build or []
    assets_to_process = ctx.assets_to_process or []

    # Phase 18: Save caches in parallel
    cache_start = time.perf_counter()

    def _save_main() -> None:
        orchestrator.incremental.save_cache(pages_to_build, assets_to_process)

    def _save_generated() -> None:
        gpc = ctx._generated_page_cache
        if gpc:
            gpc.save()

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="CacheSave") as pool:
        futures = [pool.submit(_save_main), pool.submit(_save_generated)]
        for future in as_completed(futures):
            future.result()

    cache_ms = (time.perf_counter() - cache_start) * 1000
    if ctx.cli is not None:
        ctx.cli.phase("Cache save", duration_ms=cache_ms)
    logger.info("cache_saved")

    # Phase 19: Collect stats
    phase_collect_stats(orchestrator, ctx.build_start, cli=ctx.cli)

    # Phase 19.5: Finalize error session
    orchestrator._finalize_error_session()

    # Populate changed_outputs for hot reload
    if ctx.output_collector is not None:
        ctx.stats.changed_outputs = ctx.output_collector.get_outputs()

    # Save provenance cache
    if hasattr(orchestrator, "_provenance_filter"):
        from bengal.orchestration.build.provenance_filter import save_provenance_cache

        save_provenance_cache(orchestrator)

    # Phase 21: Finalize build
    opts = ctx._build_options
    verbose = opts.verbose if opts else False
    collector = None  # PerformanceCollector handled in switchover
    phase_finalize(orchestrator, verbose, collector)


TASK = BuildTask(
    name="save_cache",
    requires=frozenset({"postprocess_outputs", "health_report", "orchestrator"}),
    produces=frozenset({"cache_saved"}),
    execute=_execute,
    skip_if=_skip,
)
