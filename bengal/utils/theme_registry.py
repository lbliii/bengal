"""
Installed theme discovery and utilities.

DEPRECATED: This module has moved to bengal.core.theme.registry.
Import from bengal.core.theme instead:

    from bengal.core.theme import ThemePackage, get_theme_package

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.core.theme.registry import (
    ThemePackage,
    clear_theme_cache,
    get_installed_themes,
    get_theme_package,
)

__all__ = [
    "ThemePackage",
    "get_installed_themes",
    "get_theme_package",
    "clear_theme_cache",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.theme_registry is deprecated. "
        "Import from bengal.core.theme instead: "
        "from bengal.core.theme import ThemePackage, get_theme_package",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
