"""
Command-line interface for Bengal SSG.
"""

from __future__ import annotations

import click

from bengal import __version__
from bengal.cli.commands.assets import assets as assets_cli
from bengal.cli.commands.config import config_cli
from bengal.cli.commands.health import health_cli
from bengal.cli.commands.new import new
from bengal.cli.commands.project import project_cli
from bengal.cli.commands.site import site_cli
from bengal.cli.commands.utils import utils_cli
from bengal.cli.commands.validate import validate_cli
from bengal.utils.cli_output import CLIOutput
from bengal.utils.traceback_config import TracebackConfig

# Import commands from new modular structure
from .base import BengalCommand, BengalGroup


@click.group(cls=BengalGroup, name="bengal", invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main(ctx) -> None:
    """
    Bengal Static Site Generator CLI.

    Build fast, modern static sites with Python.

    Quick Start:
        bengal new site my-site    Create a new site
        bengal site build          Build your site
        bengal site serve          Start dev server with live reload

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


# Register commands from new modular structure
main.add_command(site_cli)
main.add_command(config_cli)
main.add_command(health_cli)
main.add_command(validate_cli)
main.add_command(utils_cli)
main.add_command(new)
main.add_command(project_cli)
main.add_command(assets_cli)


if __name__ == "__main__":
    main()
