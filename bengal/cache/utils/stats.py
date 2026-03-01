"""
Cache statistics utilities.

Provides common patterns for computing cache statistics:
- Entry counts (total, valid, invalid)
- Size estimation
- Average metrics

Usage:
    stats = compute_validity_stats(
        entries=self.pages,
        is_valid=lambda e: e.is_valid,
        serialize=lambda e: e.to_cache_dict(),
    )
    # Returns: {"total": 100, "valid": 95, "invalid": 5, "size_bytes": 12345}

"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def compute_validity_stats[V](
    entries: dict[str, V],
    is_valid: Callable[[V], bool],
    serialize: Callable[[V], dict[str, Any]] | None = None,
) -> dict[str, int]:
    """
    Compute validity statistics for cache entries.

    Args:
        entries: Dictionary of key → entry
        is_valid: Function to check if entry is valid
        serialize: Optional function to serialize entry for size calculation

    Returns:
        Dictionary with:
        - total_entries: Total count
        - valid_entries: Count of valid entries
        - invalid_entries: Count of invalid entries
        - cache_size_bytes: Approximate serialized size (if serialize provided)

    """
    valid = sum(1 for e in entries.values() if is_valid(e))
    invalid = len(entries) - valid

    stats: dict[str, int] = {
        "total_entries": len(entries),
        "valid_entries": valid,
        "invalid_entries": invalid,
    }

    if serialize is not None:
        try:
            size = len(json.dumps([serialize(e) for e in entries.values()]))
            stats["cache_size_bytes"] = size
        except TypeError, ValueError:
            stats["cache_size_bytes"] = 0

    return stats


def compute_index_stats(
    entries: dict[str, Any],
    get_page_count: Callable[[Any], int],
    reverse_index: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    """
    Compute statistics for index-type caches.

    Args:
        entries: Dictionary of key → entry
        get_page_count: Function to get page count from entry
        reverse_index: Optional reverse index (page → keys)

    Returns:
        Dictionary with:
        - total_keys: Number of index keys
        - total_page_entries: Total page references (may have duplicates)
        - unique_pages: Number of unique pages (from reverse index)
        - avg_pages_per_key: Average pages per key

    """
    total_keys = len(entries)
    total_page_entries = sum(get_page_count(e) for e in entries.values())

    unique_pages = len(reverse_index) if reverse_index else 0

    avg_pages_per_key = total_page_entries / total_keys if total_keys > 0 else 0.0

    return {
        "total_keys": total_keys,
        "total_page_entries": total_page_entries,
        "unique_pages": unique_pages,
        "avg_pages_per_key": round(avg_pages_per_key, 2),
    }


def compute_taxonomy_stats(
    tags: dict[str, Any],
    is_valid: Callable[[Any], bool],
    get_page_paths: Callable[[Any], list[str]],
    serialize: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Compute statistics for taxonomy-type caches.

    Args:
        tags: Dictionary of tag_slug → TagEntry
        is_valid: Function to check if tag is valid
        get_page_paths: Function to get page_paths from tag entry
        serialize: Optional function to serialize entry for size calculation

    Returns:
        Dictionary with taxonomy-specific stats
    """
    valid = sum(1 for e in tags.values() if is_valid(e))
    invalid = len(tags) - valid

    # Count unique pages and page-tag pairs
    unique_pages: set[str] = set()
    total_page_tag_pairs = 0

    for entry in tags.values():
        if is_valid(entry):
            paths = get_page_paths(entry)
            total_page_tag_pairs += len(paths)
            unique_pages.update(paths)

    avg_tags_per_page = 0.0
    if unique_pages:
        avg_tags_per_page = total_page_tag_pairs / len(unique_pages)

    stats: dict[str, Any] = {
        "total_tags": len(tags),
        "valid_tags": valid,
        "invalid_tags": invalid,
        "total_unique_pages": len(unique_pages),
        "total_page_tag_pairs": total_page_tag_pairs,
        "avg_tags_per_page": round(avg_tags_per_page, 2),
    }

    if serialize is not None:
        try:
            size = len(json.dumps([serialize(e) for e in tags.values()]))
            stats["cache_size_bytes"] = size
        except TypeError, ValueError:
            stats["cache_size_bytes"] = 0

    return stats
