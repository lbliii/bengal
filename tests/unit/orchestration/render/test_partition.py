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
    ContentFile,
    discover_content_files,
    estimate_file_cost,
    estimate_render_cost,
    partition_content_files,
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


# ---------------------------------------------------------------------------
# S12: pre-parse content-file sharder — partition_content_files
# ---------------------------------------------------------------------------
#
# Same cover/determinism/balance contract as partition_pages, but the unit is an
# unparsed content file costed by on-disk byte size (the only signal available
# before a worker parses its shard).


def _make_content_files(n: int, *, section: str = "docs", size: int = 100) -> list[ContentFile]:
    return [ContentFile(Path(f"content/{section}/page-{i}.md"), size, section) for i in range(n)]


def test_file_partition_is_a_cover() -> None:
    files = _make_content_files(50)
    shards = partition_content_files(files, 8)
    flat = [i for shard in shards for i in shard]
    assert sorted(flat) == list(range(50))
    assert len(flat) == len(set(flat))  # no duplicates


def test_file_partition_respects_shard_count() -> None:
    files = _make_content_files(50)
    shards = partition_content_files(files, 8)
    assert len(shards) == 8
    assert all(shard for shard in shards)  # no empty shards when files >> shards


def test_file_partition_is_deterministic() -> None:
    files = _make_content_files(37, size=250)
    a = partition_content_files(files, 6)
    b = partition_content_files(files, 6)
    assert a == b


def test_file_partition_balances_cost() -> None:
    # Mixed sizes so balancing actually matters (big files alternate with tiny).
    files = [
        ContentFile(Path(f"content/docs/page-{i}.md"), (10 if i % 2 else 5000), "docs")
        for i in range(40)
    ]
    shards = partition_content_files(files, 8)
    loads = [sum(estimate_file_cost(files[i].size_bytes) for i in shard) for shard in shards]
    # LPT keeps the heaviest shard within ~1.5x of the lightest on this workload.
    assert max(loads) <= 1.5 * min(loads)


def test_file_partition_empty() -> None:
    assert partition_content_files([], 8) == []


def test_more_shards_than_files() -> None:
    files = _make_content_files(3)
    shards = partition_content_files(files, 8)
    assert _flatten(shards) == [0, 1, 2]
    # Clamped: at most one file per shard, no empties.
    assert all(len(shard) == 1 for shard in shards)
    assert len(shards) == 3


def test_single_shard_files() -> None:
    files = _make_content_files(10)
    shards = partition_content_files(files, 1)
    assert len(shards) == 1
    assert shards[0] == list(range(10))


def test_file_section_strategy_keeps_sections_together() -> None:
    # Three balanced sections, three shards: each section should land whole.
    files = (
        _make_content_files(6, section="docs")
        + _make_content_files(6, section="api")
        + _make_content_files(6, section="guides")
    )
    shards = partition_content_files(files, 3, strategy="section")
    assert _flatten(shards) == list(range(18))
    for shard in shards:
        sections = {files[i].section_key for i in shard}
        assert len(sections) == 1


# ---------------------------------------------------------------------------
# S12: pre-parse cost model — estimate_file_cost
# ---------------------------------------------------------------------------


def test_estimate_file_cost_scales_with_size() -> None:
    assert estimate_file_cost(10_000) > estimate_file_cost(10)


def test_estimate_file_cost_base_for_empty_file() -> None:
    # A zero-byte file still costs the fixed per-file overhead (never ~free), and
    # strictly less than a file with content (so the base does not swamp size).
    assert estimate_file_cost(0) > 0
    assert estimate_file_cost(0) < estimate_file_cost(1)


def test_estimate_file_cost_floors_negative_size() -> None:
    # A bad stat (negative size) is floored to the base cost, never below it.
    assert estimate_file_cost(-100) == estimate_file_cost(0)


# ---------------------------------------------------------------------------
# S12: pre-parse enumeration — discover_content_files
# ---------------------------------------------------------------------------
#
# The cover guarantee that the barrier reduce depends on: the sharder's file set
# must be EXACTLY the set ContentDiscovery parses. The discriminating test
# (test_discover_matches_content_discovery) compares against the real discovery
# walk, so it fails if the two ever diverge.


