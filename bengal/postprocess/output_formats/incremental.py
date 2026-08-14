"""Incremental cache merge, fingerprints, and site-wide skip helpers."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.paths import (
    _accumulated_data_by_source,
    _hash_page_artifact,
    _load_page_hash_manifest,
    _lookup_accumulated_data,
    _output_relative_path,
    _page_artifact_to_accumulated,
    _page_hash_manifest_key,
    _path_keys,
    _path_matches,
    _per_page_output_path,
    _site_fingerprint,
    _site_relative_path,
    _source_lookup_keys,
    _source_manifest_key,
    expected_search_backend_outputs,
    expected_site_wide_outputs,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bengal.postprocess.output_formats.generator import OutputFormatsGenerator
    from bengal.protocols import PageLike

logger = get_logger(__name__)


def _merge_cached_page_artifacts(
    self: OutputFormatsGenerator,
    pages: list[PageLike],
    accumulated_data: list[Any],
) -> list[Any]:
    """Merge current rendered page data with cached records for unchanged pages."""
    if not self.build_context or not getattr(self.build_context, "incremental", False):
        return accumulated_data
    cache = getattr(self.build_context, "cache", None)
    page_artifacts = getattr(cache, "page_artifacts", None)
    if not cache or not isinstance(page_artifacts, dict):
        return accumulated_data

    from bengal.orchestration.build_context import AccumulatedPageData

    by_source = {data.source_path: data for data in accumulated_data}
    merged = list(accumulated_data)
    for page in pages:
        source_path = getattr(page, "source_path", None)
        if not source_path or source_path in by_source:
            continue
        cache_key = str(cache._cache_key(_site_relative_path(self.site, source_path)))
        record = page_artifacts.get(cache_key)
        if not isinstance(record, dict):
            continue
        merged.append(_page_artifact_to_accumulated(record, AccumulatedPageData))
    return merged


def _per_page_target_pages(
    self: OutputFormatsGenerator,
    pages: list[PageLike],
    output_format: str,
) -> list[PageLike]:
    """Return pages that need per-page companion artifacts for this build."""
    if not self.build_context or not getattr(self.build_context, "incremental", False):
        return pages
    if getattr(self.build_context, "config_changed", False):
        return pages

    changed_keys = self._changed_page_source_keys()
    if not changed_keys:
        targets = [
            page
            for page in pages
            if (output_path := _per_page_output_path(page, output_format)) is not None
            and not output_path.exists()
        ]
        logger.debug(
            "per_page_output_targets_selected",
            format=output_format,
            targets=len(targets),
            total=len(pages),
            reason="incremental_missing_outputs_only",
        )
        return targets

    targets = []
    for page in pages:
        source_path = getattr(page, "source_path", None)
        if source_path is None:
            continue
        output_path = _per_page_output_path(page, output_format)
        if output_path is None:
            continue
        if _path_matches(source_path, changed_keys) or not output_path.exists():
            targets.append(page)
    logger.debug(
        "per_page_output_targets_selected",
        format=output_format,
        targets=len(targets),
        total=len(pages),
        reason="incremental_changed_pages",
    )
    return targets


def _changed_page_source_keys(self: OutputFormatsGenerator) -> set[str]:
    """Return normalized source path keys for pages rendered in this build."""
    changed: set[str] = set()
    pages_to_build = getattr(self.build_context, "pages_to_build", None)
    if pages_to_build:
        for page in pages_to_build:
            source_path = getattr(page, "source_path", None)
            if source_path is not None:
                changed.update(_path_keys(source_path))

    changed_page_paths = getattr(self.build_context, "changed_page_paths", set()) or set()
    for path in changed_page_paths:
        changed.update(_path_keys(path))
    return changed


def _generate_site_wide_if_needed(
    self: OutputFormatsGenerator,
    timings: dict[str, float],
    format_name: str,
    pages: list[PageLike],
    accumulated_data: list[Any] | None,
    options: dict[str, Any],
    expected_outputs: list[Path] | None,
    generate_fn: Callable[[], Any],
    skip_result: Any = None,
) -> Any:
    """Skip unchanged site-wide generators when their artifact input fingerprint matches."""
    fingerprint = self._site_wide_input_fingerprint(format_name, pages, accumulated_data, options)
    cache = getattr(self.build_context, "cache", None)
    fingerprints = getattr(cache, "output_format_fingerprints", None)
    can_skip = (
        fingerprint is not None
        and isinstance(fingerprints, dict)
        and expected_outputs is not None
        and all(path.exists() for path in expected_outputs)
        and fingerprints.get(format_name) == fingerprint
    )
    if can_skip:
        self._pending_site_wide_page_hashes.pop(format_name, None)
        timings[format_name] = 0.0
        stats = getattr(self.build_context, "stats", None)
        if stats is not None:
            stats.postprocess_output_timings_ms[format_name] = 0.0
        logger.debug(
            "site_wide_output_skipped",
            format=format_name,
            reason="input_fingerprint_unchanged",
        )
        if skip_result is not None:
            return skip_result
        return expected_outputs if len(expected_outputs) > 1 else expected_outputs[0]

    result = self._timed_generate(timings, format_name, generate_fn)
    if fingerprint is not None and isinstance(fingerprints, dict):
        fingerprints[format_name] = fingerprint
        page_hashes = self._pending_site_wide_page_hashes.pop(format_name, None)
        if page_hashes is not None:
            fingerprints[_page_hash_manifest_key(format_name)] = json.dumps(
                page_hashes,
                sort_keys=True,
                separators=(",", ":"),
            )
    return result


def _generate_search_backend_if_needed(
    self: OutputFormatsGenerator,
    timings: dict[str, float],
    search_backend: Any,
    search_backend_config: Any,
    index_paths: list[Path],
    pages: list[PageLike],
    accumulated_data: list[Any] | None,
) -> list[str]:
    """Skip derived search backend artifacts when aggregate inputs are unchanged."""
    if not search_backend_config.enabled or not search_backend_config.prebuilt_enabled:
        return search_backend.generate(
            index_paths,
            lambda label, factory: self._timed_generate(timings, label, factory),
        )

    result = self._generate_site_wide_if_needed(
        timings,
        "site_lunr_index",
        pages,
        accumulated_data,
        self._search_backend_fingerprint_options(search_backend_config, index_paths),
        self._expected_search_backend_outputs(search_backend_config, index_paths),
        lambda: search_backend.generate(
            index_paths,
            lambda label, factory: self._timed_generate(timings, label, factory),
        ),
        skip_result=[],
    )
    return list(result or [])


def _search_backend_fingerprint_options(
    self: OutputFormatsGenerator,
    search_backend_config: Any,
    index_paths: list[Path],
) -> dict[str, Any]:
    """Return search backend options that affect derived aggregate outputs."""
    return {
        "backend": search_backend_config.backend,
        "lunr": search_backend_config.lunr,
        "index_paths": [_output_relative_path(self.site, path) for path in index_paths],
    }


def _expected_search_backend_outputs(
    self: OutputFormatsGenerator,
    search_backend_config: Any,
    index_paths: list[Path],
) -> list[Path] | None:
    """Return backend outputs that must exist before derived search can skip."""
    return expected_search_backend_outputs(search_backend_config, index_paths)


def _site_wide_input_fingerprint(
    self: OutputFormatsGenerator,
    format_name: str,
    pages: list[PageLike],
    accumulated_data: list[Any] | None,
    options: dict[str, Any],
) -> str | None:
    """Fingerprint complete site-wide generator inputs from page artifacts."""
    if not self.build_context or not getattr(self.build_context, "incremental", False):
        return None
    if format_name == "site_changelog":
        return None
    if not accumulated_data:
        return None

    cache = getattr(self.build_context, "cache", None)
    fingerprints = getattr(cache, "output_format_fingerprints", None)
    if not isinstance(fingerprints, dict):
        return None

    prior_hashes = _load_page_hash_manifest(fingerprints.get(_page_hash_manifest_key(format_name)))
    changed_keys = self._changed_page_source_keys()
    data_by_source = _accumulated_data_by_source(self.site, accumulated_data)
    page_hashes: dict[str, str] = {}

    for page in pages:
        source_path = getattr(page, "source_path", None)
        if not source_path:
            return None
        source_key = _source_manifest_key(self.site, source_path)
        lookup_keys = _source_lookup_keys(self.site, source_path)
        prior_hash = prior_hashes.get(source_key)
        if prior_hash is not None and not (lookup_keys & changed_keys):
            page_hashes[source_key] = prior_hash
            continue

        data = _lookup_accumulated_data(data_by_source, lookup_keys)
        if data is None:
            return None
        page_hashes[source_key] = _hash_page_artifact(data)

    payload = {
        "format": format_name,
        "options": options,
        "site": _site_fingerprint(self.site),
        "pages": sorted(page_hashes.items()),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fingerprint = hashlib.sha256(encoded).hexdigest()
    self._pending_site_wide_page_hashes[format_name] = page_hashes
    return fingerprint


def _expected_site_wide_outputs(
    self: OutputFormatsGenerator,
    format_name: str,
) -> list[Path] | None:
    """Return outputs that must exist before a site-wide generator can be skipped."""
    return expected_site_wide_outputs(self.site, format_name)
