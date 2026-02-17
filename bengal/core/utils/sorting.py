"""
Weight-based sorting utilities.

Provides consistent weight handling for sorting pages, sections, and
menu items. All unweighted items sort to the end using float("inf").

Constants:
    DEFAULT_WEIGHT: Standard default for unweighted items (infinity)

Functions:
    weight_sort_key: Generate sort key tuple for weight+title sorting
    sorted_by_weight: Sort items by weight then title

Why float("inf")?
    Using infinity as the default ensures unweighted items always
    sort after weighted items, regardless of what weight values
    authors choose. Using 0 would put unweighted items first,
    and using arbitrary values like 999999 can be exceeded.

"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, TypeVar

# Standard default weight for unweighted items.
# Using infinity ensures unweighted items always sort last.
# DO NOT use 0 (sorts first) or 999999 (can be exceeded).
DEFAULT_WEIGHT: float = float("inf")

T = TypeVar("T")


def weight_sort_key(
    item: Any,
    weight_getter: Callable[[Any], float | int | None] | None = None,
    title_getter: Callable[[Any], str] | None = None,
) -> tuple[float, str]:
    """
    Generate a sort key tuple for weight+title sorting.

    Returns (weight, title_lower) tuple suitable for sorted() key parameter.
    Lower weights sort first; equal weights sort alphabetically by title.

    Args:
        item: Object to generate key for
        weight_getter: Function to extract weight (default: item.metadata.get("weight"))
        title_getter: Function to extract title (default: item.title)

    Returns:
        Tuple of (weight, lowercase_title) for sorting

    Example:
        >>> pages = [page1, page2, page3]
        >>> sorted(pages, key=weight_sort_key)

        # With custom getters:
        >>> sorted(items, key=lambda x: weight_sort_key(
        ...     x,
        ...     weight_getter=lambda i: i.get("weight"),
        ...     title_getter=lambda i: i.get("name", ""),
        ... ))
    """
    # Get weight
    if weight_getter is not None:
        weight = weight_getter(item)
    elif hasattr(item, "metadata") and isinstance(item.metadata, dict):
        weight = item.metadata.get("weight")
    elif hasattr(item, "weight"):
        weight = getattr(item, "weight", None)
    else:
        weight = None

    # Normalize weight to float
    if weight is None:
        weight = DEFAULT_WEIGHT
    else:
        try:
            weight = float(weight)
        except ValueError, TypeError:
            weight = DEFAULT_WEIGHT

    # Get title
    if title_getter is not None:
        title = title_getter(item)
    elif hasattr(item, "title"):
        title = getattr(item, "title", "") or ""
    elif hasattr(item, "name"):
        title = getattr(item, "name", "") or ""
    else:
        title = ""

    return (weight, title.lower())


def sorted_by_weight(
    items: Iterable[T],
    weight_getter: Callable[[T], float | int | None] | None = None,
    title_getter: Callable[[T], str] | None = None,
    reverse: bool = False,
) -> list[T]:
    """
    Sort items by weight then title.

    Convenience wrapper around sorted() with weight_sort_key.
    Lower weights sort first by default.

    Args:
        items: Iterable of items to sort
        weight_getter: Function to extract weight from each item
        title_getter: Function to extract title from each item
        reverse: If True, sort descending (higher weights first)

    Returns:
        Sorted list of items

    Example:
        >>> sections = sorted_by_weight(site.sections)
        >>> pages = sorted_by_weight(
        ...     section.pages,
        ...     weight_getter=lambda p: p.metadata.get("weight"),
        ... )
    """
    return sorted(
        items,
        key=lambda item: weight_sort_key(item, weight_getter, title_getter),
        reverse=reverse,
    )
