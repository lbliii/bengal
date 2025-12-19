"""
Text processing utilities.

Provides canonical implementations for common text operations like slugification,
HTML stripping, truncation, and excerpt generation. These utilities consolidate
duplicate implementations found throughout the codebase.

Example:

```python
from bengal.utils.text import slugify, strip_html, truncate_words

slug = slugify("Hello World!")  # "hello-world"
text = strip_html("<p>Hello</p>")  # "Hello"
excerpt = truncate_words("Long text here...", 10)
```
"""

from __future__ import annotations

import html as html_module
import re


def slugify(
    text: str, unescape_html: bool = True, max_length: int | None = None, separator: str = "-"
) -> str:
    """
    Convert text to URL-safe slug with Unicode support.

    Preserves Unicode word characters (letters, digits, underscore) to support
    international content. Modern web browsers and servers handle Unicode URLs.

    Consolidates implementations from:
    - bengal/rendering/parser.py:629 (_slugify)
    - bengal/rendering/template_functions/strings.py:92 (slugify)
    - bengal/rendering/template_functions/taxonomies.py:184 (tag_url pattern)

    Args:
        text: Text to slugify
        unescape_html: Whether to decode HTML entities first (e.g., &amp; -> &)
        max_length: Maximum slug length (None = unlimited)
        separator: Character to use between words (default: '-')

    Returns:
        URL-safe slug (lowercase, with Unicode word chars and separators)

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("Test & Code")
        'test-code'
        >>> slugify("Test &amp; Code", unescape_html=True)
        'test-code'
        >>> slugify("Very Long Title Here", max_length=10)
        'very-long'
        >>> slugify("hello_world", separator='_')
        'hello_world'
        >>> slugify("你好世界")
        '你好世界'
        >>> slugify("Café")
        'café'

    Note:
        Uses Python's \\w regex pattern which includes Unicode letters and digits.
        This is intentional to support international content in URLs.
    """
    if not text:
        return ""

    # Decode HTML entities if requested
    # This handles cases like "Test &amp; Code" which Mistune renders with entities
    if unescape_html:
        text = html_module.unescape(text)

    # Convert to lowercase and strip whitespace
    text = text.lower().strip()

    # Remove non-word characters (except spaces and hyphens)
    # Keep Unicode word characters (\w includes non-ASCII)
    text = re.sub(r"[^\w\s-]", "", text)

    # Replace multiple spaces/hyphens with separator
    text = re.sub(r"[-\s]+", separator, text)

    # Remove leading/trailing separators
    text = text.strip(separator)

    # Apply max length if specified
    if max_length and len(text) > max_length:
        # Try to break at separator for cleaner truncation
        truncated = text[:max_length]
        if separator in truncated:
            # Find last separator before max_length
            parts = truncated.split(separator)
            text = separator.join(parts[:-1])
        else:
            text = truncated

    return text


def strip_html(text: str, decode_entities: bool = True) -> str:
    """
    Remove all HTML tags from text.

    Consolidates implementation from:
    - bengal/rendering/template_functions/strings.py:157 (strip_html)

    Args:
        text: HTML text to clean
        decode_entities: Whether to decode HTML entities (e.g., &lt; -> <)

    Returns:
        Plain text with HTML tags removed

    Examples:
        >>> strip_html("<p>Hello <strong>World</strong></p>")
        'Hello World'
        >>> strip_html("&lt;script&gt;", decode_entities=True)
        '<script>'
        >>> strip_html("&lt;script&gt;", decode_entities=False)
        '&lt;script&gt;'
    """
    if not text:
        return ""

    # Remove HTML tags using regex
    # Matches <...> including self-closing tags and tags with attributes
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities if requested
    if decode_entities:
        text = html_module.unescape(text)

    return text


def truncate_words(text: str, word_count: int, suffix: str = "...") -> str:
    """
    Truncate text to specified word count.

    Consolidates pattern from:
    - bengal/rendering/template_functions/strings.py (truncatewords)

    Args:
        text: Text to truncate
        word_count: Maximum number of words
        suffix: Suffix to append if truncated

    Returns:
        Truncated text with suffix if shortened

    Examples:
        >>> truncate_words("The quick brown fox jumps", 3)
        'The quick brown...'
        >>> truncate_words("Short text", 10)
        'Short text'
        >>> truncate_words("One two three four", 3, suffix="…")
        'One two three…'
    """
    if not text:
        return ""

    words = text.split()

    if len(words) <= word_count:
        return text

    return " ".join(words[:word_count]) + suffix


