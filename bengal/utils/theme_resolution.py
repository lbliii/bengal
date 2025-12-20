"""
Theme resolution and inheritance chain building.

DEPRECATED: This module has moved to bengal.core.theme.resolution.
Import from bengal.core.theme instead:

    from bengal.core.theme import resolve_theme_chain, iter_theme_asset_dirs

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.core.theme.resolution import (
    iter_theme_asset_dirs,
    resolve_theme_chain,
)

__all__ = [
    "resolve_theme_chain",
    "iter_theme_asset_dirs",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.theme_resolution is deprecated. "
        "Import from bengal.core.theme instead: "
        "from bengal.core.theme import resolve_theme_chain, iter_theme_asset_dirs",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
