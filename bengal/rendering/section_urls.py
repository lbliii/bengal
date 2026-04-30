"""Rendering-side URL helpers for Section template compatibility properties."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.utils.url import apply_baseurl, get_baseurl, get_site_origin
from bengal.utils.paths.url_normalization import join_url_paths, normalize_url, split_url_path

if TYPE_CHECKING:
    from pathlib import Path


class SectionURLTarget(Protocol):
    """Structural Section surface needed by URL rendering helpers."""

    name: str
    path: Path | None
    parent: Any
    subsections: list[Any]
    index_page: Any | None
    _site: Any
    _virtual: bool
    _relative_url_override: str | None

    @property
    def _path(self) -> str:
        """Site-relative section URL path."""
        ...

    @property
    def href(self) -> str:
        """Template-ready section URL with baseurl applied."""
        ...


def get_href(section: SectionURLTarget) -> str:
    """Return template-ready section URL with baseurl applied."""
    rel = section._path or "/"

    try:
        site = getattr(section, "_site", None)
        baseurl = get_baseurl(site) if site else ""
    except Exception as e:
        emit_diagnostic(section, "debug", "section_baseurl_lookup_failed", error=str(e))
        baseurl = ""

    return apply_baseurl(rel, baseurl)


def get_path(section: SectionURLTarget) -> str:
    """Return site-relative section URL path without baseurl."""
    if section._virtual:
        if not section._relative_url_override:
            emit_diagnostic(
                section,
                "error",
                "virtual_section_missing_url",
                section_name=section.name,
                tip="Virtual sections must have a _relative_url_override set.",
            )
            return "/"
        return normalize_url(section._relative_url_override)

    if section.path is None:
        return "/"

    parent_rel = section.parent._path if section.parent else "/"
    url = join_url_paths(parent_rel, section.name)

    return apply_version_path_transform(section, url)


def get_absolute_href(section: SectionURLTarget) -> str:
    """Return fully-qualified section URL when an absolute site origin is configured."""
    origin = get_site_origin(section._site) if section._site else ""
    if not origin:
        return section.href
    return f"{origin}{section._path}"


def subsection_index_urls(section: SectionURLTarget) -> set[str]:
    """Return URLs for all subsection index pages."""
    urls: set[str] = set()
    for subsection in section.subsections:
        if subsection.index_page:
            url = getattr(subsection.index_page, "_path", None)
            if url is not None:
                urls.add(str(url))
    return urls


def apply_version_path_transform(section: SectionURLTarget, url: str) -> str:
    """
    Transform versioned section URL to proper output structure.

    For sections inside _versions/<id>/, transforms the URL:
    - /_versions/v1/docs/about/ -> /docs/v1/about/ (non-latest)
    - /_versions/v3/docs/about/ -> /docs/about/ (latest)
    """
    if "/_versions/" not in url:
        return url

    site = getattr(section, "_site", None)
    if not site or not getattr(site, "versioning_enabled", False):
        return url

    version_config = getattr(site, "version_config", None)
    if not version_config:
        return url

    parts = url.split("/_versions/", 1)
    if len(parts) < 2:
        return url

    remainder_parts = split_url_path(parts[1])
    if len(remainder_parts) < 2:
        return url

    version_id = remainder_parts[0]
    section_name = remainder_parts[1]
    rest = remainder_parts[2:]

    version_obj = version_config.get_version(version_id)
    if not version_obj:
        return url

    if version_obj.latest:
        if rest:
            return f"/{section_name}/" + "/".join(rest) + "/"
        return f"/{section_name}/"

    if rest:
        return f"/{section_name}/{version_id}/" + "/".join(rest) + "/"
    return f"/{section_name}/{version_id}/"
