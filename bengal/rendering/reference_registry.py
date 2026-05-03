"""Rendering-owned registries for internal references and output targets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import content_key
from bengal.rendering.reference_resolution import (
    resolve_internal_link,
    resolved_path_url_variants,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.core.output import OutputRecord
    from bengal.protocols import SiteLike

_DEFAULT_SITE_WIDE_OUTPUT_FORMATS = (
    "index_json",
    "llm_full",
    "llms_txt",
    "changelog",
    "agent_manifest",
)
_SITE_WIDE_AUXILIARY_OUTPUTS = {
    "index_json": "index.json",
    "llm_full": "llm-full.txt",
    "llms_txt": "llms.txt",
    "changelog": "changelog.json",
    "agent_manifest": "agent.json",
}


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
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        """Precompute a deterministic fingerprint of URL and anchor truth."""
        object.__setattr__(self, "fingerprint", _fingerprint_link_registry(self))


@dataclass(frozen=True, slots=True)
class InternalReferenceResolver:
    """Resolver over a rendered site's immutable link registry."""

    registry: LinkRegistry
    all_urls: frozenset[str] = field(init=False)

    def __post_init__(self) -> None:
        """Precompute hot-path URL membership set once per resolver."""
        object.__setattr__(
            self,
            "all_urls",
            self.registry.page_urls | self.registry.auxiliary_urls,
        )

    def has_url(self, url: str) -> bool:
        """Return whether a normalized URL target is known."""
        return any(variant in self.all_urls for variant in resolved_path_url_variants(url))

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


def build_link_registry(
    site: SiteLike, output_records: Sequence[OutputRecord] | None = None
) -> LinkRegistry:
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
        auxiliary_urls=frozenset(_build_auxiliary_urls(site, output_records)),
    )


