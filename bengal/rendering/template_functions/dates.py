"""
Date and time functions for templates.

Provides date formatting, age calculation, arithmetic, and display functions.
"""

from __future__ import annotations

import calendar
from datetime import UTC, datetime, timedelta
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
            "days_ago": days_ago,
            "months_ago": months_ago,
            "month_name": month_name,
            "humanize_days": humanize_days,
            "date_add": date_add,
            "date_diff": date_diff,
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


def days_ago(date: datetime | str | None, now: datetime | None = None) -> int:
    """
    Calculate days since the given date.

    Args:
        date: Date to calculate from (datetime object or ISO string)
        now: Current time for comparison (defaults to now)

    Returns:
        Number of days since date, or 0 if date is None/invalid

    Example:
        {% if post.date | days_ago < 7 %}NEW{% endif %}
        {{ post.date | days_ago }} days old
    """
    from bengal.utils.dates import parse_date

    dt = parse_date(date)
    if not dt:
        return 0

    if now is None:
        now = datetime.now(UTC) if dt.tzinfo is not None else datetime.now()

    diff = now - dt
    return max(0, diff.days)


def months_ago(date: datetime | str | None, now: datetime | None = None) -> int:
    """
    Calculate months since the given date.

    Uses calendar months rather than 30-day periods for more intuitive results.

    Args:
        date: Date to calculate from (datetime object or ISO string)
        now: Current time for comparison (defaults to now)

    Returns:
        Number of months since date, or 0 if date is None/invalid

    Example:
        {% if post.date | months_ago > 6 %}OLD{% endif %}
        Published {{ post.date | months_ago }} months ago
    """
    from bengal.utils.dates import parse_date

    dt = parse_date(date)
    if not dt:
        return 0

    if now is None:
        now = datetime.now(UTC) if dt.tzinfo is not None else datetime.now()

    # Calculate calendar months difference
    months = (now.year - dt.year) * 12 + (now.month - dt.month)
    return max(0, months)


def month_name(month: int, abbrev: bool = False) -> str:
    """
    Get month name from month number (1-12).

    Args:
        month: Month number (1=January, 12=December)
        abbrev: If True, return abbreviated name (Jan, Feb, etc.)

    Returns:
        Month name string, or empty string if invalid

    Example:
        {{ 3 | month_name }}        → "March"
        {{ 3 | month_name(true) }}  → "Mar"
        {{ post.date.month | month_name }}
    """
    if not isinstance(month, int) or month < 1 or month > 12:
        return ""

    if abbrev:
        return calendar.month_abbr[month]
    return calendar.month_name[month]


def humanize_days(days: int) -> str:
    """
    Convert day count to human-readable relative time.

    Provides friendly labels for common time periods.

    Args:
        days: Number of days

    Returns:
        Human-readable string like "today", "yesterday", "3 days ago"

    Example:
        {{ post.date | days_ago | humanize_days }}
        → "yesterday", "3 days ago", "2 weeks ago", "3 months ago"
    """
    if not isinstance(days, int):
        try:
            days = int(days)
        except (ValueError, TypeError):
            return ""

    if days < 0:
        return ""
    elif days == 0:
        return "today"
    elif days == 1:
        return "yesterday"
    elif days < 7:
        return f"{days} days ago"
    elif days < 14:
        return "1 week ago"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} weeks ago"
    elif days < 60:
        return "1 month ago"
    elif days < 365:
        months = days // 30
        return f"{months} months ago"
    elif days < 730:
        return "1 year ago"
    else:
        years = days // 365
        return f"{years} years ago"


def date_add(
    date: datetime | str | None,
    days: int = 0,
    weeks: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> datetime | None:
    """
    Add time to a date.

    Args:
        date: Base date (datetime object or ISO string)
        days: Days to add (negative to subtract)
        weeks: Weeks to add
        hours: Hours to add
        minutes: Minutes to add
        seconds: Seconds to add

    Returns:
        New datetime, or None if date is invalid

    Example:
        {{ page.date | date_add(days=7) }}  # One week later
        {{ now | date_add(days=-30) }}  # 30 days ago
        {{ event.start | date_add(hours=2) }}  # 2 hours later
    """
    from bengal.utils.dates import parse_date

    dt = parse_date(date)
    if not dt:
        return None

    delta = timedelta(
        days=days,
        weeks=weeks,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )
    return dt + delta


def date_diff(
    date1: datetime | str | None,
    date2: datetime | str | None,
    unit: str = "days",
) -> int | dict | None:
    """
    Calculate difference between two dates.

    Args:
        date1: First date (usually the later date)
        date2: Second date (usually the earlier date)
        unit: Return unit ('days', 'hours', 'minutes', 'seconds', or 'all')

    Returns:
        Difference in specified unit, or dict with all units if unit='all'
        Returns None if either date is invalid

    Example:
        {{ end_date | date_diff(start_date) }}  # Days between dates
        {{ end_date | date_diff(start_date, unit='hours') }}  # Hours between
        {{ end_date | date_diff(start_date, unit='all') }}  # Dict with all units
    """
    from bengal.utils.dates import parse_date

    dt1 = parse_date(date1)
    dt2 = parse_date(date2)

    if not dt1 or not dt2:
        return None

    diff = dt1 - dt2
    total_seconds = int(diff.total_seconds())

    if unit == "all":
        return {
            "days": diff.days,
            "hours": total_seconds // 3600,
            "minutes": total_seconds // 60,
            "seconds": total_seconds,
        }

    if unit == "days":
        return diff.days
    elif unit == "hours":
        return total_seconds // 3600
    elif unit == "minutes":
        return total_seconds // 60
    elif unit == "seconds":
        return total_seconds

    # Default to days
    return diff.days
