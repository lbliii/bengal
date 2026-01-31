"""
Shared utilities for Bengal debug tools.

Consolidates common patterns used across debug modules:
- File size formatting
- Status/severity emoji mapping
- File type classification
- String utilities (truncate)
- Nested dict access
- ASCII tree formatting
- Levenshtein distance for typo detection

These utilities are extracted from various debug modules to ensure
consistency and reduce code duplication.

Note:
    For slugification, use ``bengal.utils.primitives.text.slugify`` instead.
    This module focuses on debug-specific utilities.

Example:
    >>> from bengal.debug.utils import format_bytes_human, classify_file
    >>> print(format_bytes_human(2048))
    '2.0 KB'
    >>> print(classify_file("content/post.md"))
    'page'

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any


# =============================================================================
# File Size Formatting
# =============================================================================


def format_bytes_human(size_bytes: int | None) -> str | None:
    """
    Format byte count as human-readable string.

    Converts raw byte counts to compact, human-readable format with
    appropriate unit suffix (B, KB, MB).

    Args:
        size_bytes: File size in bytes, or None.

    Returns:
        Formatted string like "1.5 KB" or "2.3 MB", or None if input is None.

    Examples:
        >>> format_bytes_human(512)
        '512 B'
        >>> format_bytes_human(2048)
        '2.0 KB'
        >>> format_bytes_human(1572864)
        '1.5 MB'
        >>> format_bytes_human(None)
        None

    """
    if size_bytes is None:
        return None
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# =============================================================================
# Emoji Mappings
# =============================================================================

# Status emoji for cache and general status indicators
STATUS_EMOJI: dict[str, str] = {
    "HIT": "✅",
    "STALE": "⚠️",
    "MISS": "❌",
    "UNKNOWN": "❓",
    "hit": "✅",
    "stale": "⚠️",
    "miss": "❌",
    "unknown": "❓",
}

# Severity emoji for findings and issues
SEVERITY_EMOJI: dict[str, str] = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
    "critical": "🔴",
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔴",
}

# Performance indicators
PERFORMANCE_EMOJI: dict[str, str] = {
    "slow": "🐌",
    "fast": "🚀",
}


def get_status_emoji(status: str) -> str:
    """
    Get emoji indicator for a status string.

    Args:
        status: Status string (HIT, MISS, STALE, UNKNOWN, etc.)

    Returns:
        Corresponding emoji, or ❓ if status not recognized.

    Examples:
        >>> get_status_emoji("HIT")
        '✅'
        >>> get_status_emoji("error")
        '❌'

    """
    return STATUS_EMOJI.get(status, STATUS_EMOJI.get(status.upper(), "❓"))


def get_severity_emoji(severity: str) -> str:
    """
    Get emoji indicator for a severity level.

    Args:
        severity: Severity string (info, warning, error, critical).

    Returns:
        Corresponding emoji, or ℹ️ if severity not recognized.

    Examples:
        >>> get_severity_emoji("error")
        '❌'
        >>> get_severity_emoji("WARNING")
        '⚠️'

    """
    return SEVERITY_EMOJI.get(severity, SEVERITY_EMOJI.get(severity.lower(), "ℹ️"))


# =============================================================================
# File Type Classification
# =============================================================================

# File extension to type mapping
FILE_TYPE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "page": (".md", ".markdown", ".rst"),
    "template": (".html", ".jinja2", ".jinja"),
    "data": (".yaml", ".yml", ".json", ".toml"),
    "style": (".css", ".scss", ".sass", ".less"),
    "script": (".js", ".ts", ".mjs"),
    "image": (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"),
}

# File type to emoji icon mapping
FILE_TYPE_ICONS: dict[str, str] = {
    "page": "📄",
    "template": "🎨",
    "partial": "🧩",
    "data": "📊",
    "config": "⚙️",
    "style": "🎭",
    "script": "⚡",
    "image": "🖼️",
    "unknown": "📁",
}


def classify_file(path: str) -> str:
    """
    Classify a file by its type based on extension and path.

    Determines the file type for categorization in dependency graphs,
    reports, and visualizations.

    Args:
        path: File path to classify.

    Returns:
        Type string: "page", "template", "partial", "data", "config",
        "style", "script", or "unknown".

    Examples:
        >>> classify_file("content/post.md")
        'page'
        >>> classify_file("templates/base.html")
        'template'
        >>> classify_file("config/site.yaml")
        'config'

    """
    path_lower = path.lower()

    # Check for partials/includes first (path-based classification)
    if "partial" in path_lower or "include" in path_lower:
        return "partial"

    # Check for config files
    if "config" in path_lower:
        for ext in FILE_TYPE_EXTENSIONS["data"]:
            if path_lower.endswith(ext):
                return "config"

    # Check by extension
    for file_type, extensions in FILE_TYPE_EXTENSIONS.items():
        if path_lower.endswith(extensions):
            return file_type

    # Template check (broader than just extensions)
    if "template" in path_lower:
        return "template"

    return "unknown"


def get_file_icon(path: str) -> str:
    """
    Get emoji icon for a file based on its type.

    Args:
        path: File path to get icon for.

    Returns:
        Emoji icon string.

    Examples:
        >>> get_file_icon("docs/guide.md")
        '📄'
        >>> get_file_icon("templates/page.html")
        '🎨'
        >>> get_file_icon("data/authors.yaml")
        '📊'

    """
    file_type = classify_file(path)
    return FILE_TYPE_ICONS.get(file_type, FILE_TYPE_ICONS["unknown"])


# =============================================================================
# String Utilities
# =============================================================================


def truncate_list(
    items: Sequence[Any],
    max_items: int = 5,
    formatter: str = "... +{count} more",
) -> tuple[list[Any], str | None]:
    """
    Truncate a list with "... +N more" indicator.

    Args:
        items: Sequence of items to potentially truncate.
        max_items: Maximum number of items to include.
        formatter: Format string for the "more" indicator. Must contain {count}.

    Returns:
        Tuple of (truncated_list, more_indicator).
        more_indicator is None if no truncation occurred.

    Examples:
        >>> truncate_list([1, 2, 3, 4, 5, 6, 7], max_items=3)
        ([1, 2, 3], '... +4 more')
        >>> truncate_list([1, 2], max_items=5)
        ([1, 2], None)

    """
    if len(items) <= max_items:
        return list(items), None
    truncated = list(items[:max_items])
    remaining = len(items) - max_items
    more_text = formatter.format(count=remaining)
    return truncated, more_text


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to maximum length with suffix.

    Args:
        text: String to truncate.
        max_length: Maximum length before truncation.
        suffix: Suffix to add when truncated.

    Returns:
        Truncated string with suffix, or original if within limit.

    Examples:
        >>> truncate_string("Hello World", max_length=8)
        'Hello...'
        >>> truncate_string("Short", max_length=10)
        'Short'

    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


# =============================================================================
# Dict Utilities
# =============================================================================


def get_nested_value(data: dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a value from a nested dict using dot-separated path.

    Traverses nested dictionaries using a dot-separated key path.
    Returns default if any key in the path doesn't exist.

    Args:
        data: Dictionary to traverse.
        key_path: Dot-separated path (e.g., "site.config.theme").
        default: Value to return if path not found.

    Returns:
        Value at path, or default if not found.

    Examples:
        >>> data = {"site": {"config": {"theme": "dark"}}}
        >>> get_nested_value(data, "site.config.theme")
        'dark'
        >>> get_nested_value(data, "site.missing", "default")
        'default'

    """
    keys = key_path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def set_nested_value(data: dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set a value in a nested dict using dot-separated path.

    Creates intermediate dictionaries as needed.

    Args:
        data: Dictionary to modify.
        key_path: Dot-separated path (e.g., "site.config.theme").
        value: Value to set at the path.

    Examples:
        >>> data = {}
        >>> set_nested_value(data, "site.config.theme", "dark")
        >>> data
        {'site': {'config': {'theme': 'dark'}}}

    """
    keys = key_path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


# =============================================================================
# String Distance (for typo detection)
# =============================================================================


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein (edit) distance between two strings.

    The Levenshtein distance is the minimum number of single-character
    edits (insertions, deletions, substitutions) needed to transform
    one string into another. Useful for typo detection.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Integer edit distance (0 = identical strings).

    Examples:
        >>> levenshtein_distance("note", "note")
        0
        >>> levenshtein_distance("note", "notee")
        1
        >>> levenshtein_distance("warning", "warnign")
        2

    """
    # Ensure s1 is the longer string for efficiency
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_similar_strings(
    target: str,
    candidates: frozenset[str] | set[str] | list[str],
    max_distance: int = 2,
    max_results: int = 3,
) -> list[str]:
    """
    Find strings similar to target within edit distance.

    Useful for "did you mean?" suggestions when detecting typos.

    Args:
        target: String to find matches for.
        candidates: Collection of valid strings to search.
        max_distance: Maximum Levenshtein distance to consider a match.
        max_results: Maximum number of suggestions to return.

    Returns:
        List of similar strings, sorted alphabetically.

    Examples:
        >>> find_similar_strings("notee", {"note", "warning", "tip"})
        ['note']
        >>> find_similar_strings("xyz", {"note", "warning", "tip"})
        []

    """
    similar = []
    target_lower = target.lower()
    for candidate in candidates:
        distance = levenshtein_distance(target_lower, candidate.lower())
        if distance <= max_distance:
            similar.append(candidate)
    return sorted(similar)[:max_results]


# =============================================================================
# Tree Formatting
# =============================================================================


class TreeFormatter:
    """
    Helper for building ASCII tree representations.

    Provides consistent tree formatting with Unicode box-drawing
    characters for visual hierarchy.

    Attributes:
        BRANCH: Character for non-last items (├─).
        LAST: Character for last item (└─).
        PIPE: Character for continuing vertical line (│ ).
        SPACE: Character for spacing after last item (  ).

    Example:
        >>> fmt = TreeFormatter()
        >>> lines = [fmt.format_item("root", is_last=False, depth=0)]
        >>> lines.append(fmt.format_item("child1", is_last=False, depth=1))
        >>> lines.append(fmt.format_item("child2", is_last=True, depth=1))
        >>> print("\\n".join(lines))
        ├─ root
        │  ├─ child1
        │  └─ child2

    """

    BRANCH = "├─"
    LAST = "└─"
    PIPE = "│  "
    SPACE = "   "

    def __init__(self, indent: str = "   ") -> None:
        """
        Initialize tree formatter.

        Args:
            indent: Base indentation string per level.
        """
        self.indent = indent

    def format_item(
        self,
        text: str,
        is_last: bool = False,
        depth: int = 0,
        prefix: str = "",
    ) -> str:
        """
        Format a single tree item with appropriate connector.

        Args:
            text: Text content of the item.
            is_last: Whether this is the last item at its level.
            depth: Nesting depth (0 = root level).
            prefix: Accumulated prefix from parent levels.

        Returns:
            Formatted line with tree connectors.
        """
        connector = self.LAST if is_last else self.BRANCH
        return f"{prefix}{connector} {text}"

    def get_child_prefix(self, parent_prefix: str, parent_is_last: bool) -> str:
        """
        Get prefix for children based on parent state.

        Args:
            parent_prefix: Prefix used for parent item.
            parent_is_last: Whether parent was the last item.

        Returns:
            Prefix string for child items.
        """
        return parent_prefix + (self.SPACE if parent_is_last else self.PIPE)


def format_tree(
    root_text: str,
    children: list[tuple[str, bool]],
    root_icon: str = "📄",
) -> str:
    """
    Format a simple tree structure as ASCII art.

    Args:
        root_text: Text for the root node.
        children: List of (text, is_last) tuples for child nodes.
        root_icon: Emoji icon for root node.

    Returns:
        Multi-line string with tree representation.

    Example:
        >>> print(format_tree("page.md", [("base.html", False), ("styles.css", True)]))
        📄 page.md
        ├─ base.html
        └─ styles.css

    """
    lines = [f"{root_icon} {root_text}"]
    fmt = TreeFormatter()

    for text, is_last in children:
        lines.append(fmt.format_item(text, is_last=is_last))

    return "\n".join(lines)


# =============================================================================
# Time Formatting
# =============================================================================


def format_time_ms(ms: float, include_unit: bool = True) -> str:
    """
    Format milliseconds as human-readable time.

    Automatically chooses appropriate unit (ms or s).

    Args:
        ms: Time in milliseconds.
        include_unit: Whether to include unit suffix.

    Returns:
        Formatted time string.

    Examples:
        >>> format_time_ms(150.5)
        '151ms'
        >>> format_time_ms(2500)
        '2.50s'

    """
    if abs(ms) < 1000:
        value = f"{ms:.0f}"
        unit = "ms" if include_unit else ""
    else:
        value = f"{ms / 1000:.2f}"
        unit = "s" if include_unit else ""
    return f"{value}{unit}"


def format_time_change(
    ms: float,
    pct: float | None = None,
    threshold_pct: float = 5.0,
) -> str:
    """
    Format a time change with optional percentage and emoji.

    Args:
        ms: Time change in milliseconds (positive = slower).
        pct: Optional percentage change.
        threshold_pct: Percentage threshold for showing emoji indicator.

    Returns:
        Formatted string like "+150ms (+12%) 🐌" or "-50ms (-5%) 🚀"

    Examples:
        >>> format_time_change(150, 12)
        '+150ms (+12%) 🐌'
        >>> format_time_change(-50, -5)
        '-50ms (-5%) 🚀'
        >>> format_time_change(10, 1)
        '+10ms'

    """
    sign = "+" if ms > 0 else ""
    time_str = f"{sign}{format_time_ms(ms)}"

    if pct is not None and abs(pct) >= threshold_pct:
        emoji = PERFORMANCE_EMOJI["slow"] if pct > 0 else PERFORMANCE_EMOJI["fast"]
        return f"{time_str} ({pct:+.0f}%) {emoji}"

    return time_str
