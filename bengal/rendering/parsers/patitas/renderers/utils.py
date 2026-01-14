"""Utility functions for HTML rendering.

Provides escape functions, URL encoding, and the HeadingInfo dataclass.
Thread-safe: all functions are pure (no shared mutable state).
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape as html_escape
from html import unescape as html_unescape


@dataclass(frozen=True, slots=True)
class HeadingInfo:
    """Heading metadata collected during rendering.

    Used to build TOC without post-render regex scanning.
    Collected by HtmlRenderer during the AST walk.
    """

    level: int
    text: str
    slug: str


def escape_html(text: str) -> str:
    """Escape HTML special characters for text content.

    Per CommonMark spec:
    - < > & must be escaped (XSS prevention)
    - " should be escaped to &quot; (for safety)
    - ' should remain literal in text content (not &#x27;)

    Also strips internal \x00 markers used for lazy continuation escaping.
    """
    # Strip internal \x00 markers (used to prevent block element detection in lazy continuation)
    text = text.replace("\x00", "")
    # html_escape with quote=True escapes both " and '
    # We only want to escape " but not '
    result = html_escape(text, quote=False)  # Escapes < > &
    result = result.replace('"', "&quot;")  # Also escape "
    return result


def escape_attr(text: str) -> str:
    """Escape HTML attribute value."""
    return html_escape(text, quote=True)


def encode_url(url: str) -> str:
    """Encode URL for use in href attribute per CommonMark spec.

    CommonMark requires:
    1. Percent-encoding of special characters in URLs (space, backslash, etc.)
    2. HTML escaping of characters that are special in HTML (& → &amp;)

    The final output goes in an HTML attribute, so we need both:
    - URL percent-encoding for URL-special characters
    - HTML escaping for HTML-special characters (&, <, >, ", ')
    """
    import html
    from urllib.parse import quote

    # First, decode any HTML entities (e.g., &auml; → ä)
    decoded = html.unescape(url)

    # Preserve already-valid percent sequences
    # Split on existing %XX patterns and encode each part
    result = []
    i = 0
    while i < len(decoded):
        # Check for existing percent encoding
        if decoded[i] == "%" and i + 2 < len(decoded):
            hex_chars = decoded[i + 1 : i + 3]
            if all(c in "0123456789ABCDEFabcdef" for c in hex_chars):
                # Valid percent sequence - preserve it
                result.append(decoded[i : i + 3])
                i += 3
                continue

        char = decoded[i]

        # Characters safe in URLs (RFC 3986 unreserved + sub-delims + : / ? # @ = &)
        # CommonMark allows more lax URLs so we preserve more chars
        if (
            char
            in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;="
        ):
            result.append(char)
        else:
            # Percent-encode this character
            encoded = quote(char, safe="")
            result.append(encoded)

        i += 1

    # Now HTML-escape the result for use in an attribute
    # This converts & → &amp;, etc.
    url_encoded = "".join(result)
    return html_escape(url_encoded, quote=True)


def escape_link_title(title: str) -> str:
    """Escape link title for use in title attribute per CommonMark spec.

    Titles use HTML escaping but must also decode HTML entities first.
    E.g., &quot; in source becomes " which then becomes &quot; in output.
    """
    import html

    # Decode entities first, then HTML-escape
    decoded = html.unescape(title)
    return html_escape(decoded, quote=True)


def default_slugify(text: str) -> str:
    """Default slugify function for heading IDs.

    Uses bengal.utils.text.slugify with HTML unescaping enabled.
    """
    from bengal.utils.primitives.text import slugify

    return slugify(text, unescape_html=True, max_length=100)
