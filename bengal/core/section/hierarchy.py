"""
Section hierarchy helper functions.

Provides tree structure traversal and parent-child relationship helpers for
sections. Handles depth calculation, root finding, subsection sorting, and
identity operations behind compatibility shims on ``Section``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.section import Section


def get_hierarchy(section: Section) -> list[str]:
    """
    Get the full hierarchy path of this section.

    Safe to cache because production parent assignments go through
    add_subsection(), which invalidates this cache on the child.
    """
    if section.parent:
        return [*section.parent.hierarchy, section.name]
    return [section.name]


def get_depth(section: Section) -> int:
    """Get the depth of this section in the hierarchy."""
    return len(section.hierarchy)


def get_root(section: Section) -> Section:
    """
    Get the root section of this section's hierarchy.

    Traverses up the parent chain until reaching either:
    - A section with no parent
    - A section with nav_root: true metadata
    - The top-level section inside a version folder
    """
    current = section
    while current.parent:
        if current.metadata.get("nav_root"):
            return current
        parent = current.parent
        if parent.parent and parent.parent.name == "_versions":
            return current
        current = parent
    return current


def get_icon(section: Section) -> str | None:
    """Compatibility wrapper for rendering-owned section icon helper."""
    from bengal.rendering.section_ergonomics import icon

    return icon(section)


def sorted_subsections(section: Section) -> list[Section]:
    """Get subsections sorted by weight ascending, then title."""
    from bengal.core.utils.sorting import DEFAULT_WEIGHT

    return sorted(
        section.subsections,
        key=lambda s: (s.metadata.get("weight", DEFAULT_WEIGHT), s.title.lower()),
    )


def add_subsection(section: Section, child: Section) -> None:
    """
    Add a subsection to this section.

    Sets the parent reference on the child section and invalidates cached
    hierarchy/depth values on the child because they depend on the parent chain.
    """
    from bengal.core.section.cache import (
        invalidate_section_derived_caches,
        invalidate_section_hierarchy_caches,
    )
    from bengal.core.section.navigation import invalidate_version_content_cache

    child.parent = section
    section.subsections.append(child)
    invalidate_section_hierarchy_caches(child)
    invalidate_section_derived_caches(section)
    invalidate_version_content_cache(section)


def walk(section: Section) -> list[Section]:
    """Iteratively walk through all sections in the hierarchy."""
    sections = [section]
    stack = list(section.subsections)

    while stack:
        current = stack.pop()
        sections.append(current)
        stack.extend(current.subsections)

    return sections


def section_hash(section: Section) -> int:
    """Hash based on section path, or name and URL for virtual sections."""
    if section.path is None:
        return hash((section.name, section._relative_url_override))
    return hash(section.path)


def section_eq(section: Section, other: Any) -> bool:
    """Compare sections by path, or by name and URL for virtual sections."""
    if not (
        hasattr(other, "path")
        and hasattr(other, "name")
        and hasattr(other, "_relative_url_override")
    ):
        return NotImplemented
    if section.path is None and other.path is None:
        return (section.name, section._relative_url_override) == (
            other.name,
            other._relative_url_override,
        )
    return section.path == other.path
