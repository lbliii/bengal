"""
Text processing utilities for autodoc.

Provides functions for cleaning, sanitizing, and formatting text
from docstrings, help text, and API specifications.

Functions:
- sanitize_text: Clean text for markdown generation
- truncate_text: Safely truncate long descriptions
- slugify: Convert text to URL-friendly slug
- _convert_sphinx_roles: Convert RST cross-references to markdown (internal)

"""

from __future__ import annotations

import re
import textwrap


def _convert_sphinx_roles(text: str) -> str:
    """
    Convert reStructuredText-style cross-reference roles to inline code.

    Handles common reStructuredText roles:
    - :class:`ClassName` or :class:`~module.ClassName` → `ClassName`
    - :func:`function_name` → `function_name()`
    - :meth:`method_name` → `method_name()`
    - :mod:`module_name` → `module_name`
    - :attr:`attribute_name` → `attribute_name`
    - :exc:`ExceptionName` → `ExceptionName`

    Args:
        text: Text containing reStructuredText roles

    Returns:
        Text with roles converted to inline code

    Example:
            >>> _convert_sphinx_roles("Use :class:`~bengal.core.Site` class")
            'Use `Site` class'

    """
    # Pattern: :role:`~module.path.ClassName` or :role:`ClassName`
    # The ~ prefix means "show only the last component"

    # Helper to convert a single role type
    def convert_role(
        pattern_role: str, text: str, suffix: str = "", keep_full_path: bool = False
    ) -> str:
        if keep_full_path:
            # For :mod: - keep full module path
            pattern = rf":({pattern_role}):`~?([a-zA-Z0-9_.]+)`"
            replacement = rf"`\2`{suffix}"
        else:
            # Extract just the last component (class/function name)
            pattern = rf":({pattern_role}):`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`"
            replacement = rf"`\2`{suffix}"

        return re.sub(pattern, replacement, text)

    # Convert each role type
    text = convert_role("class", text)
    text = convert_role("func", text, suffix="()")
    text = convert_role("meth", text, suffix="()")
    text = convert_role("mod", text, keep_full_path=True)
    text = convert_role("attr", text)
    text = convert_role("exc", text)
    text = convert_role("const", text)
    text = convert_role("data", text)

    return text


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
            'Indented docstring text.\n\nMore content here.'

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

    # Convert reStructuredText-style cross-references to inline code
    # :class:`ClassName` or :class:`~module.ClassName` → `ClassName`
    # :func:`function_name` → `function_name()`
    # :meth:`method_name` → `method_name()`
    # :mod:`module_name` → `module_name`
    text = _convert_sphinx_roles(text)

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


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.

    Strips common suffixes (API, Reference, Documentation), converts to lowercase,
    replaces non-alphanumeric characters with hyphens, and collapses multiple hyphens.

    Args:
        text: Text to slugify (e.g., "Commerce API Reference")

    Returns:
        URL-friendly slug (e.g., "commerce"), or "rest" as fallback for empty results

    Example:
            >>> slugify("Commerce API Reference")
            'commerce'
            >>> slugify("User Service Documentation")
            'user'

    """
    if not text or not text.strip():
        return "rest"

    slug = text.strip().lower()

    # Strip common suffixes (case-insensitive, already lowercased)
    for suffix in ["api", "reference", "documentation", "docs", "service"]:
        if slug.endswith(f" {suffix}"):
            slug = slug[: -(len(suffix) + 1)]
        elif slug == suffix:
            slug = ""

    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Collapse multiple hyphens and strip leading/trailing hyphens
    slug = re.sub(r"-+", "-", slug).strip("-")

    return slug if slug else "rest"
