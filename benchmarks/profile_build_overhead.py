#!/usr/bin/env python3
"""
Build Overhead Profiler

Profiles non-rendering build overhead: health checks, discovery, template engine,
asset processing, etc. Run before each release to catch performance regressions.

Usage:
    # From bengal repo root, with site/ directory present:
    python benchmarks/profile_build_overhead.py

    # With specific site path:
    python benchmarks/profile_build_overhead.py --site /path/to/site

    # JSON output for CI:
    python benchmarks/profile_build_overhead.py --format json

    # Compare against baseline:
    python benchmarks/profile_build_overhead.py --baseline benchmarks/baseline.json

What this measures:
    - Health check validators (individual timing, issues found)
    - Build phase overhead (discovery, asset processing, post-processing)
    - Template engine initialization
    - Content discovery and parsing

Why it matters:
    - Health checks run every build — 1s overhead = 1s slower dev loop
    - Template engine creation happens per-worker in parallel builds
    - Discovery overhead scales with content size
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Add bengal to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["BENGAL_QUIET"] = "1"


@dataclass
class ValidatorResult:
    """Result from profiling a single validator."""

    name: str
    avg_ms: float
    min_ms: float
    max_ms: float
    std_ms: float
    issues_found: int
    runs: int


@dataclass
class PhaseResult:
    """Result from profiling a build phase."""

    name: str
    avg_ms: float
    min_ms: float
    max_ms: float
    description: str


@dataclass
class ProfileReport:
    """Complete profiling report."""

    timestamp: str
    site_path: str
    page_count: int
    runs: int

    # Health check results
    health_total_ms: float
    health_validators: list[ValidatorResult]

    # Build phase results
    phases: list[PhaseResult]

    # Summary
    total_overhead_ms: float
    recommendations: list[str] = field(default_factory=list)


def profile_validators(site: Any, runs: int = 3) -> tuple[float, list[ValidatorResult]]:
    """Profile all health check validators."""
    from bengal.health import HealthCheck

    all_times: dict[str, list[float]] = {}
    all_issues: dict[str, int] = {}

    for _run in range(runs):
        health = HealthCheck(site)
        for validator in health.validators:
            start = time.perf_counter()
            try:
                result = validator.validate(site, build_context=None)
                elapsed = (time.perf_counter() - start) * 1000

                if validator.name not in all_times:
                    all_times[validator.name] = []
                    all_issues[validator.name] = 0

                all_times[validator.name].append(elapsed)
                all_issues[validator.name] = len(result)
            except Exception:
                # Ignore individual validator failures during profiling so that
                # broken/experimental validators do not abort the benchmark or
                # skew timing aggregation.
                pass

    results = []
    for name, times in all_times.items():
        results.append(
            ValidatorResult(
                name=name,
                avg_ms=statistics.mean(times),
                min_ms=min(times),
                max_ms=max(times),
                std_ms=statistics.stdev(times) if len(times) > 1 else 0,
                issues_found=all_issues[name],
                runs=len(times),
            )
        )

    # Sort by avg time descending
    results.sort(key=lambda x: x.avg_ms, reverse=True)
    total = sum(r.avg_ms for r in results)

    return total, results


def profile_phases(site: Any, runs: int = 3) -> list[PhaseResult]:
    """Profile major build phases."""
    results = []

    # 1. Template Engine creation
    times = []
    for _ in range(runs):
        from bengal.rendering.template_engine import TemplateEngine

        start = time.perf_counter()
        TemplateEngine(site)
        times.append((time.perf_counter() - start) * 1000)

    results.append(
        PhaseResult(
            name="TemplateEngine creation",
            avg_ms=statistics.mean(times),
            min_ms=min(times),
            max_ms=max(times),
            description="Created per-worker in parallel builds",
        )
    )

    # 2. Content discovery (already done, measure fresh)
    # Note: This requires a fresh site, so we measure differently
    times = []
    for _ in range(runs):
        from bengal.core.site import Site

        fresh_site = Site.from_config(Path(site.root_path))
        start = time.perf_counter()
        fresh_site.discover_content()
        times.append((time.perf_counter() - start) * 1000)

    results.append(
        PhaseResult(
            name="Content discovery",
            avg_ms=statistics.mean(times),
            min_ms=min(times),
            max_ms=max(times),
            description=f"Parse {len(site.pages)} pages from disk",
        )
    )

    # 3. Asset discovery
    times = []
    for _ in range(runs):
        from bengal.core.site import Site

        fresh_site = Site.from_config(Path(site.root_path))
        fresh_site.discover_content()
        start = time.perf_counter()
        fresh_site.discover_assets()
        times.append((time.perf_counter() - start) * 1000)

    results.append(
        PhaseResult(
            name="Asset discovery",
            avg_ms=statistics.mean(times),
            min_ms=min(times),
            max_ms=max(times),
            description="Find and catalog static assets",
        )
    )

    # 4. RenderingPipeline creation
    times = []
    for _ in range(runs):
        from bengal.rendering.pipeline import RenderingPipeline

        start = time.perf_counter()
        RenderingPipeline(site, dependency_tracker=None, quiet=True)
        times.append((time.perf_counter() - start) * 1000)

    results.append(
        PhaseResult(
            name="RenderingPipeline creation",
            avg_ms=statistics.mean(times),
            min_ms=min(times),
            max_ms=max(times),
            description="Created per-worker in parallel builds",
        )
    )

    return results


def generate_recommendations(
    health_total: float, validators: list[ValidatorResult], phases: list[PhaseResult]
) -> list[str]:
    """Generate actionable recommendations based on profiling results."""
    recs = []

    # Health check recommendations
    if health_total > 1000:
        recs.append(f"⚠️  Health checks taking {health_total:.0f}ms (>1s) - review slow validators")

    for v in validators[:3]:  # Top 3 slowest
        if v.avg_ms > 100 and v.issues_found == 0:
            recs.append(
                f"💡 {v.name}: {v.avg_ms:.0f}ms, 0 issues - consider moving to Tier 2 or removing"
            )
        elif v.avg_ms > 200:
            recs.append(f"⚠️  {v.name}: {v.avg_ms:.0f}ms - investigate bottleneck")

    # Phase recommendations
    for p in phases:
        if "TemplateEngine" in p.name and p.avg_ms > 100:
            recs.append(f"💡 {p.name}: {p.avg_ms:.0f}ms - consider caching or lazy initialization")
        if "discovery" in p.name.lower() and p.avg_ms > 500:
            recs.append(f"⚠️  {p.name}: {p.avg_ms:.0f}ms - consider incremental discovery")

    if not recs:
        recs.append("✅ All metrics within acceptable ranges")

    return recs


def compare_to_baseline(report: ProfileReport, baseline_path: Path) -> list[str]:
    """Compare current results to baseline and flag regressions."""
    try:
        with open(baseline_path) as f:
            baseline = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return [f"Could not load baseline: {e}"]

    diffs = []
    threshold = 1.2  # 20% regression threshold

    # Compare health total
    if "health_total_ms" in baseline:
        old = baseline["health_total_ms"]
        new = report.health_total_ms
        if new > old * threshold:
            diffs.append(
                f"🔴 REGRESSION: Health checks {old:.0f}ms → {new:.0f}ms (+{((new / old) - 1) * 100:.0f}%)"
            )
        elif new < old * 0.8:
            diffs.append(
                f"🟢 IMPROVEMENT: Health checks {old:.0f}ms → {new:.0f}ms ({((new / old) - 1) * 100:.0f}%)"
            )

    # Compare individual validators
    old_validators = {v["name"]: v["avg_ms"] for v in baseline.get("health_validators", [])}
    for v in report.health_validators:
        if v.name in old_validators:
            old = old_validators[v.name]
            new = v.avg_ms
            if new > old * threshold and new > 50:  # Only flag if >50ms
                diffs.append(
                    f"🔴 {v.name}: {old:.0f}ms → {new:.0f}ms (+{((new / old) - 1) * 100:.0f}%)"
                )

    if not diffs:
        diffs.append("✅ No significant regressions detected")

    return diffs


def print_report(report: ProfileReport, format: str = "console") -> None:
    """Print profiling report."""
    if format == "json":
        # Convert to JSON-serializable dict
        data = {
            "timestamp": report.timestamp,
            "site_path": report.site_path,
            "page_count": report.page_count,
            "runs": report.runs,
            "health_total_ms": report.health_total_ms,
            "health_validators": [asdict(v) for v in report.health_validators],
            "phases": [asdict(p) for p in report.phases],
            "total_overhead_ms": report.total_overhead_ms,
            "recommendations": report.recommendations,
        }
        print(json.dumps(data, indent=2))
        return

    # Console format
    print()
    print("=" * 70)
    print("BUILD OVERHEAD PROFILER")
    print("=" * 70)
    print(f"Site: {report.site_path}")
    print(f"Pages: {report.page_count}")
    print(f"Runs: {report.runs} (averaged)")
    print(f"Time: {report.timestamp}")
    print()

    # Health validators
    print("HEALTH CHECK VALIDATORS")
    print("-" * 70)
    print(f"{'Validator':<30} {'Avg':>8} {'Min':>8} {'Max':>8} {'Issues':>8}")
    print("-" * 70)

    for v in report.health_validators:
        flag = "⚠️ " if v.avg_ms > 100 and v.issues_found == 0 else "  "
        print(
            f"{flag}{v.name:<28} {v.avg_ms:>7.1f}ms {v.min_ms:>7.1f}ms {v.max_ms:>7.1f}ms {v.issues_found:>8}"
        )

    print("-" * 70)
    print(f"{'Total':<30} {report.health_total_ms:>7.0f}ms")
    print()

    # Build phases
    print("BUILD PHASE OVERHEAD")
    print("-" * 70)
    print(f"{'Phase':<30} {'Avg':>8} {'Min':>8} {'Max':>8}")
    print("-" * 70)

    for p in report.phases:
        print(f"{p.name:<30} {p.avg_ms:>7.1f}ms {p.min_ms:>7.1f}ms {p.max_ms:>7.1f}ms")
        print(f"  └─ {p.description}")

    print()

    # Recommendations
    print("RECOMMENDATIONS")
    print("-" * 70)
    for rec in report.recommendations:
        print(f"  {rec}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile build overhead (health checks, discovery, etc.)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python benchmarks/profile_build_overhead.py
    python benchmarks/profile_build_overhead.py --site ./site --runs 5
    python benchmarks/profile_build_overhead.py --format json > baseline.json
    python benchmarks/profile_build_overhead.py --baseline baseline.json
        """,
    )
    parser.add_argument(
        "--site",
        type=Path,
        default=Path("site"),
        help="Path to site directory (default: ./site)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs for averaging (default: 3)",
    )
    parser.add_argument(
        "--format",
        choices=["console", "json"],
        default="console",
        help="Output format (default: console)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Compare against baseline JSON file",
    )
    parser.add_argument(
        "--save-baseline",
        type=Path,
        help="Save results as new baseline",
    )

    args = parser.parse_args()

    # Store original cwd for saving files
    original_cwd = Path.cwd()

    # Validate site path
    if not args.site.exists():
        print(f"Error: Site directory not found: {args.site}", file=sys.stderr)
        sys.exit(1)

    # Load site
    from bengal.core.site import Site

    os.chdir(args.site)
    site = Site.from_config(Path("."))
    site.discover_content()
    site.discover_assets()

    # Profile
    health_total, validators = profile_validators(site, runs=args.runs)
    phases = profile_phases(site, runs=args.runs)

    # Generate report
    report = ProfileReport(
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        site_path=str(args.site.absolute()),
        page_count=len(site.pages),
        runs=args.runs,
        health_total_ms=health_total,
        health_validators=validators,
        phases=phases,
        total_overhead_ms=health_total + sum(p.avg_ms for p in phases),
        recommendations=generate_recommendations(health_total, validators, phases),
    )

    # Compare to baseline if provided
    if args.baseline:
        diffs = compare_to_baseline(report, args.baseline)
        if args.format == "console":
            print()
            print("BASELINE COMPARISON")
            print("-" * 70)
            for diff in diffs:
                print(f"  {diff}")
            print()

    # Print report
    print_report(report, args.format)

    # Save baseline if requested
    if args.save_baseline:
        data = {
            "timestamp": report.timestamp,
            "site_path": report.site_path,
            "page_count": report.page_count,
            "runs": report.runs,
            "health_total_ms": report.health_total_ms,
            "health_validators": [asdict(v) for v in report.health_validators],
            "phases": [asdict(p) for p in report.phases],
            "total_overhead_ms": report.total_overhead_ms,
        }
        # Resolve path relative to original cwd (before we chdir'd to site)
        baseline_path = original_cwd / args.save_baseline
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        with open(baseline_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Baseline saved to: {baseline_path}")


if __name__ == "__main__":
    main()
