"""
Live progress display system with profile-aware output.

DEPRECATED: This module has moved to bengal.cli.progress.
Import from bengal.cli.progress instead:

    from bengal.cli.progress import LiveProgressManager, PhaseProgress

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.cli.progress import (
    LiveProgressManager,
    PhaseProgress,
    PhaseStatus,
)

__all__ = [
    "LiveProgressManager",
    "PhaseProgress",
    "PhaseStatus",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.live_progress is deprecated. "
        "Import from bengal.cli.progress instead: "
        "from bengal.cli.progress import LiveProgressManager",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
