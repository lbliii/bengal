"""
Build statistics display functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.stats.helpers import format_time
from bengal.orchestration.stats.warnings import display_warnings
from bengal.output import CLIOutput

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats
    from bengal.utils.stats_protocol import DisplayableStats


def display_simple_build_stats(stats: BuildStats, output_dir: str | None = None) -> None:
    """
    Display simple build statistics for writers.

    Clean, minimal output focused on success/failure and critical issues only.
    Perfect for content authors who just want to know "did it work?"

    Args:
        stats: Build statistics to display
        output_dir: Output directory path to display
    """
    cli = CLIOutput()

    if stats.skipped:
        cli.blank()
        cli.info("✨ No changes detected - build skipped!")
        return

    # Success indicator
    error_summary = stats.get_error_summary()
    if not stats.has_errors:
        build_time_s = stats.build_time_ms / 1000
        cli.blank()
        cli.success(f"Built {stats.total_pages} pages in {build_time_s:.1f}s")
        cli.blank()
    else:
        cli.blank()
        cli.warning(
            f"⚠️  Built with {error_summary['total_errors']} error(s), {error_summary['total_warnings']} warning(s)"
        )
        cli.blank()

    # Show errors using new error reporter
    if stats.has_errors:
        from bengal.errors import format_error_report

        error_report = format_error_report(stats, verbose=False)
        if error_report != "✅ No errors or warnings":
            cli.error_header("Errors:")
            # Split report into lines and display
            for line in error_report.split("\n"):
                if line.strip():
                    if line.startswith("  ❌"):
                        if cli.use_rich:
                            cli.console.print(f"   [error]{line[4:].strip()}[/error]")
                        else:
                            cli.error(f"   {line[4:].strip()}")
                    elif line.startswith("  ⚠️"):
                        if cli.use_rich:
                            cli.console.print(f"   [warning]{line[4:].strip()}[/warning]")
                        else:
                            cli.warning(f"   {line[4:].strip()}")
                    elif line.endswith(":"):
                        if cli.use_rich:
                            cli.console.print(f"   [header]{line}[/header]")
                        else:
                            cli.info(f"   {line}")
                    else:
                        cli.info(f"   {line}")
            cli.blank()

    # Show link validation warnings if any
    link_warnings = [w for w in stats.warnings if w.warning_type == "link"]
    if link_warnings:
        cli.warning(f"⚠️  {len(link_warnings)} broken link(s) found:")
        for warning in link_warnings[:5]:  # Show first 5
            if cli.use_rich:
                cli.console.print(
                    f"   • [warning]{warning.short_path}[/warning] → {warning.message}"
                )
            else:
                cli.info(f"   • {warning.short_path} → {warning.message}")
        if len(link_warnings) > 5:
            remaining = len(link_warnings) - 5
            cli.info(f"   ... and {remaining} more")
        cli.blank()

    # Output location
    if output_dir:
        cli.path(output_dir, label="Output")


def display_build_stats(
    stats: DisplayableStats, show_art: bool = True, output_dir: str | None = None
) -> None:
    """
    Display build statistics in a colorful table.

    Args:
        stats: Build statistics to display
        show_art: Whether to show ASCII art
        output_dir: Output directory path to display
    """
    cli = CLIOutput()

    if stats.skipped:
        cli.blank()
        cli.info("✨ No changes detected - build skipped!")
        return

    # Display errors and warnings
    if stats.has_errors or stats.warnings:
        from bengal.errors import format_error_report

        error_report = format_error_report(stats, verbose=True)
        if error_report != "✅ No errors or warnings":
            cli.blank()
            cli.error_header("Build Errors & Warnings")
            # Display formatted error report
            for line in error_report.split("\n"):
                if line.strip():
                    if line.startswith("  ❌"):
                        if cli.use_rich:
                            cli.console.print(f"   [error]{line[4:].strip()}[/error]")
                        else:
                            cli.error(f"   {line[4:].strip()}")
                    elif line.startswith("  ⚠️"):
                        if cli.use_rich:
                            cli.console.print(f"   [warning]{line[4:].strip()}[/warning]")
                        else:
                            cli.warning(f"   {line[4:].strip()}")
                    elif line.endswith(":") and not line.startswith(" "):
                        if cli.use_rich:
                            cli.console.print(f"   [header]{line}[/header]")
                        else:
                            cli.info(f"   {line}")
                    elif line.startswith("     "):  # Indented details
                        if cli.use_rich:
                            cli.console.print(f"   [dim]{line.strip()}[/dim]")
                        else:
                            cli.info(f"   {line.strip()}")
                    else:
                        cli.info(f"   {line}")
            cli.blank()

    # Also display warnings using existing function
    if stats.warnings and not stats.has_errors:
        display_warnings(stats)

    # Header with ASCII art integrated
    has_warnings = len(stats.warnings) > 0
    if has_warnings:
        if cli.use_rich:
            cli.console.print()
            cli.console.print(
                "[info]┌─────────────────────────────────────────────────────┐[/info]"
            )
            cli.console.print(
                f"[info]│[/info][warning]         {cli.icons.warning}  Build complete (with warnings)          [/warning][info]│[/info]"
            )
            cli.console.print(
                "[info]└─────────────────────────────────────────────────────┘[/info]"
            )
        else:
            cli.blank()
            cli.warning(f"         {cli.icons.warning}  Build complete (with warnings)          ")
    else:
        cli.blank()
        if show_art:
            if cli.use_rich:
                cli.console.print(
                    f"{cli.icons.success} [bengal]ᓚᘏᗢ[/bengal]  [success]Build complete[/success]"
                )
            else:
                cli.info(f"{cli.icons.success} ᓚᘏᗢ  Build complete")
        else:
            cli.console.print(f"{cli.icons.success} [success]Build complete[/success]")

    # Content stats
    cli.blank()
    if cli.use_rich:
        cli.console.print("[header]Content statistics:[/header]")
        cli.console.print(
            f"   [info]├─[/info] Pages:       [success]{stats.total_pages}[/success] "
            f"({stats.regular_pages} regular + {stats.generated_pages} generated)"
        )
        cli.console.print(
            f"   [info]├─[/info] Sections:    [success]{stats.total_sections}[/success]"
        )
        cli.console.print(
            f"   [info]├─[/info] Assets:      [success]{stats.total_assets}[/success]"
        )

        # Directive statistics (if present)
        if stats.total_directives > 0:
            top_types = sorted(stats.directives_by_type.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            type_summary = ", ".join([f"{t}({c})" for t, c in top_types])
            cli.console.print(
                f"   [info]├─[/info] Directives:  [highlight]{stats.total_directives}[/highlight] "
                f"({type_summary})"
            )

        cli.console.print(
            f"   [info]└─[/info] Taxonomies:  [success]{stats.taxonomies_count}[/success]"
        )
    else:
        cli.info("Content statistics:")
        cli.info(
            f"   ├─ Pages:       {stats.total_pages} "
            f"({stats.regular_pages} regular + {stats.generated_pages} generated)"
        )
        cli.info(f"   ├─ Sections:    {stats.total_sections}")
        cli.info(f"   ├─ Assets:      {stats.total_assets}")

        if stats.total_directives > 0:
            top_types = sorted(stats.directives_by_type.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            type_summary = ", ".join([f"{t}({c})" for t, c in top_types])
            cli.info(f"   ├─ Directives:  {stats.total_directives} ({type_summary})")

        cli.info(f"   └─ Taxonomies:  {stats.taxonomies_count}")

    # Build info
    cli.blank()
    mode_parts = []
    if stats.incremental:
        mode_parts.append("incremental")
    if stats.parallel:
        mode_parts.append("parallel")
    if not mode_parts:
        mode_parts.append("sequential")

    mode_text = " + ".join(mode_parts)

    if cli.use_rich:
        cli.console.print("[header]Build configuration:[/header]")
        cli.console.print(f"   [info]└─[/info] Mode:        [warning]{mode_text}[/warning]")
    else:
        cli.info("Build configuration:")
        cli.info(f"   └─ Mode:        {mode_text}")

    # Performance stats
    cli.blank()
    total_time_str = format_time(stats.build_time_ms)

    # Determine time styling and grade token (ASCII by default)
    if stats.build_time_ms < 100:
        time_token = "success"
        grade = cli.icons.grade_excellent
    elif stats.build_time_ms < 1000:
        time_token = "warning"
        grade = cli.icons.grade_fast
    else:
        time_token = "error"
        grade = cli.icons.grade_slow

    if cli.use_rich:
        cli.console.print("[header]Performance:[/header]")
        cli.console.print(
            f"   [info]├─[/info] Total:       [{time_token}]{total_time_str}[/{time_token}] {grade}"
        )

        # Phase breakdown (only if we have phase data)
        if stats.discovery_time_ms > 0:
            cli.console.print(
                f"   [info]├─[/info] Discovery:   {format_time(stats.discovery_time_ms)}"
            )
        if stats.taxonomy_time_ms > 0:
            cli.console.print(
                f"   [info]├─[/info] Taxonomies:  {format_time(stats.taxonomy_time_ms)}"
            )
        if stats.rendering_time_ms > 0:
            cli.console.print(
                f"   [info]├─[/info] Rendering:   {format_time(stats.rendering_time_ms)}"
            )
        if stats.assets_time_ms > 0:
            cli.console.print(
                f"   [info]├─[/info] Assets:      {format_time(stats.assets_time_ms)}"
            )
        if stats.postprocess_time_ms > 0:
            cli.console.print(
                f"   [info]├─[/info] Postprocess: {format_time(stats.postprocess_time_ms)}"
            )
        if stats.health_check_time_ms > 0:
            cli.console.print(
                f"   [info]└─[/info] Health:      {format_time(stats.health_check_time_ms)}"
            )
    else:
        cli.info("Performance:")
        cli.info(f"   ├─ Total:       {total_time_str} {grade}")

        if stats.discovery_time_ms > 0:
            cli.info(f"   ├─ Discovery:   {format_time(stats.discovery_time_ms)}")
        if stats.taxonomy_time_ms > 0:
            cli.info(f"   ├─ Taxonomies:  {format_time(stats.taxonomy_time_ms)}")
        if stats.rendering_time_ms > 0:
            cli.info(f"   ├─ Rendering:   {format_time(stats.rendering_time_ms)}")
        if stats.assets_time_ms > 0:
            cli.info(f"   ├─ Assets:      {format_time(stats.assets_time_ms)}")
        if stats.postprocess_time_ms > 0:
            cli.info(f"   ├─ Postprocess: {format_time(stats.postprocess_time_ms)}")
        if stats.health_check_time_ms > 0:
            cli.info(f"   └─ Health:      {format_time(stats.health_check_time_ms)}")

    # Fun stats
    if stats.build_time_ms > 0:
        pages_per_sec = (
            (stats.total_pages / stats.build_time_ms) * 1000 if stats.build_time_ms > 0 else 0
        )
        if pages_per_sec > 0:
            cli.blank()
            if cli.use_rich:
                cli.console.print("[header]Throughput:[/header]")
                cli.console.print(
                    f"   [info]└─[/info] [highlight]{pages_per_sec:.1f}[/highlight] pages/second"
                )
            else:
                cli.info("Throughput:")
                cli.info(f"   └─ {pages_per_sec:.1f} pages/second")

    # Output location
    if output_dir:
        cli.blank()
        cli.path(output_dir, label="Output")

    # Separator
    if cli.use_rich:
        cli.console.print()
        cli.console.print("[info]─────────────────────────────────────────────────────[/info]")
        cli.console.print()
    else:
        cli.blank()
        cli.info("─────────────────────────────────────────────────────")
        cli.blank()
