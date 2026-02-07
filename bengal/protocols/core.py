"""
Core protocols for page, section, and site-like objects.

This module provides Protocol definitions for core content objects,
enabling type-safe operations without depending on concrete implementations.

Role-Based Page Protocols:
- Renderable: Content that can be rendered to HTML
- Navigable: Objects with URL/path/hierarchy properties
- Summarizable: Objects with metadata for search/summaries
- PageLike: Full page interface (extends all three roles)

Section Protocols:
- SectionLike: Interface for content sections
- NavigableSection: Sections with navigation support
- QueryableSection: Sections with query capabilities

Role-Based Site Protocols:
- SiteConfig: Site configuration and identity
- SiteContent: Site content (pages, sections, data)
- SiteLike: Full site interface (extends both roles)

Other:
- ConfigLike: Dict-like config access protocol

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
    from bengal.config.types import SiteConfig as SiteConfigType
    from bengal.core.page.frontmatter import Frontmatter
    from bengal.core.theme import Theme
    from bengal.core.version import VersionConfig


# =============================================================================
# Page Role Protocols
# =============================================================================


@runtime_checkable
class Renderable(Protocol):
    """
    Protocol for objects with renderable content.

    Use when a function only needs access to rendered HTML, TOC, or
    template information -- not navigation or metadata.

    Consumers: rendering pipeline, cache checker, complexity estimator.
    """

    @property
    def content(self) -> str:
        """Rendered HTML content (template-ready)."""
        ...

    @property
    def toc(self) -> str:
        """Rendered table of contents HTML."""
        ...

    @property
    def toc_items(self) -> list[Any]:
        """Structured table of contents items."""
        ...

    @property
    def template_name(self) -> str:
        """Template to use for rendering."""
        ...


@runtime_checkable
class Navigable(Protocol):
    """
    Protocol for objects with navigation/URL properties.

    Use when a function only needs URL, path, or hierarchy information
    -- not content or metadata.

    Consumers: path registry, query index, nav tree, template get_page.
    """

    @property
    def href(self) -> str:
        """URL path to the page (e.g., '/docs/guide/')."""
        ...

    @property
    def source_path(self) -> Path:
        """Path to source file."""
        ...

    @property
    def output_path(self) -> Path | None:
        """Path where the rendered page will be written."""
        ...

    @property
    def slug(self) -> str:
        """URL slug derived from filename or frontmatter."""
        ...

    @property
    def is_virtual(self) -> bool:
        """Whether this is a virtual (generated) page."""
        ...


@runtime_checkable
class Summarizable(Protocol):
    """
    Protocol for objects with metadata suitable for summaries and search.

    Use when a function only needs title, date, tags, or description
    -- not rendered content or navigation paths.

    Consumers: taxonomy, indexes (category, author), content type classification.
    """

    @property
    def title(self) -> str:
        """Page title from frontmatter or filename."""
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
    def metadata(self) -> dict[str, Any]:
        """Raw frontmatter/metadata dict for template access."""
        ...

    @property
    def tags(self) -> list[str]:
        """Tags for taxonomy filtering."""
        ...

    @property
    def description(self) -> str:
        """Page description from frontmatter."""
        ...

    @property
    def word_count(self) -> int:
        """Word count of content."""
        ...

    @property
    def reading_time(self) -> int:
        """Estimated reading time in minutes."""
        ...

    @property
    def excerpt(self) -> str:
        """Content excerpt/summary."""
        ...

    @property
    def type(self) -> str:
        """Page type (e.g., 'page', 'post', 'api')."""
        ...


# =============================================================================
# Composite Page Protocol
# =============================================================================


@runtime_checkable
class PageLike(Renderable, Navigable, Summarizable, Protocol):
    """
    Full page protocol combining all three roles.

    Use PageLike when a function needs access to content, navigation,
    AND metadata (e.g., the rendering pipeline, JSON generator).
    Prefer the narrower role protocols when possible.

    Extends: Renderable, Navigable, Summarizable

    Thread Safety:
        Implementations should be thread-safe for concurrent access
        during parallel builds.

    Example:
            >>> def render_page(page: PageLike) -> str:
            ...     return f"<h1>{page.title}</h1>{page.content}"

    """


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

    # --- Identity ---

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

    # --- Content ---

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

    # --- Metadata & Navigation ---

    @property
    def metadata(self) -> dict[str, Any]:
        """Section metadata dict (from _index.md frontmatter or cascade)."""
        ...

    @property
    def nav_title(self) -> str:
        """Navigation-specific title (falls back to title)."""
        ...

    @property
    def icon(self) -> str | None:
        """Icon identifier for navigation (e.g., 'book', 'code')."""
        ...

    @property
    def is_virtual(self) -> bool:
        """Whether this is a virtual section (no directory on disk)."""
        ...

    @property
    def regular_pages(self) -> list[PageLike]:
        """Non-index pages in this section."""
        ...


# =============================================================================
# Site Role Protocols
# =============================================================================


@runtime_checkable
class SiteConfig(Protocol):
    """
    Protocol for site configuration and identity.

    Use when a function only needs config, paths, or theme information
    -- not pages or sections.

    Consumers: autodoc renderer, CSS optimizer, icon resolver, asset pipeline.
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
    def config(self) -> SiteConfigType:
        """Site configuration dictionary."""
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

    @property
    def theme_config(self) -> Theme:
        """Theme configuration object."""
        ...

    @property
    def content_dir(self) -> Path:
        """Path to the content directory."""
        ...

    @property
    def version_config(self) -> VersionConfig:
        """Site versioning configuration."""
        ...

    @property
    def versioning_enabled(self) -> bool:
        """Whether versioned documentation is enabled."""
        ...

    @property
    def build_time(self) -> datetime | None:
        """Build timestamp."""
        ...


