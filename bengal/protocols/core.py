"""
Core protocols for page, section, and site-like objects.

This module provides Protocol definitions for core content objects,
enabling type-safe operations without depending on concrete implementations.

Protocols:
- PageLike: Interface for page objects
- SectionLike: Interface for content sections
- SiteLike: Interface for site objects
- NavigableSection: Sections with navigation support
- QueryableSection: Sections with query capabilities

Thread Safety:
    All protocols are designed for use in multi-threaded contexts.
    Implementations should be thread-safe for concurrent builds.

See Also:
- bengal.core.page: Concrete Page class
- bengal.core.section: Concrete Section class
- bengal.core.site: Concrete Site class

"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.config.types import SiteConfig
    from bengal.core.page.frontmatter import Frontmatter


# =============================================================================
# Page Protocol
# =============================================================================


@runtime_checkable
class PageLike(Protocol):
    """
    Protocol for page-like objects.
    
    Provides a unified interface for objects that can be treated as pages
    in templates, navigation, and rendering. This enables type-safe access
    to page properties without depending on the concrete Page class.
    
    Use Cases:
        - Template rendering: Functions accept PageLike for flexibility
        - Navigation building: Menu items work with any PageLike
        - Testing: Create minimal page-like objects for unit tests
    
    Thread Safety:
        Implementations should be thread-safe for concurrent access
        during parallel builds.
    
    Example:
            >>> def render_page(page: PageLike) -> str:
            ...     return f"<h1>{page.title}</h1>{page.content}"
        
    """

    @property
    def title(self) -> str:
        """Page title from frontmatter or filename."""
        ...

    @property
    def href(self) -> str:
        """URL path to the page (e.g., '/docs/guide/')."""
        ...

    @property
    def content(self) -> str:
        """Rendered HTML content (template-ready)."""
        ...

    @property
    def frontmatter(self) -> Frontmatter:
        """Page frontmatter object."""
        ...

    @property
    def date(self) -> datetime | None:
        """Publication date, if set."""
        ...

    @property
    def draft(self) -> bool:
        """Whether this is a draft page."""
        ...

    @property
    def weight(self) -> int:
        """Sort weight for ordering."""
        ...

    @property
    def source_path(self) -> Path:
        """Path to source file."""
        ...

    @property
    def metadata(self) -> dict[str, Any]:
        """Raw frontmatter/metadata dict for template access."""
        ...

    @property
    def tags(self) -> list[str]:
        """Tags for taxonomy filtering."""
        ...


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
    
    Note:
        This is the canonical definition. The duplicate in
        bengal.orchestration.types has been removed.
    
    Thread Safety:
        Implementations should be thread-safe for concurrent access
        during parallel builds.
    
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
    
    Thread Safety:
        Implementations should be thread-safe for concurrent access
        during parallel builds.
    
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

    @property
    def output_dir(self) -> Path:
        """Build output directory."""
        ...

    @property
    def dev_mode(self) -> bool:
        """Whether site is in development mode."""
        ...

    @property
    def theme(self) -> str:
        """Active theme name."""
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
# Config Protocol
# =============================================================================


@runtime_checkable
class ConfigLike(Protocol):
    """
    Protocol for dict-like config access.

    Provides a unified interface for config objects, enabling type-safe
    access whether the config is a raw dict or a Config object.

    Thread Safety:
        Implementations should be thread-safe for concurrent access.

    Example:
            >>> def get_setting(config: ConfigLike, key: str) -> Any:
            ...     return config.get(key)

    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with optional default."""
        ...

    def __getitem__(self, key: str) -> Any:
        """Get config value by key."""
        ...

    def __contains__(self, key: object) -> bool:
        """Check if key exists."""
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ConfigLike",
    "NavigableSection",
    "PageLike",
    "QueryableSection",
    "SectionLike",
    "SiteLike",
]
