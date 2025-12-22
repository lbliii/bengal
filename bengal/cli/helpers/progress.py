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

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from bengal.cli.helpers import get_cli_output
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

    # Disable progress if quiet mode or not a TTY
    if not enabled or cli.quiet or not cli.use_rich or not cli.console.is_terminal:
        # Return a no-op update function
        def noop_update(
            current: int | None = None, item: str | None = None, advance: int | None = None
        ) -> None:
            pass

        yield noop_update
        return

    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="green"),
        TaskProgressColumn(),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total}" if total else ""),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=cli.console,
        transient=False,
    ) as progress:
        task = progress.add_task(f"[cyan]{description}", total=total)

        def update(
            current: int | None = None, item: str | None = None, advance: int | None = None
        ) -> None:
            """Update progress."""
            if current is not None:
                progress.update(task, completed=current)
            elif advance is not None:
                progress.update(task, advance=advance)
            elif total:
                progress.update(task, advance=1)
            else:
                progress.update(task, advance=1)

        yield update


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
