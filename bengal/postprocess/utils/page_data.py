"""
Page data extraction utilities for postprocess generators.

Provides shared functions for extracting common data from Page objects,
ensuring consistent behavior across all output format generators.

Functions:
    get_section_name: Extract section name from page safely
    tags_to_list: Convert page tags to list, handling various input types

Example:
    >>> from bengal.postprocess.utils.page_data import get_section_name, tags_to_list
    >>>
    >>> section = get_section_name(page)  # Returns "" if no section
    >>> tags = tags_to_list(page.tags)    # Always returns list[str]

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.protocols import PageLike


def get_section_name(page: PageLike) -> str:
    """
    Extract section name from page safely.

    Handles pages with or without section assignments, and sections
    with or without name attributes.

    Args:
        page: Page object to extract section from

    Returns:
        Section name string, or empty string if no section

    Example:
        >>> section = get_section_name(page)
        >>> if section:
        ...     print(f"Page is in section: {section}")

    """
    if hasattr(page, "_section") and page._section:
        return getattr(page._section, "name", "")
    return ""


def tags_to_list(tags: Any) -> list[str]:
    """
    Convert page tags to list, handling various input types safely.

    Tags in frontmatter can be:
    - A list: ["python", "api"]
    - A tuple: ("python", "api")
    - A string: "python" (single tag)
    - An iterable: set(["python", "api"])
    - None or empty

    This function normalizes all inputs to a list of strings.

    Args:
        tags: Tags value from page (any type)

    Returns:
        List of tag strings, or empty list if no valid tags

    Example:
        >>> tags_to_list(["python", "api"])
        ['python', 'api']
        >>> tags_to_list(None)
        []
        >>> tags_to_list("python")
        ['python']

    """
    if not tags:
        return []

    # Already a list or tuple - convert to list
    if isinstance(tags, list | tuple):
        return [str(tag) for tag in tags]

    # Single string tag
    if isinstance(tags, str):
        return [tags]

    # Try to convert other iterables (set, generator, etc.)
    try:
        return [str(tag) for tag in tags]
    except TypeError, ValueError:
        return []
