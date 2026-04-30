"""
Section package for content organization in Bengal SSG.

Provides the Section class—representing directories in the content tree with
pages and subsections. Sections form a hierarchy and provide navigation,
sorting, and query interfaces for templates.

Public API:
Section: Content directory with pages and subsections
WeightedPage: Helper for weight-based page sorting

Creation:
Section(name, path): Create a section for a directory
Section.create_virtual(): Create a virtual section (no disk directory)

Package Structure:
hierarchy.py: Tree traversal and identity helper functions
navigation.py: Version-aware structural navigation helper functions
queries.py: Page retrieval and collection helper functions
ergonomics.py: Compatibility re-exports for rendering-owned theme helpers
utils.py: Module-level helper functions

Key Concepts:
Hierarchy: Sections form a tree structure with parent-child relationships.
    Access via section.parent, section.subsections, section.root.

Index Pages: Special pages (_index.md or index.md) that represent the section.
    Provides section-level metadata (title, description, cascade values).

Weight-based Sorting: Pages and subsections sorted by weight metadata.
    Lower weights appear first; unweighted items sort to end.

Virtual Sections: Sections without a disk directory (e.g., autodoc API docs).
    Created via Section.create_virtual() for dynamically-generated content.

Hashability: Sections hashable by path for set operations and dict keys.
    Two sections with same path are considered equal.

Related Packages:
bengal.core.page: Page objects contained within sections
bengal.core.site: Site container that manages all sections
bengal.orchestration.content: Content discovery that builds section hierarchy

"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.diagnostics import DiagnosticEvent, DiagnosticsSink
    from bengal.core.site.context import SiteContext
    from bengal.protocols.core import PageLike

from .utils import resolve_page_section_path
from .weighted import WeightedPage


@dataclass(eq=False)
class Section:
    """
    Represents a folder or logical grouping of pages.

    HASHABILITY:
    ============
    Sections are hashable based on their path (or name for virtual sections),
    allowing them to be stored in sets and used as dictionary keys. This enables:
    - Fast membership tests and lookups
    - Type-safe Set[Section] collections
    - Set operations for section analysis

    Two sections with the same path are considered equal. The hash is stable
    throughout the section lifecycle because path is immutable.

    VIRTUAL SECTIONS:
    =================
    Virtual sections represent API documentation or other dynamically-generated
    content that doesn't have a corresponding directory on disk. Virtual sections:
    - Have _virtual=True and path=None
    - Are discovered via VirtualAutodocOrchestrator during build
    - Work with menu system via name-based lookups
    - Don't write intermediate markdown files

    Attributes:
        name: Section name
        path: Path to the section directory (None for virtual sections)
        pages: List of pages in this section
        subsections: Child sections
        metadata: Section-level metadata
        index_page: Optional index page for the section
        parent: Parent section (if nested)
        _virtual: True if this is a virtual section (no disk directory)

    """

    name: str = "root"
    path: Path | None = field(default_factory=lambda: Path("."))
    pages: list[PageLike] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    index_page: PageLike | None = None
    parent: Section | None = None

    # Virtual section support (for API docs, generated content)
    _virtual: bool = False
    _relative_url_override: str | None = field(default=None, repr=False)

    # Reference to site (set during site building)
    _site: SiteContext | None = field(default=None, repr=False)
    # Optional diagnostics sink (for unit tests or if no site is available yet)
    _diagnostics: DiagnosticsSink | None = field(default=None, repr=False)

    def _emit_diagnostic(self, event: DiagnosticEvent) -> None:
        """
        Emit a diagnostic event if a sink is available.

        Core models must not log; orchestrators decide how to surface diagnostics.
        """
        sink: Any | None = self._diagnostics
        if sink is None:
            site = getattr(self, "_site", None)
            sink = getattr(site, "diagnostics", None) if site is not None else None

        if sink is None:
            return

        try:
            sink.emit(event)
        except Exception:
            # Diagnostics must never break core behavior.
            return

    @property
    def is_virtual(self) -> bool:
        """
        Check if this is a virtual section (no disk directory).

        When to use:
            Guard any code that needs to read from or write to ``self.path``.
            Virtual sections have ``path=None`` and must not touch the disk —
            attempting to would raise ``AttributeError``. Typical callers:
            asset resolvers, file-mtime cache keys, content discovery walkers.

        Virtual sections back:
        - API documentation generated from Python source code
        - Dynamically-generated content from external sources
        - Content that doesn't have a corresponding content/ directory

        Returns:
            True if this section is virtual (not backed by a disk directory)
        """
        return self._virtual or self.path is None

    @classmethod
    def create_virtual(
        cls,
        name: str,
        relative_url: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Section:
        """
        Create a virtual section for dynamically-generated content.

        When to use:
            Use this when you need a Section for content that has no
            corresponding ``content/`` directory — typically autodoc
            (``VirtualAutodocOrchestrator``), remote content fetchers, or
            programmatically-generated indexes. Prefer the regular
            ``Section(name, path)`` constructor whenever a real directory
            exists; virtual sections skip disk-backed operations and must
            register their URL explicitly via ``relative_url``.

        Virtual sections are not backed by a disk directory but integrate
        with the site's section hierarchy, navigation, and menu system.

        Args:
            name: Section name (used for lookups, e.g., "api")
            relative_url: URL for this section (e.g., "/api/")
            title: Display title (defaults to titlecase of name)
            metadata: Optional section metadata

        Returns:
            A new virtual Section instance

        Example:
            api_section = Section.create_virtual(
                name="api",
                relative_url="/api/",
                title="API Reference",
            )
        """
        section_metadata = metadata or {}
        if title:
            section_metadata["title"] = title

        # Normalize URL at construction time
        from bengal.utils.paths.url_normalization import normalize_url

        normalized_url = normalize_url(relative_url, ensure_trailing_slash=True)

        return cls(
            name=name,
            path=None,
            metadata=section_metadata,
            _virtual=True,
            _relative_url_override=normalized_url,
        )

    @property
    def slug(self) -> str:
        """
        URL-friendly identifier for this section.

        When to use:
            Prefer this over reading ``self.path.name`` or ``self.name``
            directly when you need a stable URL segment. It handles virtual
            sections (no path) and disk-backed sections uniformly; raw
            attribute access is not safe for virtual sections.

        For virtual sections, uses the name directly.
        For physical sections, uses the directory name.

        Returns:
            Section slug (e.g., "api", "core", "bengal-core")
        """
        if self._virtual:
            return self.name
        return self.path.name if self.path else self.name

    @property
    def title(self) -> str:
        """Get section title from metadata or generate from name."""
        return str(self.metadata.get("title", self.name.replace("-", " ").title()))

    @property
    def nav_title(self) -> str:
        """
        Get short navigation title (falls back to title).

        Use this in menus and sidebars for compact display.

        Example in _index.md:
            ---
            title: Content Authoring Guide
            nav_title: Authoring
            ---
        """
        if "nav_title" in self.metadata:
            return str(self.metadata["nav_title"])
        # Also check index page for nav_title
        if self.index_page is not None:
            index_nav = getattr(self.index_page, "nav_title", None)
            if index_nav and index_nav != self.index_page.title:
                return index_nav
        return self.title

    @property
    def weight(self) -> float:
        """
        Get section weight for sorting (always returns sortable value).

        When to use:
            Prefer this over ``self.metadata.get("weight")`` whenever sorting.
            Raw metadata access returns ``None`` for unweighted sections and
            may return a non-numeric string from malformed frontmatter; this
            property coerces to ``float`` and falls back to ``inf`` so
            ``sorted(sections, key=lambda s: s.weight)`` never raises.

        Returns weight from metadata if set, otherwise infinity (sorts last).

        Example in _index.md:
            ---
            title: Getting Started
            weight: 10
            ---
        """
        w = self.metadata.get("weight")
        if w is not None:
            try:
                return float(w)
            except ValueError, TypeError:
                pass
        return float("inf")

    @cached_property
    def hierarchy(self) -> list[str]:
        """Get the full hierarchy path of this section."""
        from .hierarchy import get_hierarchy

        return get_hierarchy(self)

    @cached_property
    def depth(self) -> int:
        """Get the depth of this section in the hierarchy."""
        from .hierarchy import get_depth

        return get_depth(self)

    @property
    def root(self) -> Section:
        """Get the root section of this section's hierarchy."""
        from .hierarchy import get_root

        return get_root(self)

    @cached_property
    def icon(self) -> str | None:
        """Get section icon for theme navigation."""
        from bengal.rendering.section_ergonomics import icon

        return icon(self)

    @cached_property
    def sorted_subsections(self) -> list[Section]:
        """Get subsections sorted by weight, then title."""
        from .hierarchy import sorted_subsections

        return sorted_subsections(self)

    def add_subsection(self, section: Section) -> None:
        """Add a subsection to this section."""
        from .hierarchy import add_subsection

        add_subsection(self, section)

    def walk(self) -> list[Section]:
        """Iteratively walk through all sections in the hierarchy."""
        from .hierarchy import walk

        return walk(self)

    @cached_property
    def regular_pages(self) -> list[PageLike]:
        """Get content pages in this section, excluding index pages."""
        from .queries import regular_pages

        return regular_pages(self)

    @cached_property
    def sorted_pages(self) -> list[PageLike]:
        """Get pages sorted by weight, then title."""
        from .queries import sorted_pages

        return sorted_pages(self)

    @cached_property
    def regular_pages_recursive(self) -> list[PageLike]:
        """Get all regular pages recursively, including from subsections."""
        from .queries import regular_pages_recursive

        return regular_pages_recursive(self)

    def add_page(self, page: PageLike) -> None:
        """Add a page to this section."""
        from .queries import add_page

        add_page(self, page)

    def sort_children_by_weight(self) -> None:
        """Sort pages and subsections by weight, then title."""
        from .queries import sort_children_by_weight

        sort_children_by_weight(self)

    def needs_auto_index(self) -> bool:
        """Check if this section needs an auto-generated index page."""
        from .queries import needs_auto_index

        return needs_auto_index(self)

    def has_index(self) -> bool:
        """Check if section has a valid index page."""
        from .queries import has_index

        return has_index(self)

    def get_all_pages(self, recursive: bool = True) -> list[PageLike]:
        """Get all pages in this section."""
        from .queries import get_all_pages

        return get_all_pages(self, recursive)

    @cached_property
    def href(self) -> str:
        """URL for template href attributes. Includes baseurl."""
        from bengal.rendering.section_urls import get_href

        return get_href(self)

    @cached_property
    def _path(self) -> str:
        """Internal site-relative path. Does not include baseurl."""
        from bengal.rendering.section_urls import get_path

        return get_path(self)

    @property
    def absolute_href(self) -> str:
        """Fully-qualified URL for meta tags and sitemaps when available."""
        from bengal.rendering.section_urls import get_absolute_href

        return get_absolute_href(self)

    @cached_property
    def subsection_index_urls(self) -> set[str]:
        """Get URLs for all subsection index pages."""
        from bengal.rendering.section_urls import subsection_index_urls

        return subsection_index_urls(self)

    @cached_property
    def has_nav_children(self) -> bool:
        """Check if this section has navigable children."""
        from bengal.rendering.section_ergonomics import has_nav_children

        return has_nav_children(self)

    def pages_for_version(self, version_id: str | None) -> list[PageLike]:
        """Get pages matching the specified version."""
        from .navigation import pages_for_version

        return pages_for_version(self, version_id)

    def subsections_for_version(self, version_id: str | None) -> list[Section]:
        """Get subsections that have content for the specified version."""
        from .navigation import subsections_for_version

        return subsections_for_version(self, version_id)

    def has_content_for_version(self, version_id: str | None) -> bool:
        """Check if this section has any content for the specified version."""
        from .navigation import has_content_for_version

        return has_content_for_version(self, version_id)

    def _apply_version_path_transform(self, url: str) -> str:
        """Transform versioned section URL to proper output structure."""
        from bengal.rendering.section_urls import apply_version_path_transform

        return apply_version_path_transform(self, url)

    @cached_property
    def content_pages(self) -> list[PageLike]:
        """Get content pages for template listings."""
        from bengal.rendering.section_ergonomics import content_pages

        return content_pages(self)

    def recent_pages(self, limit: int = 10) -> list[PageLike]:
        """Get most recent pages by date."""
        from bengal.rendering.section_ergonomics import recent_pages

        return recent_pages(self, limit)

    def pages_with_tag(self, tag: str) -> list[PageLike]:
        """Get pages containing a specific tag."""
        from bengal.rendering.section_ergonomics import pages_with_tag

        return pages_with_tag(self, tag)

    def featured_posts(self, limit: int = 5) -> list[PageLike]:
        """Get featured pages from this section."""
        from bengal.rendering.section_ergonomics import featured_posts

        return featured_posts(self, limit)

    @cached_property
    def post_count(self) -> int:
        """Get total number of content pages in this section."""
        from bengal.rendering.section_ergonomics import post_count

        return post_count(self)

    @cached_property
    def post_count_recursive(self) -> int:
        """Get total number of content pages in this section and all subsections."""
        from bengal.rendering.section_ergonomics import post_count_recursive

        return post_count_recursive(self)

    @cached_property
    def word_count(self) -> int:
        """Get total word count across all pages in this section."""
        from bengal.rendering.section_ergonomics import word_count

        return word_count(self)

    @cached_property
    def total_reading_time(self) -> int:
        """Get total reading time for all pages in this section."""
        from bengal.rendering.section_ergonomics import total_reading_time

        return total_reading_time(self)

    def aggregate_content(self) -> dict[str, Any]:
        """Aggregate content from all pages in this section."""
        from bengal.rendering.section_ergonomics import aggregate_content

        return aggregate_content(self)

    def apply_section_template(self, template_engine: Any) -> str:
        """Apply a section template to generate a section index page."""
        from bengal.rendering.section_ergonomics import apply_section_template

        return apply_section_template(self, template_engine)

    def __hash__(self) -> int:
        """Hash based on section path, or name and URL for virtual sections."""
        from .hierarchy import section_hash

        return section_hash(self)

    def __eq__(self, other: object) -> bool:
        """Compare sections by path, or by name and URL for virtual sections."""
        from .hierarchy import section_eq

        return section_eq(self, other)

    def __repr__(self) -> str:
        return f"Section(name='{self.name}', pages={len(self.pages)}, subsections={len(self.subsections)})"


__all__ = [
    "Section",
    "WeightedPage",
    "resolve_page_section_path",
]
