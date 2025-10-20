"""
Utility functions for autodoc system.

Provides text sanitization and common helpers for all extractors.
"""


from __future__ import annotations

import re
import textwrap


def sanitize_text(text: str | None) -> str:
    """
    Clean user-provided text for markdown generation.

    This function is the single source of truth for text cleaning across
    all autodoc extractors. It prevents common markdown rendering issues by:

    - Removing leading/trailing whitespace
    - Dedenting indented blocks (prevents accidental code blocks)
    - Normalizing line endings
    - Collapsing excessive blank lines

    Args:
        text: Raw text from docstrings, help text, or API specs

    Returns:
        Cleaned text safe for markdown generation

    Example:
        >>> text = '''
        ...     Indented docstring text.
        ...
        ...     More content here.
        ... '''
        >>> sanitize_text(text)
        'Indented docstring text.\\n\\nMore content here.'
    """
    if not text:
        return ""

    # Dedent to remove common leading whitespace
    # This prevents "    text" from becoming a code block in markdown
    text = textwrap.dedent(text)

    # Strip leading/trailing whitespace
    text = text.strip()

    # Normalize line endings (Windows → Unix)
    text = text.replace("\r\n", "\n")

    # Collapse multiple blank lines to maximum of 2
    # (2 blank lines = paragraph break in markdown, more is excessive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, adding suffix if truncated.

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 200)
        suffix: Suffix to add if truncated (default: '...')

    Returns:
        Truncated text

    Example:
        >>> truncate_text('A very long description here', max_length=20)
        'A very long descr...'
    """
    if len(text) <= max_length:
        return text

    # Find last space before max_length to avoid breaking words
    truncate_at = text.rfind(" ", 0, max_length - len(suffix))
    if truncate_at == -1:
        truncate_at = max_length - len(suffix)

    return text[:truncate_at].rstrip() + suffix
