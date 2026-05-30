"""Page helper package.

The legacy mutable ``Page`` class has been removed from this package root.
Import concrete helper modules directly, for example
``bengal.core.page.page_core`` or ``bengal.core.page.frontmatter``.
"""

from __future__ import annotations

from .bundle import BundleType, PageResource, PageResources
from .frontmatter import Frontmatter
from .page_core import PageCore

__all__ = [
    "BundleType",
    "Frontmatter",
    "PageCore",
    "PageResource",
    "PageResources",
]
