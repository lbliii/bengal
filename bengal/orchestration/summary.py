"""
Build summary display with performance insights.

Displays build statistics with timing breakdown, performance grading,
smart suggestions, and cache analysis. This module provides the visual
feedback shown after a build completes.

Display Modes:
Full Dashboard (display_build_summary)
    Comprehensive display with all panels for interactive use.
Simple Summary (display_simple_summary)
    Minimal output for writer persona or quiet mode.

Related Modules:
bengal.analysis.performance_advisor: Generates grades and suggestions
bengal.orchestration.stats: BuildStats data model

See Also:
bengal.orchestration.build.finalization: Calls display after build

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats


def display_build_summary(
    stats: BuildStats,
    environment: dict[str, Any] | None = None,
    cli: object | None = None,
) -> None:
    """
    Display comprehensive build summary via kida template.

    This is the main entry point for build summaries.
    Shows timing breakdown, performance analysis, and smart suggestions.

    Args:
        stats: Build statistics
        environment: Environment info (from detect_environment())
        cli: CLIOutput instance; lazy-created if None

    """
    from bengal.analysis.performance.advisor import PerformanceAdvisor

    if cli is None:
        from bengal.output import get_cli_output

        cli = get_cli_output()

    # Skip if build was skipped
    if stats.skipped:
        cli.info("No changes detected - build skipped!")
        return

    # Create performance advisor
    advisor = PerformanceAdvisor(stats, environment)
    advisor.analyze()

    # ── Build context dict for the template ──────────────────────────

    context: dict[str, Any] = {}

    # Grade
    grade = advisor.get_grade()
    context["grade_letter"] = grade.grade
    context["grade_score"] = grade.score
    context["grade_summary"] = grade.summary

    # Throughput
    render_ms = stats.rendering_time_ms if stats.rendering_time_ms > 0 else stats.build_time_ms
    if render_ms > 0 and stats.total_pages > 0:
        context["throughput"] = (stats.total_pages / render_ms) * 1000
    else:
        context["throughput"] = 0

    # Render distribution
    context["render_dist"] = None
    if stats.render_p50_ms > 0:
        context["render_dist"] = (
            f"P50 {stats.render_p50_ms:.0f}ms | "
            f"P95 {stats.render_p95_ms:.0f}ms | "
            f"Max {stats.render_max_ms:.0f}ms"
        )

    # Bottleneck
    context["bottleneck"] = advisor.get_bottleneck()

    # Regression
    context["regression"] = None
    context["regression_positive"] = False
    if stats.regression_pct is not None:
        sign = "+" if stats.regression_pct > 0 else ""
        context["regression"] = f"{sign}{stats.regression_pct:.0f}% vs last build"
        context["regression_positive"] = stats.regression_pct > 0

    # ── Content stats ────────────────────────────────────────────────

    content: list[dict[str, str]] = [
        {
            "label": "Pages",
            "value": f"{stats.total_pages} ({stats.regular_pages} regular + {stats.generated_pages} generated)",
        },
        {"label": "Assets", "value": str(stats.total_assets)},
        {"label": "Sections", "value": str(stats.total_sections)},
    ]
    if stats.taxonomies_count > 0:
        content.append({"label": "Taxonomies", "value": str(stats.taxonomies_count)})
    if hasattr(stats, "total_directives") and stats.total_directives > 0:
        content.append({"label": "Directives", "value": str(stats.total_directives)})

    mode_parts: list[str] = []
    if stats.incremental:
        mode_parts.append("incremental")
    if stats.parallel:
        mode_parts.append("parallel")
    if not mode_parts:
        mode_parts.append("sequential")
    content.append({"label": "Mode", "value": ", ".join(mode_parts)})
    context["content"] = content

    # ── Timing breakdown ─────────────────────────────────────────────

    phases = [
        ("Fonts", stats.fonts_time_ms),
        ("Discovery", stats.discovery_time_ms),
        ("Taxonomies", stats.taxonomy_time_ms),
        ("Menus", stats.menu_time_ms),
        ("Related Posts", stats.related_posts_time_ms),
        ("Rendering", stats.rendering_time_ms),
        ("Assets", stats.assets_time_ms),
        ("Postprocess", stats.postprocess_time_ms),
        ("Health Check", stats.health_check_time_ms),
    ]

    total_phase_time = sum(t for _, t in phases)
    timing: list[dict[str, Any]] = []
    if total_phase_time > 0:
        for phase_name, phase_time in phases:
            if phase_time == 0:
                continue
            if phase_time < 1:
                time_str = f"{phase_time:.2f}ms"
            elif phase_time < 1000:
                time_str = f"{int(phase_time)}ms"
            else:
                time_str = f"{phase_time / 1000:.2f}s"
            pct = (phase_time / total_phase_time) * 100
            timing.append({"name": phase_name, "time_str": time_str, "pct": pct})

    context["timing"] = timing or None

    total_time = stats.build_time_ms
    context["total_time"] = (
        f"{int(total_time)}ms" if total_time < 1000 else f"{total_time / 1000:.2f}s"
    )

    # Slowest pages
    slowest: list[dict[str, Any]] = []
    if stats.slowest_pages:
        for path, ms in stats.slowest_pages[:3]:
            short = Path(path).name
            slowest.append({"name": short, "ms": ms})
    context["slowest"] = slowest or None

    # ── Cache stats ──────────────────────────────────────────────────

    cache: list[dict[str, str]] = []

    parsed_hits = getattr(stats, "parsed_cache_hits", 0)
    rendered_hits = getattr(stats, "rendered_cache_hits", 0)
    parsed_misses = getattr(stats, "parsed_cache_misses", 0)
    pipeline_total = parsed_hits + rendered_hits + parsed_misses

    if pipeline_total > 0 and (parsed_hits > 0 or rendered_hits > 0):
        cache.append({"label": "Rendered (full skip)", "value": str(rendered_hits)})
        cache.append({"label": "Parsed (skip parse)", "value": str(parsed_hits)})
        cache.append({"label": "Parsed (full parse)", "value": str(parsed_misses)})

    cache_hits = getattr(stats, "cache_hits", 0)
    cache_misses = getattr(stats, "cache_misses", 0)
    cache_total = cache_hits + cache_misses

    if stats.incremental and cache_total > 0:
        hit_rate = (cache_hits / cache_total) * 100 if cache_total > 0 else 0
        cache.append({"label": "Page cache hit rate", "value": f"{hit_rate:.1f}%"})
        cache.append({"label": "Hits / Misses", "value": f"{cache_hits} / {cache_misses}"})
        if hasattr(stats, "time_saved_ms") and stats.time_saved_ms > 0:
            cache.append({"label": "Time saved", "value": f"{stats.time_saved_ms / 1000:.2f}s"})

    block_hits = getattr(stats, "block_cache_hits", 0)
    block_misses = getattr(stats, "block_cache_misses", 0)
    block_cached = getattr(stats, "block_cache_site_blocks", 0)
    block_total = block_hits + block_misses

    if block_cached > 0 or block_total > 0:
        cache.append({"label": "Block cache", "value": f"{block_cached} blocks cached"})
        if block_total > 0:
            block_hit_rate = (block_hits / block_total) * 100 if block_total > 0 else 0
            cache.append(
                {"label": "Block reuse", "value": f"{block_hit_rate:.1f}% ({block_hits}x reused)"}
            )

    context["cache"] = cache or None

    effectiveness = stats.cache_effectiveness_pct
    context["cache_effectiveness"] = (
        f"Cache saved {effectiveness:.0f}% of render time" if effectiveness is not None else None
    )

    # ── Suggestions ──────────────────────────────────────────────────

    suggestions_raw = advisor.get_top_suggestions(5)
    if suggestions_raw:
        suggestion_list: list[dict[str, Any]] = []
        for s in suggestions_raw:
            marker = {"high": "!", "medium": "*", "low": "-"}.get(s.priority.value, "-")
            suggestion_list.append(
                {
                    "marker": marker,
                    "title": s.title,
                    "description": s.description,
                    "impact": s.impact,
                    "action": s.action,
                    "config": s.config_example,
                }
            )
        context["suggestions"] = suggestion_list
    else:
        context["suggestions"] = None

    # ── Errors & warnings ────────────────────────────────────────────

    context["errors"] = None
    if stats.has_errors or stats.warnings:
        from bengal.errors import format_error_report

        error_report = format_error_report(stats, verbose=True)
        if error_report not in ("No errors or warnings",):
            error_lines: list[dict[str, str]] = [
                {"text": line, "level": "error" if "error" in line.lower() else "warning"}
                for line in error_report.split("\n")
                if line.strip()
            ]
            context["errors"] = error_lines or None

    # ── Output dir ───────────────────────────────────────────────────

    context["output_dir"] = None
    if hasattr(stats, "output_dir") and stats.output_dir:
        context["output_dir"] = str(stats.output_dir)

    # ── Render the template ──────────────────────────────────────────

    cli.render_write("build_dashboard.kida", **context)


def display_simple_summary(stats: BuildStats) -> None:
    """
    Display simple summary for writer persona (minimal output).

    Args:
        stats: Build statistics

    """
    from bengal.orchestration.stats import display_simple_build_stats

    display_simple_build_stats(stats)
