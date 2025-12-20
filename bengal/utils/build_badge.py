"""
Build badge and duration formatting utilities.

DEPRECATED: This module has moved to bengal.orchestration.badge.
Import from bengal.orchestration.badge instead:

    from bengal.orchestration.badge import format_duration_ms_compact, build_shields_like_badge_svg

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.orchestration.badge import (
    build_shields_like_badge_svg,
    format_duration_ms_compact,
)

__all__ = [
    "format_duration_ms_compact",
    "build_shields_like_badge_svg",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.build_badge is deprecated. "
        "Import from bengal.orchestration.badge instead: "
        "from bengal.orchestration.badge import format_duration_ms_compact",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
