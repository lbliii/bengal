"""
Shared link registry built once after rendering, consumed by all validators.

The LinkRegistry is an immutable data structure that provides:
- All valid internal URLs (with slash variants)
- Content-relative source paths for .md resolution
- Anchor IDs per page URL (from toc_items)
- Auxiliary URLs (index.txt when llm_txt enabled)

Built on the main thread after rendering, before health checks run.
Thread-safe by construction (frozen dataclass with frozenset fields).

Related:
- bengal.health.validators.links: Build-time link validation (consumer)
- bengal.health.linkcheck.internal_checker: Post-build link checking (consumer)
- bengal.orchestration.build.finalization: Build site (builder)

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import content_key

if TYPE_CHECKING:
    from bengal.protocols import SiteLike


@dataclass(frozen=True)
class LinkRegistry:
    """
    Immutable registry of all valid link targets in a site.

    Built once after rendering, consumed by both build-time validators
    and post-build link checkers. Thread-safe by construction.

    Attributes:
        page_urls: All valid internal URLs (with trailing-slash variants)
        source_paths: Content-relative paths for .md link resolution
        anchors_by_url: Mapping of page URL -> valid anchor IDs on that page
        auxiliary_urls: Extra valid URLs (e.g. index.txt for llm_txt output)
    """

    page_urls: frozenset[str]
    source_paths: frozenset[str]
    anchors_by_url: MappingProxyType[str, frozenset[str]]
    auxiliary_urls: frozenset[str]


def build_link_registry(site: SiteLike) -> LinkRegistry:
    """
    Build a LinkRegistry from a fully-rendered site.

    Scans all pages to collect URLs, source paths, and anchor IDs.
    Should be called after rendering is complete (toc_items populated)
    but before health checks run.

    Args:
        site: Site instance with rendered pages

    Returns:
        Immutable LinkRegistry instance
    """
    urls: set[str] = set()
    paths: set[str] = set()
    anchors: dict[str, frozenset[str]] = {}
    root = site.root_path

    for page in site.pages:
        # Collect page URLs (href includes baseurl)
        url = getattr(page, "href", None)
        if url:
            urls.add(url)
            # Avoid adding empty string for root URL "/"
            stripped = url.rstrip("/")
            if stripped:
                urls.add(stripped)
            urls.add(stripped + "/")

            permalink = getattr(page, "permalink", None)
            if permalink and permalink != url:
                urls.add(permalink)
                p_stripped = permalink.rstrip("/")
                if p_stripped:
                    urls.add(p_stripped)
                urls.add(p_stripped + "/")

        # Collect source paths for relative .md link resolution
        source_path = getattr(page, "source_path", None)
        if source_path:
            full = (
                (root / source_path) if not Path(source_path).is_absolute() else Path(source_path)
            )
            paths.add(content_key(full, root))

        # Collect anchor IDs from toc_items (already computed during parsing).
        toc_items = getattr(page, "toc_items", [])
        if toc_items and url:
            anchor_ids = frozenset(item["id"] for item in toc_items if "id" in item)
            if anchor_ids:
                # Index by _path (no baseurl) for internal resolution
                page_path = getattr(page, "_path", None)
                if page_path:
                    anchors[page_path] = anchor_ids
                    anchors[page_path.rstrip("/")] = anchor_ids
                    anchors[page_path.rstrip("/") + "/"] = anchor_ids
                # Also index by href for post-build checker
                anchors[url] = anchor_ids
                anchors[url.rstrip("/")] = anchor_ids
                anchors[url.rstrip("/") + "/"] = anchor_ids

    # Build auxiliary URL index
    aux_urls = _build_auxiliary_urls(site)

    return LinkRegistry(
        page_urls=frozenset(urls),
        source_paths=frozenset(paths),
        anchors_by_url=MappingProxyType(anchors),
        auxiliary_urls=frozenset(aux_urls),
    )


def _build_auxiliary_urls(site: SiteLike) -> set[str]:
    """Build set of auxiliary output URLs (e.g. index.txt when llm_txt enabled)."""
    config = getattr(site, "config", {}) or {}
    of: dict[str, Any] = config.get("output_formats", {}) or {}
    if not of.get("enabled", True):
        return set()
    per_page = of.get("per_page", [])
    if "llm_txt" not in per_page:
        return set()

    urls: set[str] = set()
    for page in site.pages:
        url = getattr(page, "href", None)
        if url:
            base = url.rstrip("/") + "/"
            urls.add(base + "index.txt")
    return urls
