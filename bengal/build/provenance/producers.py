"""Generated, track, and asset provenance input producers.

Mirrors ``add_template_inputs`` / ``add_data_inputs`` so the dependency
read-index persists those kinds with ``producer="provenance"``. Fallback
scans stay; these helpers only record facts already on the page or site.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import CacheKey, content_key
from bengal.build.provenance.inputs import render_dependencies_for_page
from bengal.build.provenance.types import ContentHash, hash_content
from bengal.utils.paths.normalize import to_posix

from .assets import get_file_hash

if TYPE_CHECKING:
    from bengal.build.provenance.types import Provenance
    from bengal.protocols.core import PageLike

_ASSET_SUFFIXES = frozenset(
    {
        ".css",
        ".js",
        ".mjs",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".map",
    }
)
_ASSET_PREFIXES = ("assets/", "static/", "css/", "js/", "images/", "img/", "fonts/")


def _page_metadata(page: PageLike) -> Mapping[str, Any]:
    metadata = getattr(page, "metadata", None)
    return metadata if isinstance(metadata, Mapping) else {}


def _normalize_track_item(path: str) -> str:
    """Normalize a track item path the same way render ordering does."""
    normalized = to_posix(path)
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("content/"):
        normalized = normalized[8:]
    return normalized


def _tracks_mapping(pf: Any) -> Mapping[str, Any] | None:
    data = getattr(pf.site, "data", None)
    tracks = getattr(data, "tracks", None)
    if tracks is None and isinstance(data, Mapping):
        tracks = data.get("tracks")
    if isinstance(tracks, Mapping) and tracks:
        return tracks
    return None


def generated_page_key(page: PageLike, site_root: Path) -> str | None:
    """Return the generated-kind key for a generated page, or None."""
    metadata = _page_metadata(page)
    source = getattr(page, "source_path", None)
    is_generated = bool(metadata.get("_generated"))
    if not is_generated and isinstance(source, Path) and "generated" in source.parts:
        is_generated = True
    if not is_generated:
        return None

    term = metadata.get("_taxonomy_term") or metadata.get("tag")
    if term:
        taxonomy = metadata.get("_taxonomy") or metadata.get("taxonomy") or "tags"
        return f"{taxonomy}/{term}"

    if isinstance(source, Path):
        for marker in (".bengal/generated", "generated"):
            parts = source.parts
            if marker.split("/")[-1] in parts:
                idx = parts.index("generated")
                rel = Path(*parts[idx + 1 :])
                if rel.name in {"index.md", "index.html"}:
                    rel = rel.parent
                key = to_posix(rel)
                if key and key != ".":
                    return key
        return str(content_key(source, site_root))
    return None


def add_generated_inputs(pf: Any, provenance: Provenance, page: PageLike) -> Provenance:
    """Add a generated-kind input when this page is a generated page."""
    key = generated_page_key(page, pf.site.root_path)
    if not key:
        return provenance
    return provenance.with_input("generated", CacheKey(key), hash_content(key))


def add_track_inputs(pf: Any, provenance: Provenance, page: PageLike) -> Provenance:
    """Add track-kind inputs from page metadata and ``site.data.tracks``."""
    tracks = _tracks_mapping(pf)
    metadata = _page_metadata(page)
    keys: set[str] = set()

    track_id = metadata.get("track_id")
    if not track_id and metadata.get("template") == "tracks/single.html":
        track_id = getattr(page, "slug", None)
    if isinstance(track_id, str) and track_id:
        keys.add(track_id)
        if tracks is not None:
            track_def = tracks.get(track_id)
            raw = getattr(track_def, "_data", track_def)
            if isinstance(raw, Mapping):
                items = raw.get("items")
                if isinstance(items, (list, tuple)):
                    keys.update(
                        _normalize_track_item(item) for item in items if isinstance(item, str)
                    )

    if tracks is not None:
        page_rel = _page_content_rel(page, pf.site.root_path)
        if page_rel:
            page_no_ext = page_rel[:-3] if page_rel.endswith(".md") else page_rel
            for tid, track_def in tracks.items():
                raw = getattr(track_def, "_data", track_def)
                if not isinstance(raw, Mapping):
                    continue
                items = raw.get("items")
                if not isinstance(items, (list, tuple)):
                    continue
                normalized_items = {
                    _normalize_track_item(item) for item in items if isinstance(item, str)
                }
                item_no_ext = {i[:-3] if i.endswith(".md") else i for i in normalized_items}
                if page_rel in normalized_items or page_no_ext in item_no_ext:
                    keys.add(str(tid))
                    keys.update(normalized_items)

    for key in sorted(keys):
        provenance = provenance.with_input("track", CacheKey(key), _track_key_hash(pf, key))
    return provenance


def add_asset_inputs(pf: Any, provenance: Provenance, page: PageLike) -> Provenance:
    """Add asset-kind inputs observed during page rendering."""
    asset_paths: dict[str, Path | None] = {}
    for dep in render_dependencies_for_page(pf, page):
        resolved = resolve_asset_dependency(pf, dep)
        if resolved is None:
            continue
        key, path = resolved
        asset_paths.setdefault(key, path)

    for key, path in sorted(asset_paths.items()):
        content_hash = get_file_hash(pf, path) if path is not None else hash_content(key)
        provenance = provenance.with_input("asset", CacheKey(key), content_hash)
    return provenance


def resolve_asset_dependency(pf: Any, dependency: Path | str) -> tuple[str, Path | None] | None:
    """Resolve a render dependency as an asset key and optional file path."""
    if isinstance(dependency, Path):
        if dependency.suffix.lower() not in _ASSET_SUFFIXES:
            return None
        candidate = dependency if dependency.is_absolute() else pf.site.root_path / dependency
        try:
            if candidate.exists():
                return str(content_key(candidate, pf.site.root_path)), candidate
        except OSError:
            return None
        return to_posix(dependency), None

    if not isinstance(dependency, str) or not dependency:
        return None
    normalized = dependency.lstrip("/")
    suffix = Path(normalized).suffix.lower()
    looks_like_asset = suffix in _ASSET_SUFFIXES or normalized.startswith(_ASSET_PREFIXES)
    if not looks_like_asset:
        return None
    candidate = pf.site.root_path / normalized
    try:
        if candidate.exists() and candidate.suffix.lower() in _ASSET_SUFFIXES:
            return str(content_key(candidate, pf.site.root_path)), candidate
    except OSError:
        pass
    return normalized, None


def _page_content_rel(page: PageLike, site_root: Path) -> str | None:
    source = getattr(page, "source_path", None)
    if not isinstance(source, Path):
        return None
    content_root = site_root / "content"
    try:
        return to_posix(source.relative_to(content_root))
    except ValueError:
        try:
            rel = to_posix(source.relative_to(site_root))
        except ValueError:
            return None
        return rel.removeprefix("content/")


def _track_key_hash(pf: Any, key: str) -> ContentHash:
    """Hash a track key; prefer the item file when it exists under content/."""
    if "/" in key or key.endswith(".md"):
        for candidate in (pf.site.root_path / "content" / key, pf.site.root_path / key):
            try:
                if candidate.exists():
                    return get_file_hash(pf, candidate)
            except OSError:
                continue
    return hash_content(key)
