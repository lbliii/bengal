"""
Section navigation helper functions.

Provides version-aware filtering helpers for sections. URL presentation helpers
live in ``bengal.rendering.section_urls``; this module keeps compatibility
wrappers for older imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.section import Section
    from bengal.protocols.core import PageLike


def get_href(section: Section) -> str:
    """Compatibility wrapper for rendering-owned section URL helpers."""
    from bengal.rendering.section_urls import get_href as _get_href

    return _get_href(section)


def get_path(section: Section) -> str:
    """Compatibility wrapper for rendering-owned section URL helpers."""
    from bengal.rendering.section_urls import get_path as _get_path

    return _get_path(section)


def get_absolute_href(section: Section) -> str:
    """Compatibility wrapper for rendering-owned section URL helpers."""
    from bengal.rendering.section_urls import get_absolute_href as _get_absolute_href

    return _get_absolute_href(section)


def subsection_index_urls(section: Section) -> set[str]:
    """Compatibility wrapper for rendering-owned section URL helpers."""
    from bengal.rendering.section_urls import subsection_index_urls as _subsection_index_urls

    return _subsection_index_urls(section)


def has_nav_children(section: Section) -> bool:
    """
    Check if this section has navigable children.

    A section has navigable children if it contains either:
    - Regular pages (excluding the index page itself)
    - Subsections
    """
    return bool(section.sorted_pages or section.sorted_subsections)


def pages_for_version(section: Section, version_id: str | None) -> list[PageLike]:
    """
    Get pages matching the specified version.

    Filters sorted_pages to return only pages whose version attribute
    matches the given version_id. If version_id is None, returns all
    sorted pages.
    """
    if version_id is None:
        return section.sorted_pages
    return [p for p in section.sorted_pages if getattr(p, "version", None) == version_id]


def subsections_for_version(section: Section, version_id: str | None) -> list[Section]:
    """
    Get subsections that have content for the specified version.

    A subsection is included if has_content_for_version returns True, meaning
    either its index page matches the version or it contains pages matching the
    version.
    """
    if version_id is None:
        return section.sorted_subsections
    return [s for s in section.sorted_subsections if s.has_content_for_version(version_id)]


def has_content_for_version(section: Section, version_id: str | None) -> bool:
    """
    Check if this section has any content for the specified version.

    A section has content for a version if:
    - Its index_page exists and matches the version, OR
    - Any of its sorted_pages match the version, OR
    - Any of its subsections recursively have content for the version
    """
    if version_id is None:
        return True

    if section.index_page and getattr(section.index_page, "version", None) == version_id:
        return True

    if any(getattr(p, "version", None) == version_id for p in section.sorted_pages):
        return True

    return any(s.has_content_for_version(version_id) for s in section.subsections)


def apply_version_path_transform(section: Section, url: str) -> str:
    """Compatibility wrapper for rendering-owned section URL helpers."""
    from bengal.rendering.section_urls import (
        apply_version_path_transform as _apply_version_path_transform,
    )

    return _apply_version_path_transform(section, url)
