"""
Build statistics display with colorful output and ASCII art.
"""

from dataclasses import dataclass
from typing import Any

import click

# Bengal cat ASCII art variations (inspired by ᓚᘏᗢ)

BENGAL_ART = r"""
    ᓚᘏᗢ   Bengal SSG
"""

BENGAL_SUCCESS = r"""
    ᓚᘏᗢ
"""

BENGAL_ERROR = r"""
    ᓚᘏᗢ !!!
"""

BENGAL_BUILDING = r"""
    ᓚᘏᗢ Building...
"""


@dataclass
class BuildWarning:
    """A build warning or error."""

    file_path: str
    message: str
    warning_type: str  # 'jinja2', 'preprocessing', 'link', 'other'

    @property
    def short_path(self) -> str:
        """Get shortened path for display."""
        from pathlib import Path

        try:
            return str(Path(self.file_path).relative_to(Path.cwd()))
        except (ValueError, OSError):
            # If not relative to cwd, try to get just the filename with parent
            p = Path(self.file_path)
            return f"{p.parent.name}/{p.name}" if p.parent.name else p.name


@dataclass
class BuildStats:
    """Container for build statistics."""

    total_pages: int = 0
    regular_pages: int = 0
    generated_pages: int = 0
    tag_pages: int = 0
    archive_pages: int = 0
    pagination_pages: int = 0
    total_assets: int = 0
    total_sections: int = 0
    taxonomies_count: int = 0
    build_time_ms: float = 0
    parallel: bool = True
    incremental: bool = False
    skipped: bool = False

    # Directive statistics
    total_directives: int = 0
    directives_by_type: dict[str, int] = None

    # Phase timings
    discovery_time_ms: float = 0
    taxonomy_time_ms: float = 0
    rendering_time_ms: float = 0
    assets_time_ms: float = 0
    postprocess_time_ms: float = 0

    # Memory metrics (Phase 1 - Performance Tracking)
    memory_rss_mb: float = 0  # Process RSS (Resident Set Size) memory
    memory_heap_mb: float = 0  # Python heap memory from tracemalloc
    memory_peak_mb: float = 0  # Peak memory during build

    # Cache statistics (Phase 2 - Intelligence)
    cache_hits: int = 0  # Pages/assets served from cache
    cache_misses: int = 0  # Pages/assets rebuilt
    time_saved_ms: float = 0  # Estimated time saved by caching

    # Additional phase timings (Phase 2)
    menu_time_ms: float = 0
    related_posts_time_ms: float = 0
    fonts_time_ms: float = 0

    # Output directory (for display)
    output_dir: str = None

    # Warnings and errors
    warnings: list = None
    template_errors: list = None  # NEW: Rich template errors

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.warnings is None:
            self.warnings = []
        if self.template_errors is None:
            self.template_errors = []
        if self.directives_by_type is None:
            self.directives_by_type = {}

    def add_warning(self, file_path: str, message: str, warning_type: str = "other") -> None:
        """Add a warning to the build."""
        self.warnings.append(BuildWarning(file_path, message, warning_type))

    def add_template_error(self, error: Any) -> None:
        """Add a rich template error."""
        self.template_errors.append(error)

    def add_directive(self, directive_type: str) -> None:
        """Track a directive usage."""
        self.total_directives += 1
        self.directives_by_type[directive_type] = self.directives_by_type.get(directive_type, 0) + 1

    @property
    def has_errors(self) -> bool:
        """Check if build has any errors."""
        return len(self.template_errors) > 0

    @property
    def warnings_by_type(self) -> dict[str, list]:
        """Group warnings by type."""
        from collections import defaultdict

        grouped = defaultdict(list)
        for warning in self.warnings:
            grouped[warning.warning_type].append(warning)
        return dict(grouped)

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_pages": self.total_pages,
            "regular_pages": self.regular_pages,
            "generated_pages": self.generated_pages,
            "total_assets": self.total_assets,
            "total_sections": self.total_sections,
            "taxonomies_count": self.taxonomies_count,
            "build_time_ms": self.build_time_ms,
            "parallel": self.parallel,
            "incremental": self.incremental,
            "skipped": self.skipped,
            "discovery_time_ms": self.discovery_time_ms,
            "taxonomy_time_ms": self.taxonomy_time_ms,
            "rendering_time_ms": self.rendering_time_ms,
            "assets_time_ms": self.assets_time_ms,
            "postprocess_time_ms": self.postprocess_time_ms,
            "memory_rss_mb": self.memory_rss_mb,
            "memory_heap_mb": self.memory_heap_mb,
            "memory_peak_mb": self.memory_peak_mb,
        }


