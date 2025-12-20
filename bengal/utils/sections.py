"""
Section-related utility helpers.

DEPRECATED: This module has moved to bengal.core.section.
Import from bengal.core.section instead:

    from bengal.core.section import resolve_page_section_path

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.core.section import resolve_page_section_path

__all__ = [
    "resolve_page_section_path",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.sections is deprecated. "
        "Import from bengal.core.section instead: "
        "from bengal.core.section import resolve_page_section_path",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
