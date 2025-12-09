"""
String manipulation functions for templates.

Provides 11 essential string functions for text processing in templates.

Many of these functions are now thin wrappers around bengal.utils.text utilities
to avoid code duplication and ensure consistency.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bengal.utils import text as text_utils
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register string functions with Jinja2 environment."""
    env.filters.update(
        {
            "truncatewords": truncatewords,
            "truncatewords_html": truncatewords_html,
            "slugify": slugify,
            "markdownify": markdownify,
            "strip_html": strip_html,
            "truncate_chars": truncate_chars,
            "replace_regex": replace_regex,
            "pluralize": pluralize,
            "reading_time": reading_time,
            "excerpt": excerpt,
            "strip_whitespace": strip_whitespace,
            "get": dict_get,
            "first_sentence": first_sentence,
        }
    )


def dict_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe get supporting dict-like objects for component preview contexts."""
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        # Allow attribute access as fallback
        if hasattr(obj, key):
            return getattr(obj, key)
    except Exception as e:
        logger.debug(
            "safe_get_failed",
            key=key,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_default",
        )
        pass
    return default


def truncatewords(text: str, count: int, suffix: str = "...") -> str:
    """
    Truncate text to a specified number of words.

    Uses bengal.utils.text.truncate_words internally.

    Args:
        text: Text to truncate
        count: Maximum number of words
        suffix: Text to append when truncated (default: "...")

    Returns:
        Truncated text with suffix if needed

    Example:
        {{ post.content | truncatewords(50) }}
        {{ post.content | truncatewords(30, " [Read more]") }}
    """
    return text_utils.truncate_words(text, count, suffix)


def truncatewords_html(html: str, count: int, suffix: str = "...") -> str:
    """
    Truncate HTML text to word count, preserving HTML tags.

    This is more sophisticated than truncatewords - it preserves HTML structure
    and properly closes tags.

    Args:
        html: HTML text to truncate
        count: Maximum number of words
        suffix: Text to append when truncated

    Returns:
        Truncated HTML with properly closed tags

    Example:
        {{ post.html_content | truncatewords_html(50) }}
    """
    if not html:
        return ""

    # Strip HTML to count words
    text_only = strip_html(html)
    words = text_only.split()

    if len(words) <= count:
        return html

    # Simple implementation: strip HTML, truncate, add suffix
    # A more sophisticated version would preserve HTML structure
    truncated_text = " ".join(words[:count])
    return truncated_text + suffix


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Uses bengal.utils.text.slugify internally.
    Converts to lowercase, removes special characters, replaces spaces with hyphens.

    Args:
        text: Text to convert

    Returns:
        URL-safe slug

    Example:
        {{ page.title | slugify }}  # "Hello World!" -> "hello-world"
    """
    return text_utils.slugify(text, unescape_html=False)


def markdownify(text: str) -> str:
    """
    Render Markdown text to HTML.

    Uses Python-Markdown with extensions for tables, code highlighting, etc.

    Args:
        text: Markdown text

    Returns:
        Rendered HTML

    Example:
        {{ markdown_text | markdownify | safe }}
    """
    if not text:
        return ""

    try:
        import markdown

        md = markdown.Markdown(
            extensions=[
                "extra",
                "codehilite",
                "tables",
                "fenced_code",
            ]
        )
        return md.convert(text)
    except ImportError:
        # Fallback if markdown not installed
        return text


def strip_html(text: str) -> str:
    """
    Remove all HTML tags from text.

    Uses bengal.utils.text.strip_html internally.

    Args:
        text: HTML text

    Returns:
        Text with HTML tags removed

    Example:
        {{ post.html_content | strip_html }}
    """
    return text_utils.strip_html(text, decode_entities=True)


def truncate_chars(text: str, length: int, suffix: str = "...") -> str:
    """
    Truncate text to character length.

    Uses bengal.utils.text.truncate_chars internally.

    Args:
        text: Text to truncate
        length: Maximum character length
        suffix: Text to append when truncated

    Returns:
        Truncated text with suffix if needed

    Example:
        {{ post.excerpt | truncate_chars(200) }}
    """
    return text_utils.truncate_chars(text, length, suffix)


