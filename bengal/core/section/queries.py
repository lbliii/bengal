"""
Section query helper functions.

Provides methods for retrieving pages from sections, adding pages,
sorting children, and checking section state (has index, needs auto-index).

Required Section Attributes:
- name: str
- path: Path | None
- pages: list[Page]
- subsections: list[Section]
- metadata: dict[str, Any]
- index_page: Page | None
- _emit_diagnostic: Callable

Related Modules:
bengal.core.section: Section dataclass exposing query shims
bengal.core.page: Page objects contained in sections

Example:
    >>> section = site.get_section("blog")
    >>> section.regular_pages
[<Page 'post1'>, <Page 'post2'>]
    >>> section.sorted_pages
[<Page 'post2'>, <Page 'post1'>]  # Sorted by weight

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.utils.sorting import sorted_by_weight, weight_sort_key

if TYPE_CHECKING:
    from bengal.core.section import Section
    from bengal.protocols.core import PageLike


def regular_pages(section: Section) -> list[PageLike]:
    """
    Get content pages in this section, excluding index.

    Excludes index pages (_index.md, index.md). This is the standard
    "list content" view—the index is the section's landing page, not a
    content page. Matches SectionSnapshot.regular_pages semantics.
    Returns same pages as sorted_pages (which already excludes index).

    Returns:
        List of content Page objects sorted by weight (excludes index)

    Example:
        {% for page in section.regular_pages %}
          <article>{{ page.title }}</article>
        {% endfor %}
    """
    return list(section.sorted_pages)


def sorted_pages(section: Section) -> list[PageLike]:
    """
    Get pages sorted by weight (ascending), then by title.

    Pages without a weight field are treated as having weight=float('inf')
    and appear at the end of the sorted list, after all weighted pages.
    Lower weights appear first in the list. Pages with equal weight are sorted
    alphabetically by title.

    Returns:
        List of pages sorted by weight, then title

    Example:
        {% for page in section.sorted_pages %}
          <article>{{ page.title }}</article>
        {% endfor %}
    """

    def is_index_page(page: PageLike) -> bool:
        return page.source_path.stem in ("_index", "index")

    non_index = [page for page in section.pages if not is_index_page(page)]
    return sorted_by_weight(non_index)


def regular_pages_recursive(section: Section) -> list[PageLike]:
    """
    Get all regular pages recursively, including from subsections.

    Returns:
        List of all descendant regular pages

    Example:
        <p>Total pages: {{ section.regular_pages_recursive | length }}</p>
    """
    result = list(section.regular_pages)
    for subsection in section.subsections:
        result.extend(subsection.regular_pages_recursive)
    return result


def add_page(section: Section, page: PageLike) -> None:
    """
    Add a page to this section.

    Handles index page detection and metadata inheritance from index pages.
    Invalidates cached properties that depend on the pages list.

    Args:
        section: Section to mutate
        page: Page to add
    """
    from bengal.core.diagnostics import DiagnosticEvent

    is_index = page.source_path.stem in ("index", "_index")

    section.pages.append(page)

    # Invalidate cached properties that depend on page membership.
    from bengal.core.section.cache import invalidate_section_derived_caches
    from bengal.core.section.navigation import invalidate_version_content_cache

    invalidate_section_derived_caches(section)
    invalidate_version_content_cache(section)

    # Set as index page if it's named index.md or _index.md.
    if is_index:
        # Detect collision: both index.md and _index.md exist.
        if section.index_page is not None:
            existing_name = section.index_page.source_path.stem
            new_name = page.source_path.stem
            section._emit_diagnostic(
                DiagnosticEvent(
                    level="warning",
                    code="index_file_collision",
                    data={
                        "section": section.name,
                        "section_path": str(section.path),
                        "existing_file": f"{existing_name}.md",
                        "new_file": f"{new_name}.md",
                        "action": "preferring_underscore_version",
                        "suggestion": (
                            "Remove one of the index files - only _index.md or index.md should exist"
                        ),
                    },
                )
            )

            # Prefer _index.md over index.md (section index convention).
            if new_name == "_index":
                section.index_page = page
            # else: keep existing _index.md.
        else:
            section.index_page = page

        # Copy metadata from index page to section. This allows sections to have
        # weight, description, and other metadata.
        section.metadata.update(page.metadata)


def sort_children_by_weight(section: Section) -> None:
    """
    Sort pages and subsections in this section by weight, then by title.

    This modifies the pages and subsections lists in place.
    Pages/sections without a weight field are treated as having weight=float('inf'),
    so they appear at the end (after all weighted items).
    Lower weights appear first in the sorted lists.

    This is typically called after content discovery is complete.
    """
    # Sort pages by weight (ascending), then title (alphabetically).
    # weight_sort_key normalises weight to float, preventing mixed-type TypeError.
    section.pages.sort(key=weight_sort_key)

    # Sort subsections by weight (ascending), then title (alphabetically).
    section.subsections.sort(key=weight_sort_key)

    from bengal.core.section.cache import invalidate_section_derived_caches

    invalidate_section_derived_caches(section)


def needs_auto_index(section: Section) -> bool:
    """
    Check if this section needs an auto-generated index page.

    Returns:
        True if section needs auto-generated index (no explicit _index.md)
    """
    return section.name != "root" and section.index_page is None


def has_index(section: Section) -> bool:
    """
    Check if section has a valid index page.

    Returns:
        True if section has an index page (explicit or auto-generated)
    """
    return section.index_page is not None


def get_all_pages(section: Section, recursive: bool = True) -> list[PageLike]:
    """
    Get all pages in this section.

    Args:
        section: Section to read
        recursive: If True, include pages from subsections

    Returns:
        List of all pages
    """
    all_pages = list(section.pages)

    if recursive:
        for subsection in section.subsections:
            all_pages.extend(subsection.get_all_pages(recursive=True))

    return all_pages
