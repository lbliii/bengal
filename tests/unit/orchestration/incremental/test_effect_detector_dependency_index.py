"""Tests for EffectBasedDetector dependency-index consultation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from bengal.build.contracts import DependencyIndexEntry, DependencyReadIndex
from bengal.cache.paths import BengalPaths
from bengal.orchestration.incremental.effect_detector import (
    EffectBasedDetector,
    create_detector_from_build,
)
from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator


def _sample_index() -> DependencyReadIndex:
    return DependencyReadIndex(
        [
            DependencyIndexEntry(
                dependency_kind="data",
                dependency_key="data/team.yaml",
                page_keys=("content/about.md",),
            )
        ]
    )


def _detector_with_index(index: DependencyReadIndex) -> EffectBasedDetector:
    tracer = Mock()
    tracer.outputs_needing_rebuild.return_value = set()
    tracer.get_effects_depending_on.return_value = []
    site = Mock()
    site.pages = []
    return EffectBasedDetector(site=site, tracer=tracer, dependency_index=index)


def _site_with_provenance_index(tmp_path: Path, index: DependencyReadIndex) -> Mock:
    provenance_dir = tmp_path / ".bengal" / "provenance"
    provenance_dir.mkdir(parents=True)
    (provenance_dir / "dependency-index.json").write_text(
        json.dumps({"version": 1, "dependencies": index.to_cache_dict()}),
        encoding="utf-8",
    )

    site = Mock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.config_service.paths = BengalPaths(tmp_path)
    site.config = Mock()
    site.config.path = tmp_path / "bengal.toml"
    site.theme = None
    site.sections = []
    site.pages = []
    site.assets = []
    site.regular_pages = []
    site.generated_pages = []
    site.page_by_source_path = {}
    return site


def test_detect_changes_uses_dependency_index_for_data_file() -> None:
    """Data dependency entries map changed data files to affected pages."""
    detector = _detector_with_index(
        DependencyReadIndex(
            [
                DependencyIndexEntry(
                    dependency_kind="data",
                    dependency_key="data/team.yaml",
                    page_keys=("content/about.md",),
                )
            ]
        )
    )

    pages = detector.detect_changes({Path("data/team.yaml")})

    assert pages == {Path("content/about.md")}


def test_detect_changes_uses_dependency_index_for_template() -> None:
    """Template dependency entries map changed templates to affected pages."""
    detector = _detector_with_index(
        DependencyReadIndex(
            [
                DependencyIndexEntry(
                    dependency_kind="template",
                    dependency_key="templates/page.html",
                    page_keys=("content/about.md",),
                )
            ]
        )
    )

    pages = detector.detect_changes({Path("templates/page.html")})

    assert pages == {Path("content/about.md")}


def test_create_detector_from_build_forwards_dependency_index() -> None:
    """Factory accepts a live index and stores it on the detector."""
    index = _sample_index()
    detector = create_detector_from_build(Mock(), dependency_index=index)

    assert detector.dependency_index is index


def test_initialize_does_not_construct_detector(tmp_path: Path) -> None:
    """initialize() must not construct EffectBasedDetector (#748 Option 1)."""
    index = _sample_index()
    site = _site_with_provenance_index(tmp_path, index)
    orchestrator = IncrementalOrchestrator(site)

    orchestrator.initialize(enabled=False)

    assert orchestrator._detector is None


def test_detect_changes_passes_live_dependency_index(tmp_path: Path) -> None:
    """First _detect_changes loads the provenance cache index into the detector."""
    index = _sample_index()
    site = _site_with_provenance_index(tmp_path, index)
    orchestrator = IncrementalOrchestrator(site)
    orchestrator.initialize(enabled=False)

    orchestrator._detect_changes(set())

    assert orchestrator._detector is not None
    live = orchestrator._detector.dependency_index
    assert live is orchestrator._dependency_index
    assert live is not None
    assert live.affected_page_keys("data", "data/team.yaml") == ("content/about.md",)


def test_detect_changes_refresh_reuses_live_dependency_index(tmp_path: Path) -> None:
    """Detector refresh after first lazy init reuses the same live index object."""
    index = _sample_index()
    site = _site_with_provenance_index(tmp_path, index)
    orchestrator = IncrementalOrchestrator(site)
    orchestrator.initialize(enabled=False)
    orchestrator._detect_changes(set())
    live = orchestrator._detector.dependency_index
    orchestrator._detector = None

    orchestrator._detect_changes(set())

    assert orchestrator._detector is not None
    assert orchestrator._detector.dependency_index is live
