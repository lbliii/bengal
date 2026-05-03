"""URL resolution helpers for rendered internal references."""

from __future__ import annotations

from urllib.parse import urljoin

from bengal.utils.paths.url_normalization import split_url_path


def base_url_from_page_url(page_url: str) -> str:
    """
    Return the browser-style base URL for resolving links from a page URL.

    Directory-style URLs ending in ``/`` resolve relative links within that
    directory. File-style URLs resolve relative links against their parent.
    """
    if page_url.endswith("/"):
        return page_url
    parts = split_url_path(page_url)
    prefix = "/" if page_url.startswith("/") else ""
    if len(parts) > 1:
        return prefix + "/".join(parts[:-1]) + "/"
    return prefix


def resolve_internal_link(page_url: str, link_path: str) -> str:
    """
    Resolve an internal link path against a rendered page URL.

    The result is normalized for lookup in Bengal's rendered URL registry:
    fragments are stripped and markdown source suffixes are converted to clean
    output URL form.
    """
    resolved = urljoin(base_url_from_page_url(page_url), link_path)
    resolved_path = resolved.split("#")[0] if "#" in resolved else resolved

    if resolved_path.endswith(".md"):
        if resolved_path.endswith("/_index.md"):
            resolved_path = resolved_path[:-10] or "/"
        elif resolved_path.endswith("/index.md"):
            resolved_path = resolved_path[:-9] or "/"
        else:
            resolved_path = resolved_path[:-3]

    return resolved_path


def resolved_path_url_variants(resolved: str) -> tuple[str, str, str]:
    """Return slash variants for URL registry lookup."""
    stripped = resolved.rstrip("/")
    if not stripped:
        return (resolved, "/", "/")
    return (resolved, stripped, stripped + "/")
