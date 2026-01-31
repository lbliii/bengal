"""
Path formatting utilities for CLI output.

Provides consistent path formatting, truncation, and display functions
used across CLI commands for user-facing output.

Functions:
    truncate_path: Truncate long paths while keeping filename visible
    format_display_path: Format path based on profile preferences
    resolve_source_path: Resolve and validate source directory path

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


def truncate_path(path: str, max_len: int = 25) -> str:
    """
    Truncate path for display, keeping the filename visible.

    Intelligently truncates long paths by:
    1. Keeping the filename intact when possible
    2. Using ellipsis to indicate truncation
    3. Showing partial directory context when space permits

    Args:
        path: Path string to truncate
        max_len: Maximum length of output string (default: 25)

    Returns:
        Truncated path string, or original if already short enough.

    Example:
        >>> truncate_path("content/docs/guide/getting-started.md", 25)
        '.../guide/getting-started.md'
        >>> truncate_path("readme.md", 25)
        'readme.md'

    """
    if len(path) <= max_len:
        return path

    parts = path.split("/")

    # Single component - truncate the string itself
    if len(parts) == 1:
        return path[: max_len - 3] + "..."

    # Try to keep at least the filename
    filename = parts[-1]

    # Filename alone is too long
    if len(filename) >= max_len - 3:
        return "..." + filename[-(max_len - 3) :]

    # Calculate space for directory context
    remaining = max_len - len(filename) - 4  # 4 for ".../"

    if remaining > 0:
        return ".../" + filename

    return "..." + filename[-(max_len - 3) :]


def format_display_path(
    path: str,
    profile: Any | None = None,
    max_len: int = 60,
) -> str:
    """
    Format path for display based on profile preferences.

    Different profiles have different needs:
    - Writer: Show only filename (minimal detail)
    - Theme-Dev: Show truncated path if too long
    - Developer: Show full path

    Args:
        path: Path string to format
        profile: Build profile (determines verbosity)
        max_len: Maximum length for Theme-Dev truncation

    Returns:
        Formatted path string appropriate for the profile.

    Example:
        >>> format_display_path("/long/path/to/file.md", profile=BuildProfile.WRITER)
        'file.md'
        >>> format_display_path("/long/path/to/file.md", profile=BuildProfile.DEVELOPER)
        '/long/path/to/file.md'

    """
    if not profile:
        return path

    # Get profile name for comparison
    profile_name = (
        profile.__class__.__name__ if hasattr(profile, "__class__") else str(profile)
    )

    # Writer profile: show only filename
    if "WRITER" in profile_name:
        return Path(path).name or path

    # Theme-Dev profile: truncate if too long
    if "THEME" in profile_name and len(path) > max_len:
        parts = path.split("/")
        if len(parts) > 3:
            return f"{parts[0]}/.../{'/'.join(parts[-2:])}"

    # Developer profile: show full path
    return path


def resolve_source_path(source: str) -> Path:
    """
    Resolve source directory path to absolute path.

    Args:
        source: Source directory path (relative or absolute)

    Returns:
        Resolved absolute Path object.

    Example:
        >>> resolve_source_path(".")
        PosixPath('/current/working/directory')
        >>> resolve_source_path("./site")
        PosixPath('/current/working/directory/site')

    """
    return Path(source).resolve()
