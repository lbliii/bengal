"""Tests for provenance mtime short-circuit optimization.

RFC: rfc-provenance-mtime-short-circuit
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import (
    ContentHash,
    Provenance,
    ProvenanceRecord,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def provenance_dir(tmp_path: Path) -> Path:
    """Create provenance cache directory with v2 index."""
    cache_dir = tmp_path / ".bengal" / "provenance"
    cache_dir.mkdir(parents=True)
    (cache_dir / "records").mkdir(exist_ok=True)
    return cache_dir


@pytest.fixture
def site_root(tmp_path: Path) -> Path:
    """Create minimal site with content."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")
    (content_dir / "about.md").write_text("---\ntitle: About\n---\n# About")
    return tmp_path


def test_get_input_paths_returns_empty_for_missing_page(
    provenance_dir: Path, site_root: Path
) -> None:
    """Missing page returns empty input_paths."""
    cache = ProvenanceCache(provenance_dir)
    assert cache.get_input_paths(CacheKey("content/other.md")) == []


def test_get_last_build_time_returns_none_for_v1_index(
    provenance_dir: Path, site_root: Path
) -> None:
    """V1 index without last_build_time returns None."""
    index_path = provenance_dir / "index.json"
    index_path.write_text(json.dumps({"version": 1, "pages": {"content/index.md": "abc123"}}))
    cache = ProvenanceCache(provenance_dir)
    cache._ensure_loaded()
    assert cache.get_last_build_time() is None


def test_get_input_paths_returns_stored_paths(provenance_dir: Path, site_root: Path) -> None:
    """Stored input_paths are returned."""
    index_path = provenance_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 2,
                "last_build_time": 1709827353.0,
                "pages": {"content/index.md": "abc123"},
                "input_paths": {
                    "content/index.md": ["content/index.md", "content/_index.md"],
                },
            }
        )
    )
    cache = ProvenanceCache(provenance_dir)
    cache._ensure_loaded()
    assert cache.get_input_paths(CacheKey("content/index.md")) == [
        "content/index.md",
        "content/_index.md",
    ]
    assert cache.get_last_build_time() == 1709827353.0


def test_store_persists_input_paths(provenance_dir: Path, site_root: Path) -> None:
    """store() with input_paths persists them."""
    provenance = Provenance().with_input(
        "content", CacheKey("content/index.md"), ContentHash("abc123")
    )
    record = ProvenanceRecord(
        page_path=CacheKey("content/index.md"),
        provenance=provenance,
        output_hash=ContentHash("_rendered_"),
    )
    cache = ProvenanceCache(provenance_dir)
    cache.store(record, input_paths=["content/index.md", "content/_index.md"])
    cache.save()

    # Reload and verify
    cache2 = ProvenanceCache(provenance_dir)
    cache2._ensure_loaded()
    assert cache2.get_input_paths(CacheKey("content/index.md")) == [
        "content/index.md",
        "content/_index.md",
    ]
    assert cache2.get_last_build_time() is not None
    assert cache2.get_last_build_time_ns() is not None


def test_backward_compat_v1_index_skips_mtime_short_circuit(
    provenance_dir: Path, site_root: Path
) -> None:
    """V1 index: get_last_build_time returns None, so mtime short-circuit is skipped."""
    index_path = provenance_dir / "index.json"
    index_path.write_text(json.dumps({"version": 1, "pages": {"content/index.md": "abc123"}}))
    cache = ProvenanceCache(provenance_dir)
    cache._ensure_loaded()
    assert cache.get_last_build_time() is None
    assert cache.get_input_paths(CacheKey("content/index.md")) == []


