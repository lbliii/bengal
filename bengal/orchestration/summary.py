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

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.analysis.performance.advisor import PerformanceAdvisor
    from bengal.orchestration.stats import BuildStats


def _write(text: str = "") -> None:
    print(text, file=sys.stdout)


def display_build_summary(stats: BuildStats, environment: dict[str, Any] | None = None) -> None:
    """
    Display comprehensive build summary.

    This is the main entry point for build summaries.
    Shows timing breakdown, performance analysis, and smart suggestions.

    Args:
        stats: Build statistics
        environment: Environment info (from detect_environment())

    """
    from bengal.analysis.performance.advisor import PerformanceAdvisor

    # Skip if build was skipped
    if stats.skipped:
        _write()
        _write("  No changes detected - build skipped!")
        _write()
        return

    # Create performance advisor
    advisor = PerformanceAdvisor(stats, environment)
    advisor.analyze()

    # Header
    _write()
    _write("    Build complete!")
    _write()

    # Performance grade
    _print_performance(stats, advisor)

    # Content stats
    _print_content_stats(stats)

    # Timing breakdown
    _print_timing_breakdown(stats)

    # Cache stats
    _print_cache_stats(stats)

    # Suggestions
    _print_suggestions(advisor)

    # Errors and warnings
    if stats.has_errors or stats.warnings:
        from bengal.errors import format_error_report

        error_report = format_error_report(stats, verbose=True)
        if error_report not in ("No errors or warnings",):
            _write("  Errors & Warnings:")
            for line in error_report.split("\n"):
                _write(f"    {line}")
            _write()

    # Footer: Output location
    if hasattr(stats, "output_dir") and stats.output_dir:
        _write(f"  Output: {stats.output_dir}")
        _write()


def _print_performance(stats: BuildStats, advisor: PerformanceAdvisor) -> None:
    """Print performance grade and insights."""
    grade = advisor.get_grade()

    _write(f"  Performance: {grade.grade} ({grade.score}/100)")
    _write(f"  {grade.summary}")

    # Throughput
    render_ms = stats.rendering_time_ms if stats.rendering_time_ms > 0 else stats.build_time_ms
    if render_ms > 0 and stats.total_pages > 0:
        pages_per_sec = (stats.total_pages / render_ms) * 1000
        _write(f"  Throughput: {pages_per_sec:.1f} pages/second")

    # Per-page render distribution
    if stats.render_p50_ms > 0:
        _write(
            f"  P50 {stats.render_p50_ms:.0f}ms | P95 {stats.render_p95_ms:.0f}ms | Max {stats.render_max_ms:.0f}ms"
        )

    # Bottleneck
    bottleneck = advisor.get_bottleneck()
    if bottleneck:
        _write(f"  Bottleneck: {bottleneck}")

    _write()


def _print_content_stats(stats: BuildStats) -> None:
    """Print content statistics."""
    _write("  Content Statistics:")
    _write(
        f"    Pages:      {stats.total_pages} ({stats.regular_pages} regular + {stats.generated_pages} generated)"
    )
    _write(f"    Assets:     {stats.total_assets}")
    _write(f"    Sections:   {stats.total_sections}")
    if stats.taxonomies_count > 0:
        _write(f"    Taxonomies: {stats.taxonomies_count}")

    # Directives
    if hasattr(stats, "total_directives") and stats.total_directives > 0:
        _write(f"    Directives: {stats.total_directives}")

    # Build mode
    mode_parts = []
    if stats.incremental:
        mode_parts.append("incremental")
    if stats.parallel:
        mode_parts.append("parallel")
    if not mode_parts:
        mode_parts.append("sequential")
    _write(f"    Mode:       {', '.join(mode_parts)}")
    _write()


