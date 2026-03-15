#!/usr/bin/env python3
"""
Cross-SSG Build Benchmark: Bengal vs MkDocs vs Pelican
======================================================

Generates identical content and runs cold builds across all three SSGs
on the same machine, same content, same measurement methodology.

Requirements:
    pip install mkdocs pelican

Usage:
    # Quick comparison (64, 256, 1024 pages)
    python benchmarks/benchmark_cross_ssg.py

    # Full comparison (up to 4096 pages)
    python benchmarks/benchmark_cross_ssg.py --full

    # Specific scale
    python benchmarks/benchmark_cross_ssg.py --pages 500

    # Save results to JSON
    python benchmarks/benchmark_cross_ssg.py --output results.json

Methodology:
    - Minimal markdown: YAML frontmatter + 3 lorem ipsum paragraphs
    - Cold builds only (fresh temp directory per run)
    - No asset processing, syntax highlighting, or optimization
    - 3 runs per scale, median reported (resistant to outliers)
    - All SSGs use their default themes
    - Timed via time.perf_counter() around the build command
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

PARAGRAPHS = [
    (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
        "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
    ),
    (
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat "
        "nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui "
        "officia deserunt mollit anim id est laborum."
    ),
    (
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque "
        "laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi "
        "architecto beatae vitae dicta sunt explicabo."
    ),
    (
        "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia "
        "consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro "
        "quisquam est, qui dolorem ipsum quia dolor sit amet."
    ),
    (
        "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium "
        "voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint "
        "occaecati cupiditate non provident."
    ),
    (
        "Temporibus autem quibusdam et aut officiis debitis aut rerum necessitatibus saepe "
        "eveniet ut et voluptates repudiandae sint et molestiae non recusandae. Itaque earum "
        "rerum hic tenetur a sapiente delectus."
    ),
    (
        "Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil impedit quo minus "
        "id quod maxime placeat facere possimus, omnis voluptas assumenda est, omnis dolor "
        "repellendus."
    ),
]


def _random_title(index: int) -> str:
    adjectives = [
        "Amazing",
        "Incredible",
        "Fantastic",
        "Wonderful",
        "Great",
        "Perfect",
        "Beautiful",
        "Awesome",
        "Brilliant",
        "Excellent",
    ]
    nouns = [
        "Story",
        "Article",
        "Post",
        "Guide",
        "Tutorial",
        "Journey",
        "Adventure",
        "Experience",
        "Discovery",
        "Insight",
    ]
    return f"{random.choice(adjectives)} {random.choice(nouns)} {index}"


def _random_body() -> str:
    paras = random.sample(PARAGRAPHS, 3)
    return "\n\n".join(paras)


# ---------------------------------------------------------------------------
# Site generators — each creates a project dir and returns the build command
# ---------------------------------------------------------------------------


def _setup_bengal(root: Path, num_pages: int) -> list[str]:
    content = root / "content"
    content.mkdir()
    (root / "public").mkdir()

    (root / "bengal.toml").write_text(
        'title = "Benchmark"\n'
        'baseurl = "https://example.com"\n'
        "\n"
        "[build]\n"
        'theme = "default"\n'
        "parallel = true\n"
        "minify_assets = false\n"
        "optimize_assets = false\n"
        "fingerprint_assets = false\n"
        "generate_sitemap = false\n"
        "generate_rss = false\n"
    )

    (content / "index.md").write_text(f"---\ntitle: Home\n---\n\n{_random_body()}\n")
    for i in range(1, num_pages):
        (content / f"page-{i:05d}.md").write_text(
            f"---\ntitle: {_random_title(i)}\n---\n\n{_random_body()}\n"
        )

    return [sys.executable, "-m", "bengal", "site", "build", "--fast"]


def _setup_mkdocs(root: Path, num_pages: int) -> list[str]:
    docs = root / "docs"
    docs.mkdir()

    (root / "mkdocs.yml").write_text("site_name: Benchmark\ndocs_dir: docs\nsite_dir: site\n")

    (docs / "index.md").write_text(f"---\ntitle: Home\n---\n\n{_random_body()}\n")
    for i in range(1, num_pages):
        (docs / f"page-{i:05d}.md").write_text(
            f"---\ntitle: {_random_title(i)}\n---\n\n{_random_body()}\n"
        )

    return [sys.executable, "-m", "mkdocs", "build", "--quiet"]


def _setup_pelican(root: Path, num_pages: int) -> list[str]:
    content = root / "content"
    content.mkdir()
    (root / "output").mkdir()

    (root / "pelicanconf.py").write_text(
        "SITENAME = 'Benchmark'\n"
        "SITEURL = 'https://example.com'\n"
        "PATH = 'content'\n"
        "OUTPUT_PATH = 'output'\n"
        "TIMEZONE = 'UTC'\n"
        "DEFAULT_LANG = 'en'\n"
        "FEED_ALL_ATOM = None\n"
        "CATEGORY_FEED_ATOM = None\n"
        "TRANSLATION_FEED_ATOM = None\n"
        "AUTHOR_FEED_ATOM = None\n"
        "AUTHOR_FEED_RSS = None\n"
    )

    for i in range(num_pages):
        title = _random_title(i) if i > 0 else "Home"
        slug = f"page-{i:05d}" if i > 0 else "home"
        # Pelican-native metadata format (most reliable, no plugin needed)
        (content / f"{slug}.md").write_text(
            f"Title: {title}\nSlug: {slug}\nDate: 2025-01-01\n\n{_random_body()}\n"
        )

    return [
        sys.executable,
        "-m",
        "pelican",
        "content",
        "-o",
        "output",
        "-s",
        "pelicanconf.py",
        "--quiet",
    ]


DEFAULT_SSGS = ("bengal", "mkdocs", "pelican")

SSG_SETUP = {
    "bengal": _setup_bengal,
    "mkdocs": _setup_mkdocs,
    "pelican": _setup_pelican,
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    ssg: str
    pages: int
    times: list[float] = field(default_factory=list)
    error: str | None = None

    @property
    def median_time(self) -> float:
        return median(self.times) if self.times else float("inf")

    @property
    def pages_per_sec(self) -> float:
        t = self.median_time
        return self.pages / t if t > 0 else 0.0


def _check_available(ssg: str) -> bool:
    cmd_map = {
        "bengal": [sys.executable, "-m", "bengal", "--version"],
        "mkdocs": [sys.executable, "-m", "mkdocs", "--version"],
        "pelican": [sys.executable, "-m", "pelican", "--version"],
    }
    try:
        subprocess.run(
            cmd_map[ssg],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return True
    except subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired:
        return False


def _bench_temp_dir(ssg: str) -> Path:
    """Return a temp dir for benchmarking, never inside the project root."""
    repo_root = Path(__file__).resolve().parent.parent
    tmp = Path(tempfile.mkdtemp(prefix=f"bench_{ssg}_"))
    try:
        resolved = tmp.resolve()
        if resolved == repo_root or repo_root in resolved.parents:
            shutil.rmtree(tmp, ignore_errors=True)
            base = Path("/tmp") if Path("/tmp").exists() else Path(tempfile.gettempdir())
            tmp = Path(tempfile.mkdtemp(prefix=f"bench_{ssg}_", dir=base))
    except OSError:
        pass
    return tmp


def benchmark_ssg(ssg: str, num_pages: int, runs: int = 3) -> RunResult:
    result = RunResult(ssg=ssg, pages=num_pages)
    setup_fn = SSG_SETUP[ssg]

    for run_idx in range(runs):
        tmp = _bench_temp_dir(ssg)
        try:
            cmd = setup_fn(tmp, num_pages)
            env = {**os.environ, "PYTHON_GIL": "0"}

            start = time.perf_counter()
            proc = subprocess.run(
                cmd,
                cwd=tmp,
                capture_output=True,
                text=True,
                env=env,
                timeout=600,
            )
            elapsed = time.perf_counter() - start

            if proc.returncode != 0:
                stderr_tail = (proc.stderr or "")[-500:]
                result.error = f"Run {run_idx + 1} failed (exit {proc.returncode}): {stderr_tail}"
                print(f"  run {run_idx + 1}/{runs}: FAILED")
                continue

            result.times.append(elapsed)
            print(f"  run {run_idx + 1}/{runs}: {elapsed:.3f}s")

        except subprocess.TimeoutExpired:
            result.error = f"Run {run_idx + 1} timed out (>600s)"
            print(f"  run {run_idx + 1}/{runs}: TIMEOUT")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_comparison(all_results: list[RunResult]) -> None:
    scales = sorted({r.pages for r in all_results})
    ssgs = sorted({r.ssg for r in all_results})

    print()
    print("=" * 88)
    print("CROSS-SSG BUILD BENCHMARK RESULTS")
    print("=" * 88)
    print()
    print(f"  {'Pages':<8}", end="")
    for ssg in ssgs:
        print(f"  {ssg:>12} {'pps':>10}", end="")
    print()
    print("-" * 88)

    for scale in scales:
        print(f"  {scale:<8,}", end="")
        for ssg in ssgs:
            match = next((r for r in all_results if r.ssg == ssg and r.pages == scale), None)
            if match is None or not match.times:
                print(f"  {'ERR':>12} {'—':>10}", end="")
            else:
                t = match.median_time
                pps = match.pages_per_sec
                print(f"  {t:>10.3f}s {pps:>9.0f}", end="")
        print()

    print()

    # Speedup table (relative to slowest)
    print("Relative speedup (vs slowest per row):")
    print(f"  {'Pages':<8}", end="")
    for ssg in ssgs:
        print(f"  {ssg:>12}", end="")
    print()
    print("-" * 60)

    for scale in scales:
        row = []
        for ssg in ssgs:
            match = next((r for r in all_results if r.ssg == ssg and r.pages == scale), None)
            row.append(match.median_time if match and match.times else float("inf"))

        slowest = (
            max(t for t in row if t < float("inf")) if any(t < float("inf") for t in row) else 1.0
        )

        print(f"  {scale:<8,}", end="")
        for t in row:
            if t < float("inf"):
                ratio = slowest / t
                print(f"  {ratio:>10.1f}x", end="")
            else:
                print(f"  {'—':>12}", end="")
        print()

    print()


def export_json(all_results: list[RunResult], path: str) -> None:
    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "methodology": "cold build, minimal markdown, 3 runs median",
        "results": [],
    }
    for r in all_results:
        data["results"].append(
            {
                "ssg": r.ssg,
                "pages": r.pages,
                "median_seconds": r.median_time if r.times else None,
                "pages_per_second": r.pages_per_sec if r.times else None,
                "all_runs": r.times,
                "error": r.error,
            }
        )
    Path(path).write_text(json.dumps(data, indent=2))
    print(f"Results saved to {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-SSG build benchmark: Bengal vs MkDocs vs Pelican",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full scale suite (64 → 4096 pages)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Run a single scale (e.g. --pages 500)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per (ssg, scale) pair (default: 3)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated SSGs to run (e.g. --only bengal,mkdocs)",
    )
    args = parser.parse_args()

    random.seed(42)  # Reproducible content for comparable runs

    if args.pages:
        scales = [args.pages]
    elif args.full:
        scales = [64, 256, 512, 1024, 2048, 4096]
    else:
        scales = [64, 256, 1024]

    ssgs = [s.strip() for s in args.only.split(",")] if args.only else list(DEFAULT_SSGS)

    # Check availability
    available = {}
    print("Checking SSG availability:")
    for ssg in ssgs:
        ok = _check_available(ssg)
        available[ssg] = ok
        status = "OK" if ok else "NOT FOUND"
        print(f"  {ssg}: {status}")

    active_ssgs = [s for s in ssgs if available.get(s)]
    if not active_ssgs:
        print("\nNo SSGs available. Install with:")
        print("  pip install mkdocs pelican")
        return 1

    missing = [s for s in ssgs if not available.get(s)]
    if missing:
        print(f"\nSkipping unavailable: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))

    print(f"\nBenchmarking: {', '.join(active_ssgs)}")
    print(f"Scales: {', '.join(str(s) for s in scales)} pages")
    print(f"Runs per benchmark: {args.runs}")
    print()

    all_results: list[RunResult] = []

    for scale in scales:
        print(f"--- {scale} pages ---")
        for ssg in active_ssgs:
            print(f"  {ssg}:")
            result = benchmark_ssg(ssg, scale, runs=args.runs)
            all_results.append(result)
            if result.times:
                print(
                    f"    median: {result.median_time:.3f}s ({result.pages_per_sec:.0f} pages/sec)"
                )
            elif result.error:
                print(f"    error: {result.error[:120]}")
        print()

    print_comparison(all_results)

    if args.output:
        export_json(all_results, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
