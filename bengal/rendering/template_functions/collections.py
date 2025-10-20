"""
Collection manipulation functions for templates.

Provides 8 functions for filtering, sorting, and transforming lists and dicts.
"""

from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register collection functions with Jinja2 environment."""

    # Create closure for resolve_pages with access to site
    def resolve_pages_with_site(page_paths: list[str]) -> list:
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
            "resolve_pages": resolve_pages_with_site,
        }
    )


def where(items: list[dict[str, Any]], key: str, value: Any) -> list[dict[str, Any]]:
    """
    Filter items where key equals value.

    Args:
        items: List of dictionaries to filter
        key: Dictionary key to check
        value: Value to match

    Returns:
        Filtered list

    Example:
        {% set tutorials = site.pages | where('category', 'tutorial') %}
        {% set published = posts | where('status', 'published') %}
    """
    if not items:
        return []

    result = []
    for item in items:
        # Handle both dict access and object attribute access
        if isinstance(item, dict):
            if item.get(key) == value:
                result.append(item)
        elif getattr(item, key, None) == value:
            result.append(item)

    return result


def where_not(items: list[dict[str, Any]], key: str, value: Any) -> list[dict[str, Any]]:
    """
    Filter items where key does not equal value.

    Args:
        items: List of dictionaries to filter
        key: Dictionary key to check
        value: Value to exclude

    Returns:
        Filtered list

    Example:
        {% set active = users | where_not('status', 'archived') %}
    """
    if not items:
        return []

    result = []
    for item in items:
        # Handle both dict access and object attribute access
        if isinstance(item, dict):
            if item.get(key) != value:
                result.append(item)
        elif getattr(item, key, None) != value:
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
    def get_value(item):
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

    def get_sort_key(item):
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    try:
        return sorted(items, key=get_sort_key, reverse=reverse)
    except (TypeError, AttributeError):
        # If sorting fails, return original list
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


def resolve_pages(page_paths: list[str], site: Site) -> list:
    """
    Resolve page paths to Page objects.
    
    Used with query indexes to convert O(1) path lookups into Page objects:
        {% set blog_paths = site.indexes.section.get('blog') %}
        {% set blog_pages = blog_paths | resolve_pages %}
    
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

    # Build lookup map: path -> page (O(n) once, then O(1) per lookup)
    page_map = {str(p.source_path): p for p in site.pages}

    # Resolve paths to pages
    pages = []
    for path in page_paths:
        page = page_map.get(path)
        if page:
            pages.append(page)

    return pages
