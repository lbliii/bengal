"""
Contract tests for incremental coherence across cache, provenance, and orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from bengal.build.provenance.filter import ProvenanceFilter
from bengal.build.provenance.store import ProvenanceCache
from bengal.cache import BuildCache
from bengal.core.page import Page
from bengal.orchestration.incremental import IncrementalOrchestrator


@dataclass(frozen=True, slots=True)
class _Asset:
    source_path: Path


class _PassThroughDetector:
    """Detector stub that returns whatever changed paths it receives."""

    def detect_changes(self, changed_paths: set[Path], *, verbose: bool = False) -> set[Path]:
        _ = verbose
        return set(changed_paths)


def _create_site(tmp_path: Path) -> tuple[SimpleNamespace, list[Page], list[_Asset], BuildCache]:
    root = tmp_path / "site"
    content_dir = root / "content"
    assets_dir = root / "assets"
    output_dir = root / "public"
    content_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_one_path = content_dir / "about.md"
    page_two_path = content_dir / "guides.md"
    asset_path = assets_dir / "style.css"

    page_one_path.write_text("# About", encoding="utf-8")
    page_two_path.write_text("# Guides", encoding="utf-8")
    asset_path.write_text("body { color: #222; }", encoding="utf-8")

    pages = [
        Page(
            source_path=page_one_path,
            _raw_content="# About",
            _raw_metadata={"title": "About"},
        ),
        Page(
            source_path=page_two_path,
            _raw_content="# Guides",
            _raw_metadata={"title": "Guides"},
        ),
    ]
    assets = [_Asset(source_path=asset_path)]

    site = SimpleNamespace(
        root_path=root,
        output_dir=output_dir,
        config={"site": {"title": "Test Site"}},
        pages=pages,
        assets=assets,
        sections=[],
        theme=None,
        page_by_source_path={page.source_path: page for page in pages},
    )

    build_cache = BuildCache()
    for page in pages:
        build_cache.update_file(page.source_path)
    for asset in assets:
        build_cache.update_file(asset.source_path)

    return site, pages, assets, build_cache


def _prime_provenance_cache(site: Any, pages: list[Page], cache_dir: Path) -> None:
    provenance_cache = ProvenanceCache(cache_dir=cache_dir)
    provenance_filter = ProvenanceFilter(site=site, cache=provenance_cache)
    # Full build pass computes canonical provenance for all pages.
    provenance_filter.filter(pages=pages, assets=[], incremental=False)
    for page in pages:
        provenance_filter.record_build(page)
    provenance_filter.save()


def test_forced_page_change_contract_is_consistent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Forced content changes should be treated as rebuilds by all three layers.
    """
    site, pages, _assets, build_cache = _create_site(tmp_path)
    forced_changed = {pages[0].source_path}

    _prime_provenance_cache(site, pages, tmp_path / ".bengal" / "provenance")
    provenance_filter = ProvenanceFilter(
        site=site,
        cache=ProvenanceCache(cache_dir=tmp_path / ".bengal" / "provenance"),
    )
    provenance_result = provenance_filter.filter(
        pages=pages,
        assets=[],
        incremental=True,
        forced_changed=forced_changed,
        trust_unchanged=True,
    )

    orchestrator = IncrementalOrchestrator(site)
    orchestrator.cache = build_cache
    orchestrator._detector = _PassThroughDetector()
    monkeypatch.setattr(orchestrator._cache_manager, "_get_theme_templates_dir", lambda: None)
    pages_to_build, _assets_to_process, _summary = orchestrator.find_work_early(
        forced_changed_sources=forced_changed
    )

    assert build_cache.should_bypass(pages[0].source_path, changed_sources=forced_changed)
    assert not build_cache.should_bypass(pages[1].source_path, changed_sources=forced_changed)
    assert {page.source_path for page in provenance_result.pages_to_build} == forced_changed
    assert {page.source_path for page in pages_to_build} == forced_changed


def test_trust_unchanged_contract_is_consistent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    trust_unchanged should skip non-forced pages while still rebuilding forced pages.
    """
    site, pages, _assets, build_cache = _create_site(tmp_path)
    forced_changed = {pages[0].source_path}

    _prime_provenance_cache(site, pages, tmp_path / ".bengal" / "provenance")
    provenance_filter = ProvenanceFilter(
        site=site,
        cache=ProvenanceCache(cache_dir=tmp_path / ".bengal" / "provenance"),
    )
    result = provenance_filter.filter(
        pages=pages,
        assets=[],
        incremental=True,
        forced_changed=forced_changed,
        trust_unchanged=True,
    )

    orchestrator = IncrementalOrchestrator(site)
    orchestrator.cache = build_cache
    orchestrator._detector = _PassThroughDetector()
    monkeypatch.setattr(orchestrator._cache_manager, "_get_theme_templates_dir", lambda: None)
    pages_to_build, _assets_to_process, _summary = orchestrator.find_work_early(
        forced_changed_sources=forced_changed
    )

    assert {page.source_path for page in result.pages_to_build} == forced_changed
    assert {page.source_path for page in result.pages_skipped} == {pages[1].source_path}
    assert not build_cache.should_bypass(pages[1].source_path, changed_sources=forced_changed)
    assert {page.source_path for page in pages_to_build} == forced_changed


def test_forced_asset_change_contract_is_consistent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Forced asset changes should be selected by both provenance and orchestrator paths.
    """
    site, pages, assets, build_cache = _create_site(tmp_path)
    forced_changed = {assets[0].source_path}

    _prime_provenance_cache(site, pages, tmp_path / ".bengal" / "provenance")
    provenance_filter = ProvenanceFilter(
        site=site,
        cache=ProvenanceCache(cache_dir=tmp_path / ".bengal" / "provenance"),
    )
    provenance_result = provenance_filter.filter(
        pages=pages,
        assets=assets,  # type: ignore[arg-type]
        incremental=True,
        forced_changed=forced_changed,
        trust_unchanged=True,
    )

    orchestrator = IncrementalOrchestrator(site)
    orchestrator.cache = build_cache
    orchestrator._detector = _PassThroughDetector()
    monkeypatch.setattr(orchestrator._cache_manager, "_get_theme_templates_dir", lambda: None)
    _pages_to_build, assets_to_process, _summary = orchestrator.find_work_early(
        forced_changed_sources=forced_changed
    )

    assert build_cache.should_bypass(assets[0].source_path, changed_sources=forced_changed)
    assert {asset.source_path for asset in provenance_result.assets_to_process} == forced_changed
    assert {asset.source_path for asset in assets_to_process} == forced_changed
