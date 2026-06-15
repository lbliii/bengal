"""
Record-only consumer of the committed warm-build scaling baseline (#331).

This test CONSUMES ``benchmarks/baselines/warm_build.json`` (the warm/incremental
single-page rebuild baseline) so the baseline is exercised by the suite, and it
exercises the reusable comparison logic that the v0.6.0 proportional-rebuild
sagas (#332/#333) will call to prove their speedup.

RECORD-ONLY by design (maintainer decision): this test does NOT run the (slow)
benchmark and does NOT assert any wall-clock threshold, so it can never go
flaky-red on a noisy runner. It is fast (pure JSON + arithmetic), which is why
it lives in the canonical ``poe benchmark-smoke`` set rather than the opt-in
timed-benchmark tests. It asserts only structural / contract invariants:

  * the committed baseline exists, is shaped like its neighbours
    (metadata + data.cells), and is flagged record_only;
  * it captures the warm single-page rebuild metric at >= 2 site sizes;
  * the warm cost grows with total page count today (the scaling curve the
    proportional-rebuild saga must flatten — this is the number to beat);
  * ``compare_to_baseline`` reports a speedup when a downstream saga feeds in a
    faster measurement (the assertion #332/#333 will rely on).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BENCHMARKS = REPO_ROOT / "benchmarks"
BASELINE = BENCHMARKS / "baselines" / "warm_build.json"

# The emitter/comparison module lives under benchmarks/; import its reusable
# comparison helpers without running any build.
sys.path.insert(0, str(BENCHMARKS))
from benchmark_warm_build_scaling import (  # noqa: E402
    WARM_METRIC,
    compare_to_baseline,
    load_baseline,
)


def test_warm_build_baseline_is_committed_and_well_formed() -> None:
    """The committed baseline exists and mirrors the neighbouring baseline shape."""
    assert BASELINE.exists(), (
        f"missing committed warm-build baseline at {BASELINE}; "
        "regenerate with: python benchmarks/benchmark_warm_build_scaling.py --publish"
    )
    payload = json.loads(BASELINE.read_text())
    assert set(payload) >= {"metadata", "data"}, (
        "baseline must have metadata + data (gil_speedup shape)"
    )
    meta = payload["metadata"]
    assert meta.get("record_only") is True, "warm baseline must be flagged record_only"
    assert "warm" in payload["data"]["methodology"].lower(), (
        "methodology must distinguish warm vs cold"
    )


def test_warm_build_baseline_covers_multiple_sizes_with_metric() -> None:
    """>= 2 site sizes, each carrying the warm single-page rebuild metric."""
    cells = load_baseline(BASELINE)["data"]["cells"]
    sizes = sorted(int(c["pages"]) for c in cells)
    assert len(sizes) >= 2, f"baseline must cover >=2 site sizes, got {sizes}"
    for cell in cells:
        assert WARM_METRIC in cell, f"cell {cell.get('pages')} missing {WARM_METRIC}"
        assert cell[WARM_METRIC] > 0, f"cell {cell.get('pages')} has non-positive warm time"
        # Warm time must be cheaper than the cold build it followed (sanity: an
        # incremental single-page rebuild is not a full cold rebuild).
        assert cell[WARM_METRIC] < cell["cold_s"], (
            f"cell {cell.get('pages')}: warm rebuild ({cell[WARM_METRIC]:.3f}s) "
            f"should be cheaper than cold ({cell['cold_s']:.3f}s)"
        )


def test_warm_build_baseline_shows_total_pages_scaling() -> None:
    """
    The current warm rebuild cost rises with total page count.

    This is the property the proportional-discovery saga (#332/#333) must flatten:
    today a single-page edit re-does work proportional to the whole site, so the
    larger site's warm rebuild is strictly slower. If this assertion ever flips
    (warm cost no longer grows with size), proportional rebuild has landed and
    this baseline should be re-captured / promoted.
    """
    cells = sorted(load_baseline(BASELINE)["data"]["cells"], key=lambda c: int(c["pages"]))
    smallest, largest = cells[0], cells[-1]
    assert int(largest["pages"]) > int(smallest["pages"])
    assert largest[WARM_METRIC] > smallest[WARM_METRIC], (
        "expected warm single-page rebuild to scale UP with total pages "
        f"({smallest['pages']}p={smallest[WARM_METRIC]:.3f}s vs "
        f"{largest['pages']}p={largest[WARM_METRIC]:.3f}s); if this no longer "
        "holds, proportional rebuild may have landed — re-capture the baseline"
    )


def test_compare_to_baseline_reports_downstream_speedup() -> None:
    """
    The reusable comparison logic reports a speedup for a faster measurement.

    This is the exact call #332/#333 will make: feed in measured cells and read
    back per-size delta/speedup vs the committed baseline. A halved warm time
    must surface as ~2x speedup and a negative delta.
    """
    baseline = load_baseline(BASELINE)
    cells = baseline["data"]["cells"]
    faster = [{"pages": int(c["pages"]), WARM_METRIC: c[WARM_METRIC] / 2.0} for c in cells]
    rows = compare_to_baseline(baseline, faster)
    assert rows, "comparison should produce a row per shared size"
    for row in rows:
        assert row["speedup"] == pytest.approx(2.0, rel=1e-6)
        assert row["delta"] == pytest.approx(-0.5, rel=1e-6)
