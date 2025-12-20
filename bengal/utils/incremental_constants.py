"""
Constants for incremental build logic.

DEPRECATED: This module has moved to bengal.orchestration.constants.
Import from bengal.orchestration.constants instead:

    from bengal.orchestration.constants import NAV_AFFECTING_KEYS, extract_nav_metadata

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.orchestration.constants import (
    NAV_AFFECTING_KEYS,
    extract_nav_metadata,
)

__all__ = [
    "NAV_AFFECTING_KEYS",
    "extract_nav_metadata",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.incremental_constants is deprecated. "
        "Import from bengal.orchestration.constants instead: "
        "from bengal.orchestration.constants import NAV_AFFECTING_KEYS",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
