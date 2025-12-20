"""
Page Initializer - Ensures pages are correctly initialized.

DEPRECATED: This module has moved to bengal.discovery.page_factory.
Import from bengal.discovery.page_factory instead:

    from bengal.discovery.page_factory import PageInitializer

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.discovery.page_factory import PageInitializer

__all__ = [
    "PageInitializer",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.utils.page_initializer is deprecated. "
        "Import from bengal.discovery.page_factory instead: "
        "from bengal.discovery.page_factory import PageInitializer",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
