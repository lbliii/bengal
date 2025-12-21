"""
Date and time utilities for Bengal SSG.

Provides centralized date parsing, formatting, and manipulation functions
to eliminate duplicate logic across templates and core code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_type

# Type alias for date-like values
type DateLike = datetime | date_type | str | None


def parse_date(
    value: DateLike, formats: list[str] | None = None, on_error: str = "return_none"
) -> datetime | None:
    """
    Parse various date formats into datetime.

    Handles:
    - datetime objects (pass through)
    - date objects (convert to datetime at midnight)
    - ISO 8601 strings (with or without timezone)
    - Custom format strings

    Args:
        value: Date value in various formats
        formats: Optional list of strptime format strings to try
        on_error: How to handle parse errors:
            - 'return_none': Return None (default)
            - 'raise': Raise ValueError
            - 'return_original': Return original value as-is

    Returns:
        datetime object or None if parsing fails

    Examples:
        >>> parse_date("2025-10-09")
        datetime(2025, 10, 9, 0, 0)
        >>> parse_date("2025-10-09T14:30:00Z")
        datetime(2025, 10, 9, 14, 30, tzinfo=...)
        >>> parse_date(datetime.now())
        datetime(...)
    """
    if value is None:
        return None

    # Already a datetime - pass through
    if isinstance(value, datetime):
        return value

    # date object - convert to datetime at midnight
    if isinstance(value, date_type):
        return datetime.combine(value, datetime.min.time())

    # String - try parsing
    if isinstance(value, str):
        # Try ISO format first (most common)
        try:
            # Handle 'Z' timezone suffix
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

        # Try custom formats if provided
        if formats:
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

        # Try common formats
        default_formats = [
            "%Y-%m-%d",  # 2025-10-09
            "%Y/%m/%d",  # 2025/10/09
            "%d-%m-%Y",  # 09-10-2025
            "%d/%m/%Y",  # 09/10/2025
            "%B %d, %Y",  # October 09, 2025
            "%b %d, %Y",  # Oct 09, 2025
            "%Y-%m-%d %H:%M:%S",  # 2025-10-09 14:30:00
            "%Y/%m/%d %H:%M:%S",  # 2025/10/09 14:30:00
        ]

        for fmt in default_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

    # Couldn't parse
    if on_error == "raise":
        from bengal.errors import BengalError

        raise BengalError(
            f"Could not parse date from: {value!r}",
            suggestion="Use ISO 8601 format (YYYY-MM-DD) or common date formats",
        )
    elif on_error == "return_original":
        return value  # type: ignore
    else:  # 'return_none'
        return None


def format_date_iso(date: DateLike) -> str:
    """
    Format date as ISO 8601 string.

    Uses parse_date internally for flexible input handling.

    Args:
        date: Date value in various formats

    Returns:
        ISO 8601 formatted string (YYYY-MM-DDTHH:MM:SS)

    Examples:
        >>> format_date_iso(datetime(2025, 10, 9, 14, 30))
        '2025-10-09T14:30:00'
        >>> format_date_iso("2025-10-09")
        '2025-10-09T00:00:00'
    """
    dt = parse_date(date)
    return dt.isoformat() if dt else ""


def format_date_rfc822(date: DateLike) -> str:
    """
    Format date as RFC 822 string (for RSS feeds).

    Uses parse_date internally for flexible input handling.

    Args:
        date: Date value in various formats

    Returns:
        RFC 822 formatted string (e.g., "Fri, 03 Oct 2025 14:30:00 +0000")

    Examples:
        >>> format_date_rfc822(datetime(2025, 10, 9, 14, 30))
        'Thu, 09 Oct 2025 14:30:00 '
    """
    dt = parse_date(date)
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z") if dt else ""


def format_date_human(date: DateLike, format: str = "%B %d, %Y") -> str:
    """
    Format date in human-readable format.

    Uses parse_date internally for flexible input handling.

    Args:
        date: Date value in various formats
        format: strftime format string (default: "October 09, 2025")

    Returns:
        Formatted date string

    Examples:
        >>> format_date_human(datetime(2025, 10, 9))
        'October 09, 2025'
        >>> format_date_human("2025-10-09", format='%Y-%m-%d')
        '2025-10-09'
    """
    dt = parse_date(date)
    return dt.strftime(format) if dt else ""


def time_ago(date: DateLike, now: datetime | None = None) -> str:
    """
    Convert date to human-readable "time ago" format.

    Uses parse_date internally for flexible input handling.

    Args:
        date: Date to convert
        now: Current time (defaults to datetime.now())

    Returns:
        Human-readable time ago string

    Examples:
        >>> time_ago(datetime.now() - timedelta(minutes=5))
        '5 minutes ago'
        >>> time_ago(datetime.now() - timedelta(days=2))
        '2 days ago'
        >>> time_ago("2025-10-01")
        '8 days ago'
    """
    dt = parse_date(date)
    if not dt:
        return ""

    # Determine current time with timezone awareness matching the input
    if now is None:
        now = datetime.now(UTC) if dt.tzinfo is not None else datetime.now()

    # Calculate difference
    diff = now - dt

    # Handle future dates
    if diff.total_seconds() < 0:
        return "just now"

    # Calculate time components
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:  # Less than 1 hour
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:  # Less than 1 day
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.days < 30:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"


def get_current_year() -> int:
    """
    Get current year as integer.

    Useful for copyright notices and templates.

    Returns:
        Current year

    Example:
        >>> get_current_year()
        2025
    """
    return datetime.now().year


def is_recent(date: DateLike, days: int = 7, now: datetime | None = None) -> bool:
    """
    Check if date is recent (within specified days).

    Args:
        date: Date to check
        days: Number of days to consider "recent" (default: 7)
        now: Current time (defaults to datetime.now())

    Returns:
        True if date is within the last N days

    Examples:
        >>> is_recent(datetime.now() - timedelta(days=3))
        True
        >>> is_recent("2025-01-01", days=7)
        False
    """
    dt = parse_date(date)
    if not dt:
        return False

    if now is None:
        now = datetime.now(UTC) if dt.tzinfo is not None else datetime.now()

    diff = now - dt
    return 0 <= diff.days <= days


def date_range_overlap(start1: DateLike, end1: DateLike, start2: DateLike, end2: DateLike) -> bool:
    """
    Check if two date ranges overlap.

    Args:
        start1: Start of first range
        end1: End of first range
        start2: Start of second range
        end2: End of second range

    Returns:
        True if ranges overlap

    Examples:
        >>> date_range_overlap("2025-01-01", "2025-01-10", "2025-01-05", "2025-01-15")
        True
        >>> date_range_overlap("2025-01-01", "2025-01-10", "2025-01-15", "2025-01-20")
        False
    """
    dt_start1 = parse_date(start1)
    dt_end1 = parse_date(end1)
    dt_start2 = parse_date(start2)
    dt_end2 = parse_date(end2)

    if not all([dt_start1, dt_end1, dt_start2, dt_end2]):
        return False

    return dt_start1 <= dt_end2 and dt_start2 <= dt_end1  # type: ignore


def utc_now() -> datetime:
    """Get current UTC datetime (low-level primitive)."""
    return datetime.now(UTC)


def iso_timestamp(dt: datetime | None = None) -> str:
    """Get ISO 8601 timestamp from datetime (UTC)."""
    if dt is None:
        dt = utc_now()
    return dt.isoformat()
