"""
Global CLI output instance management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.cli.output.core import CLIOutput

_cli_output: CLIOutput | None = None


def get_cli_output() -> CLIOutput:
    """Get the global CLI output instance."""
    global _cli_output
    if _cli_output is None:
        from bengal.cli.output.core import CLIOutput

        _cli_output = CLIOutput()
    return _cli_output


def init_cli_output(
    profile: Any | None = None, quiet: bool = False, verbose: bool = False
) -> CLIOutput:
    """Initialize the global CLI output instance with settings."""
    global _cli_output
    from bengal.cli.output.core import CLIOutput

    _cli_output = CLIOutput(profile=profile, quiet=quiet, verbose=verbose)
    return _cli_output


