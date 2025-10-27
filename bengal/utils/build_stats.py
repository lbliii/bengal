"""
Build statistics display with colorful output and ASCII art.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bengal.utils.cli_output import CLIOutput


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

    # Optional: builder-provided list of changed output paths (relative to output dir)
    # When provided, the dev server will prefer this over snapshot diffing for reload decisions.
    changed_outputs: list[str] | None = None

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

    cli = CLIOutput()

    # Header
    warning_count = len(stats.warnings)
    cli.error_header(f"Build completed with warnings ({warning_count})")

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

        if cli.use_rich:
            cli.console.print(f"   [header]{type_name} ({len(type_warnings)}):[/header]")
        else:
            cli.info(f"   {type_name} ({len(type_warnings)}):")

        for i, warning in enumerate(type_warnings):
            is_last = i == len(type_warnings) - 1
            prefix = "   └─ " if is_last else "   ├─ "

            # Show short path
            if cli.use_rich:
                cli.console.print(
                    f"   [info]{prefix}[/info][warning]{warning.short_path}[/warning]"
                )
            else:
                cli.info(f"{prefix}{warning.short_path}")

            # Show message indented
            msg_prefix = "      " if is_last else "   │  "
            if cli.use_rich:
                cli.console.print(
                    f"   [info]{msg_prefix}└─[/info] [error]{warning.message}[/error]"
                )
            else:
                cli.info(f"{msg_prefix}└─ {warning.message}")

        cli.blank()


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
    if not stats.has_errors:
        build_time_s = stats.build_time_ms / 1000
        cli.blank()
        cli.success(f"✨ Built {stats.total_pages} pages in {build_time_s:.1f}s")
        cli.blank()
    else:
        cli.blank()
        cli.warning(f"⚠️  Built with {len(stats.template_errors)} error(s)")
        cli.blank()

    # Show template errors if any (critical for writers)
    if stats.template_errors:
        cli.error_header(f"{len(stats.template_errors)} template error(s)")

        for error in stats.template_errors[:3]:  # Show first 3
            # Extract key info without overwhelming detail
            template_name = (
                error.template_context.template_name
                if hasattr(error, "template_context")
                else "unknown"
            )
            message = str(error.message)[:80]  # Truncate long messages

            if cli.use_rich:
                cli.console.print(f"   • [warning]{template_name}[/warning]: {message}")
            else:
                cli.info(f"   • {template_name}: {message}")

            # Show suggestion if available
            if hasattr(error, "suggestion") and error.suggestion:
                if cli.use_rich:
                    cli.console.print(f"     💡 [info]{error.suggestion}[/info]")
                else:
                    cli.info(f"     💡 {error.suggestion}")

        if len(stats.template_errors) > 3:
            remaining = len(stats.template_errors) - 3
            cli.info(f"   ... and {remaining} more")
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
        cli.path(output_dir, icon="📂", label="Output")


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
    cli = CLIOutput()

    if stats.skipped:
        cli.blank()
        cli.info("✨ No changes detected - build skipped!")
        return

    # Display warnings first if any
    if stats.warnings:
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
                "[info]│[/info][warning]         ⚠️  BUILD COMPLETE (WITH WARNINGS)          [/warning][info]│[/info]"
            )
            cli.console.print(
                "[info]└─────────────────────────────────────────────────────┘[/info]"
            )
        else:
            cli.blank()
            cli.warning("         ⚠️  BUILD COMPLETE (WITH WARNINGS)          ")
    else:
        cli.blank()
        if show_art:
            if cli.use_rich:
                cli.console.print("    [bengal]ᓚᘏᗢ[/bengal]  [success]BUILD COMPLETE[/success]")
            else:
                cli.info("    ᓚᘏᗢ  BUILD COMPLETE")
        else:
            cli.success("    BUILD COMPLETE")

    # Content stats
    cli.blank()
    if cli.use_rich:
        cli.console.print("[header]📊 Content Statistics:[/header]")
        cli.console.print(
            f"   [info]├─[/info] Pages:       [success]{stats.total_pages}[/success] ({stats.regular_pages} regular + {stats.generated_pages} generated)"
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
                f"   [info]├─[/info] Directives:  [highlight]{stats.total_directives}[/highlight] ({type_summary})"
            )

        cli.console.print(
            f"   [info]└─[/info] Taxonomies:  [success]{stats.taxonomies_count}[/success]"
        )
    else:
        cli.info("📊 Content Statistics:")
        cli.info(
            f"   ├─ Pages:       {stats.total_pages} ({stats.regular_pages} regular + {stats.generated_pages} generated)"
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
        cli.console.print("[header]⚙️  Build Configuration:[/header]")
        cli.console.print(f"   [info]└─[/info] Mode:        [warning]{mode_text}[/warning]")
    else:
        cli.info("⚙️  Build Configuration:")
        cli.info(f"   └─ Mode:        {mode_text}")

    # Performance stats
    cli.blank()
    total_time_str = format_time(stats.build_time_ms)

    # Determine time styling
    if stats.build_time_ms < 100:
        time_token = "success"
        emoji = "🚀"
    elif stats.build_time_ms < 1000:
        time_token = "warning"
        emoji = "⚡"
    else:
        time_token = "error"
        emoji = "🐌"

    if cli.use_rich:
        cli.console.print("[header]⏱️  Performance:[/header]")
        cli.console.print(
            f"   [info]├─[/info] Total:       [{time_token}]{total_time_str}[/{time_token}] {emoji}"
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
                f"   [info]└─[/info] Postprocess: {format_time(stats.postprocess_time_ms)}"
            )
    else:
        cli.info("⏱️  Performance:")
        cli.info(f"   ├─ Total:       {total_time_str} {emoji}")

        if stats.discovery_time_ms > 0:
            cli.info(f"   ├─ Discovery:   {format_time(stats.discovery_time_ms)}")
        if stats.taxonomy_time_ms > 0:
            cli.info(f"   ├─ Taxonomies:  {format_time(stats.taxonomy_time_ms)}")
        if stats.rendering_time_ms > 0:
            cli.info(f"   ├─ Rendering:   {format_time(stats.rendering_time_ms)}")
        if stats.assets_time_ms > 0:
            cli.info(f"   ├─ Assets:      {format_time(stats.assets_time_ms)}")
        if stats.postprocess_time_ms > 0:
            cli.info(f"   └─ Postprocess: {format_time(stats.postprocess_time_ms)}")

    # Fun stats
    if stats.build_time_ms > 0:
        pages_per_sec = (
            (stats.total_pages / stats.build_time_ms) * 1000 if stats.build_time_ms > 0 else 0
        )
        if pages_per_sec > 0:
            cli.blank()
            if cli.use_rich:
                cli.console.print("[header]📈 Throughput:[/header]")
                cli.console.print(
                    f"   [info]└─[/info] [highlight]{pages_per_sec:.1f}[/highlight] pages/second"
                )
            else:
                cli.info("📈 Throughput:")
                cli.info(f"   └─ {pages_per_sec:.1f} pages/second")

    # Output location
    if output_dir:
        cli.blank()
        cli.path(output_dir, icon="📂", label="Output")

    # Separator
    if cli.use_rich:
        cli.console.print()
        cli.console.print("[info]─────────────────────────────────────────────────────[/info]")
        cli.console.print()
    else:
        cli.blank()
        cli.info("─────────────────────────────────────────────────────")
        cli.blank()


def show_building_indicator(text: str = "Building") -> None:
    """Show a building indicator with Bengal cat mascot."""
    from bengal.utils.rich_console import get_console

    console = get_console()
    console.print()
    console.print("    [bengal]ᓚᘏᗢ[/bengal]  [header]Building your site...[/header]")
    console.print()


def show_error(message: str, show_art: bool = True) -> None:
    """Show an error message with mouse emoji (errors that Bengal needs to catch!)."""
    cli = CLIOutput()

    # Use the nice themed error header with mouse
    cli.error_header(message, mouse=show_art)


def show_welcome() -> None:
    """Show welcome banner with Bengal cat mascot."""
    from bengal.utils.cli_output import CLIOutput

    cli = CLIOutput()
    cli.header("BENGAL SSG", mascot=True, leading_blank=True, trailing_blank=False)


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

    cli = CLIOutput()
    error_count = len(stats.template_errors)

    # Use mouse emoji error header
    cli.error_header(f"❌ Template Errors ({error_count})")

    for i, error in enumerate(stats.template_errors, 1):
        if cli.use_rich:
            cli.console.print(f"[error]Error {i}/{error_count}:[/error]")
        else:
            cli.error(f"Error {i}/{error_count}:")

        display_template_error(error, use_color=True)

        if i < error_count:
            if cli.use_rich:
                cli.console.print("[info]" + "─" * 80 + "[/info]")
            else:
                cli.info("─" * 80)
