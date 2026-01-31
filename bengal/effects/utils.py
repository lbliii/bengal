"""
Shared utilities for the effects package.

Provides common operations used across effect modules:
- Content hashing for change detection
- Frontmatter extraction from markdown
- Type-safe frozenset conversions
"""

import hashlib


def compute_content_hash(content: str, prefix_length: int = 16) -> str:
    """
    Compute SHA-256 hash for change detection.

    Args:
        content: Raw content string
        prefix_length: Number of hex chars to return (default 16)

    Returns:
        Truncated SHA-256 hex digest
    """
    return hashlib.sha256(content.encode()).hexdigest()[:prefix_length]


def extract_body_after_frontmatter(content: str) -> str:
    """
    Extract body content after YAML frontmatter.

    Frontmatter is delimited by `---` at the start and end.
    If no frontmatter is present, returns the original content.

    Args:
        content: Raw markdown content (may have --- delimited frontmatter)

    Returns:
        Content after frontmatter, or original if no frontmatter
    """
    if not content.startswith("---"):
        return content

    lines = content.split("\n")
    in_frontmatter = False
    body_start = 0

    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
            else:
                body_start = i + 1
                break

    return "\n".join(lines[body_start:])


def frozenset_or_none[T](items: set[T]) -> frozenset[T] | None:
    """
    Convert set to frozenset, or None if empty.

    Useful for optional frozenset parameters that should be None
    rather than an empty frozenset when no items are present.

    Args:
        items: Set to convert

    Returns:
        frozenset if items is non-empty, None otherwise
    """
    return frozenset(items) if items else None
