"""Rendering-owned registries for internal references and output targets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import content_key
from bengal.rendering.reference_resolution import (
    resolve_internal_link,
    resolved_path_url_variants,
)

if TYPE_CHECKING:
    from bengal.protocols import SiteLike


@dataclass(frozen=True, slots=True)
class LinkRegistry:
    """
    Immutable registry of all valid link targets in a rendered site.

    Rendering owns this registry because rendered pages define the canonical
    URLs, anchors, and auxiliary output URLs that validators consume.
    """

    page_urls: frozenset[str]
    source_paths: frozenset[str]
    anchors_by_url: MappingProxyType[str, frozenset[str]]
    auxiliary_urls: frozenset[str]


@dataclass(frozen=True, slots=True)
class InternalReferenceResolver:
    """Resolver over a rendered site's immutable link registry."""

    registry: LinkRegistry

    def has_url(self, url: str) -> bool:
        """Return whether a normalized URL target is known."""
        return any(variant in self._all_urls for variant in resolved_path_url_variants(url))

    def resolve(self, page_url: str, link_path: str) -> str:
        """Resolve an internal link path from the given rendered page URL."""
        return resolve_internal_link(page_url, link_path)

    def anchors_for(self, url: str) -> frozenset[str]:
        """Return anchors for a URL, checking slash variants."""
        for variant in resolved_path_url_variants(url):
            anchors = self.registry.anchors_by_url.get(variant)
            if anchors is not None:
                return anchors
        return frozenset()

    def has_anchor(self, url: str, anchor: str) -> bool:
        """Return whether a URL has the requested anchor."""
        anchors = self.anchors_for(url)
        return bool(anchors) and anchor in anchors

    @property
    def _all_urls(self) -> frozenset[str]:
        return self.registry.page_urls | self.registry.auxiliary_urls


def build_link_registry(site: SiteLike) -> LinkRegistry:
    """
    Build a LinkRegistry from a fully rendered site.

    Scans all pages to collect URLs, source paths, and anchor IDs. Should be
    called after rendering is complete so ``toc_items`` and generated outputs
    have been populated.
    """
    urls: set[str] = set()
    paths: set[str] = set()
    anchors: dict[str, frozenset[str]] = {}
    root = site.root_path

    for page in site.pages:
        url = getattr(page, "href", None)
        if url:
            _add_url_variants(urls, str(url))

            permalink = getattr(page, "permalink", None)
            if permalink and permalink != url:
                _add_url_variants(urls, str(permalink))

        source_path = getattr(page, "source_path", None)
        if source_path:
            full = (
                (root / source_path) if not Path(source_path).is_absolute() else Path(source_path)
            )
            paths.add(content_key(full, root))

        toc_items = getattr(page, "toc_items", [])
        if toc_items and url:
            anchor_ids = frozenset(item["id"] for item in toc_items if "id" in item)
            if anchor_ids:
                page_path = getattr(page, "_path", None)
                if page_path:
                    _add_anchor_variants(anchors, str(page_path), anchor_ids)
                _add_anchor_variants(anchors, str(url), anchor_ids)

    return LinkRegistry(
        page_urls=frozenset(urls),
        source_paths=frozenset(paths),
        anchors_by_url=MappingProxyType(anchors),
        auxiliary_urls=frozenset(_build_auxiliary_urls(site)),
    )


def build_reference_resolver(site: SiteLike) -> InternalReferenceResolver:
    """Return a resolver backed by ``site.link_registry`` when available."""
    registry = getattr(site, "link_registry", None)
    if registry is None:
        registry = build_link_registry(site)
    return InternalReferenceResolver(registry)


def _add_url_variants(urls: set[str], url: str) -> None:
    """Add slash variants for a page URL."""
    urls.add(url)
    stripped = url.rstrip("/")
    if stripped:
        urls.add(stripped)
    urls.add(stripped + "/")


def _add_anchor_variants(
    anchors: dict[str, frozenset[str]], url: str, anchor_ids: frozenset[str]
) -> None:
    """Index anchors by URL and slash variants."""
    for variant in resolved_path_url_variants(url):
        anchors[variant] = anchor_ids


def _build_auxiliary_urls(site: SiteLike) -> set[str]:
    """Build set of auxiliary output URLs, such as per-page ``index.txt``."""
    config = getattr(site, "config", {}) or {}
    output_formats: dict[str, Any] = config.get("output_formats", {}) or {}
    if not output_formats.get("enabled", True):
        return set()
    per_page = output_formats.get("per_page", [])
    if "llm_txt" not in per_page:
        return set()

    urls: set[str] = set()
    for page in site.pages:
        url = getattr(page, "href", None)
        if url:
            urls.add(str(url).rstrip("/") + "/index.txt")
    return urls
