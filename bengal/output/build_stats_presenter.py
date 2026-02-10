"""CLI presenter for build stats output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.stats.helpers import format_time
from bengal.orchestration.stats.warnings import display_warnings
from bengal.output import CLIOutput

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats
    from bengal.utils.stats_protocol import DisplayableStats


def display_simple_build_stats(stats: BuildStats, output_dir: str | None = None) -> None:
    """Display minimal writer-focused build stats output."""
    cli = CLIOutput()

    if stats.skipped:
        cli.blank()
        cli.info("✨ No changes detected - build skipped!")
        return

    error_summary = stats.get_error_summary()
    if not stats.has_errors:
        build_time_s = stats.build_time_ms / 1000
        cli.blank()
        cli.success(f"Built {stats.total_pages} pages in {build_time_s:.1f}s")
    else:
        cli.blank()
        cli.warning(
            f"Built with {error_summary['total_errors']} error(s), {error_summary['total_warnings']} warning(s)"
        )

    if stats.has_errors:
        from bengal.errors import format_error_report

        error_report = format_error_report(stats, verbose=False)
        if error_report != "✅ No errors or warnings":
            cli.error_header("Errors:")
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

    link_warnings = [w for w in stats.warnings if w.warning_type == "link"]
    if link_warnings:
        cli.warning(f"⚠️  {len(link_warnings)} broken link(s) found:")
        for warning in link_warnings[:5]:
            if cli.use_rich:
                cli.console.print(f"   • [warning]{warning.short_path}[/warning] → {warning.message}")
            else:
                cli.info(f"   • {warning.short_path} → {warning.message}")
        if len(link_warnings) > 5:
            remaining = len(link_warnings) - 5
            cli.info(f"   ... and {remaining} more")
        cli.blank()

    if output_dir:
        cli.path(output_dir, label="Output")


def display_build_stats(
    stats: DisplayableStats, show_art: bool = True, output_dir: str | None = None
) -> None:
    """Display full build stats output."""
    _ = show_art
    cli = CLIOutput()

    if stats.skipped:
        cli.blank()
        cli.info("✨ No changes detected - build skipped!")
        return

    if stats.has_errors or stats.warnings:
        from bengal.errors import format_error_report

        error_report = format_error_report(stats, verbose=True)
        if error_report != "✅ No errors or warnings":
            cli.blank()
            cli.error_header("Build Errors & Warnings")
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
                    elif line.startswith("     "):
                        if cli.use_rich:
                            cli.console.print(f"   [dim]{line.strip()}[/dim]")
                        else:
                            cli.info(f"   {line.strip()}")
                    else:
                        cli.info(f"   {line}")
            cli.blank()

    if stats.warnings and not stats.has_errors:
        display_warnings(stats)

    mode_parts = []
    if stats.incremental:
        mode_parts.append("incremental")
    if stats.parallel:
        mode_parts.append("parallel")
    mode_text = "+".join(mode_parts) if mode_parts else "sequential"

    pages_per_sec = (stats.total_pages / stats.build_time_ms) * 1000 if stats.build_time_ms > 0 else 0

    phases = []
    if stats.rendering_time_ms > 0:
        phases.append(f"Render {format_time(stats.rendering_time_ms)}")
    if stats.discovery_time_ms > 0:
        phases.append(f"Discovery {format_time(stats.discovery_time_ms)}")
    if stats.health_check_time_ms > 0:
        phases.append(f"Health {format_time(stats.health_check_time_ms)}")
    if stats.postprocess_time_ms > 0:
        phases.append(f"Post {format_time(stats.postprocess_time_ms)}")
    if stats.assets_time_ms > 0:
        phases.append(f"Assets {format_time(stats.assets_time_ms)}")

    total_time_str = format_time(stats.build_time_ms)
    has_warnings = len(stats.warnings) > 0

    cli.blank()
    if has_warnings:
        if cli.use_rich:
            cli.console.print(
                f"[warning]{cli.icons.warning}[/warning] [bengal]ᓚᘏᗢ[/bengal]  "
                f"[warning]Built {stats.total_pages} pages in {total_time_str} ({mode_text}) with warnings[/warning]"
            )
        else:
            cli.warning(
                f"{cli.icons.warning} ᓚᘏᗢ  Built {stats.total_pages} pages in {total_time_str} ({mode_text}) with warnings"
            )
    else:
        if cli.use_rich:
            cli.console.print(
                f"[success]{cli.icons.success}[/success] [bengal]ᓚᘏᗢ[/bengal]  "
                f"[success]Built {stats.total_pages} pages[/success] "
                f"({stats.regular_pages}+{stats.generated_pages}) in [highlight]{total_time_str}[/highlight] "
                f"({mode_text}) | [highlight]{pages_per_sec:.1f}[/highlight] pages/sec"
            )
        else:
            cli.success(
                f"ᓚᘏᗢ  Built {stats.total_pages} pages ({stats.regular_pages}+{stats.generated_pages}) "
                f"in {total_time_str} ({mode_text}) | {pages_per_sec:.1f} pages/sec"
            )

    content_parts = [f"{stats.total_sections} sections", f"{stats.total_assets} assets"]
    if stats.taxonomies_count > 0:
        content_parts.append(f"{stats.taxonomies_count} taxonomies")
    if stats.total_directives > 0:
        content_parts.append(f"{stats.total_directives} directives")

    if cli.use_rich:
        cli.console.print(f"   [dim]{', '.join(content_parts)}[/dim]")
    else:
        cli.info(f"   {', '.join(content_parts)}")

    if phases:
        phase_str = ", ".join(phases[:4])
        if cli.use_rich:
            cli.console.print(f"   [dim]{phase_str}[/dim]")
        else:
            cli.info(f"   {phase_str}")

    if output_dir:
        if cli.use_rich:
            cli.console.print(f"   [dim]↪ {output_dir}[/dim]")
        else:
            cli.info(f"   ↪ {output_dir}")

    cli.blank()
