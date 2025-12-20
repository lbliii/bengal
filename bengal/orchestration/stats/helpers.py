"""
Build statistics helper functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.output import CLIOutput

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats


def format_time(ms: float) -> str:
    """Format milliseconds for display."""
    if ms < 1:
        return f"{ms:.2f} ms"
    elif ms < 1000:
        return f"{int(ms)} ms"
    else:
        seconds = ms / 1000
        return f"{seconds:.2f} s"


def show_building_indicator(text: str = "Building") -> None:
    """Show a building indicator (minimal - header is shown by build orchestrator)."""
    # Note: The build orchestrator shows the full header with border, so we don't duplicate it here
    pass


def show_error(message: str, show_art: bool = True) -> None:
    """Show an error message with mouse emoji (errors that Bengal needs to catch!)."""
    cli = CLIOutput()

    # Use the nice themed error header with mouse
    cli.error_header(message, mouse=show_art)


def show_welcome() -> None:
    """Show welcome banner with Bengal cat mascot."""
    cli = CLIOutput()
    cli.header("BENGAL SSG", mascot=True, leading_blank=True, trailing_blank=False)


def show_clean_success(output_dir: str) -> None:
    """Show clean success message using CLI output system.

    Note: This is now only used for --force mode (when there's no prompt).
    Regular clean uses inline success message after prompt confirmation.
    """
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
