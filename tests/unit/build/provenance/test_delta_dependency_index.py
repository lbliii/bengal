"""Byte-parity gate for the incremental dependency-index writer.

The warm-build optimization (``BENGAL_PROVENANCE_DELTA_SAVE``) updates the dependency
reverse map incrementally on ``save()`` from the LOADED prior index plus the in-memory
records of changed pages only — instead of re-reading every page's record from disk (which
dominated warm 1-page-edit builds). This is only safe if the incremental result is
**byte-identical** to a full ``_build_dependency_index`` rebuild of the same final state.

These tests assert exactly that across edit / add / delete / multi-consumer / combined
scenarios, and that the rollback lever (``=0``) forces the full rebuild. If a future change
breaks the equivalence, CI fails here rather than silently shipping a stale reverse map
(which would under-rebuild on warm incremental builds — a correctness bug, not a perf one).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import ContentHash, Provenance, ProvenanceRecord

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    import pytest

# A shared theme template every page consumes — the multi-consumer edge that must survive a
# single-page edit. ``config`` inputs are present specifically to prove both paths skip them.
_SHARED_TEMPLATE = ("template", "templates/page.html", "tmpl-v1")
_SITE_CONFIG = ("config", "bengal.toml", "cfg-v1")


def _rec(page: str, *inputs: tuple[str, str, str]) -> ProvenanceRecord:
    """Build a record for ``page`` from ``(kind, path, hash)`` inputs."""
    prov = Provenance()
    for kind, path, content_hash in inputs:
        prov = prov.with_input(kind, CacheKey(path), ContentHash(content_hash))
    return ProvenanceRecord(
        page_path=CacheKey(page),
        provenance=prov,
        output_hash=ContentHash(f"out-{page}"),
    )


def _read_dep_index(cache_dir: Path) -> tuple[str, dict]:
    """Return (raw JSON text, parsed ``dependencies`` mapping) for byte + semantic compare."""
    text = (cache_dir / "dependency-index.json").read_text(encoding="utf-8")
    return text, json.loads(text)["dependencies"]


def _full_rebuild(cache_dir: Path, records: Iterable[ProvenanceRecord]) -> tuple[str, dict]:
    """Ground truth: a from-scratch full rebuild of the final record set.

    A fresh cache has an empty base index, so ``save()`` deterministically takes the full
    ``_build_dependency_index`` branch — the canonical output the delta must reproduce.
    """
    cache = ProvenanceCache(cache_dir=cache_dir)
    cache.store_batch(list(records))
    cache.save()
    return _read_dep_index(cache_dir)


class _BranchSpy:
    """Records which dependency-index branch ``save()`` took (delta vs full rebuild)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[str] = []
        inc = ProvenanceCache._incremental_dependency_index
        full = ProvenanceCache._build_dependency_index

        def spy_inc(self_: ProvenanceCache, *a: object, **k: object) -> object:
            self.calls.append("incremental")
            return inc(self_, *a, **k)  # type: ignore[arg-type]

        def spy_full(self_: ProvenanceCache, *a: object, **k: object) -> object:
            self.calls.append("full")
            return full(self_, *a, **k)  # type: ignore[arg-type]

        monkeypatch.setattr(ProvenanceCache, "_incremental_dependency_index", spy_inc)
        monkeypatch.setattr(ProvenanceCache, "_build_dependency_index", spy_full)


def _cold_then_warm(
    cache_dir: Path,
    initial: list[ProvenanceRecord],
    mutate,
) -> ProvenanceCache:
    """Cold build (full rebuild) then a warm reopen that applies ``mutate`` and saves (delta).

    Returns the warm cache after ``save()`` so the test can read its on-disk index.
    """
    cold = ProvenanceCache(cache_dir=cache_dir)
    cold.store_batch(initial)
    cold.save()

    warm = ProvenanceCache(cache_dir=cache_dir)
    warm._ensure_loaded()  # load the prior index so save() has a non-empty base
    mutate(warm)
    warm.save()
    return warm


