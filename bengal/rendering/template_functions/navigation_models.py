"""
DEPRECATED: Navigation models have moved to navigation/models.py.

This module provides backward-compatible imports. Update imports to:
    from bengal.rendering.template_functions.navigation.models import (
        BreadcrumbItem,
        PaginationItem,
        PaginationInfo,
        NavTreeItem,
        TocGroupItem,
        AutoNavItem,
    )

Or import from the package directly:
    from bengal.rendering.template_functions.navigation import BreadcrumbItem

This redirect will be removed in a future release.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "Import from bengal.rendering.template_functions.navigation.models instead of "
    "bengal.rendering.template_functions.navigation_models. "
    "This module is deprecated and will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all public symbols from new location
from bengal.rendering.template_functions.navigation.models import (  # noqa: E402
    AutoNavItem,
    BreadcrumbItem,
    NavTreeItem,
    PaginationInfo,
    PaginationItem,
    TocGroupItem,
)

__all__ = [
    "BreadcrumbItem",
    "PaginationItem",
    "PaginationInfo",
    "NavTreeItem",
    "TocGroupItem",
    "AutoNavItem",
]
