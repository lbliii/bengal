"""
Collection manipulation functions for templates.

Provides 15+ functions for filtering, sorting, and transforming lists and dicts.
Includes advanced page querying and manipulation functions.
"""

from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """Register collection functions with Jinja2 environment."""

    # Create closure for resolve_pages with access to site
    def resolve_pages_with_site(page_paths: list[str]) -> list[Any]:
        return resolve_pages(page_paths, site)

    env.filters.update(
        {
            "where": where,
            "where_not": where_not,
            "group_by": group_by,
            "sort_by": sort_by,
            "limit": limit,
            "offset": offset,
            "uniq": uniq,
            "flatten": flatten,
            "first": first,
            "last": last,
            "reverse": reverse,
            "union": union,
            "intersect": intersect,
            "complement": complement,
            "resolve_pages": resolve_pages_with_site,
        }
    )


def _get_nested_value(obj: Any, path: str) -> Any:
    """Get nested value using dot notation (e.g., 'metadata.track_id')."""
    parts = path.split(".")
    current = obj

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part, None)
        else:
            return None
        if current is None:
            return None
    return current


def where(
    items: list[dict[str, Any]], key: str, value: Any = None, operator: str = "eq"
) -> list[dict[str, Any]]:
    """
    Filter items where key matches value using specified operator.

    Supports nested attribute access (e.g., 'metadata.track_id') and comparison operators.

    Args:
        items: List of dictionaries or objects to filter
        key: Dictionary key or attribute path to check (supports dot notation like 'metadata.track_id')
        value: Value to compare against (required for all operators)
        operator: Comparison operator: 'eq' (default), 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not in'

    Returns:
        Filtered list

    Example:
        {# Basic equality (backward compatible) #}
        {% set tutorials = site.pages | where('category', 'tutorial') %}
        {% set track_pages = site.pages | where('metadata.track_id', 'getting-started') %}

        {# With operators #}
        {% set recent = site.pages | where('date', one_year_ago, 'gt') %}
        {% set python = site.pages | where('tags', ['python', 'web'], 'in') %}
        {% set published = site.pages | where('status', 'draft', 'ne') %}
    """
    if not items:
        return []

    # Operator functions
    operators = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
        "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
    }

    # Normalize operator name (handle spaces and variations)
    operator_normalized = str(operator).lower().replace(" ", "_")
    if operator_normalized not in operators:
        # Fallback to 'eq' for unknown operators
        operator_normalized = "eq"

    compare = operators[operator_normalized]

    result = []
    for item in items:
        item_value = _get_nested_value(item, key)

        # Handle 'in' / 'not_in' operator - supports both directions
        if operator_normalized in ("in", "not_in"):
            # Case 1: item_value is a list (e.g., tags), check if value is in it
            if isinstance(item_value, (list, tuple)):
                matches = value in item_value
            # Case 2: value is a list, check if item_value is in it
            elif isinstance(value, (list, tuple)):
                matches = item_value in value
            # Case 3: Neither is a list - use compare function (will return False)
            else:
                matches = compare(item_value, value)

            # Apply 'not_in' negation
            if operator_normalized == "not_in":
                matches = not matches

            if matches:
                result.append(item)
        else:
            # Standard comparison (works for all other operators)
            try:
                if compare(item_value, value):
                    result.append(item)
            except (TypeError, ValueError):
                # Skip items where comparison fails (e.g., comparing incompatible types)
                continue

    return result


def where_not(items: list[dict[str, Any]], key: str, value: Any) -> list[dict[str, Any]]:
    """
    Filter items where key does not equal value.

    Supports nested attribute access (e.g., 'metadata.track_id').

    Args:
        items: List of dictionaries or objects to filter
        key: Dictionary key or attribute path to check (supports dot notation like 'metadata.track_id')
        value: Value to exclude

    Returns:
        Filtered list

    Example:
        {% set active = users | where_not('status', 'archived') %}
        {% set non_tracks = site.pages | where_not('metadata.track_id', 'getting-started') %}
    """
    if not items:
        return []

    result = []
    for item in items:
        item_value = _get_nested_value(item, key)
        if item_value != value:
            result.append(item)

    return result


