"""
Module name inference and path resolution for Python files.

Provides utilities for:
- Inferring qualified module names from file paths
- Computing relative source paths for GitHub links
- Generating output paths for documentation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.autodoc.base import DocElement
from bengal.autodoc.utils import apply_grouping
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def infer_module_name(file_path: Path, source_root: Path | None) -> str:
    """
    Infer module name from file path relative to source root.

    Examples:
        source_root: bengal/
        file_path: bengal/cli/commands/build.py
        result: bengal.cli.commands.build

    Args:
        file_path: Path to the Python file
        source_root: Root directory of the source tree

    Returns:
        Qualified module name (e.g., "bengal.cli.commands.build")
    """
    # Resolve file_path to handle relative paths correctly
    resolved_file = file_path.resolve()

    if source_root is None:
        # Fallback to old behavior if source root not set
        parts = list(resolved_file.parts)
        package_start = 0
        for i in range(len(parts) - 1, -1, -1):
            parent = Path(*parts[: i + 1])
            if (parent / "__init__.py").exists():
                package_start = i
                break
        module_parts = parts[package_start:]
    else:
        # Use source root to compute relative path
        try:
            rel_path = resolved_file.relative_to(source_root)
            module_parts = list(rel_path.parts)
        except ValueError:
            # File not under source root - find package root via __init__.py
            logger.debug(
                "file_not_under_source_root",
                file=str(resolved_file),
                source_root=str(source_root),
            )
            parts = list(resolved_file.parts)
            package_start = 0
            for i in range(len(parts) - 1, -1, -1):
                parent = Path(*parts[: i + 1])
                if (parent / "__init__.py").exists():
                    package_start = i
                    break
            module_parts = parts[package_start:]

    # Handle __init__.py (package) vs regular module
    if module_parts and module_parts[-1] == "__init__.py":
        module_parts = module_parts[:-1]
    elif module_parts and module_parts[-1].endswith(".py"):
        module_parts[-1] = module_parts[-1][:-3]

    # If module_parts is empty (root __init__.py), use source_root name
    if not module_parts and source_root:
        module_parts = [source_root.name]

    return ".".join(module_parts)


def get_relative_source_path(file_path: Path, source_root: Path | None) -> Path:
    """
    Get source path relative to source root for GitHub links.

    Args:
        file_path: Absolute file path
        source_root: Root directory of the source tree

    Returns:
        Path relative to source root (e.g., "bengal/core/page.py")
    """
    if source_root:
        for base in (source_root, source_root.parent):
            try:
                return file_path.relative_to(base)
            except ValueError:
                continue
    return file_path


def get_output_path(
    element: DocElement,
    config: dict[str, Any],
    grouping_config: dict[str, Any],
) -> Path | None:
    """
    Get output path for a DocElement.

    Packages (modules from __init__.py) generate _index.md files to act as
    section indexes. With grouping enabled, modules are organized under
    group directories based on package hierarchy or explicit configuration.

    Examples (without grouping):
        bengal (package) → bengal/_index.md
        bengal.core (package) → bengal/core/_index.md
        bengal.core.site (module) → bengal/core/site.md

    Examples (with grouping, strip_prefix="bengal."):
        bengal.core (package) → core/_index.md
        bengal.cli.templates.blog (module) → templates/blog.md

    Args:
        element: DocElement to get path for
        config: Extractor configuration
        grouping_config: Grouping configuration from _init_grouping()

    Returns:
        Path object for output location, or None if element should be skipped
    """
    qualified_name = element.qualified_name

    # Apply strip_prefix if configured
    strip_prefix = config.get("strip_prefix", "")
    if strip_prefix:
        # Check if this is the stripped prefix itself
        # (e.g., "mypackage" when strip_prefix="mypackage.")
        strip_prefix_base = strip_prefix.rstrip(".")
        if qualified_name == strip_prefix_base:
            # Don't generate output for the stripped prefix package itself
            return None

        # Strip the prefix if present
        if qualified_name.startswith(strip_prefix):
            qualified_name = qualified_name[len(strip_prefix) :]

    # Apply grouping
    group_name, remaining = apply_grouping(qualified_name, grouping_config)

    if element.element_type == "module":
        # Check if this is a package (__init__.py file)
        is_package = element.source_file and element.source_file.name == "__init__.py"

        if is_package:
            # Packages get _index.md to act as section indexes
            if group_name:
                # Grouped: {group}/{remaining}/_index.md
                if remaining:
                    path = Path(group_name) / remaining.replace(".", "/")
                else:
                    # Package is the group itself
                    path = Path(group_name)
                return path / "_index.md"
            else:
                # Ungrouped: {qualified_name}/_index.md
                module_path = remaining.replace(".", "/")
                return Path(module_path) / "_index.md"
        else:
            # Regular modules get their own file
            if group_name:
                # Grouped: {group}/{remaining}.md
                if remaining:
                    return Path(group_name) / f"{remaining.replace('.', '/')}.md"
                else:
                    # Module is the group itself
                    return Path(f"{group_name}.md")
            else:
                # Ungrouped: {qualified_name}.md
                return Path(f"{remaining.replace('.', '/')}.md")
    else:
        # Classes/functions are part of module file
        # Use the already-processed qualified_name (with strip_prefix applied)
        parts = remaining.split(".") if group_name is None else qualified_name.split(".")
        module_parts = parts[:-1] if len(parts) > 1 else parts

        # If we have a group, the remaining is already module-relative
        if group_name:
            # Build path from remaining (minus class/function name)
            if len(remaining.split(".")) > 1:
                module_path = ".".join(remaining.split(".")[:-1])
                return Path(group_name) / f"{module_path.replace('.', '/')}.md"
            else:
                # Class/function at group root
                return Path(f"{group_name}.md")
        else:
            # No grouping - use qualified_name directly
            module_path = ".".join(module_parts)
            return Path(f"{module_path.replace('.', '/')}.md")
