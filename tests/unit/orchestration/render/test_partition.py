"""
Unit tests for the isolated render partitioner (issue #350, saga S3).

The partition is the correctness foundation of the separate-heap backend: it
must be a *cover* (every page rendered exactly once), deterministic, and
reasonably cost-balanced.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bengal.orchestration.render.isolated.partition import (
    estimate_render_cost,
    partition_pages,
)


@dataclass
class _FakePage:
    source_path: Path
    html_content: str = ""


def _make_pages(n: int, *, section: str = "docs", size: int = 100) -> list[_FakePage]:
    return [_FakePage(Path(f"content/{section}/page-{i}.md"), "x" * size) for i in range(n)]


def _flatten(chunks: list[list[int]]) -> list[int]:
    return sorted(i for chunk in chunks for i in chunk)


def test_partition_is_a_cover() -> None:
    pages = _make_pages(50)
    chunks = partition_pages(pages, 8)
    # Every index appears exactly once across all chunks.
    flat = [i for chunk in chunks for i in chunk]
    assert sorted(flat) == list(range(50))
    assert len(flat) == len(set(flat))  # no duplicates


def test_partition_respects_chunk_count() -> None:
    pages = _make_pages(50)
    chunks = partition_pages(pages, 8)
    assert len(chunks) == 8
    assert all(chunk for chunk in chunks)  # no empty chunks when pages >> chunks


def test_partition_is_deterministic() -> None:
    pages = _make_pages(37, size=250)
    a = partition_pages(pages, 6)
    b = partition_pages(pages, 6)
    assert a == b


def test_partition_balances_cost() -> None:
    # Mixed sizes so balancing actually matters.
    pages = [
        _FakePage(Path(f"content/docs/page-{i}.md"), "x" * (10 if i % 2 else 5000))
        for i in range(40)
    ]
    chunks = partition_pages(pages, 8)
    loads = [sum(estimate_render_cost(pages[i]) for i in chunk) for chunk in chunks]
    # LPT keeps the heaviest bin within ~1.5x of the lightest on this workload.
    assert max(loads) <= 1.5 * min(loads)


def test_partition_empty() -> None:
    assert partition_pages([], 8) == []


def test_more_chunks_than_pages() -> None:
    pages = _make_pages(3)
    chunks = partition_pages(pages, 8)
    assert _flatten(chunks) == [0, 1, 2]
    # Clamped: at most one page per chunk, no empties.
    assert all(len(chunk) == 1 for chunk in chunks)
    assert len(chunks) == 3


def test_single_chunk() -> None:
    pages = _make_pages(10)
    chunks = partition_pages(pages, 1)
    assert len(chunks) == 1
    assert chunks[0] == list(range(10))


def test_section_strategy_keeps_sections_together() -> None:
    # Three balanced sections, three chunks: each section should land whole.
    pages = (
        _make_pages(6, section="docs")
        + _make_pages(6, section="api")
        + _make_pages(6, section="guides")
    )
    chunks = partition_pages(pages, 3, strategy="section")
    assert _flatten(chunks) == list(range(18))
    # No chunk should mix sections when sections divide evenly across chunks.
    for chunk in chunks:
        sections = {pages[i].source_path.parts[1] for i in chunk}
        assert len(sections) == 1


def test_estimate_render_cost_scales_with_content() -> None:
    small = _FakePage(Path("content/a.md"), "x" * 10)
    big = _FakePage(Path("content/b.md"), "x" * 10_000)
    assert estimate_render_cost(big) > estimate_render_cost(small)


def test_estimate_render_cost_never_raises_on_bare_page() -> None:
    @dataclass
    class _Bare:
        source_path: Path

    cost = estimate_render_cost(_Bare(Path("content/x.md")))  # type: ignore[arg-type]
    assert cost > 0
