"""
Inverted index building utilities for analysis modules.

Provides efficient index construction for page attributes like tags
and categories, enabling O(overlap) candidate filtering instead of
O(N) brute force comparisons.

This centralizes indexing logic that was previously in:
- suggestions.py (_build_inverted_tag_index, _build_inverted_category_index)

Example:
    >>> from bengal.analysis.utils import build_inverted_index
    >>>
    >>> # Build tag index
    >>> tag_index = build_inverted_index(
    ...     pages,
    ...     get_values=lambda p: set(p.tags) if p.tags else set()
    ... )
    >>> # tag_index["python"] = {page1, page2, ...}

"""

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
V = TypeVar("V")


def build_inverted_index(
    items: list[T],
    get_values: Callable[[T], set[V]],
) -> dict[V, set[T]]:
    """
    Build an inverted index mapping values to items that have those values.

    This is useful for efficient lookups like "find all pages with tag X"
    or "find all pages in category Y".

    Args:
        items: List of items to index
        get_values: Function that extracts the set of values from each item.
                   For example, lambda page: set(page.tags) if page.tags else set()

    Returns:
        Dictionary mapping each value to the set of items that have it.

    Example:
        >>> # Build tag -> pages index
        >>> def get_tags(page):
        ...     if page.tags:
        ...         return {str(t).lower() for t in page.tags if t}
        ...     return set()
        >>>
        >>> tag_index = build_inverted_index(pages, get_tags)
        >>> python_pages = tag_index.get("python", set())

        >>> # Build category -> pages index
        >>> def get_categories(page):
        ...     cat = getattr(page, "category", None)
        ...     return {cat.lower()} if cat else set()
        >>>
        >>> cat_index = build_inverted_index(pages, get_categories)

    """
    index: dict[V, set[T]] = {}

    for item in items:
        for value in get_values(item):
            if value not in index:
                index[value] = set()
            index[value].add(item)

    return index


def build_tag_index[T](
    pages: list[T],
    tag_attr: str = "tags",
    normalize: bool = True,
) -> dict[str, set[T]]:
    """
    Build an inverted index of tags to pages.

    Convenience wrapper around build_inverted_index for the common
    case of indexing pages by tags.

    Args:
        pages: List of page objects
        tag_attr: Attribute name containing tags (default: "tags")
        normalize: If True, normalize tags to lowercase with hyphens

    Returns:
        Dictionary mapping tag strings to sets of pages with that tag.

    Example:
        >>> tag_index = build_tag_index(pages)
        >>> python_pages = tag_index.get("python", set())

    """

    def get_tags(page: T) -> set[str]:
        tags = getattr(page, tag_attr, None)
        if not tags:
            return set()

        result: set[str] = set()
        for tag in tags:
            if tag is not None:
                tag_str = str(tag)
                if normalize:
                    tag_str = tag_str.lower().replace(" ", "-")
                result.add(tag_str)
        return result

    return build_inverted_index(pages, get_tags)


def build_category_index[T](
    pages: list[T],
    category_attr: str = "category",
    categories_attr: str = "categories",
    normalize: bool = True,
) -> dict[str, set[T]]:
    """
    Build an inverted index of categories to pages.

    Handles both single category (category_attr) and multiple
    categories (categories_attr) attributes.

    Args:
        pages: List of page objects
        category_attr: Attribute for single category (default: "category")
        categories_attr: Attribute for multiple categories (default: "categories")
        normalize: If True, normalize categories to lowercase with hyphens

    Returns:
        Dictionary mapping category strings to sets of pages in that category.

    Example:
        >>> cat_index = build_category_index(pages)
        >>> tutorial_pages = cat_index.get("tutorials", set())

    """

    def get_categories(page: T) -> set[str]:
        result: set[str] = set()

        # Check single category
        cat = getattr(page, category_attr, None)
        if cat:
            cat_str = str(cat)
            if normalize:
                cat_str = cat_str.lower().replace(" ", "-")
            result.add(cat_str)

        # Check multiple categories
        cats = getattr(page, categories_attr, None)
        if cats:
            for c in cats:
                if c is not None:
                    c_str = str(c)
                    if normalize:
                        c_str = c_str.lower().replace(" ", "-")
                    result.add(c_str)

        return result

    return build_inverted_index(pages, get_categories)
