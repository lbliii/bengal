"""
Module grouping utilities for autodoc.

Provides functions for organizing Python modules into documentation groups
based on package hierarchy or explicit configuration.

Functions:
- auto_detect_prefix_map: Scan packages for automatic grouping
- apply_grouping: Map module paths to documentation groups

"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def auto_detect_prefix_map(source_dirs: list[Path], strip_prefix: str = "") -> dict[str, str]:
    """
    Auto-detect grouping from __init__.py hierarchy.

    Scans source directories for packages (directories containing __init__.py)
    and builds a prefix map for every package path. Each entry maps the full
    dotted module path to its slash-separated path relative to the stripped
    prefix (e.g., "scaffolds" → "scaffolds"). Using the full path
    ensures nested packages stay under their parent directories (scaffolds
    lives under scaffolds/).

    Args:
        source_dirs: Directories to scan for packages
        strip_prefix: Optional dotted prefix to remove from detected modules

    Returns:
        Prefix map: {"package.path": "group_path"}

    Example:
            >>> auto_detect_prefix_map([Path("bengal")], "bengal.")
        {
            "cli": "cli",
            "scaffolds": "scaffolds",
            "core": "core",
            "cache": "cache",
        }

    """
    prefix_map: dict[str, str] = {}
    normalized_strip = strip_prefix.rstrip(".") if strip_prefix else ""
    strip_with_dot = f"{normalized_strip}." if normalized_strip else ""

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

            # Strip prefix if configured, respecting dot boundaries
            if normalized_strip:
                if module_name == normalized_strip:
                    continue
                if strip_with_dot and module_name.startswith(strip_with_dot):
                    module_name = module_name[len(strip_with_dot) :]
                elif strip_prefix and module_name.startswith(strip_prefix):
                    # Handles cases where strip_prefix includes additional segments
                    module_name = module_name[len(strip_prefix) :].lstrip(".")

            module_name = module_name.lstrip(".")

            # Skip if empty after stripping
            if not module_name:
                continue

            display_path = module_name.replace(".", "/")
            prefix_map.setdefault(module_name, display_path)

    return prefix_map


def apply_grouping(qualified_name: str, config: dict[str, Any]) -> tuple[str | None, str]:
    """
    Apply grouping config to qualified module name.

    Args:
        qualified_name: Full module name (e.g., "bengal.scaffolds.blog")
        config: Grouping config dict with mode and prefix_map

    Returns:
        Tuple of (group_name, remaining_path):
        - group_name: Top-level group (or None if no grouping)
        - remaining_path: Path after group prefix

    Example:
            >>> apply_grouping("bengal.scaffolds.blog", {
            ...     "mode": "auto",
            ...     "prefix_map": {"scaffolds": "scaffolds"}
            ... })
        ("scaffolds", "blog")

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
