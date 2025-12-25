"""HTML escaping utilities for Rosettes.

Thread-safe string escaping for HTML output.
"""

__all__ = ["escape_html"]

# Pre-computed escape table for performance
_ESCAPE_TABLE = {
    ord("&"): "&amp;",
    ord("<"): "&lt;",
    ord(">"): "&gt;",
    ord('"'): "&quot;",
    ord("'"): "&#x27;",
}


def escape_html(text: str) -> str:
    """Escape HTML special characters.

    Escapes: & < > " '

    Args:
        text: The text to escape.

    Returns:
        HTML-safe string.

    Example:
        >>> escape_html('<script>alert("xss")</script>')
        '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
    """
    return text.translate(_ESCAPE_TABLE)
