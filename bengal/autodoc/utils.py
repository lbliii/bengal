"""
Utility functions for autodoc system.

Provides text sanitization and common helpers for all extractors.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any


def _convert_sphinx_roles(text: str) -> str:
    """
    Convert Sphinx-style cross-reference roles to inline code.

    Handles common Sphinx roles:
    - :class:`ClassName` or :class:`~module.ClassName` → `ClassName`
    - :func:`function_name` → `function_name()`
    - :meth:`method_name` → `method_name()`
    - :mod:`module_name` → `module_name`
    - :attr:`attribute_name` → `attribute_name`
    - :exc:`ExceptionName` → `ExceptionName`

    Args:
        text: Text containing Sphinx roles

    Returns:
        Text with roles converted to inline code

    Example:
        >>> _convert_sphinx_roles("Use :class:`~bengal.core.Site` class")
        'Use `Site` class'
    """
    # Pattern: :role:`~module.path.ClassName` or :role:`ClassName`
    # The ~ prefix means "show only the last component"
    # Add leading space to prevent running into previous word (markdown collapses multiple spaces)

    # :class:`~module.ClassName` → `ClassName`
    # :class:`ClassName` → `ClassName`
    text = re.sub(r":class:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :func:`function_name` → `function_name()`
    text = re.sub(r":func:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1()`", text)

    # :meth:`method_name` → `method_name()`
    text = re.sub(r":meth:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1()`", text)

    # :mod:`module.name` → `module.name` (keep full module path)
    text = re.sub(r":mod:`~?([a-zA-Z0-9_.]+)`", r" `\1`", text)

    # :attr:`attribute_name` → `attribute_name`
    text = re.sub(r":attr:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :exc:`ExceptionName` → `ExceptionName`
    text = re.sub(r":exc:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :const:`CONSTANT_NAME` → `CONSTANT_NAME`
    text = re.sub(r":const:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :data:`variable_name` → `variable_name`
    text = re.sub(r":data:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

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

    # Convert Sphinx-style cross-references to inline code
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


def auto_detect_prefix_map(source_dirs: list[Path], strip_prefix: str = "") -> dict[str, str]:
    """
    Auto-detect grouping from __init__.py hierarchy.

    Scans source directories for packages (dirs with __init__.py) and
    builds a prefix map. Only top-level packages (direct children after
    strip_prefix) become groups.

    Args:
        source_dirs: Directories to scan for packages
        strip_prefix: Optional prefix to strip from module names

    Returns:
        Prefix map: {"package": "group_name"}

    Example:
        >>> auto_detect_prefix_map([Path("bengal")], "bengal.")
        {
            "cli": "cli",
            "core": "core",
            "cache": "cache",
            # Note: cli.commands, cli.templates NOT here (nested under cli)
        }
    """
    prefix_map = {}

    for source_dir in source_dirs:
        # Ensure source_dir is a Path
        if not isinstance(source_dir, Path):
            source_dir = Path(source_dir)

        # Skip if directory doesn't exist
        if not source_dir.exists() or not source_dir.is_dir():
            continue

        # Find all __init__.py files
        for init_file in source_dir.rglob("__init__.py"):
            package_dir = init_file.parent

            # Skip if outside source_dir (shouldn't happen with rglob)
            try:
                rel_path = package_dir.relative_to(source_dir)
            except ValueError:
                # Not relative to source_dir, skip
                continue

            # Build module name from path
            module_parts = list(rel_path.parts)
            if not module_parts:
                # Root __init__.py, skip
                continue

            module_name = ".".join(module_parts)

            # Strip prefix if configured
            if strip_prefix and module_name.startswith(strip_prefix):
                module_name = module_name[len(strip_prefix) :]

            # Skip if empty after stripping
            if not module_name:
                continue

            # ONLY add top-level packages (no dots in the name after stripping)
            # This ensures cli.commands doesn't become its own group
            if "." not in module_name:
                group_name = module_parts[-1]
                prefix_map[module_name] = group_name

    return prefix_map


def apply_grouping(qualified_name: str, config: dict[str, Any]) -> tuple[str | None, str]:
    """
    Apply grouping config to qualified module name.

    Args:
        qualified_name: Full module name (e.g., "bengal.cli.templates.blog")
        config: Grouping config dict with mode and prefix_map

    Returns:
        Tuple of (group_name, remaining_path):
        - group_name: Top-level group (or None if no grouping)
        - remaining_path: Path after group prefix

    Example:
        >>> apply_grouping("bengal.cli.templates.blog", {
        ...     "mode": "auto",
        ...     "prefix_map": {"cli.templates": "templates"}
        ... })
        ("templates", "blog")
    """
    mode = config.get("mode", "off")

    # Mode "off" - no grouping
    if mode == "off":
        return None, qualified_name

    # Get prefix map (already built for auto mode, provided for explicit)
    prefix_map = config.get("prefix_map", {})
    if not prefix_map:
        return None, qualified_name

    # Find longest matching prefix
    # Check for exact match first (package is the group itself)
    if qualified_name in prefix_map:
        return prefix_map[qualified_name], ""

    # Find longest matching parent prefix
    best_match = None
    best_length = 0

    for prefix in prefix_map:
        # Check if qualified_name starts with this prefix (dot-separated)
        # Only match parent packages (not exact matches, handled above)
        if qualified_name.startswith(prefix + "."):
            prefix_length = len(prefix)
            if prefix_length > best_length:
                best_match = prefix
                best_length = prefix_length

    if not best_match:
        return None, qualified_name

    # Extract group and remaining path
    group_name = prefix_map[best_match]
    remaining = qualified_name[len(best_match) :].lstrip(".")

    return group_name, remaining
