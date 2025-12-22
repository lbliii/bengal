"""
Command-line interface for Bengal Static Site Generator.

This module provides the main CLI entry point and command registration
for the Bengal SSG. It assembles all command groups and registers
aliases for convenient access.

Alias System:
    Bengal supports intuitive command aliases for faster workflows:

    Top-level shortcuts (most common operations):
        bengal build     → bengal site build
        bengal serve     → bengal site serve
        bengal dev       → bengal site serve (alias)
        bengal clean     → bengal site clean
        bengal check     → bengal validate

    Short aliases (single letter for power users):
        bengal b         → bengal build
        bengal s         → bengal serve
        bengal c         → bengal clean
        bengal v         → bengal validate

    All original nested commands still work for discoverability.

Command Groups:
    - site: Core site operations (build, serve, clean)
    - config: Configuration management
    - collections: Content collections
    - health: Site health checks and diagnostics
    - debug: Developer debugging tools
    - engine: Template engine management
    - new: Project scaffolding
    - assets: Asset pipeline management
    - sources: Content source management
    - graph: Site structure analysis
    - version: Documentation versioning

Architecture:
    The CLI uses Click with custom BengalGroup and BengalCommand classes
    that provide themed help output and fuzzy command matching for typos.

Example:
    >>> # From command line
    >>> bengal build
    >>> bengal serve --port 8080
    >>> bengal new site my-blog --template blog

Related:
    - bengal/cli/base.py: Custom Click classes
    - bengal/cli/commands/: Individual command implementations
    - bengal/cli/dashboard/: Interactive TUI dashboard
"""

from __future__ import annotations

import click

from bengal import __version__
from bengal.cli.commands.assets import assets as assets_cli
from bengal.cli.commands.build import build as build_cmd
from bengal.cli.commands.clean import clean as clean_cmd
from bengal.cli.commands.collections import collections as collections_cli
from bengal.cli.commands.config import config_cli
from bengal.cli.commands.debug import debug_cli
from bengal.cli.commands.engine import engine as engine_cli
from bengal.cli.commands.explain import explain as explain_cli
from bengal.cli.commands.fix import fix as fix_cli
from bengal.cli.commands.graph import analyze as graph_analyze_cmd
from bengal.cli.commands.graph import graph_cli
from bengal.cli.commands.health import health_cli
from bengal.cli.commands.new import new
from bengal.cli.commands.project import project_cli
from bengal.cli.commands.serve import serve as serve_cmd
from bengal.cli.commands.site import site_cli
from bengal.cli.commands.sources import sources_group
from bengal.cli.commands.utils import utils_cli
from bengal.cli.commands.validate import validate as validate_cli
from bengal.cli.commands.version import version_cli
from bengal.errors.traceback import TracebackConfig
from bengal.output import CLIOutput

# Import commands from new modular structure
from .base import BengalCommand, BengalGroup


@click.group(cls=BengalGroup, name="bengal", invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="Bengal SSG")
@click.option(
    "--dashboard",
    is_flag=True,
    help="Launch unified interactive dashboard (Textual TUI)",
)
@click.option(
    "--start",
    "-s",
    type=click.Choice(["build", "serve", "health", "landing"]),
    default="build",
    help="Start dashboard on specific screen (requires --dashboard)",
)
@click.option(
    "--serve",
    "serve_web",
    is_flag=True,
    help="Serve dashboard as web app via textual-serve (requires --dashboard)",
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port for web dashboard server (default: 8000)",
)
@click.option(
    "--host",
    default="localhost",
    help="Host for web dashboard server (default: localhost)",
)
def main(
    ctx: click.Context,
    dashboard: bool = False,
    start: str = "build",
    serve_web: bool = False,
    port: int = 8000,
    host: str = "localhost",
) -> None:
    """
    Bengal Static Site Generator CLI.

    Build fast, modern static sites with Python.

    For more information, see: https://bengal.dev/docs
    """
    # Install rich traceback handler using centralized configuration
    # Style is determined by env (BENGAL_TRACEBACK) → defaults
    TracebackConfig.from_environment().install()

    # Launch unified dashboard if requested
    if dashboard:
        from pathlib import Path

        from bengal.cli.dashboard import run_unified_dashboard
        from bengal.core.site import Site

        # Load site from current directory
        site = None
        startup_error: str | None = None
        try:
            site = Site.from_config(Path.cwd())
        except Exception as e:
            startup_error = str(e)

        if serve_web:
            # Serve dashboard as web app via textual-serve
            import sys

            from textual_serve.server import Server

            # Reconstruct command without --serve to avoid recursion
            cmd = f"{sys.executable} -m bengal --dashboard --start {start}"
            server = Server(cmd, host=host, port=port, title="Bengal Dashboard")
            cli = CLIOutput()
            cli.success(f"Starting Bengal Dashboard at http://{host}:{port}")
            server.serve()
        else:
            run_unified_dashboard(site=site, start_screen=start, startup_error=startup_error)
        return

    # Show welcome banner if no command provided (but not if --help was used)
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        from click.core import HelpFormatter

        from bengal.orchestration.stats import show_welcome

        show_welcome()
        formatter = HelpFormatter()
        main.format_help(ctx, formatter)


# =============================================================================
# PRIMARY COMMAND GROUPS (organized by category)
# =============================================================================

# Site operations group (nested commands for discoverability)
main.add_command(site_cli)

# Configuration management
main.add_command(config_cli)

# Content collections
main.add_command(collections_cli)

# Health checks
main.add_command(health_cli)

# Debug and diagnostic tools
main.add_command(debug_cli)

# Template engine management
main.add_command(engine_cli)

# Project scaffolding
main.add_command(new)
main.add_command(project_cli)

# Asset management
main.add_command(assets_cli)

# Content sources
main.add_command(sources_group)

# Utilities
main.add_command(utils_cli)

# Graph analysis (promoted from utils for discoverability)
main.add_command(graph_cli)

# Version management for documentation
main.add_command(version_cli)

# =============================================================================
# TOP-LEVEL ALIASES (most common operations - no nesting required!)
# =============================================================================

# Build command - top level for convenience
main.add_command(build_cmd, name="build")

# Serve command - top level for convenience
main.add_command(serve_cmd, name="serve")

# Clean command - top level for convenience
main.add_command(clean_cmd, name="clean")

# Validate command - top level
main.add_command(validate_cli)

# Fix command - top level
main.add_command(fix_cli)

# Explain command - page introspection
main.add_command(explain_cli)

# =============================================================================
# SHORT ALIASES (single letter for power users)
# =============================================================================

# b → build
main.add_command(build_cmd, name="b")

# s → serve
main.add_command(serve_cmd, name="s")

# c → clean
main.add_command(clean_cmd, name="c")

# v → validate (check is also an alias)
main.add_command(validate_cli, name="v")
main.add_command(validate_cli, name="check")

# =============================================================================
# SEMANTIC ALIASES (alternative names that make sense)
# =============================================================================

# dev → serve (common in web dev)
main.add_command(serve_cmd, name="dev")

# lint → validate (common name for code checking)
main.add_command(validate_cli, name="lint")

# g → graph (short alias for graph commands)
main.add_command(graph_cli, name="g")

# analyze → graph report (unified site analysis)
main.add_command(graph_analyze_cmd, name="analyze")


if __name__ == "__main__":
    main()
