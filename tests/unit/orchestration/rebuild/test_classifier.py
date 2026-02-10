"""Tests for rebuild classification service."""

from __future__ import annotations

from pathlib import Path

from bengal.orchestration.rebuild.classifier import RebuildClassifier


def _false(_: set[Path]) -> bool:
    return False


def test_structural_change_forces_full_rebuild() -> None:
    classifier = RebuildClassifier()
    decision = classifier.classify(
        {Path("docs/test.md")},
        {"created"},
        is_template_change=_false,
        should_regenerate_autodoc=_false,
        is_shared_content_change=_false,
        is_version_config_change=_false,
    )
    assert decision.full_rebuild is True
    assert decision.reason == "structural"


def test_template_change_forces_full_rebuild() -> None:
    classifier = RebuildClassifier()
    decision = classifier.classify(
        {Path("templates/base.html")},
        {"modified"},
        is_template_change=lambda _paths: True,
        should_regenerate_autodoc=_false,
        is_shared_content_change=_false,
        is_version_config_change=_false,
    )
    assert decision.full_rebuild is True
    assert decision.reason == "template"


def test_incremental_when_no_full_rebuild_signals() -> None:
    classifier = RebuildClassifier()
    decision = classifier.classify(
        {Path("docs/test.md")},
        {"modified"},
        is_template_change=_false,
        should_regenerate_autodoc=_false,
        is_shared_content_change=_false,
        is_version_config_change=_false,
    )
    assert decision.full_rebuild is False
    assert decision.reason == "incremental"
