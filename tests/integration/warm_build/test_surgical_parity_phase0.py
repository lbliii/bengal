"""
Phase 0 guard tests for the persistent-resident-Site warm-rebuild work (#522).

Phase 0 lands the skeleton + the byte-parity safety net only; no surgical
change-type is enabled, so behavior is unchanged. These tests lock in the
foundation every later phase relies on:

1. Determinism floor — two full builds of the same source are byte-identical
   (after normalizing documented timestamp nondeterminism). The surgical
   parity gate is meaningless without this.
2. Discriminating power — the comparison FAILS on a real content difference, so
   a future surgical==full assertion cannot pass vacuously (#130 lesson).
3. Mutator contract — ``SiteStateMutator.apply`` declines conservatively with an
   observable reason (steward: "conservative fallback with reasons").
4. Harness + fallback wiring — the surgical-vs-full gate runs end-to-end; with
   the Phase 0 stub (fallback → full rebuild) the two legs match.

See ``surgical_parity.py`` and ``plan/rfc-persistent-resident-site.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.incremental.state_mutator import SiteStateMutator, SurgicalRebuildPlan

from .conftest import create_output_formats_site_structure, create_taxonomy_site_structure
from .surgical_parity import (
    assert_full_build_deterministic,
    assert_surgical_matches_full,
    diff_trees,
    snapshot_output_tree,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.integration


def _build_cold(site_dir: Path) -> None:
    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()
    site.build(BuildOptions(incremental=False, force_sequential=True))


# ---------------------------------------------------------------------------
# 1. Determinism floor
# ---------------------------------------------------------------------------


def test_full_build_is_byte_deterministic_output_formats(tmp_path: Path) -> None:
    """Two full builds of a site with sitemap/RSS/output-formats match byte-for-byte.

    Output formats carry the most nondeterminism surface (timestamps in
    index.json / agent.json / llm-full.txt) — exactly what the harness must
    normalize. If this fails on something other than a timestamp, there is real
    build nondeterminism to fix before any surgical parity claim.
    """
    src = tmp_path / "src"
    src.mkdir()
    create_output_formats_site_structure(src)
    assert_full_build_deterministic(src, tmp_path / "work")


def test_full_build_is_byte_deterministic_taxonomy(tmp_path: Path) -> None:
    """Determinism also holds for taxonomy (generated tag/category pages)."""
    src = tmp_path / "src"
    src.mkdir()
    create_taxonomy_site_structure(src)
    assert_full_build_deterministic(src, tmp_path / "work")


# ---------------------------------------------------------------------------
# 2. Discriminating power (the comparison is NOT vacuous)
# ---------------------------------------------------------------------------


def test_parity_comparison_detects_a_real_content_difference(tmp_path: Path) -> None:
    """A one-page content change MUST surface as an output-tree diff.

    Guards the #130 vacuous-test failure mode: if this comparison could not
    detect a real divergence, a surgical==full assertion built on it would be
    worthless.
    """
    base = tmp_path / "base"
    base.mkdir()
    create_taxonomy_site_structure(base)

    import shutil

    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    shutil.copytree(base, a_dir)
    shutil.copytree(base, b_dir)

    # Diverge one page's body in b only.
    (b_dir / "content" / "blog" / "post1.md").write_text(
        """---
title: Python Tutorial
date: 2026-01-01
tags: [python, tutorial]
categories: [tutorials]
---

A DIFFERENT python tutorial body that changes the rendered HTML.
"""
    )

    _build_cold(a_dir)
    _build_cold(b_dir)

    diffs = diff_trees(
        snapshot_output_tree(a_dir / "public"),
        snapshot_output_tree(b_dir / "public"),
    )
    assert diffs, "comparison is vacuous: it failed to detect a real content change"
    assert any("post1" in d for d in diffs), f"expected the changed page in diffs, got: {diffs}"


# ---------------------------------------------------------------------------
# 3. Mutator contract (conservative fallback with reasons)
# ---------------------------------------------------------------------------


def test_mutator_declines_conservatively_in_phase0(tmp_path: Path) -> None:
    """Phase 0 SiteStateMutator.apply always returns an observable fallback."""
    src = tmp_path / "src"
    src.mkdir()
    create_taxonomy_site_structure(src)
    site = Site.from_config(src)
    site.discover_content()

    mutator = SiteStateMutator(site=site)
    plan = mutator.apply([src / "content" / "blog" / "post1.md"])

    assert plan.is_fallback, "phase 0 must decline every change"
    assert plan.fallback_reasons, "fallback must name an observable reason"
    assert plan.changed_inputs == (src / "content" / "blog" / "post1.md",)
    assert plan.affected_pages == ()
    assert plan.affected_outputs == ()


def test_empty_plan_is_not_a_fallback() -> None:
    """A plan with no fallback_reasons signals a usable surgical result."""
    assert SurgicalRebuildPlan().is_fallback is False
    assert SurgicalRebuildPlan(fallback_reasons=("x",)).is_fallback is True


# ---------------------------------------------------------------------------
# 4. Harness + fallback wiring (end-to-end)
# ---------------------------------------------------------------------------


def test_surgical_gate_falls_back_to_full_and_matches(tmp_path: Path) -> None:
    """End-to-end: the surgical gate (Phase 0 stub) falls back to full and matches.

    Exercises the full surgical-vs-full harness path. Because the Phase 0 mutator
    declines, the 'surgical' leg performs a full rebuild — so the two legs are
    byte-identical. This proves the harness + fallback contract before any real
    surgical mutation exists.
    """
    src = tmp_path / "src"
    src.mkdir()
    create_taxonomy_site_structure(src)

    def apply_change(site_dir: Path) -> None:
        (site_dir / "content" / "blog" / "post1.md").write_text(
            """---
title: Python Tutorial
date: 2026-01-01
tags: [python, tutorial]
categories: [tutorials]
---

Edited body for the surgical-vs-full parity harness.
"""
        )

    def surgical_rebuild(site_dir: Path) -> SiteStateMutator | None:
        # Mirror the caller contract: attempt surgery; on fallback, full rebuild.
        site = Site.from_config(site_dir)
        site.discover_content()
        site.discover_assets()
        plan = SiteStateMutator(site=site).apply([site_dir / "content" / "blog" / "post1.md"])
        if plan.is_fallback:
            site.build(BuildOptions(incremental=False, force_sequential=True))
        return None

    assert_surgical_matches_full(src, tmp_path / "work", apply_change, surgical_rebuild)
