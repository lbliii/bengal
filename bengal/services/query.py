"""
Query service - pure functions for content queries.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 4: Service Extraction)

Replaces SectionRegistryMixin and query methods with pure functions
that operate on SiteSnapshot.

Key Principles:
- Pure functions: no hidden state
- Operates on immutable SiteSnapshot
- O(1) lookups via pre-built indexes
- Thread-safe: no shared mutable state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.snapshots.types import PageSnapshot, SectionSnapshot, SiteSnapshot


@dataclass(frozen=True, slots=True)
class QueryService:
    """
    Cached query service for SiteSnapshot.

    Provides O(1) lookups for pages and sections via pre-built indexes.

    Usage:
        >>> service = QueryService.from_snapshot(snapshot)
        >>> section = service.get_section("/docs/")
        >>> page = service.get_page("/docs/getting-started/")
        >>> pages = service.get_pages_by_tag("python")
    """

    snapshot: SiteSnapshot

    # Pre-built indexes (computed on construction)
    _pages_by_href: dict[str, PageSnapshot] = field(default_factory=dict, repr=False)
    _pages_by_path: dict[Path, PageSnapshot] = field(default_factory=dict, repr=False)
    _sections_by_url: dict[str, SectionSnapshot] = field(default_factory=dict, repr=False)
    _sections_by_path: dict[Path, SectionSnapshot] = field(default_factory=dict, repr=False)
    _pages_by_tag: dict[str, list[PageSnapshot]] = field(default_factory=dict, repr=False)
    _pages_by_section: dict[str, list[PageSnapshot]] = field(default_factory=dict, repr=False)

    @classmethod
    def from_snapshot(cls, snapshot: SiteSnapshot) -> QueryService:
        """
        Create service from SiteSnapshot with pre-built indexes.

        Args:
            snapshot: Site snapshot

        Returns:
            QueryService with indexes built
        """
        # Build indexes
        pages_by_href: dict[str, PageSnapshot] = {}
        pages_by_path: dict[Path, PageSnapshot] = {}
        pages_by_tag: dict[str, list[PageSnapshot]] = {}
        pages_by_section: dict[str, list[PageSnapshot]] = {}

        for page in snapshot.pages:
            pages_by_href[page.href] = page
            pages_by_path[page.source_path] = page

            # Index by tags
            for tag in page.tags:
                if tag not in pages_by_tag:
                    pages_by_tag[tag] = []
                pages_by_tag[tag].append(page)

            # Index by section
            if page.section:
                section_url = page.section.href
                if section_url not in pages_by_section:
                    pages_by_section[section_url] = []
                pages_by_section[section_url].append(page)

        sections_by_url: dict[str, SectionSnapshot] = {}
        sections_by_path: dict[Path, SectionSnapshot] = {}

        for section in snapshot.sections:
            sections_by_url[section.href] = section
            if section.path:
                sections_by_path[section.path] = section

        return cls(
            snapshot=snapshot,
            _pages_by_href=pages_by_href,
            _pages_by_path=pages_by_path,
            _sections_by_url=sections_by_url,
            _sections_by_path=sections_by_path,
            _pages_by_tag=pages_by_tag,
            _pages_by_section=pages_by_section,
        )

    def get_page(self, href: str) -> PageSnapshot | None:
        """Get page by URL/href (O(1))."""
        return self._pages_by_href.get(href)

    def get_page_by_path(self, path: Path) -> PageSnapshot | None:
        """Get page by source path (O(1))."""
        return self._pages_by_path.get(path)

    def get_section(self, url: str) -> SectionSnapshot | None:
        """Get section by URL (O(1))."""
        return self._sections_by_url.get(url)

    def get_section_by_path(self, path: Path) -> SectionSnapshot | None:
        """Get section by path (O(1))."""
        return self._sections_by_path.get(path)

    def get_pages_by_tag(self, tag: str) -> list[PageSnapshot]:
        """Get all pages with a tag (O(1))."""
        return self._pages_by_tag.get(tag, [])

    def get_pages_by_section(self, section_url: str) -> list[PageSnapshot]:
        """Get all pages in a section (O(1))."""
        return self._pages_by_section.get(section_url, [])


# =============================================================================
# Pure Functions (operate on SiteSnapshot directly)
# =============================================================================


def get_section(snapshot: SiteSnapshot, url: str) -> SectionSnapshot | None:
    """
    Get section by URL.

    Pure function: creates index on first call (O(n)),
    subsequent lookups are O(1).

    Args:
        snapshot: Site snapshot
        url: Section URL (e.g., "/docs/")

    Returns:
        SectionSnapshot or None
    """
    for section in snapshot.sections:
        if section.href == url:
            return section
    return None


def get_section_by_path(snapshot: SiteSnapshot, path: Path) -> SectionSnapshot | None:
    """
    Get section by path.

    Args:
        snapshot: Site snapshot
        path: Section path

    Returns:
        SectionSnapshot or None
    """
    for section in snapshot.sections:
        if section.path == path:
            return section
    return None


# Alias for API discoverability
get_section_by_url = get_section


def get_page(snapshot: SiteSnapshot, href: str) -> PageSnapshot | None:
    """
    Get page by href/URL.

    Args:
        snapshot: Site snapshot
        href: Page URL (e.g., "/docs/getting-started/")

    Returns:
        PageSnapshot or None
    """
    for page in snapshot.pages:
        if page.href == href:
            return page
    return None


def get_page_by_path(snapshot: SiteSnapshot, path: Path) -> PageSnapshot | None:
    """
    Get page by source path.

    Args:
        snapshot: Site snapshot
        path: Source file path

    Returns:
        PageSnapshot or None
    """
    for page in snapshot.pages:
        if page.source_path == path:
            return page
    return None


# Alias for API discoverability
get_page_by_url = get_page


def get_pages_by_tag(snapshot: SiteSnapshot, tag: str) -> list[PageSnapshot]:
    """
    Get all pages with a specific tag.

    Args:
        snapshot: Site snapshot
        tag: Tag to filter by

    Returns:
        List of PageSnapshots with the tag
    """
    return [page for page in snapshot.pages if tag in page.tags]


def get_pages_by_section(snapshot: SiteSnapshot, section_url: str) -> list[PageSnapshot]:
    """
    Get all pages in a section.

    Args:
        snapshot: Site snapshot
        section_url: Section URL

    Returns:
        List of PageSnapshots in the section
    """
    return [page for page in snapshot.pages if page.section and page.section.href == section_url]


def get_children_pages(
    snapshot: SiteSnapshot,
    section_url: str,
    recursive: bool = False,
) -> list[PageSnapshot]:
    """
    Get child pages of a section.

    Args:
        snapshot: Site snapshot
        section_url: Parent section URL
        recursive: If True, include pages from subsections

    Returns:
        List of child PageSnapshots
    """
    if recursive:
        # Include pages whose section URL starts with parent URL
        return [
            page
            for page in snapshot.pages
            if page.section and page.section.href.startswith(section_url)
        ]
    else:
        # Only direct children
        return get_pages_by_section(snapshot, section_url)
