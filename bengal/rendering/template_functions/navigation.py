"""
DEPRECATED: Navigation functions have moved to navigation/ package.

This module provides backward-compatible imports. Update imports to:
    from bengal.rendering.template_functions.navigation import (
        register,
        get_breadcrumbs,
        get_pagination_items,
        get_nav_tree,
        get_auto_nav,
        get_toc_grouped,
        get_section,
        section_pages,
    )

This redirect will be removed in a future release.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "Import from bengal.rendering.template_functions.navigation instead of "
    "bengal.rendering.template_functions.navigation (module). "
    "The navigation.py module is deprecated and will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all public symbols from new package
from bengal.rendering.template_functions.navigation import (  # noqa: E402
    AutoNavItem,
    BreadcrumbItem,
    NavTreeItem,
    PaginationInfo,
    PaginationItem,
    TocGroupItem,
    combine_track_toc_items,
    get_auto_nav,
    get_breadcrumbs,
    get_nav_tree,
    get_pagination_items,
    get_section,
    get_toc_grouped,
    register,
    section_pages,
)

__all__ = [
    "register",
    "get_breadcrumbs",
    "get_toc_grouped",
    "get_pagination_items",
    "get_nav_tree",
    "get_auto_nav",
    "get_section",
    "section_pages",
    "combine_track_toc_items",
    "BreadcrumbItem",
    "PaginationItem",
    "PaginationInfo",
    "NavTreeItem",
    "TocGroupItem",
    "AutoNavItem",
]
