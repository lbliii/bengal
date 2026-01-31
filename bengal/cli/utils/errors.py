"""
Unified error handling utilities for CLI commands.

Consolidates the duplicated error handling logic from helpers/error_handling.py
into reusable functions. The decorator and context manager in error_handling.py
now delegate to these shared utilities.

Functions:
    handle_exception: Process and display an exception with appropriate formatting
    should_show_traceback: Determine if traceback should be shown based on config

"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.output import CLIOutput


def should_show_traceback(
    show_traceback: bool | None,
    is_bengal_error: bool = False,
) -> bool:
    """
    Determine if traceback should be shown based on configuration.

    Args:
        show_traceback: Explicit setting (None = auto-detect from config)
        is_bengal_error: Whether the exception is a BengalError

    Returns:
        True if traceback should be displayed.

    """
    if show_traceback is not None:
        return show_traceback

    # Auto-detect from traceback config
    try:
        from bengal.errors.traceback import TracebackConfig

        config = TracebackConfig.from_environment()
        renderer = config.get_renderer()
        style_value = renderer.style.value  # type: ignore[attr-defined]

        if is_bengal_error:
            # For BengalError, show if not minimal/off
            return style_value not in ("off", "minimal")
        else:
            # For other errors, show if not off
            return style_value != "off"
    except Exception:
        return False


def display_traceback(exception: BaseException, show_traceback: bool | None) -> None:
    """
    Display traceback for an exception if appropriate.

    Args:
        exception: The exception to display traceback for
        show_traceback: Whether to show traceback (None = auto-detect)

    """
    from bengal.errors import BengalError

    is_bengal = isinstance(exception, BengalError)

    if not should_show_traceback(show_traceback, is_bengal):
        return

    with contextlib.suppress(Exception):
        from bengal.errors.traceback import TracebackConfig

        TracebackConfig.from_environment().get_renderer().display_exception(exception)


def handle_exception(
    exception: BaseException,
    cli: CLIOutput,
    operation: str | None = None,
    show_art: bool = False,
    show_traceback: bool | None = None,
) -> None:
    """
    Handle an exception with appropriate CLI formatting.

    This is the unified exception handler that both handle_cli_errors decorator
    and cli_error_context context manager delegate to, eliminating code duplication.

    Args:
        exception: The exception to handle
        cli: CLIOutput instance for formatted output
        operation: Optional description of the operation that failed
        show_art: Whether to show ASCII art in error messages
        show_traceback: Whether to show traceback (None = auto-detect)

    Example:
        try:
            do_something()
        except Exception as e:
            handle_exception(e, cli, operation="building site")
            raise click.Abort() from e

    """
    from bengal.errors import BengalError

    if isinstance(exception, BengalError):
        _handle_bengal_error(exception, cli, show_traceback)
    else:
        _handle_generic_error(exception, cli, operation, show_art, show_traceback)


def _handle_bengal_error(
    exception: BaseException,
    cli: CLIOutput,
    show_traceback: bool | None,
) -> None:
    """Handle BengalError with beautiful formatted display."""
    from bengal.errors.display import display_bengal_error

    display_bengal_error(exception, cli)
    display_traceback(exception, show_traceback)


def _handle_generic_error(
    exception: BaseException,
    cli: CLIOutput,
    operation: str | None,
    show_art: bool,
    show_traceback: bool | None,
) -> None:
    """Handle non-Bengal errors with beautification attempt."""
    from bengal.errors.display import beautify_common_exception
    from bengal.orchestration.stats import show_error

    beautified = beautify_common_exception(exception)

    if beautified:
        message, suggestion = beautified

        if operation:
            cli.error_header(f"Failed to {operation}")
        else:
            cli.error_header("Error")

        cli.console.print(f"  {message}")

        if suggestion:
            cli.console.print()
            if cli.use_rich:
                cli.console.print(f"  [bold cyan]Tip:[/bold cyan] {suggestion}")
            else:
                cli.console.print(f"  Tip: {suggestion}")
        cli.console.print()
    else:
        # Generic error formatting
        error_msg = str(exception) or type(exception).__name__
        if operation:
            show_error(f"Failed to {operation}: {error_msg}", show_art=show_art)
        else:
            show_error(f"Command failed: {error_msg}", show_art=show_art)

    display_traceback(exception, show_traceback)