def format_time(ms: float) -> str:
    """Format milliseconds for display."""
    if ms < 1:
        return f"{ms:.2f} ms"
    elif ms < 1000:
        return f"{int(ms)} ms"
    else:
        seconds = ms / 1000
        return f"{seconds:.2f} s"


def display_warnings(stats: BuildStats) -> None:
    """
    Display grouped warnings and errors.

    Args:
        stats: Build statistics with warnings
    """
    if not stats.warnings:
        return

    # Header
    warning_count = len(stats.warnings)
    click.echo(
        click.style(
            f"\n⚠️  Build completed with warnings ({warning_count}):\n", fg="yellow", bold=True
        )
    )

    # Group by type
    type_names = {
        "jinja2": "Jinja2 Template Errors",
        "preprocessing": "Pre-processing Errors",
        "link": "Link Validation Warnings",
        "other": "Other Warnings",
    }

    grouped = stats.warnings_by_type

    for warning_type, type_warnings in grouped.items():
        type_name = type_names.get(warning_type, warning_type.title())
        click.echo(click.style(f"   {type_name} ({len(type_warnings)}):", fg="cyan", bold=True))

        for i, warning in enumerate(type_warnings):
            is_last = i == len(type_warnings) - 1
            prefix = "   └─ " if is_last else "   ├─ "

            # Show short path in yellow
            click.echo(
                click.style(prefix, fg="cyan") + click.style(warning.short_path, fg="yellow")
            )

            # Show message indented
            msg_prefix = "      " if is_last else "   │  "
            click.echo(
                click.style(msg_prefix + "└─ ", fg="cyan") + click.style(warning.message, fg="red")
            )

        click.echo()  # Blank line between types


def display_simple_build_stats(stats: BuildStats, output_dir: str | None = None) -> None:
    """
    Display simple build statistics for writers.

    Clean, minimal output focused on success/failure and critical issues only.
    Perfect for content authors who just want to know "did it work?"

    Args:
        stats: Build statistics to display
        output_dir: Output directory path to display
    """
    if stats.skipped:
        click.echo(click.style("\n✨ No changes detected - build skipped!", fg="cyan", bold=True))
        return

    # Success indicator
    if not stats.has_errors:
        build_time_s = stats.build_time_ms / 1000
        click.echo(
            click.style(
                f"\n✨ Built {stats.total_pages} pages in {build_time_s:.1f}s\n",
                fg="green",
                bold=True,
            )
        )
    else:
        click.echo(
            click.style(
                f"\n⚠️  Built with {len(stats.template_errors)} error(s)\n", fg="yellow", bold=True
            )
        )

    # Show template errors if any (critical for writers)
    if stats.template_errors:
        click.echo(
            click.style(f"❌ {len(stats.template_errors)} template error(s):", fg="red", bold=True)
        )
        for error in stats.template_errors[:3]:  # Show first 3
            # Extract key info without overwhelming detail
            template_name = (
                error.template_context.template_name
                if hasattr(error, "template_context")
                else "unknown"
            )
            message = str(error.message)[:80]  # Truncate long messages
            click.echo(f"   • {click.style(template_name, fg='yellow')}: {message}")

            # Show suggestion if available
            if hasattr(error, "suggestion") and error.suggestion:
                click.echo(click.style(f"     💡 {error.suggestion}", fg="cyan"))

        if len(stats.template_errors) > 3:
            remaining = len(stats.template_errors) - 3
            click.echo(f"   ... and {remaining} more")
        click.echo()

    # Show link validation warnings if any
    link_warnings = [w for w in stats.warnings if w.warning_type == "link"]
    if link_warnings:
        click.echo(click.style(f"⚠️  {len(link_warnings)} broken link(s) found:", fg="yellow"))
        for warning in link_warnings[:5]:  # Show first 5
            click.echo(f"   • {click.style(warning.short_path, fg='yellow')} → {warning.message}")
        if len(link_warnings) > 5:
            remaining = len(link_warnings) - 5
            click.echo(f"   ... and {remaining} more")
        click.echo()

    # Output location
    if output_dir:
        click.echo(click.style("📂 Output:", fg="cyan"))
        click.echo(click.style("   ↪ ", fg="cyan") + click.style(output_dir, fg="white", bold=True))
        click.echo()


