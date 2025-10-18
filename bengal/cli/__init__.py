"""
Command-line interface for Bengal SSG.
"""

import click

from bengal import __version__
from bengal.cli.commands.new import new
from bengal.cli.commands.project import project_cli
from bengal.cli.commands.site import site_cli
from bengal.cli.commands.utils import utils_cli
from bengal.utils.cli_output import CLIOutput

# Import commands from new modular structure
from .base import BengalCommand, BengalGroup


@click.group(cls=BengalGroup, name="bengal", invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main(ctx) -> None:
    """ """
    # Install rich traceback handler for beautiful error messages (unless in CI)
    import os

    if not os.getenv("CI"):
        try:
            from rich.traceback import install

            from bengal.utils.rich_console import get_console

            install(
                console=get_console(),
                show_locals=True,
                suppress=[click],  # Don't show click internals
                max_frames=20,
                width=None,  # Auto-detect terminal width
            )
        except ImportError:
            # Rich not available, skip
            pass

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
main.add_command(utils_cli)
main.add_command(new)
main.add_command(project_cli)


if __name__ == "__main__":
    main()
