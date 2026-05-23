"""Tests for immutable render snapshot handoff facts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from bengal.snapshots.handoff import create_render_snapshot_handoff

pytestmark = pytest.mark.parallel_unsafe


def _page(path: str) -> SimpleNamespace:
    return SimpleNamespace(source_path=Path(path))


def _snapshot(
    *,
    pages: tuple[SimpleNamespace, ...],
    templates: dict[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        pages=pages,
        page_count=len(pages),
        section_count=1,
        schedule=SimpleNamespace(templates=templates or {}),
    )


def test_render_snapshot_handoff_is_complete_when_live_pages_match() -> None:
    snapshot = _snapshot(
        pages=(_page("content/a.md"), _page("content/b.md")),
        templates={"page.html": object()},
    )

    handoff = create_render_snapshot_handoff(
        snapshot,
        [_page("content/a.md"), _page("content/b.md")],
    )

    assert handoff.is_complete is True
    assert handoff.page_sources == (Path("content/a.md"), Path("content/b.md"))
    assert handoff.missing_snapshot_sources == ()
    assert handoff.extra_snapshot_sources == ()
    assert handoff.page_count == 2
    assert handoff.section_count == 1
    assert handoff.template_count == 1


def test_render_snapshot_handoff_records_hybrid_mismatches() -> None:
    snapshot = _snapshot(pages=(_page("content/a.md"), _page("content/stale.md")))

    handoff = create_render_snapshot_handoff(
        snapshot,
        [_page("content/a.md"), _page("content/new.md")],
    )

    assert handoff.is_complete is False
    assert handoff.missing_snapshot_sources == (Path("content/new.md"),)
    assert handoff.extra_snapshot_sources == (Path("content/stale.md"),)


def test_render_snapshot_handoff_parallel_reads_are_stable() -> None:
    snapshot = _snapshot(
        pages=tuple(_page(f"content/page-{index}.md") for index in range(50)),
        templates={"page.html": object(), "docs.html": object()},
    )
    handoff = create_render_snapshot_handoff(snapshot, list(snapshot.pages))

    def read_handoff(_index: int) -> tuple[bool, tuple[Path, ...], int, int, int]:
        return (
            handoff.is_complete,
            handoff.page_sources,
            handoff.page_count,
            handoff.section_count,
            handoff.template_count,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(executor.map(read_handoff, range(200)))

    assert len(set(results)) == 1
    assert results[0][0] is True
    assert len(results[0][1]) == 50
