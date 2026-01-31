"""
Path and URL resolution utilities for autodoc.

Provides functions for resolving file paths, URL paths, and template directories.

Functions:
- resolve_cli_url_path: Convert CLI command names to URL paths
- format_source_file_for_display: Normalize paths for GitHub links
- get_template_dir_for_type: Map page types to template directories

"""

from __future__ import annotations

from pathlib import Path


def resolve_cli_url_path(qualified_name: str) -> str:
    """
    Resolve CLI qualified name to a URL path by dropping the root command.

    This ensures that CLI documentation paths are concise and don't redundantly
    include the tool name (e.g., /cli/build instead of /cli/bengal/build).

    Args:
        qualified_name: Dotted qualified name from Click/Typer (e.g. 'bengal.build')

    Returns:
        Slash-separated path relative to CLI prefix

    Example:
            >>> resolve_cli_url_path("bengal.build")
            'build'
            >>> resolve_cli_url_path("bengal.site.new")
            'site/new'
            >>> resolve_cli_url_path("bengal")
            ''

    """
    if not qualified_name:
        return ""

    parts = qualified_name.split(".")
    if len(parts) > 1:
        # Drop the first part (the root CLI name, e.g. "bengal")
        return "/".join(parts[1:])

    # This is the root group itself
    return ""


def format_source_file_for_display(source_file: Path | str | None, root_path: Path) -> str | None:
    """
    Normalize source_file paths for GitHub links.

    Converts source file paths to repository-relative POSIX paths suitable
    for constructing GitHub blob URLs.

    Strategy:
        1. If path is relative, keep as-is (already repo-relative)
        2. If absolute, try to make relative to repo root (root_path.parent)
        3. Fall back to site root (root_path)
        4. If neither works, return POSIX-ified absolute path

    Args:
        source_file: Path to source file (absolute or relative)
        root_path: Site root path (typically the site/ directory within a repo)

    Returns:
        Repository-relative POSIX path, or None if source_file is None

    Example:
            >>> # Site root: /home/user/myproject/site
            >>> # Source: /home/user/myproject/mypackage/core/module.py
            >>> format_source_file_for_display(source, site_root)
            'mypackage/core/module.py'

    """
    if not source_file:
        return None

    source_path = Path(source_file)

    # If already relative, assume it's repo-relative and return as POSIX
    if not source_path.is_absolute():
        return source_path.as_posix()

    # Resolve to handle any symlinks or relative components
    source_path = source_path.resolve()

    # Try repo root first (parent of site root), then site root
    # This handles typical layouts where site/ is inside the repo
    for base in (root_path.parent.resolve(), root_path.resolve()):
        try:
            return source_path.relative_to(base).as_posix()
        except ValueError:
            continue

    # Fallback: return absolute POSIX path
    # This shouldn't happen in normal use but handles edge cases
    return source_path.as_posix()


def get_template_dir_for_type(page_type: str) -> str:
    """
    Map page types to template directories.

    Page types control CSS styling via data-type attribute, but templates are
    organized in different directories. This function maps the page type to
    the appropriate template directory.

    Args:
        page_type: The page type (e.g., 'autodoc-python', 'autodoc-cli', 'autodoc-rest')

    Returns:
        Template directory name (e.g., 'autodoc/python', 'autodoc/cli', 'api-hub')

    Example:
            >>> get_template_dir_for_type("autodoc-python")
            'autodoc/python'
            >>> get_template_dir_for_type("autodoc-hub")
            'api-hub'

    """
    # Map standardized page types to template directories
    type_to_template = {
        "autodoc-python": "autodoc/python",
        "autodoc-cli": "autodoc/cli",
        "autodoc-rest": "autodoc/openapi",
        "autodoc-hub": "api-hub",
    }
    return type_to_template.get(page_type, page_type)
