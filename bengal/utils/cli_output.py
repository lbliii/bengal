"""
Centralized CLI output system for Bengal.

DEPRECATED: This module has moved to bengal.cli.output.
Import from bengal.output instead:

    from bengal.output import CLIOutput, get_cli_output, init_cli_output

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.output import (
    CLIOutput,
    MessageLevel,
    OutputStyle,
    get_cli_output,
    init_cli_output,
)

__all__ = [
    "CLIOutput",
    "MessageLevel",
    "OutputStyle",
    "get_cli_output",
    "init_cli_output",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.cli_output is deprecated. "
        "Import from bengal.output instead: "
        "from bengal.output import CLIOutput, get_cli_output",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
