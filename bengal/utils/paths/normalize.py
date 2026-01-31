"""
Path normalization utilities for cross-platform compatibility.

Provides consistent POSIX-style path handling across Windows and Unix systems.
This is critical for Bengal because paths are used as dictionary keys, manifest
lookups, and URL generation where consistency across platforms is required.

Example:
    >>> from bengal.utils.paths.normalize import to_posix
    >>> to_posix("css\\style.css")
    'css/style.css'
    >>> to_posix(Path("assets/js/main.js"))
    'assets/js/main.js'

Related Modules:
- bengal/assets/manifest.py: Uses for asset path normalization
- bengal/assets/js_bundler.py: Uses for bundle path handling

"""

from __future__ import annotations

from pathlib import Path, PurePosixPath


def to_posix(path: str | Path) -> str:
    """
    Normalize a path to POSIX format (forward slashes).

    Converts backslashes to forward slashes for cross-platform portability.
    This ensures consistent path strings for use as dictionary keys, manifest
    entries, and URL components.

    Args:
        path: Path string (potentially with backslashes) or Path object.

    Returns:
        POSIX-style path string with forward slashes only.

    Examples:
        >>> to_posix("css\\style.css")
        'css/style.css'
        >>> to_posix(Path("assets/js/main.js"))
        'assets/js/main.js'
        >>> to_posix("already/posix/path")
        'already/posix/path'

    Note:
        For Path objects, uses the efficient `as_posix()` method.
        For strings, uses PurePosixPath for proper parsing.

    """
    if isinstance(path, Path):
        return path.as_posix()
    return PurePosixPath(path).as_posix()
