"""
Benchmark first vs second warm build consistency (dev server scenario).

Investigates why the first file-edit-triggered warm rebuild can be slower than
the second, even though both are incremental builds after a cold build.

Flow (matches dev server BuildTrigger):
  1. Cold build: site.build(incremental=False)
  2. Warm 1: prepare_for_rebuild() + build(incremental=True, changed_sources)
  3. Warm 2: prepare_for_rebuild() + build(incremental=True, changed_sources)
  4. Compare Warm 1 vs Warm 2 times

Hypotheses for first-warm slowdown:
  - Thread pool / pipeline creation warmup on watcher-triggered path
  - Template engine or Kida bytecode cache cold on first render
  - Provenance filter or snapshot loading differences
  - clear_thread_local_pipelines() forcing fresh pipeline creation on warm 1
  - Index/section pages (e.g. docs/_index.md) triggering more downstream work
    than leaf pages (cascade, children, nav)

Run: pytest tests/performance/benchmark_warm_build_consistency.py -v -m performance
     (or python -m pytest ... --runxfail to include performance markers)

Or: python tests/performance/benchmark_warm_build_consistency.py
    python tests/performance/benchmark_warm_build_consistency.py --index   # edit docs/_index
    python tests/performance/benchmark_warm_build_consistency.py --leaf   # edit leaf page
    python tests/performance/benchmark_warm_build_consistency.py --compare  # both, compare
"""

from __future__ import annotations

import argparse
import shutil
import statistics
import sys
import time
from pathlib import Path
from tempfile import mkdtemp

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.utils.observability.profile import BuildProfile

# Bengal docs site root (site/ relative to repo)
BENGAL_SITE_ROOT = Path(__file__).resolve().parent.parent.parent / "site"


def create_test_site(num_pages: int = 100) -> Path:
    """Create a test site for warm build benchmarking."""
    site_root = Path(mkdtemp(prefix="bengal_warm_bench_"))

    content_dir = site_root / "content"
    content_dir.mkdir(parents=True)

    (site_root / "bengal.toml").write_text(
        """
[site]
title = "Warm Build Benchmark"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
parallel = true
"""
    )

    for i in range(num_pages):
        section_dir = content_dir / f"section-{i // 20 + 1}"
        section_dir.mkdir(exist_ok=True)
        if not (section_dir / "_index.md").exists():
            (section_dir / "_index.md").write_text(
                f"---\ntitle: Section {i // 20 + 1}\n---\n# Section\n"
            )

        (section_dir / f"page-{i + 1:03d}.md").write_text(
            f"""---
title: "Page {i + 1}"
date: 2025-01-01
tags: ["tag-{i % 10}"]
---

# Page {i + 1}

Content for page {i + 1}.
"""
        )

    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Welcome\n")

    return site_root


def run_warm_build_consistency_benchmark(
    site_root: Path,
    num_warm_builds: int = 5,
    file_to_modify: Path | None = None,
) -> dict[str, float]:
    """
    Run cold + repeated warm builds, return timing stats.

    Returns dict with: cold_s, warm_1_s, warm_2_s, warm_1_vs_2_ratio, etc.
    """
    site = Site.from_config(site_root)
    content_dir = site_root / "content"
    pages = sorted(content_dir.glob("section-*/page-*.md"))
    target_file = file_to_modify or (pages[0] if pages else content_dir / "index.md")

    # Cold build
    cold_start = time.perf_counter()
    site.build(BuildOptions(incremental=False, profile=BuildProfile.WRITER))
    cold_s = time.perf_counter() - cold_start

    warm_times: list[float] = []

    for i in range(num_warm_builds):
        original = target_file.read_text()
        modified = original + f"\n\n<!-- warm-{i + 1} -->\n"
        target_file.write_text(modified)

        site.prepare_for_rebuild()
        warm_start = time.perf_counter()
        site.build(
            BuildOptions(
                incremental=True,
                profile=BuildProfile.WRITER,
                changed_sources={target_file},
            )
        )
        warm_s = time.perf_counter() - warm_start
        warm_times.append(warm_s)

        target_file.write_text(original)

    return {
        "cold_s": cold_s,
        "warm_1_s": warm_times[0] if warm_times else 0,
        "warm_2_s": warm_times[1] if len(warm_times) > 1 else 0,
        "warm_mean_s": statistics.mean(warm_times) if warm_times else 0,
        "warm_1_vs_2_ratio": (
            warm_times[0] / warm_times[1] if len(warm_times) > 1 and warm_times[1] > 0 else 1.0
        ),
        "warm_times": warm_times,
    }


@pytest.mark.performance
@pytest.mark.slow
def test_warm_build_first_vs_second_consistency() -> None:
    """
    Assert first warm build is not excessively slower than second.

    Documents the first-warm overhead; fails if ratio exceeds 1.5x
    (first warm taking >50% longer than second suggests regression).
    """
    site_root = create_test_site(num_pages=50)
    try:
        result = run_warm_build_consistency_benchmark(site_root, num_warm_builds=4)
        ratio = result["warm_1_vs_2_ratio"]
        # Allow up to 1.5x: first warm can be slower, but not drastically
        assert ratio <= 1.5, (
            f"First warm build {ratio:.2f}x slower than second "
            f"(warm_1={result['warm_1_s']:.3f}s, warm_2={result['warm_2_s']:.3f}s). "
            "Investigate first-warm overhead."
        )
    finally:
        shutil.rmtree(site_root, ignore_errors=True)


