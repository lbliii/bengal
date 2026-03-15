"""Scaling regression tests — assert that build phases stay linear.

Runs timed builds at two page counts (SMALL, LARGE) and asserts the
per-doubling ratio stays below LINEAR_THRESHOLD for every phase group.
Catches O(n^2) regressions before they hit production.

Run with:
    cd /path/to/bengal && uv run pytest benchmarks/test_scaling.py -v

The test is intentionally deterministic (force_sequential, no incremental) so
that timing ratios reflect algorithmic complexity, not scheduling jitter.

Math: if LARGE = 4 * SMALL (2 doublings), an O(n) phase has raw ratio ~4x
and per-doubling ratio ~2.0x. An O(n^2) phase has raw ratio ~16x and
per-doubling ratio ~4.0x. LINEAR_THRESHOLD (2.2) catches the latter.
"""

import math
import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.build.profiler import (
    LINEAR_THRESHOLD,
    PHASE_GROUPS,
    PhaseTimer,
    format_scaling_table,
)

SMALL = 256
LARGE = 1024
SIZE_RATIO = LARGE / SMALL
DOUBLINGS = math.log2(SIZE_RATIO)

JITTER_FLOOR_MS = 10.0


def _create_site(num_pages: int) -> Path:
    """Create a minimal temporary site with N pages and varied tags."""
    tmp = Path(tempfile.mkdtemp(prefix=f"bengal_scale_{num_pages}_"))
    content = tmp / "content" / "posts"
    content.mkdir(parents=True)
    (tmp / "public").mkdir()

    for i in range(num_pages):
        tag_a = f"tag-{i % 10}"
        tag_b = f"category-{i % 7}"
        md = (
            f"---\n"
            f'title: "Post {i}"\n'
            f"date: 2025-06-{(i % 28) + 1:02d}\n"
            f"tags: [{tag_a}, {tag_b}]\n"
            f"---\n\n"
            f"# Post {i}\n\n"
            f"Lorem ipsum dolor sit amet. Paragraph for post {i}.\n"
        )
        (content / f"post-{i}.md").write_text(md)

    (tmp / "content" / "_index.md").write_text("---\ntitle: Home\n---\n\n# Site\n")
    (tmp / "content" / "posts" / "_index.md").write_text("---\ntitle: Posts\n---\n")

    (tmp / "bengal.toml").write_text(
        'title = "Scaling Test"\n'
        'baseurl = "https://example.com"\n\n'
        "[build]\n"
        'theme = "default"\n'
        "parallel = true\n"
        "minify_assets = false\n"
        "optimize_assets = false\n"
        "fingerprint_assets = false\n\n"
        "[features]\n"
        "sitemap = true\n"
        "rss = true\n"
        "json_index = true\n"
    )
    return tmp


def _run_timed_build(site_dir: Path) -> PhaseTimer:
    """Build the site with phase instrumentation, return the timer."""
    site = Site.from_config(site_dir)

    for d in [site.output_dir, site_dir / ".bengal"]:
        if d.exists():
            shutil.rmtree(d)

    timer = PhaseTimer()
    opts = BuildOptions(
        force_sequential=True,
        incremental=False,
        verbose=False,
        quiet=True,
        on_phase_start=timer.on_start,
        on_phase_complete=timer.on_complete,
    )
    site.build(options=opts)
    return timer


@pytest.fixture(scope="module")
def scaling_results() -> dict[int, PhaseTimer]:
    """Build at SMALL and LARGE page counts, cache results for all tests."""
    results: dict[int, PhaseTimer] = {}
    dirs: list[Path] = []
    try:
        for n in (SMALL, LARGE):
            d = _create_site(n)
            dirs.append(d)
            results[n] = _run_timed_build(d)
    finally:
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
    return results


def _per_doubling_ratio(results: dict[int, PhaseTimer], group: str) -> float | None:
    """Compute the per-doubling timing ratio for a phase group.

    Normalizes the raw ratio (LARGE/SMALL) to a per-doubling basis so the
    threshold works regardless of SIZE_RATIO.  Returns None if the SMALL
    timing is below the jitter floor.
    """
    small_ms = results[SMALL].group_totals().get(group, 0.0)
    large_ms = results[LARGE].group_totals().get(group, 0.0)
    if small_ms < JITTER_FLOOR_MS:
        return None
    raw = large_ms / small_ms
    return raw ** (1.0 / DOUBLINGS)


class TestPhaseScaling:
    """Each phase group must scale at most linearly (per-doubling < LINEAR_THRESHOLD)."""

    @pytest.mark.parametrize("group", list(PHASE_GROUPS.keys()))
    def test_phase_group_linear(self, scaling_results: dict[int, PhaseTimer], group: str) -> None:
        ratio = _per_doubling_ratio(scaling_results, group)
        if ratio is None:
            pytest.skip(f"{group} too fast to measure ({JITTER_FLOOR_MS}ms floor)")

        assert ratio < LINEAR_THRESHOLD, (
            f"{group} scales super-linearly: {ratio:.2f}x per doubling "
            f"(raw {ratio**DOUBLINGS:.2f}x for {SIZE_RATIO:.0f}x pages, "
            f"threshold: {LINEAR_THRESHOLD}x per doubling)"
        )

    def test_wall_time_linear(self, scaling_results: dict[int, PhaseTimer]) -> None:
        small_total = scaling_results[SMALL].total_ms()
        large_total = scaling_results[LARGE].total_ms()
        if small_total < JITTER_FLOOR_MS:
            pytest.skip("Total build too fast to measure")

        raw = large_total / small_total
        ratio = raw ** (1.0 / DOUBLINGS)
        assert ratio < LINEAR_THRESHOLD, (
            f"Total build scales super-linearly: {ratio:.2f}x per doubling "
            f"(raw {raw:.2f}x for {SIZE_RATIO:.0f}x pages, "
            f"threshold: {LINEAR_THRESHOLD}x per doubling)"
        )

    def test_pages_per_second_floor(self, scaling_results: dict[int, PhaseTimer]) -> None:
        """Large build should sustain at least 50 pages/second."""
        total_s = scaling_results[LARGE].total_ms() / 1000
        pps = LARGE / total_s if total_s > 0 else 0
        assert pps > 50, f"Large build too slow: {pps:.0f} pages/sec (minimum 50)"


class TestScalingReport:
    """Print a human-readable report (always passes, for CI logs)."""

    def test_print_scaling_table(self, scaling_results: dict[int, PhaseTimer]) -> None:
        report = format_scaling_table(scaling_results)
        print(f"\n{report}")
