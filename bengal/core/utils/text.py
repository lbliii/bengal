"""
Text processing utilities.

Provides HTML stripping and text truncation functions used across
Page, Section, and Asset models for generating excerpts, meta descriptions,
and plain text content.

Functions:
    strip_html: Remove HTML tags from text
    truncate_at_sentence: Truncate text at sentence boundary
    truncate_at_word: Truncate text at word boundary
    normalize_whitespace: Collapse multiple whitespace to single spaces

"""

from __future__ import annotations

import re

# Compiled regex patterns for performance
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """
    Strip HTML tags from text.

    Removes all HTML tags while preserving the text content between them.
    Does not decode HTML entities (use html.unescape for that).

    Args:
        text: HTML content to strip

    Returns:
        Plain text with HTML tags removed

    Example:
        >>> strip_html("<p>Hello <strong>world</strong>!</p>")
        'Hello world!'
    """
    if not text:
        return ""
    return _HTML_TAG_PATTERN.sub("", text)


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    Collapses multiple whitespace characters (spaces, tabs, newlines)
    into single spaces and strips leading/trailing whitespace.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace

    Example:
        >>> normalize_whitespace("Hello   world\\n\\ntest")
        'Hello world test'
    """
    if not text:
        return ""
    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def strip_html_and_normalize(text: str) -> str:
    """
    Strip HTML tags and normalize whitespace in one operation.

    Combines strip_html and normalize_whitespace for common use case
    of converting HTML to clean plain text.

    Args:
        text: HTML content to process

    Returns:
        Plain text with tags removed and whitespace normalized

    Example:
        >>> strip_html_and_normalize("<p>Hello</p>\\n<p>World</p>")
        'Hello World'
    """
    return normalize_whitespace(strip_html(text))


def truncate_at_sentence(text: str, length: int = 160, min_ratio: float = 0.6) -> str:
    """
    Truncate text at a sentence boundary.

    Attempts to find a sentence ending (. ! ?) before the length limit.
    If no suitable boundary is found within min_ratio of the length,
    falls back to word boundary truncation with ellipsis.

    Args:
        text: Text to truncate
        length: Maximum length (default 160 for meta descriptions)
        min_ratio: Minimum acceptable length ratio (default 0.6 = 60%)

    Returns:
        Truncated text, possibly with ellipsis

    Example:
        >>> truncate_at_sentence("Hello world. This is a test.", 20)
        'Hello world.'
        >>> truncate_at_sentence("Hello world this is a test", 15)
        'Hello world...'
    """
    if not text:
        return ""

    if len(text) <= length:
        return text

    truncated = text[:length]

    # Try to find sentence boundary
    sentence_end = max(
        truncated.rfind(". "),
        truncated.rfind("! "),
        truncated.rfind("? "),
    )

    min_length = int(length * min_ratio)
    if sentence_end > min_length:
        return truncated[: sentence_end + 1].strip()

    # Fall back to word boundary
    return truncate_at_word(text, length)


# Trailing markdown syntax that would look broken in excerpt (**, *, _, `, [, etc.)
_ORPHAN_ENDINGS = ("**", "*", "__", "_", "``", "`", "[", "![")


def _strip_trailing_orphan_markdown(text: str) -> str:
    """Remove trailing orphaned markdown syntax so excerpt doesn't end mid-token."""
    if not text:
        return text
    stripped = text.rstrip()
    while stripped:
        orphan_len = 0
        for s in _ORPHAN_ENDINGS:
            if stripped.endswith(s):
                orphan_len = len(s)
                break
        if orphan_len and orphan_len < len(stripped):
            char_before = stripped[-(orphan_len + 1)]
            if char_before.isspace():
                last_space = stripped.rfind(" ")
                if last_space > 0:
                    stripped = stripped[:last_space].rstrip()
                else:
                    break
            else:
                break
        else:
            break
    return stripped


def truncate_at_word(text: str, length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text at a word boundary.

    Finds the last space before the length limit to avoid cutting
    words in half. Adds ellipsis if truncated. The final result
    (including suffix) will not exceed the specified length.

    Args:
        text: Text to truncate
        length: Maximum total length including suffix (default 200 for excerpts)
        suffix: Suffix to append if truncated (default "...")

    Returns:
        Truncated text with ellipsis if truncated, never exceeding length

    Example:
        >>> truncate_at_word("Hello world test", 12)
        'Hello...'
    """
    if not text:
        return ""

    if len(text) <= length:
        return text

    # Account for suffix length so total stays within length
    suffix_len = len(suffix)
    max_content_len = length - suffix_len

    if max_content_len <= 0:
        return suffix[:length]

    truncated = text[:max_content_len]

    # Find last space
    last_space = truncated.rfind(" ")
    result = truncated[:last_space].strip() if last_space > 0 else truncated.strip()

    # Avoid ending with orphaned markdown (**, *, _, etc.)
    result = _strip_trailing_orphan_markdown(result)
    return result + suffix