def _print_timing_breakdown(stats: BuildStats) -> None:
    """Print timing breakdown table."""
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
    if total_phase_time == 0:
        return

    _write("  Build Phase Breakdown:")

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
        bar_width = int((pct / 100) * 20)
        bar = "#" * bar_width + "." * (20 - bar_width)

        _write(f"    {phase_name:<15} {time_str:>8}  {pct:5.1f}%  [{bar}]")

    # Total
    total_time = stats.build_time_ms
    total_str = f"{int(total_time)}ms" if total_time < 1000 else f"{total_time / 1000:.2f}s"
    _write(f"    {'Total':<15} {total_str:>8}  100.0%")

    # Slowest pages
    if stats.slowest_pages:
        _write()
        _write("  Slowest pages:")
        for path, ms in stats.slowest_pages[:3]:
            short = Path(path).name
            _write(f"    {short}: {ms:.0f}ms")

    _write()


def _print_cache_stats(stats: BuildStats) -> None:
    """Print cache statistics if available."""
    has_any = False

    # Render pipeline cache
    parsed_hits = getattr(stats, "parsed_cache_hits", 0)
    rendered_hits = getattr(stats, "rendered_cache_hits", 0)
    parsed_misses = getattr(stats, "parsed_cache_misses", 0)
    pipeline_total = parsed_hits + rendered_hits + parsed_misses

    if pipeline_total > 0 and (parsed_hits > 0 or rendered_hits > 0):
        if not has_any:
            _write("  Cache Statistics:")
            has_any = True
        _write(f"    Rendered (full skip): {rendered_hits}")
        _write(f"    Parsed (skip parse):  {parsed_hits}")
        _write(f"    Parsed (full parse):  {parsed_misses}")

    # Page-level cache
    cache_hits = getattr(stats, "cache_hits", 0)
    cache_misses = getattr(stats, "cache_misses", 0)
    cache_total = cache_hits + cache_misses

    if stats.incremental and cache_total > 0:
        if not has_any:
            _write("  Cache Statistics:")
            has_any = True
        hit_rate = (cache_hits / cache_total) * 100 if cache_total > 0 else 0
        _write(f"    Page cache hit rate: {hit_rate:.1f}%")
        _write(f"    Hits: {cache_hits}  Misses: {cache_misses}")

        if hasattr(stats, "time_saved_ms") and stats.time_saved_ms > 0:
            _write(f"    Time saved: {stats.time_saved_ms / 1000:.2f}s")

    # Block-level cache
    block_hits = getattr(stats, "block_cache_hits", 0)
    block_misses = getattr(stats, "block_cache_misses", 0)
    block_cached = getattr(stats, "block_cache_site_blocks", 0)
    block_total = block_hits + block_misses

    if block_cached > 0 or block_total > 0:
        if not has_any:
            _write("  Cache Statistics:")
            has_any = True
        _write(f"    Block cache: {block_cached} blocks cached")
        if block_total > 0:
            block_hit_rate = (block_hits / block_total) * 100 if block_total > 0 else 0
            _write(f"    Block reuse: {block_hit_rate:.1f}% ({block_hits}x reused)")

    # Effectiveness
    effectiveness = stats.cache_effectiveness_pct
    if effectiveness is not None:
        if not has_any:
            _write("  Cache Statistics:")
            has_any = True
        _write(f"    Cache saved {effectiveness:.0f}% of render time")

    if has_any:
        _write()


def _print_suggestions(advisor: PerformanceAdvisor) -> None:
    """Print smart suggestions."""
    suggestions = advisor.get_top_suggestions(5)
    if not suggestions:
        return

    _write("  Suggestions:")

    for i, suggestion in enumerate(suggestions, 1):
        priority_marker = {"high": "!", "medium": "*", "low": "-"}.get(
            suggestion.priority.value, "-"
        )
        _write(f"    {priority_marker} {i}. {suggestion.title}")
        _write(f"        {suggestion.description}")
        _write(f"        Impact: {suggestion.impact}")
        _write(f"        Action: {suggestion.action}")
        if suggestion.config_example:
            _write(f"        Config: {suggestion.config_example}")

    _write()


def display_simple_summary(stats: BuildStats) -> None:
    """
    Display simple summary for writer persona (minimal output).

    Args:
        stats: Build statistics

    """
    from bengal.orchestration.stats import display_simple_build_stats

    display_simple_build_stats(stats)