def test_mtime_short_circuit_disabled_via_env(
    provenance_dir: Path, site_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BENGAL_PROVENANCE_MTIME=0 disables mtime short-circuit."""
    from bengal.build.provenance.filter import ProvenanceFilter

    monkeypatch.setenv("BENGAL_PROVENANCE_MTIME", "0")

    index_path = provenance_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 2,
                "last_build_time": 9999999999.0,  # Future - all files would be "old"
                "pages": {"content/index.md": "abc123"},
                "input_paths": {"content/index.md": ["content/index.md"]},
            }
        )
    )

    site = MagicMock()
    site.root_path = site_root
    site.config = {"site": {"title": "Test"}}

    cache = ProvenanceCache(provenance_dir)
    cache._ensure_loaded()

    page = MagicMock()
    page.source_path = site_root / "content" / "index.md"
    page.virtual = False

    filter_obj = ProvenanceFilter(site, cache)
    # Should return False (disabled) - full verification needed
    assert filter_obj._mtime_short_circuit(page, ContentHash("abc123")) is False


def test_mtime_short_circuit_returns_true_when_no_changes(
    provenance_dir: Path, site_root: Path
) -> None:
    """When no file mtime > last_build_time, short-circuit returns True."""
    from bengal.build.provenance.filter import ProvenanceFilter

    # Create index with last_build_time in future (all files "older")
    index_path = provenance_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 2,
                "last_build_time": 9999999999.0,
                "pages": {"content/index.md": "abc123"},
                "input_paths": {"content/index.md": ["content/index.md"]},
            }
        )
    )

    site = MagicMock()
    site.root_path = site_root
    site.config = {"site": {"title": "Test"}}

    cache = ProvenanceCache(provenance_dir)
    cache._ensure_loaded()

    page = MagicMock()
    page.source_path = site_root / "content" / "index.md"
    page.virtual = False

    filter_obj = ProvenanceFilter(site, cache)
    assert filter_obj._mtime_short_circuit(page, ContentHash("abc123")) is True


def test_mtime_short_circuit_returns_false_when_content_changed(
    provenance_dir: Path, site_root: Path
) -> None:
    """When file mtime > last_build_time, short-circuit returns False."""
    from bengal.build.provenance.filter import ProvenanceFilter

    content_file = site_root / "content" / "index.md"
    content_file.touch()
    last_mtime = content_file.stat().st_mtime - 10  # 10 seconds ago

    index_path = provenance_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 2,
                "last_build_time": last_mtime,
                "pages": {"content/index.md": "abc123"},
                "input_paths": {"content/index.md": ["content/index.md"]},
            }
        )
    )

    site = MagicMock()
    site.root_path = site_root
    site.config = {"site": {"title": "Test"}}

    cache = ProvenanceCache(provenance_dir)
    cache._ensure_loaded()

    page = MagicMock()
    page.source_path = content_file
    page.virtual = False

    filter_obj = ProvenanceFilter(site, cache)
    assert filter_obj._mtime_short_circuit(page, ContentHash("abc123")) is False


def test_mtime_short_circuit_uses_nanosecond_timestamp(
    provenance_dir: Path, site_root: Path
) -> None:
    """Nanosecond build time prevents same-second edits from short-circuiting."""
    from bengal.build.provenance.filter import ProvenanceFilter

    content_file = site_root / "content" / "index.md"
    stat = content_file.stat()

    index_path = provenance_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 3,
                "last_build_time": 9999999999.0,
                "last_build_time_ns": stat.st_mtime_ns - 1,
                "pages": {"content/index.md": "abc123"},
                "input_paths": {"content/index.md": ["content/index.md"]},
            }
        )
    )

    site = MagicMock()
    site.root_path = site_root
    site.config = {"site": {"title": "Test"}}

    cache = ProvenanceCache(provenance_dir)
    cache._ensure_loaded()

    page = MagicMock()
    page.source_path = content_file
    page.virtual = False

    filter_obj = ProvenanceFilter(site, cache)
    assert filter_obj._mtime_short_circuit(page, ContentHash("abc123")) is False


def test_filter_save_uses_filter_creation_time(provenance_dir: Path, site_root: Path) -> None:
    """Saving provenance records uses build-start time, not cache-save time."""
    from bengal.build.provenance.filter import ProvenanceFilter

    site = MagicMock()
    site.root_path = site_root
    site.config = {}

    cache = ProvenanceCache(provenance_dir)
    filter_obj = ProvenanceFilter(site, cache)
    filter_obj._build_started_at = 100.0
    filter_obj._build_started_at_ns = 100_000_000_000

    provenance = Provenance().with_input(
        "content", CacheKey("content/index.md"), ContentHash("abc123")
    )
    record = ProvenanceRecord(
        page_path=CacheKey("content/index.md"),
        provenance=provenance,
        output_hash=ContentHash("_rendered_"),
    )
    cache.store(record, input_paths=["content/index.md"])

    filter_obj.save()

    data = json.loads((provenance_dir / "index.json").read_text())
    assert data["last_build_time"] == 100.0
    assert data["last_build_time_ns"] == 100_000_000_000


def test_extract_input_paths_skips_taxonomy(provenance_dir: Path, site_root: Path) -> None:
    """Taxonomy pages get empty input_paths (no file to mtime-check)."""
    from bengal.build.provenance.filter import ProvenanceFilter

    provenance = Provenance()
    provenance = provenance.with_input("taxonomy", CacheKey("tag:deployment"), ContentHash("xyz"))
    provenance = provenance.with_input("config", CacheKey("site_config"), ContentHash("cfg"))
    record = ProvenanceRecord(
        page_path=CacheKey(".bengal/generated/tags/deployment/page_1/index.md"),
        provenance=provenance,
        output_hash=ContentHash("_rendered_"),
    )

    site = MagicMock()
    site.root_path = site_root
    site.config = {}

    cache = ProvenanceCache(provenance_dir)
    filter_obj = ProvenanceFilter(site, cache)

    paths = filter_obj._extract_input_paths_for_mtime(record)
    assert paths == []