def display_build_stats(
    stats: BuildStats, show_art: bool = True, output_dir: str | None = None
) -> None:
    """
    Display build statistics in a colorful table.

    Args:
        stats: Build statistics to display
        show_art: Whether to show ASCII art
        output_dir: Output directory path to display
    """
    if stats.skipped:
        click.echo(click.style("\n✨ No changes detected - build skipped!", fg="cyan", bold=True))
        return

    # Display warnings first if any
    if stats.warnings:
        display_warnings(stats)

    # Header with ASCII art integrated
    has_warnings = len(stats.warnings) > 0
    if has_warnings:
        click.echo(
            click.style("\n┌─────────────────────────────────────────────────────┐", fg="cyan")
        )
        click.echo(
            click.style("│", fg="cyan")
            + click.style(
                "         ⚠️  BUILD COMPLETE (WITH WARNINGS)          ", fg="yellow", bold=True
            )
            + click.style("│", fg="cyan")
        )
        click.echo(
            click.style("└─────────────────────────────────────────────────────┘", fg="cyan")
        )
    else:
        click.echo()
        if show_art:
            click.echo(
                click.style("    ᓚᘏᗢ  ", fg="yellow")
                + click.style("BUILD COMPLETE", fg="green", bold=True)
            )
        else:
            click.echo(click.style("    BUILD COMPLETE", fg="green", bold=True))

    # Content stats
    click.echo(click.style("\n📊 Content Statistics:", fg="cyan", bold=True))
    click.echo(
        click.style("   ├─ ", fg="cyan")
        + f"Pages:       {click.style(str(stats.total_pages), fg='green', bold=True)}"
        + f" ({stats.regular_pages} regular + {stats.generated_pages} generated)"
    )
    click.echo(
        click.style("   ├─ ", fg="cyan")
        + f"Sections:    {click.style(str(stats.total_sections), fg='green', bold=True)}"
    )
    click.echo(
        click.style("   ├─ ", fg="cyan")
        + f"Assets:      {click.style(str(stats.total_assets), fg='green', bold=True)}"
    )

    # Directive statistics (if present)
    if stats.total_directives > 0:
        # Get top 3 directive types
        top_types = sorted(stats.directives_by_type.items(), key=lambda x: x[1], reverse=True)[:3]
        type_summary = ", ".join([f"{t}({c})" for t, c in top_types])
        click.echo(
            click.style("   ├─ ", fg="cyan")
            + f"Directives:  {click.style(str(stats.total_directives), fg='magenta', bold=True)}"
            + f" ({type_summary})"
        )

    click.echo(
        click.style("   └─ ", fg="cyan")
        + f"Taxonomies:  {click.style(str(stats.taxonomies_count), fg='green', bold=True)}"
    )

    # Build info
    click.echo(click.style("\n⚙️  Build Configuration:", fg="cyan", bold=True))
    mode_parts = []
    if stats.incremental:
        mode_parts.append(click.style("incremental", fg="yellow"))
    if stats.parallel:
        mode_parts.append(click.style("parallel", fg="yellow"))
    if not mode_parts:
        mode_parts.append(click.style("sequential", fg="yellow"))

    mode_text = " + ".join(mode_parts)
    click.echo(click.style("   └─ ", fg="cyan") + f"Mode:        {mode_text}")

    # Performance stats
    click.echo(click.style("\n⏱️  Performance:", fg="cyan", bold=True))

    # Total time with color coding
    total_time_str = format_time(stats.build_time_ms)
    if stats.build_time_ms < 100:
        time_color = "green"
        emoji = "🚀"
    elif stats.build_time_ms < 1000:
        time_color = "yellow"
        emoji = "⚡"
    else:
        time_color = "red"
        emoji = "🐌"

    click.echo(
        click.style("   ├─ ", fg="cyan")
        + f"Total:       {click.style(total_time_str, fg=time_color, bold=True)} {emoji}"
    )

    # Phase breakdown (only if we have phase data)
    if stats.discovery_time_ms > 0:
        click.echo(
            click.style("   ├─ ", fg="cyan")
            + f"Discovery:   {click.style(format_time(stats.discovery_time_ms), fg='white')}"
        )
    if stats.taxonomy_time_ms > 0:
        click.echo(
            click.style("   ├─ ", fg="cyan")
            + f"Taxonomies:  {click.style(format_time(stats.taxonomy_time_ms), fg='white')}"
        )
    if stats.rendering_time_ms > 0:
        click.echo(
            click.style("   ├─ ", fg="cyan")
            + f"Rendering:   {click.style(format_time(stats.rendering_time_ms), fg='white')}"
        )
    if stats.assets_time_ms > 0:
        click.echo(
            click.style("   ├─ ", fg="cyan")
            + f"Assets:      {click.style(format_time(stats.assets_time_ms), fg='white')}"
        )
    if stats.postprocess_time_ms > 0:
        click.echo(
            click.style("   └─ ", fg="cyan")
            + f"Postprocess: {click.style(format_time(stats.postprocess_time_ms), fg='white')}"
        )

    # Fun stats
    if stats.build_time_ms > 0:
        pages_per_sec = (
            (stats.total_pages / stats.build_time_ms) * 1000 if stats.build_time_ms > 0 else 0
        )
        if pages_per_sec > 0:
            click.echo(click.style("\n📈 Throughput:", fg="cyan", bold=True))
            click.echo(
                click.style("   └─ ", fg="cyan")
                + f"{click.style(f'{pages_per_sec:.1f}', fg='magenta', bold=True)} pages/second"
            )

    # Output location
    if output_dir:
        click.echo(click.style("\n📂 Output:", fg="cyan", bold=True))
        click.echo(click.style("   ↪ ", fg="cyan") + click.style(output_dir, fg="white", bold=True))

    click.echo(click.style("\n─────────────────────────────────────────────────────\n", fg="cyan"))