def _print_result(label: str, result: dict[str, float]) -> None:
    """Print a single benchmark result."""
    print(f"{label}:")
    print(f"  Cold build:     {result['cold_s']:.3f}s")
    print(f"  Warm build 1:   {result['warm_1_s']:.3f}s")
    print(f"  Warm build 2:   {result['warm_2_s']:.3f}s")
    print(f"  Warm mean:      {result['warm_mean_s']:.3f}s")
    print(f"  Warm 1 vs 2:    {result['warm_1_vs_2_ratio']:.2f}x")
    print("  All warm times:", [f"{t:.3f}s" for t in result["warm_times"]])
    if result["warm_1_vs_2_ratio"] > 1.1:
        print(f"  ⚠️  First warm slower than second ({result['warm_1_vs_2_ratio']:.2f}x)")
    else:
        print("  ✅ Warm builds consistent.")
    print()


def run_benchmark(
    site_root: Path | None = None,
    file_to_modify: Path | None = None,
    num_warm_builds: int = 5,
) -> dict[str, float]:
    """Run benchmark and print results (for manual execution)."""
    print("=" * 80)
    print("WARM BUILD CONSISTENCY BENCHMARK")
    print("=" * 80)
    print()
    print("Simulates dev server: cold build, then repeated warm builds")
    print("(prepare_for_rebuild + build with changed_sources)")
    print()

    use_synthetic = site_root is None
    if site_root is None:
        site_root = create_test_site(num_pages=100)

    try:
        result = run_warm_build_consistency_benchmark(
            site_root,
            num_warm_builds=num_warm_builds,
            file_to_modify=file_to_modify,
        )

        label = f"Editing {file_to_modify.name}" if file_to_modify else "Synthetic site"
        _print_result(label, result)
        return result
    finally:
        if use_synthetic:
            shutil.rmtree(site_root, ignore_errors=True)


def run_compare_index_vs_leaf() -> None:
    """Run benchmark for index vs leaf page and compare."""
    if not BENGAL_SITE_ROOT.exists():
        print(f"Bengal site not found at {BENGAL_SITE_ROOT}")
        print("Run from Bengal repo root.")
        sys.exit(1)

    index_file = BENGAL_SITE_ROOT / "content" / "docs" / "_index.md"
    leaf_file = BENGAL_SITE_ROOT / "content" / "docs" / "theming" / "recipes" / "archive-page.md"

    if not index_file.exists():
        print(f"Index file not found: {index_file}")
        sys.exit(1)
    if not leaf_file.exists():
        print(f"Leaf file not found: {leaf_file}")
        sys.exit(1)

    print("=" * 80)
    print("INDEX vs LEAF PAGE WARM BUILD COMPARISON")
    print("=" * 80)
    print()
    print("Compares warm build times when editing:")
    print(f"  Index: {index_file.relative_to(BENGAL_SITE_ROOT)}")
    print(f"  Leaf:  {leaf_file.relative_to(BENGAL_SITE_ROOT)}")
    print()

    result_index = run_warm_build_consistency_benchmark(
        BENGAL_SITE_ROOT,
        num_warm_builds=4,
        file_to_modify=index_file,
    )
    _print_result("Editing docs/_index.md (section index)", result_index)

    result_leaf = run_warm_build_consistency_benchmark(
        BENGAL_SITE_ROOT,
        num_warm_builds=4,
        file_to_modify=leaf_file,
    )
    _print_result("Editing archive-page.md (leaf)", result_leaf)

    # Compare
    idx_mean = result_index["warm_mean_s"]
    leaf_mean = result_leaf["warm_mean_s"]
    ratio = idx_mean / leaf_mean if leaf_mean > 0 else 0
    print("Comparison:")
    print(f"  Index warm mean: {idx_mean:.3f}s")
    print(f"  Leaf warm mean:  {leaf_mean:.3f}s")
    print(f"  Index/Leaf:      {ratio:.2f}x")
    if ratio > 1.2:
        print(
            f"  ⚠️  Index page edits are {ratio:.1f}x slower than leaf. "
            "Section/cascade work may dominate."
        )
    else:
        print("  ✅ Index and leaf warm times are similar.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm build consistency benchmark (index vs leaf)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--index",
        action="store_true",
        help="Use Bengal site, edit docs/_index.md (section index)",
    )
    group.add_argument(
        "--leaf",
        action="store_true",
        help="Use Bengal site, edit docs/theming/recipes/archive-page.md (leaf)",
    )
    group.add_argument(
        "--compare",
        action="store_true",
        help="Run both index and leaf, compare warm build times",
    )
    args = parser.parse_args()

    if args.compare:
        run_compare_index_vs_leaf()
    elif args.index:
        run_benchmark(
            site_root=BENGAL_SITE_ROOT,
            file_to_modify=BENGAL_SITE_ROOT / "content" / "docs" / "_index.md",
        )
    elif args.leaf:
        run_benchmark(
            site_root=BENGAL_SITE_ROOT,
            file_to_modify=BENGAL_SITE_ROOT
            / "content"
            / "docs"
            / "theming"
            / "recipes"
            / "archive-page.md",
        )
    else:
        run_benchmark()


if __name__ == "__main__":
    main()
