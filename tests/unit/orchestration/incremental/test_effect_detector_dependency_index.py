"""Tests for EffectBasedDetector dependency-index consultation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from bengal.build.contracts import DependencyIndexEntry, DependencyReadIndex
from bengal.orchestration.incremental.effect_detector import EffectBasedDetector


def _detector_with_index(index: DependencyReadIndex) -> EffectBasedDetector:
    tracer = Mock()
    tracer.outputs_needing_rebuild.return_value = set()
    tracer.get_effects_depending_on.return_value = []
    site = Mock()
    site.pages = []
    return EffectBasedDetector(site=site, tracer=tracer, dependency_index=index)


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
