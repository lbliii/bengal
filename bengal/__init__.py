"""
Bengal SSG - A pythonic static site generator.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any


def _get_version() -> str:
    """Single source of truth: pyproject.toml via installed package metadata."""
    try:
        return version("bengal")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()
__author__ = "Bengal Contributors"

if TYPE_CHECKING:
    # Keep type-checker visibility for the public surface while avoiding
    # eager runtime imports of deep modules at `import bengal` time.
    from bengal.core.asset import Asset
    from bengal.core.section import Section
    from bengal.core.site import Site

__all__ = ["Asset", "Section", "Site", "__version__"]


def __getattr__(name: str) -> Any:
    """
    Lazily resolve top-level re-exports.

    This keeps `import bengal` lightweight while preserving the existing
    `bengal.Asset`, `bengal.Section`, and `bengal.Site` API.

    """
    if name == "Asset":
        from bengal.core.asset import Asset

        return Asset
    if name == "Section":
        from bengal.core.section import Section

        return Section
    if name == "Site":
        from bengal.core.site import Site

        return Site
    raise AttributeError(f"module 'bengal' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals().keys(), "Asset", "Section", "Site"])
