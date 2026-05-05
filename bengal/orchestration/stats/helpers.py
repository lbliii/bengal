"""
Build statistics helper functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.output import get_cli_output

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats


def format_time(ms: float) -> str:
    """Format milliseconds for display."""
    if ms < 1:
        return f"{ms:.2f} ms"
    if ms < 1000:
        return f"{int(ms)} ms"
    seconds = ms / 1000
    return f"{seconds:.2f} s"


def show_building_indicator(text: str = "Building") -> None:
    """Show a building indicator (minimal - header is shown by build orchestrator)."""
    # Note: The build orchestrator shows the full header with border, so we don't duplicate it here


def show_error(message: str, show_art: bool = True) -> None:
    """Show an error message with mouse emoji (errors that Bengal needs to catch!)."""
    cli = get_cli_output()
    cli.error_header(message, mouse=show_art)


def show_welcome() -> None:
    """Show welcome banner with Bengal cat mascot."""
    cli = get_cli_output()
    cli.header("BENGAL SSG", mascot=True, leading_blank=True, trailing_blank=False)


def show_clean_success(output_dir: str) -> None:
    """Show clean success message.

    Note: This is now only used for --force mode (when there's no prompt).
    Regular clean uses inline success message after prompt confirmation.

    """
    cli = get_cli_output(quiet=False, verbose=False)

    cli.blank()
    cli.header("Cleaning output directory...")
    cli.info(f"   ↪ {output_dir}")
    cli.blank()
    cli.success("Clean complete!", icon="✓")
    cli.blank()


def display_template_errors(stats: BuildStats) -> None:
    """
    Display all collected template errors cleanly after build completes.

    Args:
        stats: Build statistics with template errors

    """
    if not stats.template_errors:
        return

    from bengal.errors.display import display_template_render_error

    cli = get_cli_output()
    error_count = len(stats.template_errors)

    cli.error_header(f"❌ Template Errors ({error_count})")

    for i, error in enumerate(stats.template_errors, 1):
        cli.error(f"Error {i}/{error_count}:")
        display_template_render_error(error, cli)

        if i < error_count:
            cli.info("─" * 80)

    # Show summary of suppressed duplicate errors (if any)
    dedup = stats.get_error_deduplicator()
    dedup.display_summary()
