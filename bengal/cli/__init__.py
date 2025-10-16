"""
Command-line interface for Bengal SSG.
"""

import click

from bengal import __version__
from bengal.cli.commands.new import new
from bengal.cli.commands.project import project_cli
from bengal.cli.commands.site import site_cli
from bengal.cli.commands.utils import utils_cli

# Import commands from new modular structure


class BengalGroup(click.Group):
    """Custom Click group with typo detection and suggestions."""

    def resolve_command(self, ctx, args):
        """Resolve command with fuzzy matching for typos."""
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as e:
            # Check if it's an unknown command error
            if "No such command" in str(e) and args:
                unknown_cmd = args[0]
                suggestions = self._get_similar_commands(unknown_cmd)

                if suggestions:
                    # Format error message with suggestions
                    msg = f"Unknown command '{unknown_cmd}'.\n\n"
                    msg += "Did you mean one of these?\n"
                    for _i, suggestion in enumerate(suggestions, 1):
                        msg += f"  • {click.style(suggestion, fg='cyan', bold=True)}\n"
                    msg += (
                        f"\nRun '{click.style('bengal --help', fg='yellow')}' to see all commands."
                    )
                    raise click.exceptions.UsageError(msg) from e

            # Re-raise original error if no suggestions
            raise

    def _get_similar_commands(self, unknown_cmd: str, max_suggestions: int = 3):
        """Find similar command names using simple string similarity."""
        from difflib import get_close_matches

        available_commands = list(self.commands.keys())

        # Use difflib for fuzzy matching
        matches = get_close_matches(
            unknown_cmd,
            available_commands,
            n=max_suggestions,
            cutoff=0.6,  # 60% similarity threshold
        )

        return matches


@click.group(cls=BengalGroup, name="bengal")
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main() -> None:
    """
    ᓚᘏᗢ Bengal SSG - A high-performance static site generator.

    """
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


from bengal.cli.commands.build import build as build_command

# Register commands from new modular structure
main.add_command(site_cli)
main.add_command(utils_cli)
main.add_command(new)
main.add_command(project_cli)
main.add_command(build_command)


if __name__ == "__main__":
    main()
