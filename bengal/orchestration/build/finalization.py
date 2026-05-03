"""
Finalization phases for build orchestration.

Phases 17-21: Post-processing, cache save, collect stats, health check, finalize build.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.output import OutputCollector
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.orchestration.build_context import BuildContext
    from bengal.output import CLIOutput
    from bengal.utils.observability.performance_collector import PerformanceCollector
    from bengal.utils.observability.profile import BuildProfile


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

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: Pages that were built
        assets_to_process: Assets that were processed
        cli: CLI output (optional) for timing display

    """
    with orchestrator.logger.phase("cache_save"):
        start = time.perf_counter()
        orchestrator.incremental.save_cache(pages_to_build, assets_to_process)
        duration_ms = (time.perf_counter() - start) * 1000
        if cli is not None:
            cli.phase("Cache save", duration_ms=duration_ms)
        orchestrator.logger.info("cache_saved")


def phase_collect_stats(
    orchestrator: BuildOrchestrator, build_start: float, cli: CLIOutput | None = None
) -> None:
    """
    Phase 19: Collect Final Stats.

    Collects final build statistics.

    Args:
        orchestrator: Build orchestrator instance
        build_start: Build start time for duration calculation
        cli: CLI output (optional) for timing display

    """
    start = time.perf_counter()
    site = orchestrator.site
    orchestrator.stats.regular_pages = len(site.regular_pages)
    orchestrator.stats.generated_pages = len(site.generated_pages)

    # Single pass over site.pages for total count and autodoc detection
    from bengal.utils.autodoc import is_autodoc_page

    total = 0
    autodoc = 0
    for p in site.pages:
        total += 1
        if is_autodoc_page(p):
            autodoc += 1
    orchestrator.stats.total_pages = total
    orchestrator.stats.autodoc_pages = autodoc
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

    # Build rendering-owned link registry before health checks (zero-cost: reuses toc_items)
    from bengal.rendering.reference_registry import build_link_registry

    orchestrator.site.link_registry = build_link_registry(orchestrator.site)

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
        cli.render_write(
            "validation_report.kida",
            **report.format_validation_report(verbose=True, show_suggestions=True),
        )
    elif report.has_errors() or report.has_warnings():
        cli.render_write(
            "validation_report.kida",
            **report.format_validation_report(verbose=False, show_suggestions=False),
        )

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

    Args:
        orchestrator: Build orchestrator instance
        verbose: Whether verbose mode is enabled
        collector: Performance collector (if enabled)

    """
    # Collect memory metrics and save performance data (if enabled by profile)
    if collector:
        orchestrator.stats = collector.end_build(orchestrator.stats)
        if collector.regression_pct is not None:
            orchestrator.stats.regression_pct = collector.regression_pct
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
    except Exception:  # noqa: S110
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