def build_link_registry_from_artifacts(site: SiteLike, build_context: Any) -> LinkRegistry | None:
    """
    Build a LinkRegistry from cached post-render page artifacts when complete.

    Returns ``None`` when any current page lacks a compatible artifact so callers
    can conservatively fall back to scanning rendered page objects.
    """
    cache = getattr(build_context, "cache", None)
    page_artifacts = getattr(cache, "page_artifacts", None)
    if cache is None or not isinstance(page_artifacts, dict):
        return None

    urls: set[str] = set()
    paths: set[str] = set()
    anchors: dict[str, frozenset[str]] = {}
    output_records = _output_records_from_build_context(build_context)
    auxiliary_urls = _build_auxiliary_urls(site, output_records)
    root = site.root_path
    output_llm_txt = output_records is None and _outputs_per_page_llm_txt(site)

    for page in site.pages:
        source_path = getattr(page, "source_path", None)
        if not source_path:
            return None
        key = str(cache._cache_key(_site_relative_path(root, source_path)))
        record = page_artifacts.get(key)
        if not isinstance(record, dict) or "anchors" not in record:
            return None

        uri = record.get("uri")
        if not isinstance(uri, str) or not uri:
            return None
        _add_url_variants(urls, uri)

        permalink = getattr(page, "permalink", None)
        if permalink and permalink != uri:
            _add_url_variants(urls, str(permalink))

        paths.add(content_key(_site_relative_path(root, Path(source_path)), root))

        anchor_ids = frozenset(str(anchor) for anchor in record.get("anchors", []))
        if anchor_ids:
            _add_anchor_variants(anchors, uri, anchor_ids)

        if output_llm_txt:
            auxiliary_urls.add(uri.rstrip("/") + "/index.txt")

    return LinkRegistry(
        page_urls=frozenset(urls),
        source_paths=frozenset(paths),
        anchors_by_url=MappingProxyType(anchors),
        auxiliary_urls=frozenset(auxiliary_urls),
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


def _build_auxiliary_urls(site: SiteLike, output_records: Sequence[Any] | None = None) -> set[str]:
    """Build set of auxiliary output URLs, such as output-format files."""
    if output_records is not None:
        return _build_auxiliary_urls_from_output_records(site, output_records)

    urls: set[str] = set()
    if _outputs_per_page_llm_txt(site):
        for page in site.pages:
            url = getattr(page, "href", None)
            if url:
                urls.add(str(url).rstrip("/") + "/index.txt")
    urls.update(_build_site_wide_auxiliary_urls(site))
    return urls


def _build_auxiliary_urls_from_output_records(
    site: SiteLike, output_records: Sequence[Any]
) -> set[str]:
    """Build auxiliary URLs from actual generated artifact records."""
    urls: set[str] = set()
    for record in output_records:
        path = getattr(record, "path", None)
        if path is None:
            continue
        url = _url_from_output_record_path(Path(path))
        if url:
            _add_auxiliary_output_url_variants(urls, site, url)
    return urls


def _outputs_per_page_llm_txt(site: SiteLike) -> bool:
    """Return whether per-page LLM text outputs are enabled."""
    config = getattr(site, "config", {}) or {}
    output_formats: dict[str, Any] = config.get("output_formats", {}) or {}
    if not output_formats.get("enabled", True):
        return False
    if "per_page" in output_formats:
        return "llm_txt" in (output_formats.get("per_page") or [])
    if "llm_txt" in output_formats:
        return bool(output_formats.get("llm_txt"))
    return "json" not in output_formats


def _build_site_wide_auxiliary_urls(site: SiteLike) -> set[str]:
    """Build valid internal URLs for generated site-wide output-format files."""
    urls: set[str] = set()
    for output_format in _configured_site_wide_output_formats(site):
        filename = _SITE_WIDE_AUXILIARY_OUTPUTS.get(output_format)
        if filename:
            _add_auxiliary_output_variants(urls, site, filename)
    return urls


def _configured_site_wide_output_formats(site: SiteLike) -> tuple[str, ...]:
    """Return normalized site-wide output formats from the site configuration."""
    config = getattr(site, "config", {}) or {}
    output_formats: dict[str, Any] = config.get("output_formats", {}) or {}
    if not output_formats.get("enabled", True):
        return ()
    if "site_wide" in output_formats:
        return tuple(str(item) for item in output_formats.get("site_wide") or [])

    simple_keys = {"site_json", "site_llm"}
    if simple_keys & output_formats.keys():
        site_wide: list[str] = []
        if output_formats.get("site_json", False):
            site_wide.append("index_json")
        if output_formats.get("site_llm", False):
            site_wide.append("llm_full")
        return tuple(site_wide)

    return _DEFAULT_SITE_WIDE_OUTPUT_FORMATS


def _add_auxiliary_output_variants(urls: set[str], site: SiteLike, filename: str) -> None:
    """Add root and baseurl-prefixed variants for a generated auxiliary file."""
    _add_auxiliary_output_url_variants(urls, site, f"/{filename}")


def _add_auxiliary_output_url_variants(urls: set[str], site: SiteLike, url: str) -> None:
    """Add root and baseurl-prefixed variants for a generated auxiliary URL."""
    _add_url_variants(urls, url)
    baseurl = _site_baseurl(site)
    if baseurl:
        _add_url_variants(urls, f"{baseurl}/{url.lstrip('/')}")


def _site_baseurl(site: SiteLike) -> str:
    """Return normalized site baseurl without a trailing slash."""
    baseurl = getattr(site, "baseurl", None)
    if not isinstance(baseurl, str):
        config = getattr(site, "config", {}) or {}
        baseurl = config.get("baseurl", "")
    baseurl = str(baseurl or "").strip()
    if not baseurl or baseurl == "/":
        return ""
    return "/" + baseurl.strip("/")


def _url_from_output_record_path(path: Path) -> str | None:
    """Convert an output-record path into its public URL path."""
    path_str = path.as_posix().lstrip("/")
    if not path_str or path_str in {".", ".."}:
        return None
    if path.name == "index.html":
        parent = path.parent.as_posix().strip(".").strip("/")
        return f"/{parent}/" if parent else "/"
    return f"/{path_str}"


def _output_records_from_build_context(build_context: Any) -> Sequence[Any] | None:
    """Return artifact output records from build context when available."""
    collector = getattr(build_context, "artifact_collector", None)
    if collector is None:
        return None
    get_outputs = getattr(collector, "get_outputs", None)
    if not callable(get_outputs):
        return None
    return get_outputs()


def _site_relative_path(root_path: Path, source_path: Path) -> Path:
    """Resolve relative source paths against the current site root."""
    if source_path.is_absolute():
        return source_path
    return root_path / source_path


def _fingerprint_link_registry(registry: LinkRegistry) -> str:
    """Return a stable fingerprint for link target and anchor invalidation."""
    payload = {
        "page_urls": sorted(registry.page_urls),
        "source_paths": sorted(registry.source_paths),
        "auxiliary_urls": sorted(registry.auxiliary_urls),
        "anchors_by_url": [
            [url, sorted(anchors)] for url, anchors in sorted(registry.anchors_by_url.items())
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
