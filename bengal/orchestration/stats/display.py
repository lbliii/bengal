"""
Build statistics display functions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.orchestration.stats.helpers import format_time
from bengal.output import get_cli_output

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats
    from bengal.utils.stats_protocol import DisplayableStats


def _build_context(stats: DisplayableStats, output_dir: str | None = None) -> dict:
    """Build the template context dict from stats."""
    ascii_output = os.environ.get("BENGAL_CLI_ASCII") == "1"
    glyphs = {
        "brand": "Bengal" if ascii_output else "ᓚᘏᗢ",
        "success": "v" if ascii_output else "✓",
        "warning": "!" if ascii_output else "▲",
        "error": "x" if ascii_output else "✗",
        "arrow": ">" if ascii_output else "↪",
        "separator": "|" if ascii_output else "│",
        "tree_branch": "+-" if ascii_output else "├─",
        "tree_end": "`-" if ascii_output else "└─",
        "tree_pipe": "   " if ascii_output else "│  ",
    }

    # Build mode
    mode_parts = []
    if stats.incremental:
        mode_parts.append("incremental")
    if stats.parallel:
        mode_parts.append("parallel")
    mode_text = "+".join(mode_parts) if mode_parts else "sequential"

    # Throughput
    render_ms = stats.rendering_time_ms if stats.rendering_time_ms > 0 else stats.build_time_ms
    pages_per_sec = (stats.total_pages / render_ms) * 1000 if render_ms > 0 else 0

    # Phase breakdown — show the slowest phases, not insertion order.
    phase_items = [
        ("Fonts", getattr(stats, "fonts_time_ms", 0)),
        ("Discovery", getattr(stats, "discovery_time_ms", 0)),
        ("Menus", getattr(stats, "menu_time_ms", 0)),
        ("Related", getattr(stats, "related_posts_time_ms", 0)),
        ("Render", getattr(stats, "rendering_time_ms", 0)),
        ("Assets", getattr(stats, "assets_time_ms", 0)),
        ("Post", getattr(stats, "postprocess_time_ms", 0)),
        ("Health", getattr(stats, "health_check_time_ms", 0)),
    ]
    phases = [
        f"{name} {format_time(duration_ms)}"
        for name, duration_ms in sorted(phase_items, key=lambda item: item[1], reverse=True)
        if duration_ms > 0
    ]
    postprocess_detail = _format_slowest_postprocess(stats)
    if postprocess_detail:
        phases.append(postprocess_detail)
    visible_phases = [*phases[:3], postprocess_detail] if postprocess_detail else phases[:4]

    # Breakdown string
    breakdown = f"{stats.regular_pages}+{stats.generated_pages}"
    if getattr(stats, "autodoc_pages", 0) > 0:
        breakdown += f"+{stats.autodoc_pages} autodoc"

    # Content parts
    content_parts = [f"{stats.total_sections} sections", f"{stats.total_assets} assets"]
    if stats.taxonomies_count > 0:
        content_parts.append(f"{stats.taxonomies_count} taxonomies")
    if stats.total_directives > 0:
        content_parts.append(f"{stats.total_directives} directives")

    # Render distribution
    render_dist = None
    if stats.render_p50_ms > 0:
        render_dist = f"P50 {stats.render_p50_ms:.0f}ms | P95 {stats.render_p95_ms:.0f}ms"
        if stats.slowest_pages:
            slowest_path, slowest_ms = stats.slowest_pages[0]
            short_path = Path(slowest_path).name if "/" in slowest_path else slowest_path
            render_dist += f" | Slowest: {short_path} ({slowest_ms:.0f}ms)"

    # Regression
    regression = None
    regression_positive = False
    if stats.regression_pct is not None and abs(stats.regression_pct) > 10:
        sign = "+" if stats.regression_pct > 0 else ""
        regression = f"Build: {sign}{stats.regression_pct:.0f}% vs last"
        regression_positive = stats.regression_pct > 0

    # Cache stats
    cache_line = None
    parsed_hits = getattr(stats, "parsed_cache_hits", 0)
    rendered_hits = getattr(stats, "rendered_cache_hits", 0)
    parsed_misses = getattr(stats, "parsed_cache_misses", 0)
    if parsed_hits > 0 or rendered_hits > 0:
        cache_line = (
            f"Parsed: {parsed_hits} hits, {parsed_misses} misses | Rendered: {rendered_hits} hits"
        )
        effectiveness = stats.cache_effectiveness_pct
        if effectiveness is not None:
            cache_line += f" | Cache saved {effectiveness:.0f}% of render time"

    # Error summary
    error_summary = stats.get_error_summary() if hasattr(stats, "get_error_summary") else {}

    # Error code breakdown (Sprint A4.3)
    template_errors = getattr(stats, "template_errors", None) or []
    error_code_summary = ""
    if template_errors:
        from bengal.errors.aggregation import format_error_code_summary

        error_code_summary = format_error_code_summary(template_errors)

    return {
        "skipped": stats.skipped,
        "ascii": ascii_output,
        "glyphs": glyphs,
        "has_errors": stats.has_errors,
        "has_warnings": len(stats.warnings) > 0,
        "total_pages": stats.total_pages,
        "breakdown": breakdown,
        "build_time": format_time(stats.build_time_ms),
        "mode": mode_text,
        "pages_per_sec": pages_per_sec,
        "content_parts": content_parts,
        "phases": visible_phases,
        "render_dist": render_dist,
        "regression": regression,
        "regression_positive": regression_positive,
        "cache_line": cache_line,
        "output_dir": output_dir,
        "error_count": error_summary.get("total_errors", 0),
        # get_error_summary().total_warnings already includes len(stats.warnings)
        "warning_count": error_summary.get("total_warnings", 0)
        if error_summary
        else len(stats.warnings),
        "error_code_summary": error_code_summary,
    }


def _format_slowest_postprocess(stats: DisplayableStats) -> str | None:
    """Return a compact detail for the slowest post-render subtask."""
    timing_maps = [
        getattr(stats, "postprocess_task_timings_ms", None),
        getattr(stats, "postprocess_output_timings_ms", None),
        getattr(stats, "post_render_timings_ms", None),
    ]
    combined: dict[str, float] = {}
    for timings in timing_maps:
        if isinstance(timings, dict):
            for name, duration_ms in timings.items():
                if isinstance(duration_ms, int | float) and duration_ms > 0:
                    combined[str(name)] = float(duration_ms)
    if not combined:
        return None
    name, duration_ms = max(combined.items(), key=lambda item: item[1])
    return f"Slowest post {name} {format_time(duration_ms)}"


def _build_warning_groups(stats: DisplayableStats) -> list[dict]:
    """Build warning group data for the template."""
    if not stats.warnings:
        return []

    type_names = {
        "jinja2": "Jinja2 Template Errors",
        "kida": "Kida Template Errors",
        "template": "Template Syntax Errors",
        "preprocessing": "Pre-processing Errors",
        "link": "Link Validation Warnings",
        "other": "Other Warnings",
    }

    grouped = stats.warnings_by_type
    groups = []
    for warning_type, type_warnings in grouped.items():
        type_name = type_names.get(warning_type, warning_type.title())
        groups.append(
            {
                "type_name": type_name,
                "warnings": [
                    {"short_path": w.short_path, "message": w.message} for w in type_warnings
                ],
            }
        )
    return groups


def _build_error_lines(stats: DisplayableStats, verbose: bool = False) -> list[dict]:
    """Build structured error lines from the error report."""
    if not stats.has_errors and not stats.warnings:
        return []

    from bengal.errors import format_error_report

    error_report = format_error_report(stats, verbose=verbose)
    if error_report == "✅ No errors or warnings":
        return []

    lines = []
    for line in error_report.split("\n"):
        if not line.strip():
            continue
        if line.startswith("  ❌"):
            lines.append({"text": line[4:].strip(), "level": "error"})
        elif line.startswith("  ⚠️"):
            lines.append({"text": line[4:].strip(), "level": "warning"})
        elif line.endswith(":") and not line.startswith(" "):
            lines.append({"text": line, "level": "header"})
        elif line.startswith("     "):
            lines.append({"text": line.strip(), "level": "dim"})
        else:
            lines.append({"text": line, "level": "info"})
    return lines


def display_simple_build_stats(stats: BuildStats, output_dir: str | None = None) -> None:
    """
    Display simple build statistics for writers.

    Clean, minimal output focused on success/failure and critical issues only.

    Args:
        stats: Build statistics to display
        output_dir: Output directory path to display

    """
    cli = get_cli_output()

    if stats.skipped:
        cli.blank()
        cli.render_write("build_summary.kida", skipped=True)
        cli.blank()
        return

    ctx = _build_context(stats, output_dir)

    # For simple mode, add error lines (non-verbose) if errors exist
    if stats.has_errors:
        ctx["error_lines"] = _build_error_lines(stats, verbose=False)

    # Link warnings for simple mode
    link_warnings = [w for w in stats.warnings if w.warning_type == "link"]
    if link_warnings:
        link_lines = [
            {"text": f"⚠️  {len(link_warnings)} broken link(s) found:", "level": "warning"}
        ]
        link_lines.extend(
            {"text": f"• {w.short_path} → {w.message}", "level": "info"} for w in link_warnings[:5]
        )
        if len(link_warnings) > 5:
            link_lines.append({"text": f"... and {len(link_warnings) - 5} more", "level": "dim"})
        ctx.setdefault("error_lines", []).extend(link_lines)

    # Regression nudge for writers (only when significantly slower)
    if stats.regression_pct is not None and stats.regression_pct > 30:
        sign = "+" if stats.regression_pct > 0 else ""
        ctx["regression"] = f"Slower than usual ({sign}{stats.regression_pct:.0f}%)"
        ctx["regression_positive"] = True

    # Simple mode: strip detailed lines (phases, render dist, cache)
    ctx["phases"] = []
    ctx["render_dist"] = None
    ctx["cache_line"] = None

    cli.blank()
    cli.render_write("build_summary.kida", **ctx)
    cli.blank()


def display_build_stats(
    stats: DisplayableStats, show_art: bool = True, output_dir: str | None = None
) -> None:
    """
    Display build statistics.

    Args:
        stats: Build statistics to display
        show_art: Whether to show ASCII art
        output_dir: Output directory path to display

    """
    cli = get_cli_output()

    if stats.skipped:
        cli.blank()
        cli.render_write("build_summary.kida", skipped=True)
        cli.blank()
        return

    ctx = _build_context(stats, output_dir)

    # Error lines only when actual errors exist (not just warnings)
    if stats.has_errors:
        ctx["error_lines"] = _build_error_lines(stats, verbose=True)

    # Warning groups for warnings (shown separately from error lines)
    if stats.warnings:
        ctx["warning_groups"] = _build_warning_groups(stats)

    cli.blank()
    cli.render_write("build_summary.kida", **ctx)
    cli.blank()