@runtime_checkable
class SiteContent(Protocol):
    """
    Protocol for site content (pages, sections, data).

    Use when a function only needs access to pages, sections, or data
    -- not configuration or theme.

    Consumers: query index, JSON/LLM generators, nav tree, taxonomy.
    """

    @property
    def pages(self) -> list[PageLike]:
        """All pages in the site."""
        ...

    @property
    def regular_pages(self) -> list[PageLike]:
        """Non-generated, non-index pages."""
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
    def data(self) -> dict[str, Any]:
        """Data directory contents (loaded from data/ directory)."""
        ...

    @property
    def menu(self) -> dict[str, Any]:
        """Navigation menus configuration."""
        ...

    @property
    def taxonomies(self) -> dict[str, dict[str, Any]]:
        """Collected taxonomies (tags, categories, etc.)."""
        ...

    @property
    def xref_index(self) -> dict[str, Any]:
        """Cross-reference index for internal linking."""
        ...

    @property
    def versions(self) -> list[Any]:
        """Available documentation versions."""
        ...

    def get_page_path_map(self) -> dict[str, PageLike]:
        """Get cached page path lookup map for O(1) page resolution."""
        ...

    def get_section_by_path(self, path: Path | str) -> SectionLike | None:
        """Look up a section by its path (O(1) operation)."""
        ...


# =============================================================================
# Composite Site Protocol
# =============================================================================


@runtime_checkable
class SiteLike(SiteConfig, SiteContent, Protocol):
    """
    Full site protocol combining configuration and content roles.

    Use SiteLike when a function needs access to BOTH config/paths
    AND pages/sections. Prefer the narrower role protocols when possible.

    Extends: SiteConfig, SiteContent

    Thread Safety:
        Implementations should be thread-safe for concurrent access
        during parallel builds.

    Example:
            >>> def get_page_count(site: SiteLike) -> int:
            ...     return len(site.pages)

    """


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
    # Page role protocols
    "Renderable",
    "Navigable",
    "Summarizable",
    "PageLike",
    # Section protocols
    "SectionLike",
    "NavigableSection",
    "QueryableSection",
    # Site role protocols
    "SiteConfig",
    "SiteContent",
    "SiteLike",
    # Config protocol
    "ConfigLike",
]
