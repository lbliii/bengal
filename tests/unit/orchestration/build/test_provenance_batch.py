"""Tests for batched provenance recording after rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bengal.build.provenance.filter import ProvenanceFilter
from bengal.build.provenance.store import ProvenanceCache
from bengal.orchestration.build.provenance_filter import (
    record_all_page_builds,
    record_page_build,
)

if TYPE_CHECKING:
    from pathlib import Path


def _page(root: Path, name: str = "page.md") -> MagicMock:
    source_path = root / "content" / name
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("# Page\n", encoding="utf-8")

    page = MagicMock()
    page.source_path = source_path
    page.metadata = {}
    page.virtual = False
    page._section = None
    return page


def _filter(tmp_path: Path) -> ProvenanceFilter:
    site = MagicMock()
    site.root_path = tmp_path
    site.config = {}
    site.get_section_by_path.return_value = None
    cache = ProvenanceCache(tmp_path / ".bengal" / "provenance")
    return ProvenanceFilter(site=site, cache=cache)


def test_record_all_page_builds_uses_store_batch(tmp_path: Path) -> None:
    provenance_filter = _filter(tmp_path)
    provenance_filter.cache.store = MagicMock()
    provenance_filter.cache.store_batch = MagicMock()
    orchestrator = MagicMock()
    orchestrator._provenance_filter = provenance_filter
    page = _page(tmp_path)

    record_all_page_builds(orchestrator, [page], parallel=False)

    provenance_filter.cache.store.assert_not_called()
    provenance_filter.cache.store_batch.assert_called_once()
    records, input_paths_map = provenance_filter.cache.store_batch.call_args.args
    assert len(records) == 1
    assert records[0].page_path in input_paths_map


def test_record_page_build_keeps_single_record_path(tmp_path: Path) -> None:
    provenance_filter = _filter(tmp_path)
    provenance_filter.cache.store = MagicMock()
    provenance_filter.cache.store_batch = MagicMock()
    orchestrator = MagicMock()
    orchestrator._provenance_filter = provenance_filter
    page = _page(tmp_path)

    record_page_build(orchestrator, page)

    provenance_filter.cache.store.assert_called_once()
    provenance_filter.cache.store_batch.assert_not_called()