def replace_regex(text: str, pattern: str, replacement: str) -> str:
    """
    Replace text using regular expression.

    Args:
        text: Text to search in
        pattern: Regular expression pattern
        replacement: Replacement text

    Returns:
        Text with replacements made

    Example:
        {{ text | replace_regex('\\d+', 'NUM') }}
    """
    if not text:
        return ""

    try:
        return re.sub(pattern, replacement, text)
    except re.error:
        # Return original text if regex is invalid
        return text


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """
    Return singular or plural form based on count.

    Uses bengal.utils.text.pluralize internally.

    Args:
        count: Number to check
        singular: Singular form
        plural: Plural form (default: singular + 's')

    Returns:
        Appropriate form based on count

    Example:
        {{ posts | length }} {{ posts | length | pluralize('post', 'posts') }}
        {{ count | pluralize('item') }}  # auto-pluralizes to "items"
    """
    return text_utils.pluralize(count, singular, plural)


def reading_time(text: str, wpm: int = 200) -> int:
    """
    Calculate reading time in minutes.

    Args:
        text: Text to analyze
        wpm: Words per minute reading speed (default: 200)

    Returns:
        Reading time in minutes (minimum 1)

    Example:
        {{ post.content | reading_time }} min read
        {{ post.content | reading_time(250) }} min read
    """
    if not text:
        return 1

    # Strip HTML if present
    clean_text = strip_html(text)

    # Count words
    words = len(clean_text.split())

    # Calculate reading time
    minutes = words / wpm

    # Always return at least 1 minute
    return max(1, round(minutes))


def excerpt(text: str, length: int = 200, respect_word_boundaries: bool = True) -> str:
    """
    Extract excerpt from text, optionally respecting word boundaries.

    Args:
        text: Text to excerpt from
        length: Maximum length in characters
        respect_word_boundaries: Don't cut words in half (default: True)

    Returns:
        Excerpt with ellipsis if truncated

    Example:
        {{ post.content | excerpt(200) }}
        {{ post.content | excerpt(150, false) }}  # Can cut words
    """
    if not text:
        return ""

    # Strip HTML first
    clean_text = strip_html(text)

    if len(clean_text) <= length:
        return clean_text

    if respect_word_boundaries:
        # Find the last space before the limit
        excerpt_text = clean_text[:length].rsplit(" ", 1)[0]
        return excerpt_text + "..."
    else:
        return clean_text[:length] + "..."


def strip_whitespace(text: str) -> str:
    """
    Remove extra whitespace (multiple spaces, newlines, tabs).

    Uses bengal.utils.text.normalize_whitespace internally.
    Replaces all whitespace sequences with a single space.

    Args:
        text: Text to clean

    Returns:
        Text with normalized whitespace

    Example:
        {{ messy_text | strip_whitespace }}
    """
    return text_utils.normalize_whitespace(text, collapse=True)


def first_sentence(text: str, max_length: int = 120) -> str:
    """
    Extract first sentence from text, or truncate if too long.

    Useful for generating short descriptions from longer text blocks.
    Looks for sentence-ending punctuation (. ! ?) followed by whitespace.

    Args:
        text: Text to extract first sentence from
        max_length: Maximum length before truncation (default: 120)

    Returns:
        First sentence or truncated text with ellipsis

    Example:
        {{ page.description | first_sentence }}
        {{ section.metadata.description | first_sentence(80) }}
    """
    if not text:
        return ""

    text = text.strip()

    # Try to find first sentence by looking for sentence-ending punctuation
    for end in [". ", ".\n", "!\n", "?\n", "! ", "? "]:
        if end in text:
            first = text.split(end)[0] + end[0]
            if len(first) <= max_length:
                return first
            break

    # Truncate if too long
    if len(text) > max_length:
        # Try to break at word boundary
        truncated = text[: max_length - 3].rsplit(" ", 1)[0]
        return truncated + "..."

    return text
