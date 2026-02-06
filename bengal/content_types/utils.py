"""
Shared utilities for content type strategies.

Provides reusable sorting keys and detection helpers to reduce code
duplication across strategy implementations.

Functions:
    weight_title_key: Sort key for weight then title ordering
    date_key: Sort key for date-based ordering
    section_name_matches: Check section name against patterns
    has_dated_pages: Detect sections with date-heavy content
    has_page_type_metadata: Detect sections by page type metadata
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.protocols import SectionLike


# ─── Sorting Keys ─────────────────────────────────────────────────────────────


def weight_title_key(page: Page) -> tuple[int, str]:
    """
    Sort key for weight ascending, then title alphabetical.

    Pages without explicit weight default to 999999 (sorted last).
    Commonly used for documentation, tutorials, and generic pages.

    Args:
        page: Page to generate sort key for.

    Returns:
        Tuple of (weight, lowercase_title) for sorting.

    Example:
        >>> sorted_pages = sorted(pages, key=weight_title_key)
    """
    return (page.metadata.get("weight", 999999), page.title.lower())


def date_key(page: Page) -> datetime:
    """
    Sort key for date-based ordering.

    Pages without dates use datetime.min (sorted to end when using reverse=True).
    Commonly used for blog posts, changelogs, and news.

    Args:
        page: Page to generate sort key for.

    Returns:
        Page date or datetime.min if no date.

    Example:
        >>> # Newest first
        >>> sorted_pages = sorted(pages, key=date_key, reverse=True)
    """
    return page.date if page.date else datetime.min


# ─── Detection Helpers ────────────────────────────────────────────────────────


def section_name_matches(section: SectionLike, patterns: Iterable[str]) -> bool:
    """
    Check if section name matches any pattern (case-insensitive).

    Args:
        section: Section to check.
        patterns: Iterable of lowercase pattern strings to match against.

    Returns:
        True if section name matches any pattern.

    Example:
        >>> if section_name_matches(section, ("blog", "posts", "news")):
        ...     return BlogStrategy()
    """
    return section.name.lower() in patterns


def has_dated_pages(
    section: SectionLike,
    threshold: float = 0.6,
    sample_size: int = 5,
) -> bool:
    """
    Check if sampled pages have date metadata above threshold.

    Useful for auto-detecting blog-like sections where most pages have dates.

    Args:
        section: Section to analyze.
        threshold: Minimum ratio of dated pages (default 0.6 = 60%).
        sample_size: Number of pages to sample (default 5).

    Returns:
        True if dated pages meet or exceed threshold ratio.

    Example:
        >>> if has_dated_pages(section, threshold=0.6):
        ...     # Likely a blog section
    """
    if not section.pages:
        return False
    sample = section.pages[:sample_size]
    dated_count = sum(1 for p in sample if p.metadata.get("date") or p.date)
    return dated_count >= len(sample) * threshold


def has_page_type_metadata(
    section: SectionLike,
    type_values: Iterable[str],
    sample_size: int = 3,
    substring_match: bool = False,
) -> bool:
    """
    Check if sampled pages have matching type metadata.

    Useful for auto-detecting autodoc sections where pages have specific
    type metadata (e.g., "python-module", "cli-command").

    Args:
        section: Section to analyze.
        type_values: Type values to match against page metadata.
        sample_size: Number of pages to sample (default 3).
        substring_match: If True, also matches if any type_value is
            a substring of the page type (e.g., "python-" in "python-module").

    Returns:
        True if any sampled page has matching type metadata.

    Example:
        >>> if has_page_type_metadata(section, ("python-module", "autodoc-python")):
        ...     return ApiReferenceStrategy()
    """
    if not section.pages:
        return False

    type_set = set(type_values)

    for page in section.pages[:sample_size]:
        page_type = page.metadata.get("type", "")
        if not page_type:
            continue

        # Exact match
        if page_type in type_set:
            return True

        # Substring match
        if substring_match and any(t in page_type for t in type_set):
            return True

    return False