def group_by(items: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    """
    Group items by key value.

    Args:
        items: List of dictionaries to group
        key: Dictionary key to group by

    Returns:
        Dictionary mapping key values to lists of items

    Example:
        {% set by_category = posts | group_by('category') %}
        {% for category, posts in by_category.items() %}
            <h2>{{ category }}</h2>
            ...
        {% endfor %}
    """
    if not items:
        return {}

    # Handle both dict and object attributes
    def get_value(item: Any) -> Any:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    # Sort by key first (required for groupby)
    sorted_items = sorted(items, key=get_value)

    # Group by key
    result = {}
    for k, g in groupby(sorted_items, key=get_value):
        result[k] = list(g)

    return result


def sort_by(items: list[Any], key: str, reverse: bool = False) -> list[Any]:
    """
    Sort items by key.

    Args:
        items: List to sort
        key: Dictionary key or object attribute to sort by
        reverse: Sort in descending order (default: False)

    Returns:
        Sorted list

    Example:
        {% set recent = posts | sort_by('date', reverse=true) %}
        {% set alphabetical = pages | sort_by('title') %}
    """
    if not items:
        return []

    def get_sort_key(item: Any) -> Any:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    try:
        return sorted(items, key=get_sort_key, reverse=reverse)
    except (TypeError, AttributeError) as e:
        # Log debug for sort failures (expected edge case with heterogeneous data)
        logger.debug(
            "sort_by_failed",
            key=key,
            error=str(e),
            item_count=len(items),
            caller="template",
        )
        return items


def limit(items: list[Any], count: int) -> list[Any]:
    """
    Limit items to specified count.

    Args:
        items: List to limit
        count: Maximum number of items

    Returns:
        First N items

    Example:
        {% set recent_5 = posts | sort_by('date', reverse=true) | limit(5) %}
    """
    if not items:
        return []

    return items[:count]


def offset(items: list[Any], count: int) -> list[Any]:
    """
    Skip first N items.

    Args:
        items: List to skip from
        count: Number of items to skip

    Returns:
        Items after offset

    Example:
        {% set page_2 = posts | offset(10) | limit(10) %}
    """
    if not items:
        return []

    return items[count:]


def uniq(items: list[Any]) -> list[Any]:
    """
    Remove duplicate items while preserving order.

    Args:
        items: List with potential duplicates

    Returns:
        List with duplicates removed

    Example:
        {% set unique_tags = all_tags | uniq %}
    """
    if not items:
        return []

    seen = set()
    result = []

    for item in items:
        # Handle unhashable types (like dicts)
        try:
            if item not in seen:
                seen.add(item)
                result.append(item)
        except TypeError:
            # For unhashable types, use linear search
            if item not in result:
                result.append(item)

    return result


def flatten(items: list[list[Any]]) -> list[Any]:
    """
    Flatten nested lists into single list.

    Only flattens one level deep.

    Args:
        items: List of lists

    Returns:
        Flattened list

    Example:
        {% set all_tags = posts | map(attribute='tags') | flatten %}
    """
    if not items:
        return []

    result = []
    for item in items:
        if isinstance(item, list | tuple):
            result.extend(item)
        else:
            result.append(item)

    return result


def first(items: list[Any]) -> Any:
    """
    Get first item from list.

    Args:
        items: List to get first item from

    Returns:
        First item or None if list is empty

    Example:
        {% set featured = site.pages | where('metadata.featured', true) | first %}
        {% if featured %}
            <h2>{{ featured.title }}</h2>
        {% endif %}
    """
    if not items:
        return None
    return items[0]


def last(items: list[Any]) -> Any:
    """
    Get last item from list.

    Args:
        items: List to get last item from

    Returns:
        Last item or None if list is empty

    Example:
        {% set latest = posts | sort_by('date', reverse=true) | first %}
        {% set oldest = posts | sort_by('date') | last %}
    """
    if not items:
        return None
    return items[-1]


def reverse(items: list[Any]) -> list[Any]:
    """
    Reverse a list.

    Args:
        items: List to reverse

    Returns:
        Reversed copy of list

    Example:
        {% set reversed = posts | reverse %}
        {% set chronological = posts | sort_by('date') | reverse %}
    """
    if not items:
        return []
    return list(reversed(items))


def _get_item_key(item: Any) -> Any:
    """Get unique key for an item (for set operations)."""
    # For Page objects, use source_path as key
    if hasattr(item, "source_path"):
        return str(item.source_path)
    # For hashable types, use the item itself
    try:
        hash(item)
        return item
    except TypeError:
        # For unhashable types, use string representation (less ideal but works)
        return str(item)


def union(items1: list[Any], items2: list[Any]) -> list[Any]:
    """
    Combine two lists, removing duplicates (set union).

    Preserves order from first list, then adds items from second list that aren't already present.

    Args:
        items1: First list
        items2: Second list

    Returns:
        Combined list with duplicates removed

    Example:
        {% set all = posts | union(pages) %}
        {% set combined = site.pages | where('type', 'post') | union(site.pages | where('type', 'page')) %}
    """
    if not items1:
        return list(items2) if items2 else []
    if not items2:
        return list(items1)

    seen = set()
    result = []

    # Add items from first list
    for item in items1:
        key = _get_item_key(item)
        if key not in seen:
            seen.add(key)
            result.append(item)

    # Add items from second list that aren't already present
    for item in items2:
        key = _get_item_key(item)
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def intersect(items1: list[Any], items2: list[Any]) -> list[Any]:
    """
    Get items that appear in both lists (set intersection).

    Args:
        items1: First list
        items2: Second list

    Returns:
        List of items present in both lists

    Example:
        {% set common = posts | intersect(featured_pages) %}
        {% set python_and_web = site.pages | where('tags', 'python', 'in') | intersect(site.pages | where('tags', 'web', 'in')) %}
    """
    if not items1 or not items2:
        return []

    # Build set of keys from second list for O(1) lookup
    keys2 = {_get_item_key(item) for item in items2}

    result = []
    seen = set()

    # Find items in first list that are also in second list
    for item in items1:
        key = _get_item_key(item)
        if key in keys2 and key not in seen:
            seen.add(key)
            result.append(item)

    return result


def complement(items1: list[Any], items2: list[Any]) -> list[Any]:
    """
    Get items in first list that are not in second list (set difference).

    Args:
        items1: First list (items to keep)
        items2: Second list (items to exclude)

    Returns:
        List of items in first list but not in second list

    Example:
        {% set only_posts = posts | complement(pages) %}
        {% set non_featured = site.pages | complement(site.pages | where('metadata.featured', true)) %}
    """
    if not items1:
        return []
    if not items2:
        return list(items1)

    # Build set of keys from second list for O(1) lookup
    keys2 = {_get_item_key(item) for item in items2}

    result = []
    seen = set()

    # Keep items from first list that aren't in second list
    for item in items1:
        key = _get_item_key(item)
        if key not in keys2 and key not in seen:
            seen.add(key)
            result.append(item)

    return result


def resolve_pages(page_paths: list[str], site: Site) -> list[Any]:
    """
    Resolve page paths to Page objects.

    Used with query indexes to convert O(1) path lookups into Page objects:
        {% set blog_paths = site.indexes.section.get('blog') %}
        {% set blog_pages = blog_paths | resolve_pages %}

    PERFORMANCE: Uses cached page path map from Site for O(1) lookups.
    The cache is automatically invalidated when pages are added/removed.

    Args:
        page_paths: List of page source paths (strings)
        site: Site instance with pages

    Returns:
        List of Page objects

    Example:
        {% set author_paths = site.indexes.author.get('Jane Smith') %}
        {% set author_posts = author_paths | resolve_pages %}
        {% for post in author_posts | sort(attribute='date', reverse=true) %}
            <h2>{{ post.title }}</h2>
        {% endfor %}
    """
    if not page_paths:
        return []

    # Use cached lookup map from Site (O(1) per lookup after first call)
    page_map = site.get_page_path_map()

    # Resolve paths to pages
    pages = []
    for path in page_paths:
        page = page_map.get(path)
        if page:
            pages.append(page)

    return pages
