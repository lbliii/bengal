"""HTML utilities for Kida template engine.

Provides optimized HTML escaping and manipulation functions.
"""

from __future__ import annotations

import re
from typing import Any

from markupsafe import Markup

# Pre-compiled escape table for O(n) single-pass HTML escaping
# This replaces the O(5n) chained .replace() approach
_ESCAPE_TABLE = str.maketrans(
    {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }
)

# Fast path: regex to check if escaping is needed at all
_ESCAPE_CHECK = re.compile(r'[&<>"\']')

# Pre-compiled regex for stripping HTML tags
_STRIPTAGS_RE = re.compile(r"<[^>]*>")

# Pre-compiled regex for removing whitespace between HTML tags
_SPACELESS_RE = re.compile(r">\s+<")


def html_escape(value: Any) -> str:
    """O(n) single-pass HTML escaping.
    
    Returns plain str (for template._escape use).
    
    Complexity: O(n) single-pass using str.translate().
    
    Optimizations:
    1. Skip Markup objects (already safe)
    2. Fast path check - if no escapable chars, return as-is
    3. Single-pass translation instead of 5 chained .replace()
    
    This is ~3-5x faster than the naive approach for escape-heavy content.
    
    Args:
        value: Value to escape (will be converted to string)
        
    Returns:
        Escaped string (not Markup, so it can be escaped again if needed)
    """
    # Skip Markup objects - they're already safe
    # Must check before str() conversion since str(Markup) returns plain str
    if isinstance(value, Markup):
        return str(value)
    s = str(value)
    # Fast path: no escapable characters
    if not _ESCAPE_CHECK.search(s):
        return s
    return s.translate(_ESCAPE_TABLE)


def html_escape_filter(value: Any) -> Markup:
    """HTML escape returning Markup (for filter use).
    
    Returns Markup object so result won't be escaped again by autoescape.
    
    Args:
        value: Value to escape (will be converted to string)
        
    Returns:
        Markup object (safe, won't be double-escaped)
    """
    # Already safe - return as-is
    if isinstance(value, Markup):
        return value
    return Markup(html_escape(value))


def strip_tags(value: str) -> str:
    """Remove HTML tags from string.
    
    Uses pre-compiled regex for performance.
    
    Args:
        value: String potentially containing HTML tags
        
    Returns:
        String with all HTML tags removed
    """
    return _STRIPTAGS_RE.sub("", str(value))


def spaceless(html: str) -> str:
    """Remove whitespace between HTML tags.
    
    Args:
        html: HTML string
        
    Returns:
        HTML string with whitespace between tags removed
    """
    return _SPACELESS_RE.sub("><", html).strip()


def xmlattr(value: dict) -> Markup:
    """Convert dict to XML attributes string.
    
    Escapes attribute values and formats as key="value" pairs.
    Returns Markup to prevent double-escaping when autoescape is enabled.
    
    Args:
        value: Dictionary of attribute names to values
        
    Returns:
        Markup object containing space-separated key="value" pairs
    """
    parts = []
    for key, val in value.items():
        if val is not None:
            escaped = html_escape(str(val))
            parts.append(f'{key}="{escaped}"')
    return Markup(" ".join(parts))

