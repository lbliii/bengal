"""Task: render_pages -- render all pages to HTML."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when there are no pages to render or in dry-run mode."""
    opts = ctx._build_options
    if opts and opts.dry_run:
        return True
    return not ctx.pages_to_build


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build import rendering

    orchestrator = ctx._orchestrator
    opts = ctx._build_options
    force_sequential = opts.force_sequential if opts else False
    pages_to_build = ctx.pages_to_build or []

    # --- Snapshot creation (after parsing, before rendering) ---
    from bengal.cache.directive_cache import configure_for_site
    from bengal.core.nav_tree import NavTreeCache
    from bengal.rendering.context import _get_global_contexts
    from bengal.snapshots import create_site_snapshot
    from bengal.snapshots.persistence import SnapshotCache

    site_snapshot = create_site_snapshot(ctx.site)
    ctx.snapshot = site_snapshot

    NavTreeCache.set_precomputed(dict(site_snapshot.nav_trees))
    _get_global_contexts(ctx.site, build_context=ctx)
    configure_for_site(ctx.site)

    cache_dir = ctx.site.root_path / ".bengal" / "cache" / "snapshots"
    snapshot_cache = SnapshotCache(cache_dir)
    snapshot_cache.save(site_snapshot)

    # --- Service instantiation ---
    from bengal.services.query import QueryService

    ctx.query_service = QueryService.from_snapshot(site_snapshot)
    try:
        from bengal.services.data import DataService

        ctx.data_service = DataService.from_root(ctx.site.root_path)
    except Exception:
        pass

    # --- Render profiling setup ---
    _render_metrics = None
    _render_profiler_ctx = None
    _use_render_profiling = getattr(ctx.site, "dev_mode", False)

    if _use_render_profiling:
        try:
            from kida.render_accumulator import profiled_render

            _render_profiler_ctx = profiled_render()
            _render_metrics = _render_profiler_ctx.__enter__()
        except ImportError:
            _render_profiler_ctx = None

    # --- Live progress ---
    progress_manager = ctx.progress_manager
    if progress_manager:
        total_pages = len(pages_to_build)
        progress_manager.start()
        progress_manager.add_phase("rendering", "Rendering", total=total_pages)
        progress_manager.start_phase("rendering")

    rendering_start = time.time()

    try:
        render_ctx = rendering.phase_render(
            orchestrator,
            ctx.cli,
            ctx.incremental,
            force_sequential,
            ctx.quiet,
            ctx.verbose,
            ctx.memory_optimized,
            pages_to_build,
            ctx.profile,
            progress_manager,
            ctx.reporter,
            profile_templates=ctx.profile_templates,
            early_context=ctx,
            changed_sources=opts.changed_sources if opts else None,
            collector=ctx.output_collector,
        )
    finally:
        if progress_manager:
            elapsed = (time.time() - rendering_start) * 1000
            progress_manager.complete_phase("rendering", elapsed_ms=elapsed)
            progress_manager.stop()
        if _render_profiler_ctx is not None:
            _render_profiler_ctx.__exit__(None, None, None)

    # Log Kida profiling
    if _render_metrics is not None:
        summary = _render_metrics.summary()
        orchestrator.logger.info(
            "kida_render_profiling",
            total_ms=summary.get("total_ms"),
            block_count=summary.get("block_count"),
            macro_calls=summary.get("macro_calls"),
            include_count=summary.get("include_count"),
            filter_calls=summary.get("filter_calls"),
        )

    if _use_render_profiling:
        try:
            engine = getattr(ctx.site, "template_engine", None)
            if engine is not None and hasattr(engine, "cache_info"):
                orchestrator.logger.info("kida_cache_info", **engine.cache_info())
        except Exception:
            pass

    # Phase 15: Update site pages
    rendering.phase_update_site_pages(
        orchestrator, ctx.incremental, pages_to_build, cli=ctx.cli
    )

    # Phase 16: Track asset dependencies
    rendering.phase_track_assets(
        orchestrator, pages_to_build, cli=ctx.cli, build_context=render_ctx
    )

    # Record provenance
    if hasattr(orchestrator, "_provenance_filter") and pages_to_build:
        from bengal.orchestration.build.provenance_filter import record_all_page_builds

        record_all_page_builds(orchestrator, pages_to_build)

    ctx.stats.rendering_time_ms = (time.time() - rendering_start) * 1000


TASK = BuildTask(
    name="render_pages",
    requires=frozenset({
        "parsed_pages",
        "menu_tree",
        "query_indexes",
        "taxonomy_pages",
        "related_index",
        "asset_manifest",
        "font_css",
    }),
    produces=frozenset({"rendered_pages"}),
    execute=_execute,
    skip_if=_skip,
)
