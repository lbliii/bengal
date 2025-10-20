"""Development server command."""


from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.core.site import Site
from bengal.server.constants import DEFAULT_DEV_HOST, DEFAULT_DEV_PORT
from bengal.utils.build_stats import show_error
from bengal.utils.logger import LogLevel, configure_logging, truncate_error


@click.command(cls=BengalCommand)
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
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def serve(
    host: str,
    port: int,
    watch: bool,
    auto_port: bool,
    open_browser: bool,
    verbose: bool,
    debug: bool,
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

    try:
        # Welcome banner removed for consistency with build command
        # The "Building your site..." header is sufficient

        config_path = Path(config).resolve() if config else None

        # Create site
        site = Site.from_config(root_path, config_path)

        # Enable strict mode in development (fail fast on errors)
        site.config["strict_mode"] = True

        # Enable debug mode if requested
        if debug:
            site.config["debug"] = True

        # Start server (this blocks)
        site.serve(
            host=host, port=port, watch=watch, auto_port=auto_port, open_browser=open_browser
        )

    except Exception as e:
        show_error(f"Server failed: {truncate_error(e)}", show_art=True)
        raise click.Abort() from e
