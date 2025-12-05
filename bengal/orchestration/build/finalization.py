"""
Finalization phases for build orchestration.

Phases 17-21: Post-processing, cache save, collect stats, health check, finalize build.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.utils.profile import BuildProfile


def phase_postprocess(
    orchestrator: BuildOrchestrator, cli, parallel: bool, ctx, incremental: bool
) -> None:
    """
    Phase 17: Post-processing.

    Runs post-build tasks: sitemap, RSS, output formats, validation.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        parallel: Whether to use parallel processing
        ctx: Build context
        incremental: Whether this is an incremental build
    """
    with orchestrator.logger.phase("postprocessing", parallel=parallel):
        postprocess_start = time.time()

        orchestrator.postprocess.run(
            parallel=parallel,
            progress_manager=None,
            build_context=ctx,
            incremental=incremental,
        )

        orchestrator.stats.postprocess_time_ms = (time.time() - postprocess_start) * 1000

        # Show phase completion
        cli.phase("Post-process", duration_ms=orchestrator.stats.postprocess_time_ms)

        orchestrator.logger.info("postprocessing_complete")


def phase_cache_save(
    orchestrator: BuildOrchestrator, pages_to_build: list, assets_to_process: list
) -> None:
    """
    Phase 18: Save Cache.

    Saves build cache for future incremental builds.

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: Pages that were built
        assets_to_process: Assets that were processed
    """
    with orchestrator.logger.phase("cache_save"):
        orchestrator.incremental.save_cache(pages_to_build, assets_to_process)
        orchestrator.logger.info("cache_saved")


def phase_collect_stats(orchestrator: BuildOrchestrator, build_start: float) -> None:
    """
    Phase 19: Collect Final Stats.

    Collects final build statistics.

    Args:
        orchestrator: Build orchestrator instance
        build_start: Build start time for duration calculation
    """
    orchestrator.stats.total_pages = len(orchestrator.site.pages)
    orchestrator.stats.regular_pages = len(orchestrator.site.regular_pages)
    orchestrator.stats.generated_pages = len(orchestrator.site.generated_pages)
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
        "total_assets": orchestrator.stats.total_assets,
    }


def run_health_check(
    orchestrator: BuildOrchestrator,
    profile: BuildProfile = None,
    incremental: bool = False,
    build_context=None,
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
    from bengal.utils.cli_output import get_cli_output

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

    if health_config.get("verbose", False):
        cli.info(report.format_console(verbose=True))
    # Only print if there are issues
    elif report.has_errors() or report.has_warnings():
        cli.info(report.format_console(verbose=False))

    # Store report in stats
    orchestrator.stats.health_report = report

    # Fail build in strict mode if there are errors
    strict_mode = health_config.get("strict_mode", False)
    if strict_mode and report.has_errors():
        raise Exception(
            f"Build failed health checks: {report.error_count} error(s) found. "
            "Review output or disable strict_mode."
        )


def phase_finalize(orchestrator: BuildOrchestrator, verbose: bool, collector) -> None:
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

    # Restore normal logger console output if we suppressed it
    if not verbose:
        from bengal.utils.logger import set_console_quiet

        set_console_quiet(False)

    # Log Pygments cache statistics (performance monitoring)
    try:
        from bengal.rendering.pygments_cache import log_cache_stats

        log_cache_stats()
    except ImportError:
        pass  # Cache not used
