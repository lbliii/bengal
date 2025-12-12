"""
Bengal SSG - A pythonic static site generator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.5-rc1"
__author__ = "Bengal Contributors"

if TYPE_CHECKING:
    # Keep type-checker visibility for the public surface while avoiding
    # eager runtime imports of deep modules at `import bengal` time.
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

__all__ = ["Asset", "Page", "Section", "Site", "__version__"]


def __getattr__(name: str) -> Any:
    """
    Lazily resolve top-level re-exports.

    This keeps `import bengal` lightweight while preserving the existing
    `bengal.Asset`, `bengal.Page`, `bengal.Section`, and `bengal.Site` API.
    """
    if name == "Asset":
        from bengal.core.asset import Asset

        return Asset
    if name == "Page":
        from bengal.core.page import Page

        return Page
    if name == "Section":
        from bengal.core.section import Section

        return Section
    if name == "Site":
        from bengal.core.site import Site

        return Site
    raise AttributeError(f"module 'bengal' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals().keys(), "Asset", "Page", "Section", "Site"])
