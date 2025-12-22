"""
Rich build summary dashboard with performance insights.

Displays comprehensive build statistics using Rich formatting with timing
breakdown, performance grading, smart suggestions, and cache analysis.
This module provides the visual feedback shown after a build completes.

Components:
    Timing Breakdown Table
        Shows time spent in each phase (discovery, taxonomies, rendering,
        assets, postprocess) with percentage bars and bottleneck highlighting.
    Performance Panel
        Displays letter grade (A-F) with score, throughput (pages/sec),
        and identified bottleneck phase.
    Suggestions Panel
        Smart optimization suggestions from PerformanceAdvisor based on
        the specific build profile and detected issues.
    Cache Statistics Panel
        Cache hit rate, time saved, and cache effectiveness metrics
        (shown only for incremental builds).
    Content Statistics Table
        Page, asset, section, and taxonomy counts with build mode info.

Display Modes:
    Full Dashboard (display_build_summary)
        Comprehensive display with all panels for interactive use.
    Simple Summary (display_simple_summary)
        Minimal output for writer persona or quiet mode.

Related Modules:
    bengal.analysis.performance_advisor: Generates grades and suggestions
    bengal.orchestration.stats: BuildStats data model
    bengal.utils.rich_console: Console setup and detection

See Also:
    bengal.orchestration.build.finalization: Calls display after build
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from bengal.analysis.performance_advisor import PerformanceAdvisor
    from bengal.orchestration.stats import BuildStats


def create_timing_breakdown_table(stats: BuildStats) -> Table:
    """
    Create a detailed timing breakdown table.

    Args:
        stats: Build statistics

    Returns:
        Rich Table with phase timing breakdown
    """
    table = Table(
        title="⏱️  Build Phase Breakdown",
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
        title_style="bold cyan",
    )

    table.add_column("Phase", style="cyan", no_wrap=True)
    table.add_column("Time", justify="right", style="white")
    table.add_column("% of Total", justify="right")
    table.add_column("Bar", width=20)

    # Calculate total phase time
    total_phase_time = (
        stats.discovery_time_ms
        + stats.taxonomy_time_ms
        + stats.rendering_time_ms
        + stats.assets_time_ms
        + stats.postprocess_time_ms
    )

    # Add rows for each phase
    phases = [
        ("Discovery", stats.discovery_time_ms),
        ("Taxonomies", stats.taxonomy_time_ms),
        ("Rendering", stats.rendering_time_ms),
        ("Assets", stats.assets_time_ms),
        ("Postprocess", stats.postprocess_time_ms),
    ]

    for phase_name, phase_time in phases:
        if phase_time == 0:
            continue

        # Format time
        if phase_time < 1:
            time_str = f"{phase_time:.2f}ms"
        elif phase_time < 1000:
            time_str = f"{int(phase_time)}ms"
        else:
            time_str = f"{phase_time / 1000:.2f}s"

        # Calculate percentage
        if total_phase_time > 0:
            pct = (phase_time / total_phase_time) * 100
            pct_str = f"{pct:.1f}%"

            # Color code based on percentage (bottleneck detection)
            if pct > 60:
                pct_color = "red bold"
            elif pct > 40:
                pct_color = "yellow"
            else:
                pct_color = "green"

            # Create visual bar
            bar_width = int((pct / 100) * 20)
            bar = "█" * bar_width + "░" * (20 - bar_width)

            table.add_row(
                phase_name,
                time_str,
                f"[{pct_color}]{pct_str}[/{pct_color}]",
                f"[{pct_color}]{bar}[/{pct_color}]",
            )
        else:
            table.add_row(phase_name, time_str, "-", "")

    # Add total
    total_time = stats.build_time_ms
    total_str = f"{int(total_time)}ms" if total_time < 1000 else f"{total_time / 1000:.2f}s"

    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_str}[/bold]",
        "[bold]100%[/bold]",
        "[success]████████████████████[/success]",
    )

    return table


def create_performance_panel(stats: BuildStats, advisor: PerformanceAdvisor) -> Panel:
    """
    Create performance grade and insights panel.

    Args:
        stats: Build statistics
        advisor: Performance advisor with analysis

    Returns:
        Rich Panel with performance insights
    """
    grade = advisor.get_grade()

    # Grade visualization
    grade_colors = {"A": "bright_green", "B": "green", "C": "yellow", "D": "orange1", "F": "red"}
    grade_color = grade_colors.get(grade.grade, "white")

    # Create content
    lines = []

    # Big grade display
    lines.append(
        Text(f"   {grade.grade}   ", style=f"bold {grade_color} on black", justify="center")
    )
    lines.append(Text(f"{grade.score}/100", style="bold white", justify="center"))
    lines.append(Text())
    lines.append(Text(grade.summary, style="dim", justify="center"))

    # Throughput calculation
    if stats.build_time_ms > 0 and stats.total_pages > 0:
        pages_per_sec = (stats.total_pages / stats.build_time_ms) * 1000
        lines.append(Text())
        lines.append(Text(f"📈 {pages_per_sec:.1f} pages/second", style="cyan", justify="center"))

    # Bottleneck detection
    bottleneck = advisor.get_bottleneck()
    if bottleneck:
        lines.append(Text())
        lines.append(Text(f"🎯 Bottleneck: {bottleneck}", style="yellow", justify="center"))

    content = Group(*lines)

    return Panel(
        content,
        title="[header]⚡ Performance Grade[/header]",
        border_style="cyan",
        padding=(1, 2),
    )


def create_suggestions_panel(advisor: PerformanceAdvisor) -> Panel | None:
    """
    Create smart suggestions panel.

    Args:
        advisor: Performance advisor with analysis

    Returns:
        Rich Panel with suggestions, or None if no suggestions
    """
    suggestions = advisor.get_top_suggestions(5)

    if not suggestions:
        return None

    lines = []

    for i, suggestion in enumerate(suggestions, 1):
        # Priority emoji
        if suggestion.priority.value == "high":
            emoji = "🔥"
            style = "red bold"
        elif suggestion.priority.value == "medium":
            emoji = "💡"
            style = "yellow"
        else:
            emoji = "ℹ️"
            style = "cyan"

        # Title
        lines.append(Text())
        lines.append(Text(f"{emoji} {i}. {suggestion.title}", style=style))

        # Description
        lines.append(Text(f"   {suggestion.description}", style="dim"))

        # Impact
        lines.append(Text(f"   💫 {suggestion.impact}", style="green"))

        # Action
        lines.append(Text(f"   → {suggestion.action}", style="cyan"))

        # Config example (if provided)
        if suggestion.config_example:
            lines.append(Text(f"     {suggestion.config_example}", style="dim italic"))

    content = Group(*lines)

    return Panel(
        content,
        title="[bold yellow]💡 Smart Suggestions[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    )


def create_cache_stats_panel(stats: BuildStats) -> Panel | None:
    """
    Create cache statistics panel (if available).

    Args:
        stats: Build statistics

    Returns:
        Rich Panel with cache stats, or None if not applicable
    """
    # Check if we have cache data
    if not hasattr(stats, "cache_hits") or not stats.incremental:
        return None

    cache_hits = getattr(stats, "cache_hits", 0)
    cache_misses = getattr(stats, "cache_misses", 0)
    cache_total = cache_hits + cache_misses

    if cache_total == 0:
        return None

    hit_rate = (cache_hits / cache_total) * 100 if cache_total > 0 else 0

    # Determine color based on hit rate
    if hit_rate >= 80:
        rate_color = "bright_green"
        emoji = "✨"
    elif hit_rate >= 60:
        rate_color = "green"
        emoji = "👍"
    elif hit_rate >= 40:
        rate_color = "yellow"
        emoji = "📊"
    else:
        rate_color = "red"
        emoji = "⚠️"

    lines = []
    lines.append(
        Text(f"{emoji} Cache Hit Rate: ", style="cyan")
        + Text(f"{hit_rate:.1f}%", style=f"bold {rate_color}")
    )
    lines.append(Text())
    lines.append(Text(f"   Hits:   {cache_hits:>4}", style="green"))
    lines.append(Text(f"   Misses: {cache_misses:>4}", style="red"))
    lines.append(Text(f"   Total:  {cache_total:>4}", style="white"))

    # Time savings estimate
    if hasattr(stats, "time_saved_ms"):
        time_saved = stats.time_saved_ms / 1000
        lines.append(Text())
        lines.append(Text(f"⚡ Time Saved: {time_saved:.2f}s", style="cyan"))

    content = Group(*lines)

    return Panel(
        content,
        title="[header]💾 Cache Statistics[/header]",
        border_style="cyan",
        padding=(1, 2),
    )


def create_content_stats_table(stats: BuildStats) -> Table:
    """
    Create content statistics table.

    Args:
        stats: Build statistics

    Returns:
        Rich Table with content stats
    """
    table = Table(
        title="📊 Content Statistics",
        show_header=False,
        border_style="cyan",
        title_style="bold cyan",
    )

    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="bold white")
    table.add_column("Details", style="dim")

    # Pages
    table.add_row(
        "📄 Pages",
        str(stats.total_pages),
        f"{stats.regular_pages} regular + {stats.generated_pages} generated",
    )

    # Assets
    table.add_row("📦 Assets", str(stats.total_assets), "")

    # Sections
    table.add_row("📁 Sections", str(stats.total_sections), "")

    # Taxonomies
    if stats.taxonomies_count > 0:
        table.add_row("🏷️  Taxonomies", str(stats.taxonomies_count), "")

    # Directives (if tracked)
    if hasattr(stats, "total_directives") and stats.total_directives > 0:
        # Get top 3 directive types
        if hasattr(stats, "directives_by_type") and stats.directives_by_type:
            top_types = sorted(stats.directives_by_type.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            type_summary = ", ".join([f"{t}({c})" for t, c in top_types])
        else:
            type_summary = ""

        table.add_row("⚙️  Directives", str(stats.total_directives), type_summary)

    # Build mode
    mode_parts = []
    if stats.incremental:
        mode_parts.append("incremental")
    if stats.parallel:
        mode_parts.append("parallel")
    if not mode_parts:
        mode_parts.append("sequential")

    table.add_row("🔧 Mode", ", ".join(mode_parts), "")

    return table


def display_build_summary(stats: BuildStats, environment: dict[str, Any] | None = None) -> None:
    """
    Display comprehensive build summary with rich formatting.

    This is the main entry point for Phase 2 build summaries.
    Shows timing breakdown, performance analysis, and smart suggestions.

    Args:
        stats: Build statistics
        environment: Environment info (from detect_environment())
    """
    from bengal.analysis.performance_advisor import PerformanceAdvisor
    from bengal.utils.rich_console import get_console, should_use_rich

    # Check if we should use rich output
    if not should_use_rich():
        # Fall back to simple display
        from bengal.orchestration.stats import display_build_stats

        display_build_stats(stats)
        return

    console = get_console()

    # Skip if build was skipped
    if stats.skipped:
        console.print()
        console.print("[info]No changes detected - build skipped![/info]")
        console.print()
        return

    # Create performance advisor
    advisor = PerformanceAdvisor(stats, environment)
    advisor.analyze()

    # Header (keep cat branding - it's identity, not decoration)
    console.print()
    console.print("    [bengal]ᓚᘏᗢ[/bengal]  [success]Build complete![/success]")
    console.print()

    # Main content
    # Row 1: Performance grade + Content stats
    console.print(create_performance_panel(stats, advisor))
    console.print()
    console.print(create_content_stats_table(stats))
    console.print()

    # Row 2: Timing breakdown
    console.print(create_timing_breakdown_table(stats))
    console.print()

    # Row 3: Cache stats (if available)
    cache_panel = create_cache_stats_panel(stats)
    if cache_panel:
        console.print(cache_panel)
        console.print()

    # Row 4: Suggestions (if any)
    suggestions_panel = create_suggestions_panel(advisor)
    if suggestions_panel:
        console.print(suggestions_panel)
        console.print()

    # Row 5: Errors and warnings (if any)
    if stats.has_errors or stats.warnings:
        from bengal.errors import format_error_report

        error_report = format_error_report(stats, verbose=True)
        if error_report not in ("✅ No errors or warnings", "No errors or warnings"):
            from rich.panel import Panel

            console.print(
                Panel(
                    error_report,
                    title="[red bold]Errors & Warnings[/red bold]",
                    border_style="red" if stats.has_errors else "yellow",
                    padding=(1, 2),
                )
            )
            console.print()

    # Footer: Output location
    if hasattr(stats, "output_dir") and stats.output_dir:
        console.print("[header]Output:[/header]")
        console.print(f"   [cyan]↪[/cyan] [white bold]{stats.output_dir}[/white bold]")
        console.print()


def display_simple_summary(stats: BuildStats) -> None:
    """
    Display simple summary for writer persona (minimal output).

    Args:
        stats: Build statistics
    """
    from bengal.orchestration.stats import display_simple_build_stats

    # Use existing simple display
    display_simple_build_stats(stats)