def _assert_delta_matches_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    initial: list[ProvenanceRecord],
    final: list[ProvenanceRecord],
    mutate,
) -> None:
    """Core gate: warm delta save == from-scratch full rebuild, byte-for-byte."""
    monkeypatch.setenv("BENGAL_PROVENANCE_DELTA_SAVE", "1")
    spy = _BranchSpy(monkeypatch)

    _cold_then_warm(tmp_path / "warm", initial, mutate)
    delta_text, delta_deps = _read_dep_index(tmp_path / "warm")

    # The warm save must have used the incremental branch (not silently fallen back to full).
    warm_calls = spy.calls[1:]  # calls[0] is the cold build's full rebuild
    assert warm_calls == ["incremental"], f"warm save did not use delta: {spy.calls}"

    full_text, full_deps = _full_rebuild(tmp_path / "full", final)

    assert delta_deps == full_deps  # semantic: same reverse map
    assert delta_text == full_text  # byte-identical serialization


def test_delta_matches_rebuild_on_edit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Editing one page's content input reproduces the full rebuild exactly."""
    initial = [
        _rec("a.md", ("content", "content/a.md", "a-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("b.md", ("content", "content/b.md", "b-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
    ]
    edited_a = _rec("a.md", ("content", "content/a.md", "a-v2"), _SHARED_TEMPLATE, _SITE_CONFIG)
    final = [edited_a, initial[1]]
    _assert_delta_matches_rebuild(
        tmp_path, monkeypatch, initial=initial, final=final, mutate=lambda c: c.store(edited_a)
    )


def test_delta_matches_rebuild_on_add(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Adding a new page reproduces the full rebuild exactly."""
    initial = [
        _rec("a.md", ("content", "content/a.md", "a-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
    ]
    added = _rec("b.md", ("content", "content/b.md", "b-v1"), _SHARED_TEMPLATE, _SITE_CONFIG)
    final = [*initial, added]
    _assert_delta_matches_rebuild(
        tmp_path, monkeypatch, initial=initial, final=final, mutate=lambda c: c.store(added)
    )


def test_delta_matches_rebuild_on_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Deleting a page purges its edges, reproducing the full rebuild exactly.

    A pure deletion stores no new record, so the warm cache is marked dirty explicitly — as a
    real build would when its page set shrinks — and the deleted page is dropped from the index.
    """
    initial = [
        _rec("a.md", ("content", "content/a.md", "a-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("b.md", ("content", "content/b.md", "b-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("gone.md", ("content", "content/gone.md", "g-v1"), ("data", "data/only.yaml", "d-v1")),
    ]
    final = [initial[0], initial[1]]

    def mutate(cache: ProvenanceCache) -> None:
        del cache._index[CacheKey("gone.md")]
        cache._dirty = True

    _assert_delta_matches_rebuild(
        tmp_path, monkeypatch, initial=initial, final=final, mutate=mutate
    )


def test_delta_preserves_multi_consumer_edge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editing one consumer of a shared template keeps the other consumers on that edge.

    This is the failure mode the critique flagged: a naive 'rebuild from changed records only'
    would drop b/c from the shared-template edge. The delta must carry them over from the base.
    """
    initial = [
        _rec("a.md", ("content", "content/a.md", "a-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("b.md", ("content", "content/b.md", "b-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("c.md", ("content", "content/c.md", "c-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
    ]
    edited_a = _rec("a.md", ("content", "content/a.md", "a-v2"), _SHARED_TEMPLATE, _SITE_CONFIG)
    final = [edited_a, initial[1], initial[2]]

    _assert_delta_matches_rebuild(
        tmp_path, monkeypatch, initial=initial, final=final, mutate=lambda c: c.store(edited_a)
    )

    # Explicit: the shared-template edge still lists all three pages.
    cache = ProvenanceCache(cache_dir=tmp_path / "warm")
    cache._ensure_loaded()
    kind, key, _ = _SHARED_TEMPLATE
    assert cache._dependency_index.affected_page_keys(kind, key) == ("a.md", "b.md", "c.md")


def test_delta_matches_rebuild_on_combined_churn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Edit + add + delete + a newly-introduced shared edge, all in one warm save."""
    initial = [
        _rec("a.md", ("content", "content/a.md", "a-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("b.md", ("content", "content/b.md", "b-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("old.md", ("content", "content/old.md", "o-v1"), ("partial", "partials/x.html", "p1")),
    ]
    edited_a = _rec(
        "a.md",
        ("content", "content/a.md", "a-v2"),
        _SHARED_TEMPLATE,
        ("partial", "partials/x.html", "p1"),  # a newly references the partial old.md used
        _SITE_CONFIG,
    )
    added = _rec("new.md", ("content", "content/new.md", "n-v1"), _SHARED_TEMPLATE, _SITE_CONFIG)
    final = [edited_a, initial[1], added]

    def mutate(cache: ProvenanceCache) -> None:
        cache.store(edited_a)
        cache.store(added)
        del cache._index[CacheKey("old.md")]

    _assert_delta_matches_rebuild(
        tmp_path, monkeypatch, initial=initial, final=final, mutate=mutate
    )


def test_full_rebuild_lists_all_same_hash_pages(tmp_path: Path) -> None:
    """Pages with identical inputs share one content-addressed record but must all be listed.

    Regression for a latent reverse-map bug: empty taxonomy pagination pages (e.g. tag:x
    page_1/page_2/page_3) have identical provenance, so they dedup to ONE record whose
    page_path is an arbitrary sibling. The old builder iterated record hashes and listed only
    that one page — silently dropping the others from the reverse map (under-invalidation), and
    non-deterministically (which sibling won depended on store order). The builder must now list
    every page that consumes the input.
    """
    shared = [("taxonomy", "tag:x", "tx-v1"), _SHARED_TEMPLATE]
    pages = [
        _rec(".bengal/generated/tags/x/page_1/index.md", *shared),
        _rec(".bengal/generated/tags/x/page_2/index.md", *shared),
        _rec(".bengal/generated/tags/x/page_3/index.md", *shared),
    ]
    # All three share one combined hash (identical inputs) — the collision that exposed the bug.
    assert len({r.provenance.combined_hash for r in pages}) == 1

    _, deps = _full_rebuild(tmp_path / "full", pages)
    assert deps["taxonomy:tag:x"]["page_keys"] == [
        ".bengal/generated/tags/x/page_1/index.md",
        ".bengal/generated/tags/x/page_2/index.md",
        ".bengal/generated/tags/x/page_3/index.md",
    ]


def test_delta_matches_rebuild_with_same_hash_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Warm delta reproduces the full rebuild when same-hash pagination pages are present.

    This is the real-build scenario the end-to-end measurement caught: editing a content page
    leaves the (cache-hit, same-hash) generated taxonomy pages carried over from the base. The
    delta must keep all of them, byte-identical to a from-scratch rebuild.
    """
    shared = [("taxonomy", "tag:x", "tx-v1"), _SHARED_TEMPLATE]
    initial = [
        _rec("a.md", ("content", "content/a.md", "a-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec(".bengal/generated/tags/x/page_1/index.md", *shared),
        _rec(".bengal/generated/tags/x/page_2/index.md", *shared),
        _rec(".bengal/generated/tags/x/page_3/index.md", *shared),
    ]
    edited_a = _rec("a.md", ("content", "content/a.md", "a-v2"), _SHARED_TEMPLATE, _SITE_CONFIG)
    final = [edited_a, *initial[1:]]
    _assert_delta_matches_rebuild(
        tmp_path, monkeypatch, initial=initial, final=final, mutate=lambda c: c.store(edited_a)
    )


def test_rollback_lever_forces_full_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``BENGAL_PROVENANCE_DELTA_SAVE=0`` forces the full rebuild and still matches."""
    monkeypatch.setenv("BENGAL_PROVENANCE_DELTA_SAVE", "0")
    spy = _BranchSpy(monkeypatch)

    initial = [
        _rec("a.md", ("content", "content/a.md", "a-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
        _rec("b.md", ("content", "content/b.md", "b-v1"), _SHARED_TEMPLATE, _SITE_CONFIG),
    ]
    edited_a = _rec("a.md", ("content", "content/a.md", "a-v2"), _SHARED_TEMPLATE, _SITE_CONFIG)

    _cold_then_warm(tmp_path / "warm", initial, lambda c: c.store(edited_a))

    assert spy.calls == ["full", "full"], f"flag=0 should never use delta: {spy.calls}"
    _, delta_off_deps = _read_dep_index(tmp_path / "warm")
    _, full_deps = _full_rebuild(tmp_path / "full", [edited_a, initial[1]])
    assert delta_off_deps == full_deps