def truncate_chars(text: str, length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified character length (including suffix).

    Args:
        text: Text to truncate
        length: Maximum total length (including suffix if truncated)
        suffix: Suffix to append if truncated

    Returns:
        Truncated text with suffix if shortened, never exceeding length

    Examples:
        >>> truncate_chars("Hello World", 8)
        'Hello...'
        >>> truncate_chars("Short", 10)
        'Short'
        >>> truncate_chars("0123456789", 10)
        '0123456...'
    """
    if not text:
        return ""

    if len(text) <= length:
        return text

    # Account for suffix length when truncating so total stays within length
    suffix_len = len(suffix)
    if suffix_len >= length:
        # Edge case: suffix is longer than or equal to requested length
        return suffix[:length]

    # Truncate to (length - suffix_len), rstrip whitespace, then add suffix
    truncate_at = length - suffix_len
    return text[:truncate_at].rstrip() + suffix


def truncate_middle(text: str, max_length: int, separator: str = "...") -> str:
    """
    Truncate text in the middle (useful for file paths).

    Args:
        text: Text to truncate
        max_length: Maximum total length
        separator: Separator to use in middle

    Returns:
        Truncated text with separator in middle

    Examples:
        >>> truncate_middle('/very/long/path/to/file.txt', 20)
        '/very/.../file.txt'
        >>> truncate_middle('short.txt', 20)
        'short.txt'
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    sep_len = len(separator)
    available = max_length - sep_len

    if available <= 0:
        return separator[:max_length]

    left = available // 2
    right = available - left

    return text[:left] + separator + text[-right:]


def generate_excerpt(html: str, word_count: int = 50, suffix: str = "...") -> str:
    """
    Generate plain text excerpt from HTML content.

    Combines strip_html and truncate_words for common use case.
    Consolidates pattern from:
    - bengal/postprocess/output_formats.py:674
    - Various template functions

    Args:
        html: HTML content
        word_count: Maximum number of words
        suffix: Suffix to append if truncated

    Returns:
        Plain text excerpt

    Examples:
        >>> generate_excerpt("<p>Hello <strong>World</strong> from Bengal</p>", 2)
        'Hello World...'
    """
    # Strip HTML tags and decode entities
    text = strip_html(html, decode_entities=True)

    # Truncate to word count
    return truncate_words(text, word_count, suffix)


def normalize_whitespace(text: str, collapse: bool = True) -> str:
    """
    Normalize whitespace in text.

    Args:
        text: Text to normalize
        collapse: Whether to collapse multiple spaces to single space

    Returns:
        Text with normalized whitespace

    Examples:
        >>> normalize_whitespace("  hello   world  ")
        'hello world'
        >>> normalize_whitespace("line1\\n\\n\\nline2", collapse=True)
        'line1 line2'
    """
    if not text:
        return ""

    if collapse:
        # Collapse all whitespace (including newlines) to single space
        text = re.sub(r"\s+", " ", text)
        # Strip leading/trailing whitespace
        text = text.strip()
    else:
        # Just strip leading/trailing whitespace
        text = text.strip()

    return text


def escape_html(text: str) -> str:
    """
    Escape HTML entities.

    Converts special characters to HTML entities:
    - < becomes &lt;
    - > becomes &gt;
    - & becomes &amp;
    - " becomes &quot;
    - ' becomes &#x27;

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text

    Examples:
        >>> escape_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
    """
    if not text:
        return ""

    return html_module.escape(text)


def unescape_html(text: str) -> str:
    """
    Unescape HTML entities.

    Converts HTML entities back to characters:
    - &lt; becomes <
    - &gt; becomes >
    - &amp; becomes &
    - &quot; becomes "

    Args:
        text: HTML text with entities

    Returns:
        Unescaped text

    Examples:
        >>> unescape_html("&lt;Hello&gt;")
        '<Hello>'
    """
    if not text:
        return ""

    return html_module.unescape(text)


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """
    Return singular or plural form based on count.

    Args:
        count: Count value
        singular: Singular form
        plural: Plural form (default: singular + 's')

    Returns:
        Appropriate form for the count

    Examples:
        >>> pluralize(1, 'page')
        'page'
        >>> pluralize(2, 'page')
        'pages'
        >>> pluralize(2, 'box', 'boxes')
        'boxes'
        >>> pluralize(0, 'item')
        'items'
    """
    if count == 1:
        return singular
    return plural if plural else singular + "s"


def humanize_bytes(size_bytes: int) -> str:
    """
    Format bytes as human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string (e.g., "1.5 KB", "2.3 MB")

    Examples:
        >>> humanize_bytes(1024)
        '1.0 KB'
        >>> humanize_bytes(1536)
        '1.5 KB'
        >>> humanize_bytes(1048576)
        '1.0 MB'
    """
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    # Use 1 decimal place for sizes >= 1KB, no decimals for bytes
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def humanize_number(num: int) -> str:
    """
    Format number with thousand separators.

    Args:
        num: Number to format

    Returns:
        Formatted string with commas

    Examples:
        >>> humanize_number(1234567)
        '1,234,567'
        >>> humanize_number(1000)
        '1,000'
    """
    return f"{num:,}"


def humanize_slug(slug: str) -> str:
    """
    Convert slug or filename stem to human-readable title.

    Transforms kebab-case and snake_case identifiers into
    Title Case strings suitable for display in navigation,
    page titles, and other user-facing contexts.

    Consolidates pattern from:
    - bengal/core/page/metadata.py (title property)
    - bengal/discovery/content_discovery.py (fallback titles)
    - bengal/rendering/template_functions/navigation.py (breadcrumbs)
    - bengal/cli/helpers/menu_config.py (menu titles)
    - Various Jinja templates

    Args:
        slug: Slug or filename stem (e.g., "my-page-name", "data_model")

    Returns:
        Human-readable title (e.g., "My Page Name", "Data Model")

    Examples:
        >>> humanize_slug("my-page-name")
        'My Page Name'
        >>> humanize_slug("data_model_v2")
        'Data Model V2'
        >>> humanize_slug("_index")
        ' Index'
        >>> humanize_slug("")
        ''

    Note:
        This is a mechanical transformation (replace separators, title-case).
        Slashes and other characters are preserved. For semantic mappings
        (e.g., "autodoc/python" → "API Reference"), use domain-specific logic.
    """
    if not slug:
        return ""
    return slug.replace("-", " ").replace("_", " ").title()
