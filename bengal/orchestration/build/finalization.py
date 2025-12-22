"""
Finalization phases for build orchestration.

Phases 17-21: Post-processing, cache save, collect stats, health check, finalize build.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.output import OutputCollector
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput
    from bengal.utils.build_context import BuildContext
    from bengal.utils.performance_collector import PerformanceCollector
    from bengal.utils.profile import BuildProfile


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
        parallel: Whether to use parallel processing
        ctx: Build context
        incremental: Whether this is an incremental build
        collector: Optional output collector for hot reload tracking
    """
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

    _write_build_time_artifacts(orchestrator.site, orchestrator.site._last_build_stats)
    duration_ms = (time.perf_counter() - start) * 1000
    if cli is not None:
        cli.phase("Stats", duration_ms=duration_ms)


def _write_build_time_artifacts(site: Any, last_build_stats: dict[str, Any]) -> None:
    """
    Write build-time artifacts into the output directory (opt-in).

    Why this exists:
        `BuildStats.build_time_ms` is only finalized after templates render (Phase 19).
        Writing a small SVG/JSON artifact here allows templates to display build time
        accurately by referencing a static path like `/bengal/build.svg`.
    """
    config = getattr(site, "config", {}) or {}
    build_badge_cfg = _normalize_build_badge_config(config.get("build_badge"))
    if not build_badge_cfg["enabled"]:
        return

    output_dir = getattr(site, "output_dir", None)
    if not output_dir:
        return

    from pathlib import Path

    from bengal.orchestration.badge import build_shields_like_badge_svg, format_duration_ms_compact
    from bengal.utils.atomic_write import AtomicFile

    duration_ms = float(last_build_stats.get("build_time_ms") or 0)
    duration_text = format_duration_ms_compact(duration_ms)

    payload = {
        "build_time_ms": duration_ms,
        "build_time_human": duration_text,
        "total_pages": int(last_build_stats.get("total_pages") or 0),
        "total_assets": int(last_build_stats.get("total_assets") or 0),
        "rendering_time_ms": float(last_build_stats.get("rendering_time_ms") or 0),
        "timestamp": _safe_isoformat(getattr(site, "build_time", None)),
    }

    svg = build_shields_like_badge_svg(
        label=build_badge_cfg["label"],
        message=duration_text,
        label_color=build_badge_cfg["label_color"],
        message_color=build_badge_cfg["message_color"],
    )
    json_text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    for root in _iter_output_roots(site):
        target_dir = Path(root) / build_badge_cfg["dir_name"]
        target_dir.mkdir(parents=True, exist_ok=True)

        _write_if_changed_atomic(target_dir / "build.svg", svg, AtomicFile)
        _write_if_changed_atomic(target_dir / "build.json", json_text, AtomicFile)


def _write_if_changed_atomic(path: Any, content: str, atomic_file_cls: Any) -> None:
    """
    Write file atomically, but only if content differs.

    This prevents unnecessary touching of outputs across builds.
    """
    try:
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing == content:
                return
    except Exception:
        # Best-effort; if read fails, proceed to write.
        pass

    with atomic_file_cls(path, "w", encoding="utf-8") as f:
        f.write(content)


def _normalize_build_badge_config(value: Any) -> dict[str, Any]:
    """
    Normalize `build_badge` config.

    Supported:
      - False / None: disabled
      - True: enabled with defaults
      - {enabled: bool, ...}: enabled with overrides
    """
    if value is None or value is False:
        return {
            "enabled": False,
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }

    if value is True:
        return {
            "enabled": True,
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }

    if isinstance(value, dict):
        enabled = bool(value.get("enabled", True))
        return {
            "enabled": enabled,
            "dir_name": str(value.get("dir_name", "bengal")),
            "label": str(value.get("label", "built in")),
            "label_color": str(value.get("label_color", "#555")),
            "message_color": str(value.get("message_color", "#4c1d95")),
        }

    # Unknown type: treat as disabled rather than guessing.
    return {
        "enabled": False,
        "dir_name": "bengal",
        "label": "built in",
        "label_color": "#555",
        "message_color": "#4c1d95",
    }


def _iter_output_roots(site: Any) -> list[Any]:
    """
    Determine which output roots should receive build artifacts.

    For i18n prefix strategy, some sites render into language subdirectories.
    We mirror the behavior of site-wide outputs by also writing into those
    subdirectories so that `/en/bengal/build.svg` resolves when the site is
    deployed under a language prefix.
    """
    output_dir = getattr(site, "output_dir", None)
    if not output_dir:
        return []

    roots: list[Any] = [output_dir]

    config = getattr(site, "config", {}) or {}
    i18n = config.get("i18n", {}) or {}
    if i18n.get("strategy") != "prefix":
        return roots

    default_lang = str(i18n.get("default_language", "en"))
    default_in_subdir = bool(i18n.get("default_in_subdir", False))

    lang_codes: list[str] = []
    for entry in i18n.get("languages", []) or []:
        if isinstance(entry, str):
            lang_codes.append(entry)
        elif isinstance(entry, dict):
            code = entry.get("code") or entry.get("lang") or entry.get("language")
            if isinstance(code, str) and code:
                lang_codes.append(code)

    for code in sorted(set(lang_codes)):
        if code == default_lang and not default_in_subdir:
            continue
        roots.append(_join(output_dir, code))

    if default_in_subdir:
        roots.append(_join(output_dir, default_lang))

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[Any] = []
    for r in roots:
        key = str(r)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _join(root: Any, child: str) -> Any:
    from pathlib import Path

    return Path(root) / child


def _safe_isoformat(value: Any) -> str | None:
    try:
        from datetime import datetime

        if isinstance(value, datetime):
            return value.isoformat()
        return None
    except Exception:
        return None


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
        from bengal.utils.logger import set_console_quiet

        set_console_quiet(False)

    # Log Pygments cache statistics (performance monitoring)
    try:
        from bengal.rendering.pygments_cache import log_cache_stats

        log_cache_stats()
    except ImportError:
        pass  # Cache not used
