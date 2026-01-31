"""
Internal file discovery utilities for asset processing.

Provides shared file discovery logic used by js_bundler and pipeline modules.
This is an internal module (prefixed with _) and should not be imported
from outside the bengal.assets package.

"""

from __future__ import annotations

from pathlib import Path

from bengal.utils.paths.normalize import to_posix


def discover_files(
    directories: list[Path],
    extensions: list[str],
    *,
    excluded: set[str] | None = None,
) -> dict[str, Path]:
    """
    Discover files by extension in multiple directories.

    Searches directories recursively for files matching the given extensions.
    Returns a mapping from normalized relative paths to absolute file paths.

    Args:
        directories: Directories to search recursively.
        extensions: File extensions to match (e.g., ['.js', '.ts']).
        excluded: Set of relative paths to skip (POSIX format).

    Returns:
        Dictionary mapping relative POSIX paths to absolute file paths.
        Paths are relative to their containing directory from `directories`.

    Example:
        >>> files = discover_files(
        ...     [Path("assets/js"), Path("themes/default/assets/js")],
        ...     extensions=[".js", ".ts"],
        ...     excluded={"vendor/lib.min.js"},
        ... )
        >>> files
        {'utils.js': Path('.../utils.js'), 'core/theme.js': Path('.../theme.js')}

    """
    excluded = excluded or set()
    all_files: dict[str, Path] = {}

    for directory in directories:
        if not directory.exists():
            continue
        for ext in extensions:
            # Normalize extension to include dot
            ext_pattern = ext if ext.startswith(".") else f".{ext}"
            for file_path in directory.rglob(f"*{ext_pattern}"):
                if not file_path.is_file():
                    continue
                rel_path_str = to_posix(file_path.relative_to(directory))
                if rel_path_str not in excluded:
                    all_files[rel_path_str] = file_path

    return all_files


def order_files(
    files: dict[str, Path],
    order_hint: list[str],
    *,
    excluded: set[str] | None = None,
    index_by_name: dict[str, Path] | None = None,
) -> list[Path]:
    """
    Order discovered files according to an explicit order hint.

    Files matching the order hint are placed first in that order,
    followed by remaining files in alphabetical order.

    Args:
        files: Dictionary from `discover_files()` mapping paths to Path objects.
        order_hint: Explicit ordering for matched files (relative paths or filenames).
        excluded: Additional paths to exclude during ordering (POSIX format).
        index_by_name: Optional secondary index by filename for backward compatibility.

    Returns:
        List of file paths in the specified order.

    Example:
        >>> files = {'utils.js': Path(...), 'main.js': Path(...), 'lib.js': Path(...)}
        >>> ordered = order_files(files, order_hint=['utils.js', 'main.js'])
        [Path('.../utils.js'), Path('.../main.js'), Path('.../lib.js')]

    """
    excluded = excluded or set()
    index_by_name = index_by_name or {}
    ordered: list[Path] = []
    seen: set[Path] = set()

    # First: files in explicit order
    for name in order_hint:
        # Try relative path first, then filename
        file_path = files.get(name) or index_by_name.get(name)
        if file_path and file_path not in seen:
            # Get canonical relative path for exclusion check
            rel_path_str = next(
                (k for k, v in files.items() if v == file_path),
                name,
            )
            if rel_path_str not in excluded:
                ordered.append(file_path)
                seen.add(file_path)

    # Then: remaining files alphabetically
    for rel_path_str, file_path in sorted(files.items()):
        if file_path not in seen and rel_path_str not in excluded:
            ordered.append(file_path)
            seen.add(file_path)

    return ordered


def unique_paths(paths: list[Path]) -> list[Path]:
    """
    Remove duplicate paths while preserving order.

    Args:
        paths: List of paths that may contain duplicates.

    Returns:
        List of unique paths in original order.

    Example:
        >>> unique_paths([Path('a.js'), Path('b.js'), Path('a.js')])
        [Path('a.js'), Path('b.js')]

    """
    unique: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique
