"""
Command-line interface for Bengal SSG.

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
from bengal.cli.commands.explain import explain as explain_cli
from bengal.cli.commands.fix import fix as fix_cli
from bengal.cli.commands.graph import graph_cli
from bengal.cli.commands.health import health_cli
from bengal.cli.commands.new import new
from bengal.cli.commands.project import project_cli
from bengal.cli.commands.serve import serve as serve_cmd
from bengal.cli.commands.site import site_cli
from bengal.cli.commands.sources import sources_group
from bengal.cli.commands.utils import utils_cli
from bengal.cli.commands.validate import validate as validate_cli
from bengal.utils.cli_output import CLIOutput
from bengal.utils.traceback_config import TracebackConfig

# Import commands from new modular structure
from .base import BengalCommand, BengalGroup


@click.group(cls=BengalGroup, name="bengal", invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main(ctx: click.Context) -> None:
    """
    Bengal Static Site Generator CLI.

    Build fast, modern static sites with Python.

    Quick Start:
        bengal build          Build your site
        bengal serve          Start dev server with live reload
        bengal new site       Create a new site

    Shortcuts:
        bengal b              Build (short alias)
        bengal s / dev        Serve (short aliases)
        bengal c              Clean (short alias)

    For more information, see: https://bengal.dev/docs
    """
    # Install rich traceback handler using centralized configuration
    # Style is determined by env (BENGAL_TRACEBACK) → defaults
    TracebackConfig.from_environment().install()

    # Show welcome banner if no command provided (but not if --help was used)
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        from click.core import HelpFormatter

        from bengal.utils.build_stats import show_welcome
        from bengal.utils.cli_output import CLIOutput

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
from bengal.cli.commands.graph import analyze as graph_analyze_cmd

main.add_command(graph_analyze_cmd, name="analyze")


if __name__ == "__main__":
    main()
