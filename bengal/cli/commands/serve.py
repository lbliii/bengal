"""Development server command."""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import (
    command_metadata,
    configure_traceback,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.server.constants import DEFAULT_DEV_HOST, DEFAULT_DEV_PORT
from bengal.utils.logger import LogLevel, configure_logging
from bengal.utils.traceback_config import TracebackStyle


@click.command(cls=BengalCommand)
@command_metadata(
    category="dev",
    description="Start development server with live reload",
    examples=[
        "bengal serve",
        "bengal serve --port 8080",
        "bengal serve --watch",
    ],
    requires_site=True,
    tags=["dev", "server", "quick"],
)
@click.option("--host", default=DEFAULT_DEV_HOST, help="Server host address")
@click.option("--port", "-p", default=DEFAULT_DEV_PORT, type=int, help="Server port number")
@click.option(
    "--watch/--no-watch", default=True, help="Watch for file changes and rebuild (default: enabled)"
)
@click.option(
    "--auto-port/--no-auto-port",
    default=True,
    help="Find available port if specified port is taken (default: enabled)",
)
@click.option(
    "--open",
    "-o",
    "open_browser",
    is_flag=True,
    help="Open browser automatically after server starts",
)
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["local", "preview", "production"], case_sensitive=False),
    help="Environment name (defaults to 'local' for dev server)",
)
@click.option(
    "--profile",
    type=click.Choice(["writer", "theme-dev", "dev"]),
    help="Config profile to use: writer, theme-dev, or dev",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed server activity (file watches, rebuilds, HTTP details)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Show debug output and full tracebacks (port checks, PID files, observer setup)",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
)
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
@handle_cli_errors(show_art=True)
def serve(
    host: str,
    port: int,
    watch: bool,
    auto_port: bool,
    open_browser: bool,
    environment: str | None,
    profile: str | None,
    verbose: bool,
    debug: bool,
    traceback: str | None,
    config: str,
    source: str,
) -> None:
    """
    🚀 Start development server with hot reload.

    Watches for changes in content, assets, and templates,
    automatically rebuilding the site when files are modified.
    """
    # Validate conflicting flags
    if verbose and debug:
        raise click.UsageError(
            "--verbose and --debug cannot be used together (debug includes all verbose output)"
        )

    # Configure logging based on flags
    if debug:
        log_level = LogLevel.DEBUG
    elif verbose:
        log_level = LogLevel.INFO
    else:
        log_level = LogLevel.WARNING  # Default: only show warnings/errors

    # Determine log file path
    root_path = Path(source).resolve()
    log_path = root_path / ".bengal-serve.log"

    configure_logging(
        level=log_level,
        log_file=log_path,
        verbose=verbose or debug,
        track_memory=False,  # Memory tracking not needed for dev server
    )

    # Configure traceback behavior BEFORE site loading so errors show properly
    configure_traceback(debug=debug, traceback=traceback)

    # Default to 'local' environment for dev server (unless explicitly specified)
    dev_environment = environment or "local"

    # Load site using helper
    site = load_site_from_cli(
        source=source,
        config=config,
        environment=dev_environment,
        profile=profile,
    )

    # Apply file-based traceback config after site is loaded (lowest precedence)
    configure_traceback(debug=debug, traceback=traceback, site=site)

    # Enable strict mode in development (fail fast on errors)
    site.config["strict_mode"] = True

    # Enable debug mode if requested
    if debug:
        site.config["debug"] = True

    # Start server (this blocks)
    site.serve(host=host, port=port, watch=watch, auto_port=auto_port, open_browser=open_browser)
