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

# Import commands from new modular structure
from .base import BengalCommand, BengalGroup


# =============================================================================
# LAZY COMMAND LOADING
# =============================================================================
# Commands are loaded on-demand to drastically speed up CLI startup.
# This reduces startup time from ~3.7s to ~0.5s for simple commands like --version.


def _lazy_import(import_path: str):
    """
    Lazily import a command module and return the command object.

    Args:
        import_path: Module path and attribute (e.g., "bengal.cli.commands.build:build")

    Returns:
        The imported command object.
    """
    module_path, attr = import_path.split(":", 1)
    module = __import__(module_path, fromlist=[attr])
    return getattr(module, attr)


def _create_lazy_group(import_path: str, name: str, help: str | None = None):
    """Create a lazy-loaded command group."""

    @click.group(name=name, cls=BengalGroup, help=help)
    def lazy_group():
        pass

    # Override get_command to lazy-load subcommands
    original_get_command = lazy_group.get_command

    def get_command_lazy(ctx, cmd_name):
        cmd = original_get_command(ctx, cmd_name)
        if cmd is None:
            # Try to load from the real group
            real_group = _lazy_import(import_path)
            cmd = real_group.get_command(ctx, cmd_name)
        return cmd

    lazy_group.get_command = get_command_lazy

    # Override list_commands to lazy-load command list
    def list_commands_lazy(ctx):
        real_group = _lazy_import(import_path)
        return real_group.list_commands(ctx)

    lazy_group.list_commands = list_commands_lazy

    return lazy_group


# Lazy-loaded command groups
site_cli = _create_lazy_group(
    "bengal.cli.commands.site:site_cli", "site", "Site operations (build, serve, clean)"
)
cache_cli = _create_lazy_group(
    "bengal.cli.commands.cache:cache_cli", "cache", "Build cache management"
)
config_cli = _create_lazy_group(
    "bengal.cli.commands.config:config_cli", "config", "Configuration management"
)
collections_cli = _create_lazy_group(
    "bengal.cli.commands.collections:collections",
    "collections",
    "Content collections management",
)
health_cli = _create_lazy_group(
    "bengal.cli.commands.health:health_cli", "health", "Site health checks and diagnostics"
)
debug_cli = _create_lazy_group(
    "bengal.cli.commands.debug:debug_cli", "debug", "Developer debugging tools"
)
engine_cli = _create_lazy_group(
    "bengal.cli.commands.engine:engine", "engine", "Template engine management"
)
project_cli = _create_lazy_group(
    "bengal.cli.commands.project:project_cli", "project", "Project management"
)
assets_cli = _create_lazy_group(
    "bengal.cli.commands.assets:assets", "assets", "Asset pipeline management"
)
theme_cli = _create_lazy_group(
    "bengal.cli.commands.theme:theme", "theme", "Theme utilities"
)
sources_group = _create_lazy_group(
    "bengal.cli.commands.sources:sources_group", "sources", "Content source management"
)
utils_cli = _create_lazy_group(
    "bengal.cli.commands.utils:utils_cli", "utils", "Utility commands"
)
graph_cli = _create_lazy_group(
    "bengal.cli.commands.graph:graph_cli", "graph", "Site structure analysis"
)
version_cli = _create_lazy_group(
    "bengal.cli.commands.version:version_cli", "version", "Documentation versioning"
)


# Lazy-loaded single commands (not groups)
def _create_lazy_command(import_path: str, name: str):
    """Create a lazy-loaded single command."""

    @click.command(name=name, cls=BengalCommand)
    @click.pass_context
    def lazy_command(ctx, **kwargs):
        real_command = _lazy_import(import_path)
        return ctx.invoke(real_command, **kwargs)

    # Copy metadata from real command for help text
    def get_real_command():
        return _lazy_import(import_path)

    lazy_command.get_short_help_str = lambda *args, **kw: get_real_command().get_short_help_str(
        *args, **kw
    )
    lazy_command.get_params = lambda *args, **kw: get_real_command().get_params(*args, **kw)

    return lazy_command


build_cmd = _create_lazy_command("bengal.cli.commands.build:build", "build")
serve_cmd = _create_lazy_command("bengal.cli.commands.serve:serve", "serve")
clean_cmd = _create_lazy_command("bengal.cli.commands.clean:clean", "clean")
validate_cli = _create_lazy_command("bengal.cli.commands.validate:validate", "validate")
fix_cli = _create_lazy_command("bengal.cli.commands.fix:fix", "fix")
explain_cli = _create_lazy_command("bengal.cli.commands.explain:explain", "explain")
new = _create_lazy_command("bengal.cli.commands.new:new", "new")
upgrade_cmd = _create_lazy_command("bengal.cli.commands.upgrade.command:upgrade", "upgrade")
graph_analyze_cmd = _create_lazy_command("bengal.cli.commands.graph:analyze", "analyze")

# Experimental commands
provenance_cli = None
try:
    provenance_cli = _create_lazy_group(
        "bengal.cli.commands.provenance:provenance_cli",
        "provenance",
        "Build provenance tracking",
    )
except ImportError:
    pass


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

    For more information, see: https://lbliii.github.io/bengal/docs

    """
    import sys

    # Python 3.14+ required - warn early and clearly
    if sys.version_info < (3, 14):
        click.secho(
            f"\n⚠️  WARNING: Bengal requires Python 3.14+\n"
            f"   You are running Python {sys.version_info.major}.{sys.version_info.minor}\n"
            f"   Some features (compression.zstd, performance optimizations) will fail.\n"
            f"   Install Python 3.14: https://www.python.org/downloads/\n",
            fg="yellow",
            bold=True,
            err=True,
        )

    # Install rich traceback handler using centralized configuration
    # Style is determined by env (BENGAL_TRACEBACK) → defaults
    # Lazy-load to avoid importing all of errors.traceback on startup
    from bengal.errors.traceback import TracebackConfig

    TracebackConfig.from_environment().install()

    # Launch unified dashboard if requested
    if dashboard:
        from pathlib import Path

        from bengal.cli.dashboard import run_unified_dashboard
        from bengal.core.site import Site
        from bengal.output import CLIOutput

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

# Cache management (CI cache keys)
main.add_command(cache_cli)

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

# Theme utilities
main.add_command(theme_cli)

# Content sources
main.add_command(sources_group)

# Utilities
main.add_command(utils_cli)

# Graph analysis (promoted from utils for discoverability)
main.add_command(graph_cli)

# Version management for documentation
main.add_command(version_cli)

# Upgrade command - self-update
main.add_command(upgrade_cmd)

# Provenance tracking (experimental)
if provenance_cli is not None:
    main.add_command(provenance_cli)

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


# =============================================================================
# UPGRADE NOTIFICATION HOOK
# =============================================================================


@main.result_callback()
@click.pass_context
def _show_upgrade_notification_after_command(
    ctx: click.Context, result: object, **kwargs: object
) -> None:
    """
    Show upgrade notification after command completion.

    This is called after every command finishes. It checks for available
    upgrades and shows a non-intrusive banner if one is available.

    The notification is:
    - Cached (only checks PyPI once per 24h)
    - Skipped in CI environments
    - Skipped for non-TTY output
    - Silent on any error
    """
    # Don't show for certain commands
    if ctx.invoked_subcommand in ("upgrade", "version", None):
        return

    try:
        # Lazy import - only load upgrade check module when actually needed
        from bengal.cli.commands.upgrade.command import show_upgrade_notification

        show_upgrade_notification()
    except Exception:
        pass  # Never fail CLI due to upgrade check


if __name__ == "__main__":
    main()
