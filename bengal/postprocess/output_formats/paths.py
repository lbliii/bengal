"""Path, hash, and fingerprint helpers for output-format generation."""

from __future__ import annotations

import hashlib
import json
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.utils import (
    get_i18n_output_path,
    get_page_json_path,
    get_page_md_path,
    get_page_txt_path,
)

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike


def _page_artifact_to_accumulated(record: dict[str, Any], accumulated_type: Any) -> Any:
    """Rehydrate a cached page artifact into an AccumulatedPageData record."""
    from bengal.rendering.page_artifact import PageArtifact

    return PageArtifact.from_cache_record(record).to_accumulated(accumulated_type)


def _site_relative_path(site: SiteLike, source_path: Path) -> Path:
    """Resolve relative source paths against the site root before cache lookup."""
    if source_path.is_absolute():
        return source_path
    root_path = getattr(site, "root_path", None)
    return root_path / source_path if root_path else source_path


def _output_relative_path(site: SiteLike, path: Path) -> str:
    """Return an output-relative path for stable fingerprint payloads."""
    output_dir = getattr(site, "output_dir", None)
    if output_dir is not None:
        with suppress(ValueError):
            return str(path.relative_to(output_dir))
    return str(path)


def _per_page_output_path(page: PageLike, output_format: str) -> Path | None:
    """Return the expected per-page artifact path for a configured output format."""
    if output_format == "json":
        return get_page_json_path(page)
    if output_format == "llm_txt":
        return get_page_txt_path(page)
    if output_format == "markdown":
        return get_page_md_path(page)
    return None


def _path_keys(path: Path | str) -> set[str]:
    """Return stable path keys for matching absolute/relative source paths."""
    path = Path(path)
    keys = {str(path)}
    with suppress(OSError):
        keys.add(str(path.resolve()))
    return keys


def _path_matches(path: Path | str, keys: set[str]) -> bool:
    """Return whether path matches one of the normalized changed-path keys."""
    return bool(_path_keys(path) & keys)


def _source_manifest_key(site: SiteLike, source_path: Path | str) -> str:
    """Return a stable source key for persisted per-page aggregate hashes."""
    path = Path(source_path)
    root_path = getattr(site, "root_path", None)
    if path.is_absolute() and root_path is not None:
        with suppress(ValueError):
            return str(path.relative_to(root_path))
    return str(path)


def _source_lookup_keys(site: SiteLike, source_path: Path | str) -> set[str]:
    """Return relative and absolute source variants for artifact lookup."""
    path = Path(source_path)
    keys = _path_keys(path)
    root_path = getattr(site, "root_path", None)
    if root_path is not None:
        if path.is_absolute():
            with suppress(ValueError):
                keys.update(_path_keys(path.relative_to(root_path)))
        else:
            keys.update(_path_keys(root_path / path))
    return keys


def _accumulated_data_by_source(site: SiteLike, accumulated_data: list[Any]) -> dict[str, Any]:
    """Index accumulated page data by normalized source path variants."""
    by_source: dict[str, Any] = {}
    for data in accumulated_data:
        source_path = getattr(data, "source_path", None)
        if source_path is None:
            continue
        for key in _source_lookup_keys(site, source_path):
            by_source[key] = data
    return by_source


def _lookup_accumulated_data(data_by_source: dict[str, Any], lookup_keys: set[str]) -> Any | None:
    """Return accumulated data matching any source path variant."""
    for key in lookup_keys:
        data = data_by_source.get(key)
        if data is not None:
            return data
    return None


def _fingerprint_page_artifact(data: Any) -> dict[str, Any]:
    """Return stable page artifact fields that affect site-wide output formats."""
    from bengal.rendering.page_artifact import PageArtifact

    artifact = data if isinstance(data, PageArtifact) else PageArtifact.from_accumulated(data)
    return artifact.fingerprint_record()


def _hash_page_artifact(data: Any) -> str:
    """Hash a page artifact fingerprint record for aggregate manifests."""
    encoded = json.dumps(
        _fingerprint_page_artifact(data),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _page_hash_manifest_key(format_name: str) -> str:
    """Return the cache key for a format's per-page aggregate hash manifest."""
    return f"{format_name}:page_hashes"


def _load_page_hash_manifest(value: Any) -> dict[str, str]:
    """Load a persisted per-page hash manifest, falling back to empty on mismatch."""
    if not isinstance(value, str) or not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {str(key): str(hash_value) for key, hash_value in loaded.items()}


def _site_fingerprint(site: SiteLike) -> dict[str, Any]:
    """Return site metadata that can affect site-wide output content."""
    build_time = getattr(site, "build_time", None)
    build_time_value = build_time.isoformat() if hasattr(build_time, "isoformat") else None
    return {
        "title": getattr(site, "title", "") or "",
        "description": getattr(site, "description", "") or "",
        "baseurl": getattr(site, "baseurl", "") or "",
        "dev_mode": bool(getattr(site, "dev_mode", False)),
        "build_time": None if getattr(site, "dev_mode", False) else build_time_value,
    }


def expected_site_wide_outputs(site: SiteLike, format_name: str) -> list[Path] | None:
    """Return outputs that must exist before a site-wide generator can be skipped."""
    if format_name == "site_index_json":
        if getattr(site, "versioning_enabled", False):
            return None
        return [get_i18n_output_path(site, "index.json")]
    if format_name == "site_llm_full":
        return [site.output_dir / "llm-full.txt"]
    if format_name == "site_llms_txt":
        return [site.output_dir / "llms.txt"]
    if format_name == "site_changelog":
        return [get_i18n_output_path(site, "changelog.json")]
    if format_name == "site_agent_manifest":
        return [get_i18n_output_path(site, "agent.json")]
    return None


def expected_search_backend_outputs(
    search_backend_config: Any,
    index_paths: list[Path],
) -> list[Path] | None:
    """Return backend outputs that must exist before derived search can skip."""
    if search_backend_config.backend == "lunr" and search_backend_config.prebuilt_enabled:
        return [path.parent / "search-index.json" for path in index_paths]
    return None
