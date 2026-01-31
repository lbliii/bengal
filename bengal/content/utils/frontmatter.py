"""
Frontmatter parsing utilities.

Provides unified frontmatter parsing for all content sources with graceful
error handling and YAML syntax recovery.
"""

from __future__ import annotations

from typing import Any

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from content.

    Handles:
    - Valid frontmatter between --- delimiters
    - Missing frontmatter (returns empty dict)
    - Invalid YAML (logs warning, returns empty dict)

    Args:
        content: Raw file content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, body content)

    Example:
        >>> content = '''---
        ... title: Hello
        ... ---
        ... # Body content
        ... '''
        >>> meta, body = parse_frontmatter(content)
        >>> meta['title']
        'Hello'
        >>> body
        '# Body content'

    """
    if not content.startswith("---"):
        return {}, content

    try:
        # Find end of frontmatter
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return {}, content

        frontmatter_str = content[3:end_idx].strip()
        body = content[end_idx + 3 :].strip()

        # Parse YAML
        import yaml

        frontmatter = yaml.safe_load(frontmatter_str) or {}
        return frontmatter, body

    except Exception as e:
        from bengal.errors import BengalContentError, ErrorCode, record_error

        # Record but continue - graceful degradation
        error = BengalContentError(
            "Failed to parse frontmatter in content",
            code=ErrorCode.N001,
            suggestion="Check YAML syntax in frontmatter block",
            original_error=e,
        )
        record_error(error)
        logger.warning(f"Failed to parse frontmatter: {e}")
        return {}, content


def extract_content_skip_frontmatter(file_content: str) -> str:
    """
    Extract content, skipping broken frontmatter section.

    Use this when frontmatter parsing failed but you still want the content.
    Frontmatter is between --- delimiters at start of file.

    Args:
        file_content: Full file content

    Returns:
        Content without frontmatter section

    Example:
        >>> content = '''---
        ... title: broken: yaml: here
        ... ---
        ... # Actual content
        ... '''
        >>> extract_content_skip_frontmatter(content)
        '# Actual content'

    """
    # Check if file starts with frontmatter delimiter
    if not file_content.startswith("---"):
        return file_content.strip()

    parts = file_content.split("---", 2)

    if len(parts) >= 3:
        # Normal case: parts[0] is empty (before first ---),
        # parts[1] is frontmatter, parts[2] is content
        return parts[2].strip()
    elif len(parts) == 2:
        # Edge case: File starts with --- but has no closing ---
        # parts[0] is empty, parts[1] is everything after the first ---
        # Since there's no closing delimiter, treat the whole thing as content
        return parts[1].strip()
    else:
        return file_content.strip()
