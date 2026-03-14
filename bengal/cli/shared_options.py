"""
Shared CLI option decorators for Bengal commands.

Composable decorators for common options repeated across 10+ commands:
- --verbose: Verbose output
- --traceback: Traceback verbosity (full | compact | minimal | off)
- --source: Site root path (default: current directory)

Usage:
    from bengal.cli.shared_options import opt_source, opt_verbose, opt_traceback

    @click.command()
    @opt_source()
    @opt_verbose()
    def my_command(source: str, verbose: bool) -> None:
        ...
"""

from __future__ import annotations

import click

from bengal.errors.traceback import TracebackStyle


def opt_verbose(
    *,
    short: str | None = None,
    help_text: str = "Show verbose output",
):
    """Add --verbose option. Use short='-v' for short form."""
    opts = ["--verbose"]
    if short:
        opts.append(short)
    return click.option(
        *opts,
        "verbose",
        is_flag=True,
        default=False,
        help=help_text,
    )


def opt_traceback():
    """Add --traceback option with TracebackStyle choices."""
    return click.option(
        "--traceback",
        type=click.Choice([s.value for s in TracebackStyle]),
        default=None,
        help="Traceback verbosity: full | compact | minimal | off",
    )


def opt_source(
    *,
    default: str = ".",
    help_text: str = "Path to site root (Bengal project directory)",
):
    """Add --source option for site root path."""
    return click.option(
        "--source",
        type=click.Path(exists=True),
        default=default,
        help=help_text,
    )
