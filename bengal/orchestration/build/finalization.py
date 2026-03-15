"""
Finalization phases for build orchestration.

Phases 17-21: Post-processing, cache save, collect stats, health check, finalize build.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from bengal.orchestration.stats import ReloadHint
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.generated_page_cache import GeneratedPageCache
    from bengal.core.output import OutputCollector
    from bengal.core.page import Page
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.output import CLIOutput
    from bengal.utils.observability.performance_collector import PerformanceCollector
    from bengal.utils.observability.profile import BuildProfile

logger = get_logger(__name__)


def phase_postprocess(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    parallel: bool,
    ctx: BuildContext | Any | None,
    incremental: bool,
    collector: OutputCollector | None = None,
) -> None:
    """
    Phase 17: Post-processing.

    Runs post-build tasks: sitemap, RSS, output formats, validation.

    Complexity: O(n) — where n = number of pages
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        parallel: Whether to use parallel processing (deprecated, always False)
        ctx: Build context
        incremental: Whether this is an incremental build
        collector: Optional output collector for hot reload tracking

    """
    # Enable parallel post-processing for independent tasks (sitemap, RSS, output formats)
    # Tasks are independent and thread-safe, so parallel execution is safe
    with orchestrator.logger.phase("postprocessing", parallel=parallel):
        postprocess_start = time.time()

        orchestrator.postprocess.run(
            parallel=parallel,
            progress_manager=None,
            build_context=ctx,
            incremental=incremental,
            collector=collector,
        )

        orchestrator.stats.postprocess_time_ms = (time.time() - postprocess_start) * 1000

        # Phase 3: Drain asset fallback aggregator (render + postprocess complete)
        from bengal.rendering.assets import drain_asset_fallback_aggregator

        fallback_count, fallback_samples = drain_asset_fallback_aggregator()
        if orchestrator.stats is not None:
            orchestrator.stats.asset_manifest_fallback_count = fallback_count
            orchestrator.stats.asset_manifest_fallback_samples = fallback_samples
        if fallback_count > 0:
            strict = getattr(ctx, "strict", False) or getattr(
                orchestrator.stats, "strict_mode", False
            )
            if strict:
                from bengal.errors import BengalError

                raise BengalError(
                    f"Build failed: {fallback_count} asset manifest fallback(s) in production mode.",
                    suggestion="Ensure asset_manifest_context() wraps all template rendering paths. "
                    f"Sample paths: {fallback_samples[:5]}",
                )
            orchestrator.logger.warning(
                "asset_manifest_fallback_summary",
                count=fallback_count,
                samples=fallback_samples[:5],
                hint="ContextVar not set in some paths - check asset_manifest_context() coverage",
            )

        # Show phase completion
        cli.phase("Post-process", duration_ms=orchestrator.stats.postprocess_time_ms)

        orchestrator.logger.info("postprocessing_complete")


def phase_cache_save(
    orchestrator: BuildOrchestrator,
    pages_to_build: list[Any],
    assets_to_process: list[Any],
    cli: CLIOutput | None = None,
) -> None:
    """
    Phase 18: Save Cache.

    Persists build cache including URL claims for incremental build safety.

    Saves build cache for future incremental builds.

    Complexity: O(n + a) — where n = pages, a = assets
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: Pages that were built
        assets_to_process: Assets that were processed
        cli: CLI output (optional) for timing display

    """
    with orchestrator.logger.phase("cache_save"):
        start = time.perf_counter()
        # RFC: rfc-cache-generation-id — set before save for divergence detection
        if cache := getattr(orchestrator.incremental, "cache", None):
            cache.build_id = getattr(orchestrator, "_build_id", None)
        orchestrator.incremental.save_cache(pages_to_build, assets_to_process)
        duration_ms = (time.perf_counter() - start) * 1000
        if cli is not None:
            cli.phase("Cache save", duration_ms=duration_ms)
        orchestrator.logger.info("cache_saved")


def phase_update_generated_cache(
    orchestrator: BuildOrchestrator,
    pages_to_build: list[Page],
    cache: BuildCache | None,
    generated_page_cache: GeneratedPageCache | None,
) -> None:
    """
    Update GeneratedPageCache for tag pages that were rendered.

    RFC: Output Cache Architecture - enables skipping unchanged tag pages
    on future builds if member content hasn't changed.

    Complexity: O(n) — where n = number of pages
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: Pages that were rendered
        cache: Build cache (for parsed_content lookup)
        generated_page_cache: Cache to update (or None to skip)

    """
    if not generated_page_cache:
        return

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
    from bengal.core.page.kind import PageKind

    for page in pages_to_build:
        if PageKind.from_page(page) == PageKind.TAG and page.is_generated:
            tag_pages_found += 1
            tag_slug = page.tag_slug or ""
            member_pages = page.internal_posts
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

    logger.info(
        "generated_page_cache_updated",
        entries=updated_entries,
        tag_pages_found=tag_pages_found,
        tag_pages_with_posts=tag_pages_with_posts,
        content_hash_count=len(content_hash_lookup),
    )


def phase_cache_save_parallel(
    orchestrator: BuildOrchestrator,
    pages_to_build: list[Any],
    assets_to_process: list[Any],
    generated_page_cache: GeneratedPageCache | None,
    cli: CLIOutput | None = None,
) -> None:
    """
    Phase 18: Save caches in parallel (main cache + generated page cache).

    Runs cache saves concurrently since they're independent I/O operations.

    Complexity: O(n + a) — where n = pages, a = assets
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: Pages that were built
        assets_to_process: Assets that were processed
        generated_page_cache: GeneratedPageCache to save (or None)
        cli: CLI output (optional) for timing display

    """
    cache_start = time.perf_counter()

    # RFC: rfc-cache-generation-id — set before save for divergence detection
    if cache := getattr(orchestrator.incremental, "cache", None):
        cache.build_id = getattr(orchestrator, "_build_id", None)

    def _save_main_cache() -> None:
        orchestrator.incremental.save_cache(pages_to_build, assets_to_process)

    def _save_generated_cache() -> None:
        if generated_page_cache:
            generated_page_cache.save()

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="CacheSave") as executor:
        futures = [
            executor.submit(_save_main_cache),
            executor.submit(_save_generated_cache),
        ]
        for future in as_completed(futures):
            future.result()

    cache_duration_ms = (time.perf_counter() - cache_start) * 1000
    if cli is not None:
        cli.phase("Cache save", duration_ms=cache_duration_ms)
    orchestrator.logger.info("cache_saved")


def phase_compute_reload_hint(
    stats: BuildStats,
    output_collector: OutputCollector | None,
    pages_rendered: int = 0,
) -> None:
    """
    Compute reload_hint from output collector for dev server decisions.

    Populates stats.changed_outputs and stats.reload_hint based on
    what was written during the build.

    Complexity: O(o) — where o = number of outputs
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        stats: BuildStats to update
        output_collector: Output collector with written files (or None)
        pages_rendered: Page count for warning when collector is empty

    """
    stats.changed_outputs = output_collector.get_outputs() if output_collector else []

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

    if stats.changed_outputs:
        logger.debug(
            "output_collector_results",
            total_outputs=len(stats.changed_outputs),
            html_count=sum(1 for o in stats.changed_outputs if o.output_type.value == "html"),
            css_count=sum(1 for o in stats.changed_outputs if o.output_type.value == "css"),
        )
    else:
        logger.warning(
            "output_collector_empty",
            pages_rendered=pages_rendered,
        )


def phase_save_provenance(orchestrator: BuildOrchestrator) -> None:
    """
    Save provenance cache if using provenance-based filtering.

    RFC: rfc-cache-generation-id — sets same build_id as BuildCache.

    Complexity: O(1) — fixed disk write
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        orchestrator: Build orchestrator instance (must have _provenance_filter)

    """
    if hasattr(orchestrator, "_provenance_filter"):
        from bengal.orchestration.build.provenance_orchestration import save_provenance_cache

        orchestrator._provenance_filter.cache.set_build_id(getattr(orchestrator, "_build_id", None))
        save_provenance_cache(orchestrator)


def phase_collect_stats(
    orchestrator: BuildOrchestrator, build_start: float, cli: CLIOutput | None = None
) -> None:
    """
    Phase 19: Collect Final Stats.

    Collects final build statistics.

    Complexity: O(n) — where n = number of pages
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        orchestrator: Build orchestrator instance
        build_start: Build start time for duration calculation
        cli: CLI output (optional) for timing display

    """
    start = time.perf_counter()
    site = orchestrator.site
    orchestrator.stats.total_pages = len(site.pages)
    orchestrator.stats.regular_pages = len(site.regular_pages)
    orchestrator.stats.generated_pages = len(site.generated_pages)
    from bengal.utils.autodoc import is_autodoc_page

    orchestrator.stats.autodoc_pages = sum(1 for p in site.pages if is_autodoc_page(p))
    orchestrator.stats.total_assets = len(orchestrator.site.assets)
    orchestrator.stats.total_sections = len(orchestrator.site.sections)
    orchestrator.stats.taxonomies_count = sum(
        len(terms) for terms in orchestrator.site.taxonomies.values()
    )
    orchestrator.stats.build_time_ms = (time.time() - build_start) * 1000

    # Store stats for health check validators to access
    orchestrator.site._last_build_stats = {
        "build_time_ms": orchestrator.stats.build_time_ms,
        "rendering_time_ms": orchestrator.stats.rendering_time_ms,
        "total_pages": orchestrator.stats.total_pages,
        "autodoc_pages": orchestrator.stats.autodoc_pages,
        "total_assets": orchestrator.stats.total_assets,
        "parallel": orchestrator.stats.parallel,
        "incremental": orchestrator.stats.incremental,
        "skipped": orchestrator.stats.skipped,
        "cache_hits": orchestrator.stats.cache_hits,
        "cache_misses": orchestrator.stats.cache_misses,
        # Block cache statistics (RFC: kida-template-introspection)
        "block_cache_hits": orchestrator.stats.block_cache_hits,
        "block_cache_misses": orchestrator.stats.block_cache_misses,
        "block_cache_site_blocks": orchestrator.stats.block_cache_site_blocks,
        "block_cache_time_saved_ms": orchestrator.stats.block_cache_time_saved_ms,
    }

    from bengal.orchestration.build.artifacts import (
        write_build_time_artifacts,
        write_versioning_artifacts,
    )

    write_build_time_artifacts(orchestrator.site, orchestrator.site._last_build_stats)
    write_versioning_artifacts(orchestrator.site)
    duration_ms = (time.perf_counter() - start) * 1000
    if cli is not None:
        cli.phase("Stats", duration_ms=duration_ms)


def run_health_check(
    orchestrator: BuildOrchestrator,
    profile: BuildProfile | None = None,
    incremental: bool = False,
    build_context: BuildContext | Any | None = None,
) -> None:
    """
    Run health check system with profile-based filtering.

    Different profiles run different sets of validators:
    - WRITER: Basic checks (broken links, SEO)
    - THEME_DEV: Extended checks (performance, templates)
    - DEV: Full checks (all validators)

    Args:
        orchestrator: Build orchestrator instance
        profile: Build profile to use for filtering validators
        incremental: Whether this is an incremental build (enables incremental validation)
        build_context: Optional BuildContext with cached artifacts (e.g., knowledge graph)

    Raises:
        Exception: If strict_mode is enabled and health checks fail

    """
    from bengal.config.defaults import get_feature_config
    from bengal.health import HealthCheck

    # Get normalized health_check config (handles bool or dict)
    health_config = get_feature_config(orchestrator.site.config, "health_check")

    # Get CLI output early for timing display
    from bengal.output import get_cli_output

    cli = get_cli_output()

    if not health_config.get("enabled", True):
        return

    health_start = time.time()

    # Run health checks with profile filtering
    health_check = HealthCheck(orchestrator.site)

    # Pass cache for incremental validation if available
    cache = None
    if incremental and orchestrator.incremental.cache:
        cache = orchestrator.incremental.cache

    report = health_check.run(
        profile=profile,
        incremental=incremental,
        cache=cache,
        build_context=build_context,
    )

    health_time_ms = (time.time() - health_start) * 1000
    orchestrator.stats.health_check_time_ms = health_time_ms

    # Show phase completion timing (before report)
    cli.phase("Health check", duration_ms=health_time_ms)

    # Show parallel execution stats if available (always useful for diagnosing slow builds)
    if health_check.last_stats:
        stats = health_check.last_stats
        if stats.execution_mode == "parallel":
            cli.info(
                f"   {cli.icons.success} {stats.validator_count} validators, {stats.worker_count} workers, "
                f"{stats.speedup:.1f}x speedup"
            )
            # Also show exact validator list + per-validator durations to make slow builds diagnosable.
            # NOTE: ValidatorReport order is non-deterministic in parallel mode (as_completed),
            # so we sort by duration for stable, high-signal output.
            if report.validator_reports:
                ordered = sorted(
                    report.validator_reports, key=lambda r: r.duration_ms, reverse=True
                )
                validators_info = ", ".join(
                    f"{r.validator_name}: {r.duration_ms:.0f}ms" for r in ordered
                )
                cli.info(f"   {cli.icons.info} Validators: {validators_info}")
        # Show slowest validators if health check took > 1 second
        if health_time_ms > 1000 and report.validator_reports:
            slowest = sorted(report.validator_reports, key=lambda r: r.duration_ms, reverse=True)[
                :3
            ]
            slow_info = ", ".join(f"{r.validator_name}: {r.duration_ms:.0f}ms" for r in slowest)
            cli.info(f"   {cli.icons.warning} Slowest: {slow_info}")

            # Show detailed stats for ALL slow validators (helps diagnose perf issues)
            for slow_report in slowest:
                if slow_report.stats and slow_report.duration_ms > 500:
                    cli.info(
                        f"   {cli.icons.info} {slow_report.validator_name}: {slow_report.stats.format_summary()}"
                    )

    if health_config.get("verbose", False):
        if cli.use_rich:
            cli.console.print(report.format_console(verbose=True))
        else:
            # Strip Rich markup for plain text output
            from re import sub

            plain_text = sub(r"\[/?[^\]]+\]", "", report.format_console(verbose=True))
            print(plain_text)
    # Only print if there are issues
    elif report.has_errors() or report.has_warnings():
        if cli.use_rich:
            cli.console.print(report.format_console(verbose=False))
        else:
            # Strip Rich markup for plain text output
            from re import sub

            plain_text = sub(r"\[/?[^\]]+\]", "", report.format_console(verbose=False))
            print(plain_text)

    # Store report in stats
    orchestrator.stats.health_report = report

    # Fail build in strict mode if there are errors
    strict_mode = health_config.get("strict_mode", False)
    if strict_mode and report.has_errors():
        from bengal.errors import BengalError

        raise BengalError(
            f"Build failed health checks: {report.total_errors} error(s) found. "
            "Review output or disable strict_mode.",
            suggestion="Review the health check report above and fix the errors, or set health_check.strict_mode=false",
        )


def phase_finalize(
    orchestrator: BuildOrchestrator, verbose: bool, collector: PerformanceCollector | None
) -> None:
    """
    Phase 21: Finalize Build.

    Performs final cleanup and logging.

    Complexity: O(1) — fixed cleanup
    Budget: < 5% of total build at 1024 pages
    Scaling: < 2.2x per doubling (linear threshold)

    Args:
        orchestrator: Build orchestrator instance
        verbose: Whether verbose mode is enabled
        collector: Performance collector (if enabled)

    """
    # Collect memory metrics and save performance data (if enabled by profile)
    if collector:
        orchestrator.stats = collector.end_build(orchestrator.stats)
        collector.save(orchestrator.stats)

    # Log build completion
    log_data = {
        "duration_ms": orchestrator.stats.build_time_ms,
        "total_pages": orchestrator.stats.total_pages,
        "total_assets": orchestrator.stats.total_assets,
        "success": True,
    }

    # Only add memory metrics if they were collected
    if orchestrator.stats.memory_rss_mb > 0:
        log_data["memory_rss_mb"] = orchestrator.stats.memory_rss_mb
        log_data["memory_heap_mb"] = orchestrator.stats.memory_heap_mb

    orchestrator.logger.info("build_complete", **log_data)

    # Flush any core diagnostics that were collected during the build.
    # These are emitted by core models via a sink/collector rather than logging directly.
    try:
        diagnostics = getattr(orchestrator.site, "diagnostics", None)
        if diagnostics is not None and hasattr(diagnostics, "drain"):
            events = diagnostics.drain()
            for event in events:
                data = getattr(event, "data", {}) or {}
                code = getattr(event, "code", "core_diagnostic")
                level = getattr(event, "level", "info")

                if level == "warning":
                    orchestrator.logger.warning(code, **data)
                elif level == "error":
                    orchestrator.logger.error(code, **data)
                elif level == "debug":
                    orchestrator.logger.debug(code, **data)
                else:
                    orchestrator.logger.info(code, **data)
    except Exception:
        # Diagnostics must never break build finalization.
        pass

    # Restore normal logger console output if we suppressed it
    if not verbose:
        from bengal.utils.observability.logger import set_console_quiet

        set_console_quiet(False)

    # Clear per-key locks from caches to prevent unbounded growth across build sessions
    try:
        from bengal.core.nav_tree import NavTreeCache
        from bengal.rendering.engines.jinja import clear_template_locks
        from bengal.rendering.template_functions.navigation.scaffold import NavScaffoldCache

        NavTreeCache.clear_locks()
        NavScaffoldCache.clear_locks()
        clear_template_locks()
    except ImportError:
        pass  # Modules not available
