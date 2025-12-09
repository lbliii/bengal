"""
Date and time functions for templates.

Provides 3 functions for date formatting and display.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register date functions with Jinja2 environment."""
    env.filters.update(
        {
            "time_ago": time_ago,
            "date_iso": date_iso,
            "date_rfc822": date_rfc822,
        }
    )


def time_ago(date: datetime | str | None) -> str:
    """
    Convert date to human-readable "time ago" format.

    Uses bengal.utils.dates.time_ago internally for robust date handling.

    Args:
        date: Date to convert (datetime object or ISO string)

    Returns:
        Human-readable time ago string

    Example:
        {{ post.date | time_ago }}  # "2 days ago", "5 hours ago", etc.
    """
    from bengal.utils.dates import time_ago as time_ago_util

    return time_ago_util(date)


def date_iso(date: datetime | str | None) -> str:
    """
    Format date as ISO 8601 string.

    Uses bengal.utils.dates.format_date_iso internally for robust date handling.

    Args:
        date: Date to format

    Returns:
        ISO 8601 formatted date string

    Example:
        <time datetime="{{ post.date | date_iso }}">
        # Output: 2025-10-03T14:30:00
    """
    from bengal.utils.dates import format_date_iso

    return format_date_iso(date)


def date_rfc822(date: datetime | str | None) -> str:
    """
    Format date as RFC 822 string (for RSS feeds).

    Uses bengal.utils.dates.format_date_rfc822 internally for robust date handling.

    Args:
        date: Date to format

    Returns:
        RFC 822 formatted date string

    Example:
        <pubDate>{{ post.date | date_rfc822 }}</pubDate>
        # Output: Fri, 03 Oct 2025 14:30:00 +0000
    """
    from bengal.utils.dates import format_date_rfc822

    return format_date_rfc822(date)
