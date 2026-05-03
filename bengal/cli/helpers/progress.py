"""
Simple progress feedback helpers for CLI commands.

Provides lightweight progress display utilities for CLI commands,
with automatic TTY detection and Rich fallback support.

Functions:
    cli_progress: Context manager for manual progress updates
    simple_progress: Iterator wrapper with automatic progress tracking

Example:
    # Manual updates
    with cli_progress("Processing files...", total=100) as update:
        for i, item in enumerate(items):
            process(item)
            update(current=i + 1)

    # Automatic iteration
    for item in simple_progress("Checking...", items):
        check(item)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from bengal.cli.utils import get_cli_output

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from bengal.output import CLIOutput


@contextmanager
def cli_progress(
    description: str,
    total: int | None = None,
    cli: CLIOutput | None = None,
    enabled: bool = True,
) -> Iterator[Callable[..., None]]:
    """
    Context manager for simple progress feedback in CLI commands.

    Args:
        description: Description text for the progress task
        total: Total number of items (None for indeterminate)
        cli: Optional CLIOutput instance (creates new if not provided)
        enabled: Whether to show progress (auto-disabled for quiet/non-TTY)

    Yields:
        Update function: update(current: int | None, item: str | None) -> None

    Example:
        with cli_progress("Checking environments...", total=len(environments)) as update:
            for env in environments:
                check_environment(env)
                update(advance=1, item=env)

    """
    if cli is None:
        cli = get_cli_output()

    from bengal.utils.observability.terminal import is_interactive_terminal

    # Disable progress if quiet mode or not interactive
    if not enabled or cli.quiet or not is_interactive_terminal():

        def noop_update(
            current: int | None = None, item: str | None = None, advance: int | None = None
        ) -> None:
            pass

        yield noop_update
        return

    # Simple inline progress routed through the CLIOutput bridge.
    _current = 0

    def update(
        current: int | None = None, item: str | None = None, advance: int | None = None
    ) -> None:
        """Update progress."""
        nonlocal _current
        if current is not None:
            _current = current
        elif advance is not None:
            _current += advance
        else:
            _current += 1

        cli.progress_update(description, current=_current, total=total)

    cli.progress_start(description)
    try:
        yield update
    finally:
        cli.progress_finish()


def simple_progress(
    description: str,
    items: list[str] | Iterator[str],
    cli: CLIOutput | None = None,
    enabled: bool = True,
) -> Iterator[str]:
    """
    Simple progress wrapper for iterating over items.

    Args:
        description: Description text for the progress task
        items: List or iterator of items to process
        cli: Optional CLIOutput instance (creates new if not provided)
        enabled: Whether to show progress

    Yields:
        Each item from the input list/iterator

    Example:
        for item in simple_progress("Checking files...", file_list, cli=cli):
            process_file(item)

    """
    items_list = list(items) if not isinstance(items, list) else items

    with cli_progress(description, total=len(items_list), cli=cli, enabled=enabled) as update:
        for i, item in enumerate(items_list):
            update(current=i + 1, item=item)
            yield item
