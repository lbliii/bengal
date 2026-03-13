"""
Link resolution utilities for validation.

Pure functions for resolving relative links against page URLs during
link validation. Consolidates logic from bengal/health/validators/links.py.

Used by: bengal/health/validators/links.py
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin

from bengal.utils.paths.url_normalization import split_url_path


def parent_url_from_page_url(page_url: str) -> str:
    """
    Base URL for sibling link resolution (parent of page).

    For sibling links like ./directives/ from .../versioning/directives/,
    base must be .../versioning/ so ./directives/ resolves correctly.
    Using page URL as base would give .../directives/directives/ (broken).

    Args:
        page_url: Page URL (e.g. "content/docs/content/versioning/directives/")

    Returns:
        Parent directory URL with trailing slash

    Examples:
        >>> parent_url_from_page_url("content/docs/versioning/directives/")
        'content/docs/versioning/'
        >>> parent_url_from_page_url("single/")
        'single/'
    """
    parts = split_url_path(page_url)
    prefix = "/" if page_url.startswith("/") else ""
    if len(parts) > 1:
        return prefix + "/".join(parts[:-1]) + "/"
    return page_url if page_url.endswith("/") else page_url + "/"


def base_url_for_relative_link(page_url: str, source_path: str | Path | None = None) -> str:
    """
    Pick the correct base URL for resolving a relative internal link.

    Section index pages (`_index.md`) own a directory URL, so `./child/` should
    resolve from the page URL itself. Regular pages map to a leaf URL, so
    sibling links must resolve from the parent section URL instead.

    Args:
        page_url: URL of page containing the link
        source_path: Source content path for the page, when available

    Returns:
        Base URL to pass to `urljoin`
    """
    if source_path is not None and Path(source_path).name == "_index.md":
        return page_url if page_url.endswith("/") else page_url + "/"
    return parent_url_from_page_url(page_url)


def resolve_internal_link(
    page_url: str, link_path: str, source_path: str | Path | None = None
) -> str:
    """
    Resolve relative link against parent of page URL; normalize for matching.

    Strips fragment, resolves via urljoin against parent base, then normalizes
    .md/_index.md/index.md to clean URL form for page URL index lookup.

    Args:
        page_url: URL of page containing the link
        link_path: Relative path from parsed link (e.g. "./directives/", "sibling.md")
        source_path: Source content path for the page, when available

    Returns:
        Resolved path normalized for URL matching (no .md, no fragment)
    """
    base_url = base_url_for_relative_link(page_url, source_path)
    resolved = urljoin(base_url, link_path)

    # Strip fragment for URL matching
    resolved_path = resolved.split("#")[0] if "#" in resolved else resolved

    # Normalize .md extensions for clean URL matching
    if resolved_path.endswith(".md"):
        if resolved_path.endswith("/_index.md"):
            resolved_path = resolved_path[:-10]
            if not resolved_path:
                resolved_path = "/"
        elif resolved_path.endswith("/index.md"):
            resolved_path = resolved_path[:-9]
            if not resolved_path:
                resolved_path = "/"
        else:
            resolved_path = resolved_path[:-3]

    return resolved_path


def resolved_path_url_variants(resolved: str) -> list[str]:
    """
    URL variants for flexible matching against page URL index.

    Page URLs may have or omit trailing slashes; return all common forms.

    Args:
        resolved: Resolved path (e.g. "content/docs/versioning/directives")

    Returns:
        List of variants: [resolved, rstrip/, rstrip/+ /]
    """
    return [
        resolved,
        resolved.rstrip("/"),
        resolved.rstrip("/") + "/",
    ]