def show_building_indicator(text: str = "Building") -> None:
    """Show a building indicator (static or animated based on terminal)."""
    try:
        from bengal.utils.rich_console import get_console, should_use_rich

        if should_use_rich():
            # Rich output with cat mascot
            console = get_console()
            console.print()
            console.print("    [bengal]ᓚᘏᗢ[/bengal]  [header]Building your site...[/header]")
            console.print()
            return
    except ImportError:
        pass  # Fall back to click

    # Fallback to click (for CI, dumb terminals, or if rich not available)
    click.echo(click.style(BENGAL_BUILDING, fg="yellow"))
    click.echo(click.style(f"🔨 {text}...\n", fg="cyan", bold=True))


def show_error(message: str, show_art: bool = True) -> None:
    """Show an error message with art."""
    if show_art:
        click.echo(click.style(BENGAL_ERROR, fg="red"))
    click.echo(click.style(f"❌ {message}", fg="red", bold=True))


def show_welcome() -> None:
    """Show welcome banner using Rich for stable borders."""
    try:
        from rich.align import Align
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        # Create centered content
        content = Align.center(
            "[bengal]ᓚᘏᗢ[/bengal]     [bold yellow]BENGAL SSG[/bold yellow]\n"
            "          [dim]Fast & Fierce Static Sites[/dim]",
            vertical="middle",
        )

        panel = Panel(
            content,
            border_style="yellow",
            padding=(1, 2),
            expand=False,
            width=58,  # Match original width
        )

        console.print()
        console.print(panel)
    except ImportError:
        # Fallback if Rich not available
        banner = r"""
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║           ᓚᘏᗢ     BENGAL SSG                        ║
    ║                   Fast & Fierce Static Sites         ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
    """
        click.echo(click.style(banner, fg="yellow", bold=True))


def show_clean_success(output_dir: str) -> None:
    """Show clean success message using CLI output system.

    Note: This is now only used for --force mode (when there's no prompt).
    Regular clean uses inline success message after prompt confirmation.
    """
    from bengal.utils.cli_output import CLIOutput

    # Create CLI output instance (simple, no profile needed for clean)
    cli = CLIOutput(quiet=False, verbose=False)

    cli.blank()
    cli.header("Cleaning output directory...")
    cli.info(f"   ↪ {output_dir}")
    cli.blank()
    cli.success("Clean complete!", icon="✓")
    cli.blank()


def display_template_errors(stats: BuildStats) -> None:
    """
    Display all collected template errors.

    Args:
        stats: Build statistics with template errors
    """
    if not stats.template_errors:
        return

    from bengal.rendering.errors import display_template_error

    error_count = len(stats.template_errors)
    click.echo(click.style(f"\n❌ Template Errors ({error_count}):\n", fg="red", bold=True))

    for i, error in enumerate(stats.template_errors, 1):
        click.echo(click.style(f"Error {i}/{error_count}:", fg="red", bold=True))
        display_template_error(error, use_color=True)

        if i < error_count:
            click.echo(click.style("─" * 80, fg="cyan"))
