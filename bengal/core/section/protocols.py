"""
Protocol definitions for section and site-like objects.

This module provides Protocol definitions for section and site objects,
enabling type-safe operations without depending on concrete implementations.

Use Cases:
- Menu building: Accept SectionLike for flexible navigation
- Template rendering: Work with any site-like object
- Testing: Create minimal implementations for unit tests
- Decoupling: Break circular dependencies between modules

See Also:
- :mod:`bengal.core.section`: Concrete Section class
- :mod:`bengal.core.site`: Concrete Site class
- :mod:`bengal.core.page.computed`: PageLike protocol

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.config.types import SiteConfig
    from bengal.core.page.computed import PageLike


# =============================================================================
# Section Protocol
# =============================================================================


@runtime_checkable
class SectionLike(Protocol):
    """
    Protocol for section-like objects.
    
    Provides a unified interface for content sections in templates,
    navigation, and menu building. Enables type-safe operations without
    depending on the concrete Section class.
    
    Example:
            >>> def build_nav(section: SectionLike) -> list[dict]:
            ...     return [{"title": p.title, "href": p.href} for p in section.pages]
        
    """

    @property
    def name(self) -> str:
        """Section name (directory name)."""
        ...

    @property
    def title(self) -> str:
        """Display title (from index page or name)."""
        ...

    @property
    def path(self) -> Path | None:
        """Path to section directory (None for virtual sections)."""
        ...

    @property
    def href(self) -> str:
        """URL path to section (e.g., '/docs/')."""
        ...

    @property
    def pages(self) -> list[PageLike]:
        """Pages directly in this section."""
        ...

    @property
    def subsections(self) -> list[SectionLike]:
        """Child sections."""
        ...

    @property
    def parent(self) -> SectionLike | None:
        """Parent section (None for root)."""
        ...

    @property
    def index_page(self) -> PageLike | None:
        """Index page for this section (_index.md or index.md)."""
        ...

    @property
    def is_root(self) -> bool:
        """Whether this is the root section."""
        ...


# =============================================================================
# Site Protocol
# =============================================================================


@runtime_checkable
class SiteLike(Protocol):
    """
    Protocol for site-like objects.
    
    Provides a unified interface for site operations in templates,
    rendering, and orchestration. Enables type-safe site access without
    depending on the concrete Site class.
    
    Example:
            >>> def get_page_count(site: SiteLike) -> int:
            ...     return len(site.pages)
        
    """

    @property
    def title(self) -> str:
        """Site title from configuration."""
        ...

    @property
    def baseurl(self) -> str:
        """Base URL for the site."""
        ...

    @property
    def config(self) -> SiteConfig:
        """Site configuration dictionary."""
        ...

    @property
    def pages(self) -> list[PageLike]:
        """All pages in the site."""
        ...

    @property
    def sections(self) -> list[SectionLike]:
        """Top-level sections."""
        ...

    @property
    def root_section(self) -> SectionLike:
        """Root section of the content tree."""
        ...

    @property
    def root_path(self) -> Path:
        """Path to site root directory."""
        ...


# =============================================================================
# Navigation Protocols
# =============================================================================


@runtime_checkable
class NavigableSection(Protocol):
    """
    Protocol for sections with navigation support.
    
    Extends SectionLike with navigation-specific methods for building
    menus, breadcrumbs, and prev/next navigation.
        
    """

    @property
    def title(self) -> str:
        """Display title."""
        ...

    @property
    def href(self) -> str:
        """URL path."""
        ...

    @property
    def weight(self) -> int:
        """Sort weight (lower = earlier)."""
        ...

    @property
    def visible_in_nav(self) -> bool:
        """Whether to show in navigation."""
        ...

    @property
    def nav_label(self) -> str | None:
        """Override label for navigation (if different from title)."""
        ...


# =============================================================================
# Query Protocols
# =============================================================================


@runtime_checkable
class QueryableSection(Protocol):
    """
    Protocol for sections with query capabilities.
    
    Provides methods for retrieving pages with filtering and sorting.
        
    """

    def get_pages(
        self,
        *,
        include_drafts: bool = False,
        sort_by: str = "weight",
        reverse: bool = False,
    ) -> list[PageLike]:
        """Get pages with filtering and sorting."""
        ...

    def get_all_pages(self, *, include_drafts: bool = False) -> list[PageLike]:
        """Get all pages including from subsections."""
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "SectionLike",
    "SiteLike",
    "NavigableSection",
    "QueryableSection",
]
