"""Unit tests for the S13.4e generated-page sharding helpers (issue #350).

Covers the two new pure units that move generated-page rendering (tag / tag-index / archive)
off the serial parent and onto the fork workers:

- ``_assign_generated_pages`` — deterministic, cross-OS-stable, exact-cover LPT balance of the
  generated pages across the content workers (populates the reserved
  ``RenderPlan.generated_page_assignments`` slot).
- ``picklable_metadata`` — flattens the live ``Page``/``Section`` refs + ``MappingProxyType`` that
  generated pages inject into their metadata to a picklable, freeze-identical form, so the
  worker → parent ``RenderChunkResult`` pickles without changing output or the page-artifact cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from bengal.orchestration.render.isolated.shard_backend import _assign_generated_pages
from bengal.orchestration.render.isolated.transport import picklable_metadata
from bengal.rendering.page_artifact import _freeze_json


@dataclass
class _FakePage:
    """Minimal stand-in for the assignment helper (it touches source_path + metadata only)."""

    source_path: Path
    metadata: dict[str, Any]


def _gen(name: str, *, posts: int = 0) -> _FakePage:
    return _FakePage(
        source_path=Path(f".bengal/generated/{name}/index.md"),
        metadata={"_posts": list(range(posts))} if posts else {},
    )


def test_assign_generated_pages_exact_cover_and_in_range():
    pages = [_gen(f"tags/t{i}", posts=i) for i in range(7)]
    assignment = _assign_generated_pages(pages, 3)
    # Every page assigned exactly once, to a valid worker index.
    assert set(assignment) == {p.source_path for p in pages}
    assert all(0 <= w < 3 for w in assignment.values())


def test_assign_generated_pages_is_deterministic_regardless_of_input_order():
    pages = [_gen(f"tags/t{i}", posts=(i * 7) % 11) for i in range(9)]
    forward = _assign_generated_pages(pages, 4)
    reverse = _assign_generated_pages(list(reversed(pages)), 4)
    # Ordering is keyed by source_path.parts, so input order must not change the result.
    assert forward == reverse


def test_assign_generated_pages_distributes_load_across_workers():
    # Many comparable-cost pages must spread across all workers, not pile onto worker 0.
    pages = [_gen(f"tags/t{i:02d}", posts=5) for i in range(12)]
    assignment = _assign_generated_pages(pages, 4)
    used_workers = set(assignment.values())
    assert used_workers == {0, 1, 2, 3}, f"load not spread: only used {sorted(used_workers)}"


def test_assign_generated_pages_edge_cases():
    assert _assign_generated_pages([], 4) == {}
    assert _assign_generated_pages([_gen("tags/t0")], 0) == {}
    one = [_gen("tags/only")]
    assert _assign_generated_pages(one, 4) == {one[0].source_path: 0}


@dataclass
class _LiveRef:
    """Stands in for a live Page/Section ref injected into generated-page metadata."""

    title: str

    def __str__(self) -> str:
        return f"_LiveRef({self.title})"


def test_picklable_metadata_round_trips_through_pickle():
    import pickle

    meta = {
        "title": "All Tags",
        "_generated": True,
        "_tags": {
            "python": {"name": "python", "pages": [_LiveRef("a"), _LiveRef("b")]},
            "_frozen": MappingProxyType({"k": "v"}),
        },
        "weight": 3,
        "date": None,
        "path": Path("/tmp/x"),
    }
    cleaned = picklable_metadata(meta)
    # The whole thing now pickles (the original would raise on the MappingProxyType / live refs).
    pickle.loads(pickle.dumps(cleaned))


def test_picklable_metadata_is_freeze_identical_to_the_original():
    # The transform must be invisible under PageArtifact._freeze_json — so the page-artifact
    # cache (and any _freeze_mapping consumer) is byte-identical thread-vs-shard.
    meta = {
        "title": "All Tags",
        "_tags": {"python": {"pages": [_LiveRef("a"), _LiveRef("b")]}},
        "_frozen": MappingProxyType({"k": "v"}),
        "tags": ["a", "b"],
        "path": Path("/tmp/x"),
        "n": 7,
    }
    assert _freeze_json(picklable_metadata(meta)) == _freeze_json(meta)


def test_picklable_metadata_leaves_plain_frontmatter_intact():
    # A content page's frontmatter is already picklable; the transform must not perturb its values.
    meta = {"title": "Post", "tags": ["x", "y"], "weight": 2, "draft": False}
    assert picklable_metadata(meta) == meta
