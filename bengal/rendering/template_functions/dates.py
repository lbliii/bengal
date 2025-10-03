"""
Date and time functions for templates.

Provides 3 functions for date formatting and display.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site


def register(env: 'Environment', site: 'Site') -> None:
    """Register date functions with Jinja2 environment."""
    env.filters.update({
        'time_ago': time_ago,
        'date_iso': date_iso,
        'date_rfc822': date_rfc822,
    })


def time_ago(date: Union[datetime, str, None]) -> str:
    """
    Convert date to human-readable "time ago" format.
    
    Args:
        date: Date to convert (datetime object or ISO string)
    
    Returns:
        Human-readable time ago string
    
    Example:
        {{ post.date | time_ago }}  # "2 days ago", "5 hours ago", etc.
    """
    if not date:
        return ''
    
    # Parse if string
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return str(date)
    
    if not isinstance(date, datetime):
        return str(date)
    
    # Make timezone-naive for comparison
    if date.tzinfo is not None:
        from datetime import timezone
        now = datetime.now(timezone.utc)
    else:
        now = datetime.now()
    
    # Calculate difference
    diff = now - date
    
    # Handle future dates
    if diff.total_seconds() < 0:
        return "just now"
    
    # Calculate time ago
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


def date_iso(date: Union[datetime, str, None]) -> str:
    """
    Format date as ISO 8601 string.
    
    Args:
        date: Date to format
    
    Returns:
        ISO 8601 formatted date string
    
    Example:
        <time datetime="{{ post.date | date_iso }}">
        # Output: 2025-10-03T14:30:00
    """
    if not date:
        return ''
    
    # Parse if string
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return str(date)
    
    if not isinstance(date, datetime):
        return str(date)
    
    return date.isoformat()


def date_rfc822(date: Union[datetime, str, None]) -> str:
    """
    Format date as RFC 822 string (for RSS feeds).
    
    Args:
        date: Date to format
    
    Returns:
        RFC 822 formatted date string
    
    Example:
        <pubDate>{{ post.date | date_rfc822 }}</pubDate>
        # Output: Fri, 03 Oct 2025 14:30:00 +0000
    """
    if not date:
        return ''
    
    # Parse if string
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return str(date)
    
    if not isinstance(date, datetime):
        return str(date)
    
    # RFC 822 format
    return date.strftime("%a, %d %b %Y %H:%M:%S %z")

