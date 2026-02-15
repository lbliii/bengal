"""Cross-reference and link resolution utilities.

Lightweight module for resolving page references from xref_index.
No dependency on rendering pipeline, kida, or template engines.

Used by: cards directive, cards_utils, and any code that needs to resolve
links (id:, path:, slug:, ./, ../) to page objects or URLs.
"""

from __future__ import annotations

from typing import Any

from bengal.utils.paths.url_normalization import clean_md_path

__all__ = ["resolve_link_to_url_and_page", "resolve_page"]


def resolve_page(
    xref_index: dict[str, Any],
    link: str,
    current_page_dir: str | None = None,
) -> Any:
    """Resolve a link to a page object.

    Handles:
    - id:page-id -> by_id lookup
    - path:/docs/page/ -> by_path lookup (strips path: prefix)
    - slug:page-slug -> by_slug lookup
    - ./child, ../sibling -> relative resolution with current_page_dir
    - docs/guides/page -> by_path (implicit path)
    - slug-only -> by_slug (implicit slug)

    Args:
        xref_index: Cross-reference index with by_id, by_path, by_slug
        link: Link string (may include id:, path:, slug: prefix)
        current_page_dir: Content-relative directory for ./ and ../

    Returns:
        Page object or None if not found
    """
    if not link:
        return None

    # Relative paths (./ and ../)
    if link.startswith(("./", "../")):
        if not current_page_dir:
            return None
        clean_link = link.replace(".md", "").rstrip("/")
        if clean_link.startswith("./"):
            resolved_path = f"{current_page_dir}/{clean_link[2:]}"
        else:
            parts = current_page_dir.split("/")
            up_count = 0
            remaining = clean_link
            while remaining.startswith("../"):
                up_count += 1
                remaining = remaining[3:]
            if up_count < len(parts):
                parent = "/".join(parts[:-up_count]) if up_count > 0 else current_page_dir
                resolved_path = f"{parent}/{remaining}" if remaining else parent
            else:
                resolved_path = remaining
        return xref_index.get("by_path", {}).get(resolved_path)

    # Explicit prefixes
    if link.startswith("id:"):
        return xref_index.get("by_id", {}).get(link[3:])
    if link.startswith("path:"):
        page_path = link[5:].strip("/")
        return xref_index.get("by_path", {}).get(page_path)
    if link.startswith("slug:"):
        pages = xref_index.get("by_slug", {}).get(link[5:], [])
        return pages[0] if pages else None

    # Implicit path (contains / or ends with .md)
    if "/" in link or link.endswith(".md"):
        clean_path = clean_md_path(link)
        return xref_index.get("by_path", {}).get(clean_path)

    # Implicit slug
    pages = xref_index.get("by_slug", {}).get(link, [])
    return pages[0] if pages else None


def resolve_link_to_url_and_page(
    xref_index: dict[str, Any],
    link: str,
    current_page_dir: str | None = None,
) -> tuple[str, Any]:
    """Resolve a link to (url, page) tuple.

    Pass-through for external URLs and absolute paths (returns link as-is).
    Otherwise delegates to resolve_page and returns (page.href, page) or
    (link, None) if not found.

    Args:
        xref_index: Cross-reference index
        link: Link string
        current_page_dir: Content-relative directory for ./ and ../

    Returns:
        Tuple of (resolved_url, page_or_none)
    """
    if not link:
        return "", None

    # Pass-through: external URLs, absolute paths
    if link.startswith(("http://", "https://", "//", "mailto:", "tel:")):
        return link, None
    if link.startswith("/"):
        return link, None

    page = resolve_page(xref_index, link, current_page_dir)
    if page:
        url = getattr(page, "href", None) or getattr(page, "url", "")
        return url, page
    return link, None
