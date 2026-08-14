"""
Finalization sequencing: postprocess, caches, stats, health, finalize.

Does not add phases. Plugin hook timing around finalization and health
matches the former inline `BuildOrchestrator.build()` body.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bengal.orchestration.stats import ReloadHint
from bengal.protocols.capabilities import HasErrors

from . import finalization

if TYPE_CHECKING:
    from .session import BuildSession


def run_finalization_phases(session: BuildSession) -> None:
    """Run phases 17–21 including serve-ready skips and provenance save."""
    orchestrator = session.orchestrator
    cli = session.cli
    ctx = session.ctx
    pages_to_build = session.pages_to_build
    output_collector = session.output_collector
    artifact_collector = session.artifact_collector
    serve_ready_policy = session.serve_ready_policy

    session.run_plugin_phase("pre_finalization")
    session.notify_phase_start("finalization")
    finalization_start = time.time()

    # Phase 17: Post-processing
    finalization.phase_postprocess(
        orchestrator,
        cli,
        not session.force_sequential,
        ctx,
        session.incremental,
        collector=output_collector,
        enabled_task_names={"special pages"} if serve_ready_policy else None,
        run_asset_audit=not serve_ready_policy,
    )
    orchestrator.stats.record_phase_timing("Post-process", orchestrator.stats.postprocess_time_ms)

    from bengal.orchestration.build.artifact_inventory import populate_artifact_inventory

    if not serve_ready_policy:
        if ctx is not None:
            ctx.output_collector = output_collector
            ctx.artifact_collector = artifact_collector
        artifact_inventory_start = time.perf_counter()
        populate_artifact_inventory(orchestrator.site, ctx)
        orchestrator.stats.post_render_timings_ms["artifact_inventory"] = round(
            (time.perf_counter() - artifact_inventory_start) * 1000,
            1,
        )
        orchestrator.stats.record_phase_timing(
            "Artifact inventory",
            orchestrator.stats.post_render_timings_ms["artifact_inventory"],
        )

    if session.generated_page_cache and not serve_ready_policy:
        _update_generated_page_cache(session)

    _save_caches(session)

    # Phase 19: Collect Final Stats
    stats_start = time.perf_counter()
    finalization.phase_collect_stats(orchestrator, session.build_start, cli=cli)
    orchestrator.stats.post_render_timings_ms["stats"] = round(
        (time.perf_counter() - stats_start) * 1000,
        1,
    )
    orchestrator.stats.record_phase_timing(
        "Stats", orchestrator.stats.post_render_timings_ms["stats"]
    )

    # Phase 19.5: Finalize Error Session (track build errors for pattern detection)
    orchestrator._finalize_error_session()

    orchestrator.stats.changed_outputs = output_collector.get_outputs()
    _set_reload_hint(session)

    if orchestrator.stats.changed_outputs:
        orchestrator.logger.debug(
            "output_collector_results",
            total_outputs=len(orchestrator.stats.changed_outputs),
            html_count=sum(
                1 for o in orchestrator.stats.changed_outputs if o.output_type.value == "html"
            ),
            css_count=sum(
                1 for o in orchestrator.stats.changed_outputs if o.output_type.value == "css"
            ),
        )
    else:
        orchestrator.logger.warning(
            "output_collector_empty",
            pages_rendered=len(pages_to_build) if pages_to_build else 0,
        )

    finalization_duration_ms = (time.time() - finalization_start) * 1000
    session.notify_phase_complete(
        "finalization",
        finalization_duration_ms,
        "post-processing complete",
    )
    session.run_plugin_phase("post_finalization")

    if serve_ready_policy:
        orchestrator.stats.post_render_timings_ms["health"] = 0
        if cli is not None:
            cli.detail(
                "health check deferred for serve-ready build",
                indent=1,
                icon=cli.icons.arrow,
            )
        orchestrator.logger.info(
            "health_check_deferred", policy=session.options.completion_policy.value
        )
    else:
        session.run_plugin_phase("pre_health")
        session.notify_phase_start("health")
        health_start = time.time()

        with orchestrator.logger.phase("health_check"):
            finalization.run_health_check(
                orchestrator,
                profile=session.profile,
                incremental=session.incremental,
                build_context=ctx,
            )

        health_duration_ms = (time.time() - health_start) * 1000
        orchestrator.stats.post_render_timings_ms["health"] = round(health_duration_ms, 1)
        health_report = getattr(orchestrator.stats, "health_report", None)
        health_summary = ""
        if health_report:
            passed = health_report.total_passed
            total = health_report.total_checks
            health_summary = f"{passed}/{total} checks passed"
        session.notify_phase_complete("health", health_duration_ms, health_summary)
        session.run_plugin_phase("post_health")

    if hasattr(orchestrator, "_provenance_filter") and not serve_ready_policy:
        from bengal.orchestration.build.provenance_filter import save_provenance_cache

        provenance_save_start = time.perf_counter()
        save_provenance_cache(orchestrator)
        orchestrator.stats.post_render_timings_ms["provenance_save"] = round(
            (time.perf_counter() - provenance_save_start) * 1000,
            1,
        )
        orchestrator.stats.record_phase_timing(
            "Provenance save",
            orchestrator.stats.post_render_timings_ms["provenance_save"],
        )

    # Phase 21: Finalize Build
    finalize_start = time.perf_counter()
    orchestrator.stats.build_time_ms = (time.time() - session.build_start) * 1000
    finalization.phase_finalize(orchestrator, session.verbose, session.collector)
    orchestrator.stats.record_phase_timing(
        "Finalize",
        (time.perf_counter() - finalize_start) * 1000,
    )
    orchestrator.stats.build_time_ms = (time.time() - session.build_start) * 1000

    if orchestrator.stats.template_errors or (
        isinstance(orchestrator.stats, HasErrors) and orchestrator.stats.errors
    ):
        from bengal.rendering.pipeline.output import cleanup_fast_writes

        cleaned = cleanup_fast_writes()
        if cleaned:
            orchestrator.logger.info("fast_write_cleanup", files_removed=cleaned)

    orchestrator.site.set_build_state(None)

    session.fire_build_complete()


def _update_generated_page_cache(session: BuildSession) -> None:
    """Refresh GeneratedPageCache entries for rendered tag pages."""
    orchestrator = session.orchestrator
    cache = session.cache
    generated_page_cache = session.generated_page_cache
    pages_to_build = session.pages_to_build or []

    content_hash_lookup: dict[str, str] = {}
    if cache and hasattr(cache, "parsed_content"):
        for path_str, entry in cache.parsed_content.items():
            if isinstance(entry, dict):
                content_hash = entry.get("metadata_hash", "")
                if content_hash:
                    content_hash_lookup[path_str] = content_hash

    updated_entries = 0
    tag_pages_found = 0
    tag_pages_with_posts = 0
    for page in pages_to_build:
        if page.metadata.get("type") == "tag" and page.metadata.get("_generated"):
            tag_pages_found += 1
            tag_slug = page.metadata.get("_tag_slug", "")
            member_pages = page.metadata.get("_posts", [])
            if tag_slug and member_pages:
                tag_pages_with_posts += 1
                generated_page_cache.update(
                    page_type="tag",
                    page_id=tag_slug,
                    member_pages=member_pages,
                    content_cache=content_hash_lookup,
                    rendered_html="",
                    generation_time_ms=0,
                )
                updated_entries += 1

    orchestrator.logger.info(
        "generated_page_cache_updated",
        entries=updated_entries,
        tag_pages_found=tag_pages_found,
        tag_pages_with_posts=tag_pages_with_posts,
        content_hash_count=len(content_hash_lookup),
    )


def _save_caches(session: BuildSession) -> None:
    """Phase 18: save main and generated-page caches (or defer for serve-ready)."""
    orchestrator = session.orchestrator
    cli = session.cli
    ctx = session.ctx
    generated_page_cache = session.generated_page_cache

    cache_start = time.perf_counter()

    def _save_main_cache() -> None:
        saved = orchestrator.incremental.save_cache(
            session.pages_to_build,
            session.assets_to_process,
            build_context=ctx,
        )
        if saved is False:
            from bengal.errors import BengalCacheError, ErrorCode

            raise BengalCacheError(
                "Build cache could not be saved.",
                code=ErrorCode.A004,
                suggestion=(
                    "Check disk space and permissions. Incremental builds may be stale "
                    "until the cache can be saved."
                ),
            )

    def _save_generated_cache() -> None:
        if generated_page_cache:
            generated_page_cache.save()

    from bengal.utils.concurrency.work_scope import WorkScope

    if session.serve_ready_policy:
        orchestrator.stats.post_render_timings_ms["cache_save"] = 0
        if cli is not None:
            cli.detail("cache save deferred for serve-ready build", indent=1, icon=cli.icons.arrow)
        orchestrator.logger.info(
            "cache_save_deferred", policy=session.options.completion_policy.value
        )
    else:
        with WorkScope("CacheSave", max_workers=2) as scope:
            results = scope.map(lambda fn: fn(), [_save_main_cache, _save_generated_cache])

        for r in results:
            if r.error:
                raise r.error

        cache_duration_ms = (time.perf_counter() - cache_start) * 1000
        orchestrator.stats.post_render_timings_ms["cache_save"] = round(cache_duration_ms, 1)
        orchestrator.stats.record_phase_timing("Cache save", cache_duration_ms)
        if cli is not None:
            cli.phase("Cache save", duration_ms=cache_duration_ms)
        orchestrator.logger.info("cache_saved")


def _set_reload_hint(session: BuildSession) -> None:
    """Compute reload_hint for smarter dev server decisions."""
    stats = session.orchestrator.stats
    outputs = stats.changed_outputs
    if stats.dry_run:
        stats.reload_hint = ReloadHint.NONE
    elif not outputs:
        stats.reload_hint = None
    elif any(o.output_type.value == "html" for o in outputs):
        stats.reload_hint = ReloadHint.FULL
    elif all(o.output_type.value == "css" for o in outputs):
        stats.reload_hint = ReloadHint.CSS_ONLY
    else:
        stats.reload_hint = ReloadHint.FULL
