"""
Utility functions for autodoc orchestration.

Provides helper functions used across the autodoc orchestration system.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


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

    """
    # Map standardized page types to template directories
    type_to_template = {
        "autodoc-python": "autodoc/python",
        "autodoc-cli": "autodoc/cli",
        "autodoc-rest": "autodoc/openapi",
        "autodoc-hub": "api-hub",
    }
    return type_to_template.get(page_type, page_type)


def normalize_autodoc_config(site_config: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize github repo/branch for autodoc template consumption.

    Mirrors RenderingPipeline._normalize_config for the subset we need
    inside the autodoc orchestrator (owner/repo → https URL, default branch).

    Args:
        site_config: Site configuration dict

    Returns:
        Normalized autodoc config with github_repo and github_branch

    """
    base = {}
    if isinstance(site_config, dict):
        base.update(site_config)
    autodoc_cfg = base.get("autodoc", {}) or {}

    github_repo = base.get("github_repo") or autodoc_cfg.get("github_repo", "")
    if github_repo and not github_repo.startswith(("http://", "https://")):
        github_repo = f"https://github.com/{github_repo}"

    github_branch = base.get("github_branch") or autodoc_cfg.get("github_branch", "main")

    normalized = dict(autodoc_cfg)
    normalized["github_repo"] = github_repo
    normalized["github_branch"] = github_branch
    return normalized


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


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.

    Strips common suffixes (API, Reference, Documentation), converts to lowercase,
    replaces non-alphanumeric characters with hyphens, and collapses multiple hyphens.

    Args:
        text: Text to slugify (e.g., "Commerce API Reference")

    Returns:
        URL-friendly slug (e.g., "commerce"), or "rest" as fallback for empty results

    """
    if not text or not text.strip():
        return "rest"

    slug = text.strip().lower()

    # Strip common suffixes (case-insensitive, already lowercased)
    for suffix in ["api", "reference", "documentation", "docs", "service"]:
        if slug.endswith(f" {suffix}"):
            slug = slug[: -(len(suffix) + 1)]
        elif slug == suffix:
            slug = ""

    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Collapse multiple hyphens and strip leading/trailing hyphens
    slug = re.sub(r"-+", "-", slug).strip("-")

    return slug if slug else "rest"
