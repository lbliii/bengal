"""
Navigation helper functions for templates.

Provides functions for breadcrumbs, navigation trails, pagination,
hierarchical navigation trees, and auto-discovered navigation.

This package combines:
- Type-safe dataclass models for navigation elements
- Template functions for generating navigation structures
- Helper functions for section access and page lookups
- Cached NavTree infrastructure for O(1) navigation lookups

Organization:
    - models.py: Typed dataclasses (BreadcrumbItem, etc.)
    - breadcrumbs.py: get_breadcrumbs()
    - pagination.py: get_pagination_items()
    - tree.py: get_nav_tree(), get_nav_context()
    - auto_nav.py: get_auto_nav(), section menu helpers
    - toc.py: get_toc_grouped(), combine_track_toc_items()
    - section.py: get_section(), section_pages()

Core NavTree Models (bengal.core.nav_tree):
    - NavNode: Immutable node in navigation tree
    - NavTree: Cached tree with O(1) lookups
    - NavTreeContext: Per-page active trail overlay
    - NavNodeProxy: Template-friendly wrapper

Related:
    - bengal/rendering/template_functions/get_page.py: Page lookup
    - bengal/core/section.py: Section model
    - bengal/core/nav_tree.py: NavTree infrastructure
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.rendering.template_functions.navigation.auto_nav import (
    get_auto_nav,
)
from bengal.rendering.template_functions.navigation.breadcrumbs import (
    get_breadcrumbs,
)
from bengal.rendering.template_functions.navigation.models import (
    AutoNavItem,
    BreadcrumbItem,
    PaginationInfo,
    PaginationItem,
    TocGroupItem,
)
from bengal.rendering.template_functions.navigation.pagination import (
    get_pagination_items,
)
from bengal.rendering.template_functions.navigation.section import (
    get_section,
    section_pages,
)
from bengal.rendering.template_functions.navigation.toc import (
    combine_track_toc_items,
    get_toc_grouped,
)
from bengal.rendering.template_functions.navigation.tree import (
    get_nav_context,
    get_nav_tree,
)

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


__all__ = [
    # Functions
    "register",
    "get_breadcrumbs",
    "get_toc_grouped",
    "get_pagination_items",
    "get_nav_tree",
    "get_nav_context",
    "get_auto_nav",
    "get_section",
    "section_pages",
    "combine_track_toc_items",
    # Models
    "BreadcrumbItem",
    "PaginationItem",
    "PaginationInfo",
    "TocGroupItem",
    "AutoNavItem",
]


def register(env: Environment, site: Site) -> None:
    """Register navigation functions with Jinja2 environment."""

    # Create a closure that has access to get_page function from template context
    def combine_track_toc_with_get_page(track_items: list[str]) -> list[dict[str, Any]]:
        """Combine track TOC items using get_page from template context."""
        # Get get_page function from environment (registered by get_page.py)
        get_page_func = env.globals.get("get_page")
        if not get_page_func:
            return []
        return combine_track_toc_items(track_items, get_page_func)

    # Convenience wrappers for section lookups
    def get_section_wrapper(path: str) -> Section | None:
        """Wrapper with site closure."""
        return get_section(path, site)

    def section_pages_wrapper(path: str, recursive: bool = False) -> list[Page]:
        """Wrapper with site closure."""
        return section_pages(path, site, recursive)

    env.globals.update(
        {
            "get_breadcrumbs": get_breadcrumbs,
            "get_toc_grouped": get_toc_grouped,
            "get_pagination_items": get_pagination_items,
            "get_nav_tree": get_nav_tree,
            "get_nav_context": get_nav_context,
            "get_auto_nav": lambda: get_auto_nav(site),
            "combine_track_toc": combine_track_toc_with_get_page,
            "get_section": get_section_wrapper,
            "section_pages": section_pages_wrapper,
        }
    )
