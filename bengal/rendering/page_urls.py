"""Rendering-side URL helpers for Page template compatibility properties."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.page.metadata_helpers import fallback_url
from bengal.core.utils.url import apply_baseurl, get_baseurl, get_site_origin

if TYPE_CHECKING:
    from pathlib import Path


class PageURLTarget(Protocol):
    """Structural page surface needed by URL rendering helpers."""

    source_path: Path
    output_path: Path | None
    slug: str
    _site: Any
    _init_lock: Any
    __dict__: dict[str, Any]


def get_href(page: PageURLTarget) -> str:
    """Return template-ready page URL with baseurl applied."""
    manual_value = page.__dict__.get("href")
    if manual_value is not None:
        return str(manual_value)

    cached = page.__dict__.get("_href_cache")
    if cached is not None:
        return str(cached)

    with page._init_lock:
        cached = page.__dict__.get("_href_cache")
        if cached is not None:
            return str(cached)

        rel = get_path(page) or "/"
        try:
            site = getattr(page, "_site", None)
            baseurl = get_baseurl(site) if site else ""
        except Exception as e:
            emit_diagnostic(page, "debug", "page_baseurl_lookup_failed", error=str(e))
            baseurl = ""

        result = apply_baseurl(rel, baseurl)
        if "_path_cache" in page.__dict__:
            page.__dict__["_href_cache"] = result

    return result


def get_path(page: PageURLTarget) -> str:
    """Return site-relative URL path without baseurl."""
    manual_value = page.__dict__.get("_path")
    if manual_value is not None:
        return str(manual_value)

    cached = page.__dict__.get("_path_cache")
    if cached is not None:
        return str(cached)

    if not page.output_path:
        return get_fallback_url(page)

    site = getattr(page, "_site", None)
    if not site:
        return get_fallback_url(page)

    with page._init_lock:
        cached = page.__dict__.get("_path_cache")
        if cached is not None:
            return str(cached)

        try:
            rel_path = page.output_path.relative_to(site.output_dir)
        except ValueError:
            emit_diagnostic(
                page,
                "debug",
                "page_output_path_fallback",
                output_path=str(page.output_path),
                output_dir=str(site.output_dir),
                page_source=str(getattr(page, "source_path", "unknown")),
            )
            return get_fallback_url(page)

        url = path_from_output_relative_path(rel_path)
        page.__dict__["_path_cache"] = url
    return url


def get_absolute_href(page: PageURLTarget) -> str:
    """Return fully-qualified page URL when an absolute site origin is configured."""
    site = getattr(page, "_site", None)
    origin = get_site_origin(site) if site else ""
    if not origin:
        return get_href(page)
    return f"{origin}{get_path(page)}"


def get_fallback_url(page: PageURLTarget) -> str:
    """Return construction-time fallback URL for a page."""
    return fallback_url(page.slug)


def path_from_output_relative_path(rel_path: Path) -> str:
    """Convert an output-relative HTML path into Bengal's trailing-slash URL path."""
    url_parts = list(rel_path.parts)
    if url_parts and url_parts[-1] == "index.html":
        url_parts = url_parts[:-1]
    elif url_parts and url_parts[-1].endswith(".html"):
        url_parts[-1] = url_parts[-1][:-5]

    if not url_parts:
        return "/"

    url = "/" + "/".join(url_parts)
    return url if url.endswith("/") else f"{url}/"
