"""Helper for creating standardized CLIOutput instances."""

from __future__ import annotations

from bengal.utils.cli_output import CLIOutput


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
