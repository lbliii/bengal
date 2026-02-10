"""Agreement contracts between detector and provenance paths."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bengal.build.provenance.filter import ProvenanceFilter
from bengal.build.provenance.store import ProvenanceCache
from bengal.cache import BuildCache
from bengal.core.page import Page
from bengal.effects.effect import Effect
from bengal.effects.tracer import EffectTracer
from bengal.orchestration.build.provenance_filter import _expand_forced_changed
from bengal.orchestration.incremental import EffectBasedDetector, IncrementalOrchestrator


def _create_site(tmp_path: Path) -> tuple[SimpleNamespace, list[Page], BuildCache, Path]:
    root = tmp_path / "site"
    content_dir = root / "content"
    templates_dir = root / "templates"
    output_dir = root / "public"
    content_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    template_path = templates_dir / "page.html"
    template_path.write_text("<main>{{ content }}</main>", encoding="utf-8")

    page_one_path = content_dir / "a.md"
    page_two_path = content_dir / "b.md"
    page_one_path.write_text("# A", encoding="utf-8")
    page_two_path.write_text("# B", encoding="utf-8")

    pages = [
        Page(
            source_path=page_one_path,
            _raw_content="# A",
            _raw_metadata={"title": "A", "template": "page.html"},
        ),
        Page(
            source_path=page_two_path,
            _raw_content="# B",
            _raw_metadata={"title": "B", "template": "page.html"},
        ),
    ]
    site = SimpleNamespace(
        root_path=root,
        output_dir=output_dir,
        config={"site": {"title": "Agreement Site"}},
        pages=pages,
        assets=[],
        sections=[],
        theme=None,
        page_by_source_path={page.source_path: page for page in pages},
    )

    cache = BuildCache()
    for page in pages:
        cache.update_file(page.source_path)
    cache.update_file(template_path)

    return site, pages, cache, template_path


def _prime_provenance_cache(site: SimpleNamespace, pages: list[Page], cache_dir: Path) -> None:
    provenance_cache = ProvenanceCache(cache_dir=cache_dir)
    pf = ProvenanceFilter(site=site, cache=provenance_cache)
    pf.filter(pages=pages, assets=[], incremental=False)
    for page in pages:
        pf.record_build(page)
    pf.save()


def _create_detector(site: SimpleNamespace, pages: list[Page]) -> EffectBasedDetector:
    tracer = EffectTracer()
    effects: list[Effect] = []
    for page in pages:
        output_path = site.output_dir / page.source_path.stem / "index.html"
        effects.append(
            Effect.for_page_render(
                source_path=page.source_path,
                output_path=output_path,
                template_name="page.html",
                template_includes=frozenset(),
                page_href=f"/{page.source_path.stem}/",
            )
        )
    tracer.record_batch(effects)
    return EffectBasedDetector(site=site, tracer=tracer)


def test_markdown_change_agrees_across_detector_provenance_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, pages, cache, _template_path = _create_site(tmp_path)
    _prime_provenance_cache(site, pages, tmp_path / ".bengal" / "provenance")
    detector = _create_detector(site, pages)

    changed_paths = {pages[0].source_path}

    detector_result = detector.detect_changes(changed_paths)

    pf = ProvenanceFilter(
        site=site,
        cache=ProvenanceCache(cache_dir=tmp_path / ".bengal" / "provenance"),
    )
    provenance_result = pf.filter(
        pages=pages,
        assets=[],
        incremental=True,
        forced_changed=changed_paths,
        trust_unchanged=True,
    )

    orchestrator = IncrementalOrchestrator(site)
    orchestrator.cache = cache
    orchestrator._detector = detector
    monkeypatch.setattr(orchestrator._cache_manager, "_get_theme_templates_dir", lambda: None)
    orchestrator_pages, _assets, _summary = orchestrator.find_work_early(
        forced_changed_sources=changed_paths
    )
    orchestrator_result = {page.source_path for page in orchestrator_pages}

    assert detector_result == changed_paths
    assert {page.source_path for page in provenance_result.pages_to_build} == changed_paths
    assert orchestrator_result == changed_paths


def test_template_change_detector_is_subset_of_provenance_expansion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, pages, cache, template_path = _create_site(tmp_path)
    detector = _create_detector(site, pages)

    # Simulate a real template change after cache fingerprinting.
    template_path.write_text("<main class='changed'>{{ content }}</main>", encoding="utf-8")
    changed_paths = {template_path}

    detector_result = detector.detect_changes(changed_paths)

    orchestrator = IncrementalOrchestrator(site)
    orchestrator.cache = cache
    orchestrator._detector = detector
    monkeypatch.setattr(orchestrator._cache_manager, "_get_theme_templates_dir", lambda: None)
    orchestrator_pages, _assets, _summary = orchestrator.find_work_early(
        forced_changed_sources=changed_paths
    )
    orchestrator_result = {page.source_path for page in orchestrator_pages}

    expanded, _reasons = _expand_forced_changed(
        forced_changed=changed_paths,
        cache=cache,
        site=site,
        pages=pages,
    )
    page_sources = {page.source_path for page in pages}

    assert detector_result == page_sources
    assert orchestrator_result == detector_result
    assert detector_result.issubset(expanded)
    assert page_sources.issubset(expanded)
