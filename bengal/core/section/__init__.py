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
hierarchy.py: SectionHierarchyMixin (tree traversal, identity)
navigation.py: SectionNavigationMixin (URLs, version-aware nav)
queries.py: SectionQueryMixin (page retrieval, collection ops)
ergonomics.py: SectionErgonomicsMixin (theme developer helpers)
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
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import DiagnosticEvent, DiagnosticsSink

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

from .ergonomics import SectionErgonomicsMixin
from .hierarchy import SectionHierarchyMixin
from .navigation import SectionNavigationMixin
from .queries import SectionQueryMixin
from .utils import resolve_page_section_path
from .weighted import WeightedPage


@dataclass(eq=False)
class Section(
    SectionHierarchyMixin,
    SectionNavigationMixin,
    SectionQueryMixin,
    SectionErgonomicsMixin,
):
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
    pages: list[Page] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    index_page: Page | None = None
    parent: Section | None = None

    # Virtual section support (for API docs, generated content)
    _virtual: bool = False
    _relative_url_override: str | None = field(default=None, repr=False)

    # Reference to site (set during site building)
    _site: Site | None = field(default=None, repr=False)
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

        Virtual sections are used for:
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
        from bengal.utils.url_normalization import normalize_url

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

        Returns weight from metadata if set, otherwise infinity (sorts last).
        This property ensures sections are always sortable without None errors.

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
            except (ValueError, TypeError):
                pass
        return float("inf")

    def __repr__(self) -> str:
        return f"Section(name='{self.name}', pages={len(self.pages)}, subsections={len(self.subsections)})"


__all__ = [
    "Section",
    "WeightedPage",
    "resolve_page_section_path",
]
