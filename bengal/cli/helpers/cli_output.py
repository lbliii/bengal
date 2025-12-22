"""
Helper for creating standardized CLIOutput instances.

Provides a factory function for creating CLIOutput instances with
consistent default configuration. Use this helper in CLI commands
to ensure uniform output behavior across all commands.

Functions:
    get_cli_output: Create a CLIOutput with optional quiet/verbose flags

See Also:
    bengal.cli.output.globals: For global singleton CLIOutput management
"""

from __future__ import annotations

from bengal.output import CLIOutput


def get_cli_output(quiet: bool = False, verbose: bool = False) -> CLIOutput:
    """
    Create a standardized CLIOutput instance for command functions.

    This helper ensures consistent CLIOutput instantiation across all commands,
    making it easy to pass quiet/verbose flags and maintain consistent behavior.

    Args:
        quiet: Suppress non-critical output (default: False)
        verbose: Show detailed output (default: False)

    Returns:
        CLIOutput instance configured with the specified parameters

    Example:
        @click.command()
        @click.option("--quiet", "-q", is_flag=True)
        def my_command(quiet: bool):
            cli = get_cli_output(quiet=quiet)
            cli.info("Starting operation...")
    """
    return CLIOutput(quiet=quiet, verbose=verbose)