def _build_content_tree(content_dir: Path) -> None:
    """A representative content tree: nested sections, _index, multiple extensions,
    plus files/dirs that discovery must skip."""
    (content_dir / "docs" / "guide").mkdir(parents=True)
    (content_dir / "blog").mkdir(parents=True)
    (content_dir / "_index.md").write_text("# Home\n")
    (content_dir / "about.md").write_text("# About\n")
    (content_dir / "docs" / "_index.md").write_text("# Docs\n")
    (content_dir / "docs" / "intro.md").write_text("# Intro\n" + "x" * 500)
    (content_dir / "docs" / "guide" / "step1.md").write_text("# Step\n")
    # A top-level file that sorts INTO the docs/ subtree differently by raw string
    # ('docs-overview' vs 'docs/...') vs by path components — exercises the
    # OS-separator-independent ordering on the shared fixture.
    (content_dir / "docs-overview.md").write_text("# Overview\n")
    (content_dir / "blog" / "post.markdown").write_text("# Post\n")
    (content_dir / "blog" / "draft.txt").write_text("notes\n")
    # Must be skipped by discovery (and therefore by the sharder):
    (content_dir / ".hidden.md").write_text("nope\n")
    (content_dir / "_private.md").write_text("nope\n")
    (content_dir / "image.png").write_text("not content\n")
    (content_dir / "_drafts").mkdir()
    (content_dir / "_drafts" / "x.md").write_text("nope\n")


def test_discover_matches_content_discovery(tmp_path: Path) -> None:
    """The cover: discover_content_files enumerates EXACTLY the files
    ContentDiscovery turns into pages — no more, no fewer."""
    from bengal.content.discovery.content_discovery import ContentDiscovery

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    _build_content_tree(content_dir)

    _sections, pages = ContentDiscovery(content_dir).discover()
    discovered = {p.source_path for p in pages}

    enumerated = {f.source_path for f in discover_content_files(content_dir)}

    assert enumerated == discovered
    assert enumerated  # non-vacuous: the tree really has content


def test_discover_skips_hidden_and_underscore_but_keeps_index(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    _build_content_tree(content_dir)

    names = {f.source_path.name for f in discover_content_files(content_dir)}

    assert "_index.md" in names  # section-index pages are content
    assert "about.md" in names
    assert ".hidden.md" not in names
    assert "_private.md" not in names
    assert "x.md" not in names  # under skipped _drafts/
    assert "image.png" not in names  # not a content extension


def test_discover_recurses_subdirectories(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    _build_content_tree(content_dir)

    by_name = {f.source_path.name: f for f in discover_content_files(content_dir)}

    # Two levels deep (content/docs/guide/step1.md) is reached.
    assert "step1.md" in by_name
    assert by_name["step1.md"].section_key == "docs"
    # Top-level files carry no section key.
    assert by_name["about.md"].section_key == ""


def test_discover_sizes_reflect_bytes(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    big = content_dir / "big.md"
    small = content_dir / "small.md"
    big.write_text("y" * 4096)
    small.write_text("y")

    by_name = {f.source_path.name: f for f in discover_content_files(content_dir)}
    assert by_name["big.md"].size_bytes == big.stat().st_size
    assert by_name["big.md"].size_bytes > by_name["small.md"].size_bytes


def test_discover_is_deterministic_and_sorted(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    _build_content_tree(content_dir)

    a = discover_content_files(content_dir)
    b = discover_content_files(content_dir)
    assert a == b
    # Ordered by path COMPONENTS (not str(path)), so the index→file mapping is
    # deterministic across filesystems and OS path separators. On the shared
    # fixture this discriminates a str-sort bug: 'docs-overview.md' vs the
    # 'docs/' subtree order under str differs from the component order.
    paths = [f.source_path for f in a]
    assert paths == sorted(paths, key=lambda p: p.parts)


def test_discover_order_is_os_separator_independent(tmp_path: Path) -> None:
    """Files order by path COMPONENTS, not the raw string, so a sibling file never
    interleaves into a directory's subtree differently across operating systems.

    A ``str(Path)`` sort key places ``docs-overview.md`` BEFORE ``docs/intro.md``
    on POSIX (``-`` 0x2d < ``/`` 0x2f) but AFTER it on Windows (``-`` < ``\\`` 0x5c),
    which would shift shard assignments cross-platform. The component-tuple key
    (``'docs'`` < ``'docs-overview.md'``) yields the same order everywhere.
    """
    content_dir = tmp_path / "content"
    (content_dir / "docs").mkdir(parents=True)
    (content_dir / "docs" / "intro.md").write_text("a")
    (content_dir / "docs-overview.md").write_text("b")

    names = [f.source_path.name for f in discover_content_files(content_dir)]
    # 'docs' (the directory component) sorts before 'docs-overview.md', so the file
    # inside docs/ comes first — on every platform.
    assert names.index("intro.md") < names.index("docs-overview.md")


def test_discover_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert discover_content_files(tmp_path / "does-not-exist") == []


def test_discover_then_partition_is_a_cover(tmp_path: Path) -> None:
    """End-to-end: every discovered file lands in exactly one shard."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    _build_content_tree(content_dir)

    files = discover_content_files(content_dir)
    shards = partition_content_files(files, 4)

    flat = [i for shard in shards for i in shard]
    assert sorted(flat) == list(range(len(files)))
    assert len(flat) == len(set(flat))
