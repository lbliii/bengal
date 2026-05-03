"""CLIOutput compatibility access for Milo commands.

The canonical singleton lives in :mod:`bengal.output.globals`. This module keeps
the historical ``bengal.cli.utils.output`` import path while ensuring CLI helpers
and lower-level output callers share one renderer instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.output.globals import (
    get_cli_output as _get_cli_output,
)
from bengal.output.globals import (
    init_cli_output as _init_cli_output,
)
from bengal.output.globals import (
    reset_cli_output as _reset_cli_output,
)

if TYPE_CHECKING:
    from bengal.output import CLIOutput


def get_cli_output(
    quiet: bool = False,
    verbose: bool = False,
    profile: Any | None = None,
    use_global: bool = True,
) -> CLIOutput:
    """Return the shared CLIOutput bridge or a one-off isolated renderer."""
    return _get_cli_output(
        quiet=quiet,
        verbose=verbose,
        profile=profile,
        use_global=use_global,
    )


def init_cli_output(
    profile: Any | None = None,
    quiet: bool = False,
    verbose: bool = False,
) -> CLIOutput:
    """Initialize the shared CLIOutput bridge for the current command."""
    return _init_cli_output(profile=profile, quiet=quiet, verbose=verbose)


def reset_cli_output() -> None:
    """Reset the shared CLIOutput bridge, primarily for tests."""
    _reset_cli_output()
