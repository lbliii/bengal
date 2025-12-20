"""
Rich build summary dashboard with performance insights.

DEPRECATED: This module has moved to bengal.orchestration.summary.
Import from bengal.orchestration.summary instead:

    from bengal.orchestration.summary import display_build_summary

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.orchestration.summary import (
    create_performance_grade_panel,
    create_suggestions_panel,
    create_timing_breakdown_table,
    display_build_summary,
)

__all__ = [
    "create_performance_grade_panel",
    "create_suggestions_panel",
    "create_timing_breakdown_table",
    "display_build_summary",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.build_summary is deprecated. "
        "Import from bengal.orchestration.summary instead: "
        "from bengal.orchestration.summary import display_build_summary",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
