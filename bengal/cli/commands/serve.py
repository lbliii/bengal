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
from bengal.errors.traceback import TracebackStyle
from bengal.server.constants import DEFAULT_DEV_HOST, DEFAULT_DEV_PORT
from bengal.utils.logger import LogLevel, configure_logging


@click.command(cls=BengalCommand)
@command_metadata(
    category="dev",
    description="Start development server with live reload",
    examples=[
        "bengal serve",
        "bengal serve --port 8080",
        "bengal serve --watch",
        "bengal serve --version v2",
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
    "--open/--no-open",
    "-o/-O",
    "open_browser",
    default=True,
    help="Open browser automatically after server starts (default: enabled)",
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
    "--version",
    "-V",
    "version_scope",
    help="Focus on single version (e.g., v2, latest). Only rebuilds pages for this version.",
)
@click.option(
    "--all-versions",
    is_flag=True,
    help="Explicitly build all versions (default behavior, for clarity)",
)
@click.option(
    "--dashboard",
    is_flag=True,
    help="Launch interactive Textual dashboard (experimental)",
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
    version_scope: str | None,
    all_versions: bool,
    dashboard: bool,
    verbose: bool,
    debug: bool,
    traceback: str | None,
    config: str,
    source: str,
) -> None:
    """
    Start development server with hot reload.

    Watches for changes in content, assets, and templates,
    automatically rebuilding the site when files are modified.

    Version Scoping (RFC: rfc-versioned-docs-pipeline-integration):
        --version v2     Focus on single version, faster rebuilds
        --all-versions   Explicitly build all versions (default)
    """
    # Validate conflicting flags
    if verbose and debug:
        raise click.UsageError(
            "--verbose and --debug cannot be used together (debug includes all verbose output)"
        )

    # RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
    # Validate version flags
    if version_scope and all_versions:
        raise click.UsageError("--version and --all-versions cannot be used together")

    # Configure logging based on flags
    if debug:
        log_level = LogLevel.DEBUG
    elif verbose:
        log_level = LogLevel.INFO
    else:
        log_level = LogLevel.WARNING  # Default: only show warnings/errors

    # Determine log file path
    from bengal.utils.paths import BengalPaths

    root_path = Path(source).resolve()
    log_path = BengalPaths.get_serve_log_path(root_path)

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

    # Launch interactive dashboard if requested
    if dashboard:
        from bengal.cli.dashboard.serve import run_serve_dashboard

        run_serve_dashboard(
            site=site,
            host=host,
            port=port,
            watch=watch,
            open_browser=open_browser,
        )
        return  # Dashboard handles its own exit

    # RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
    # Start server with optional version scope
    site.serve(
        host=host,
        port=port,
        watch=watch,
        auto_port=auto_port,
        open_browser=open_browser,
        version_scope=version_scope,
    )
