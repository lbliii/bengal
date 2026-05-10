"""Tests for immutable rendering page artifacts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from bengal.orchestration.build_context import AccumulatedPageData, BuildContext
from bengal.rendering.page_artifact import PageArtifact


def test_page_artifact_freezes_and_sanitizes_accumulated_data(tmp_path: Path) -> None:
    """PageArtifact snapshots mutable accumulated data into a frozen record."""
    data = _accumulated_page_data()
    data.raw_metadata["path"] = tmp_path / "source.md"
    data.full_json_data = {
        "url": "/docs/",
        "empty_list": [],
        "updated": datetime(2026, 5, 3, 12, 0, 0),
    }

    artifact = PageArtifact.from_accumulated(data, frozenset({"intro"}))
    data.title = "Mutated"
    data.raw_metadata["path"] = "changed"

    assert artifact.title == "Docs"
    assert artifact.anchors == ("intro",)
    assert artifact.to_cache_record()["raw_metadata"]["path"] == str(tmp_path / "source.md")
    assert artifact.to_cache_record()["full_json_data"]["empty_list"] == []
    assert artifact.to_cache_record()["full_json_data"]["updated"] == "2026-05-03T12:00:00"
    attr = "title"
    with pytest.raises(FrozenInstanceError):
        setattr(artifact, attr, "Nope")


def test_page_artifact_round_trips_cache_record_to_accumulated() -> None:
    """Cached artifact records can rehydrate the legacy accumulated shape."""
    original = PageArtifact.from_accumulated(_accumulated_page_data(), frozenset({"intro"}))

    restored = PageArtifact.from_cache_record(original.to_cache_record()).to_accumulated(
        AccumulatedPageData
    )

    assert restored.source_path == Path("content/docs.md")
    assert restored.title == "Docs"
    assert restored.tags == ["guide"]
    assert restored.full_json_data == {"url": "/docs/", "chunks": []}


def test_build_context_exposes_frozen_page_artifacts() -> None:
    """BuildContext keeps the compatibility data and a frozen artifact copy."""
    ctx = BuildContext(site=SimpleNamespace())
    data = _accumulated_page_data()

    ctx.accumulate_page_data(data)
    data.title = "Mutated"

    assert ctx.get_accumulated_page_data()[0].title == "Mutated"
    artifact = ctx.get_page_artifacts()[0]
    assert artifact.title == "Docs"
    assert ctx.get_artifact_for_page(Path("content/docs.md")) == artifact


def _accumulated_page_data() -> AccumulatedPageData:
    return AccumulatedPageData(
        source_path=Path("content/docs.md"),
        url="/docs/",
        uri="/docs/",
        title="Docs",
        description="Docs page",
        date=None,
        date_iso=None,
        plain_text="Docs body",
        excerpt="Docs",
        content_preview="Docs body",
        word_count=2,
        reading_time=1,
        section="Docs",
        tags=["guide"],
        dir="/docs/",
        enhanced_metadata={"type": "guide"},
        is_autodoc=False,
        full_json_data={"url": "/docs/", "chunks": []},
        json_output_path=Path("public/docs/index.json"),
        raw_metadata={"description": "Docs page"},
    )
