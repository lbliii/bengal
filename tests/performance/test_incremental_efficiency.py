"""
Incremental build efficiency tests.

RFC: rfc-behavioral-test-hardening (follow-up)

These tests verify that incremental builds are EFFICIENT, not just CORRECT.
They define expected rebuild counts for specific scenarios and fail when
the incremental system does more work than expected.

Why this matters:
- Correctness tests pass even if all pages rebuild (correct but slow)
- Efficiency tests fail if too many pages rebuild
- Catches regressions in incremental optimization

Metrics tracked:
- rebuild_count: How many pages were rebuilt
- cache_hit_rate: Percentage of pages served from cache
- rebuild_by_reason: Breakdown of why pages rebuilt

Usage:
    # Run efficiency tests
    pytest tests/performance/test_incremental_efficiency.py -v

    # Run with verbose output to see efficiency metrics
    pytest tests/performance/test_incremental_efficiency.py -v -s
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.orchestration.stats.models import BuildStats


# =============================================================================
# EFFICIENCY METRICS
# =============================================================================


@dataclass
class EfficiencyMetrics:
    """Metrics for evaluating incremental build efficiency."""

    # Core metrics
    rebuild_count: int = 0
    skip_count: int = 0
    total_pages: int = 0

    # Derived metrics
    cache_hit_rate: float = 0.0

    # Breakdown by reason
    rebuild_by_reason: dict[str, int] = field(default_factory=dict)

    # Timing
    build_time_ms: float = 0.0

    # Metadata
    scenario: str = ""
    timestamp: str = ""

    @classmethod
    def from_build_stats(cls, stats: "BuildStats", scenario: str = "") -> "EfficiencyMetrics":
        """Extract efficiency metrics from BuildStats."""
        metrics = cls(
            scenario=scenario,
            timestamp=datetime.now().isoformat(),
        )

        metrics.build_time_ms = stats.build_time_ms
        metrics.total_pages = stats.total_pages

        # Extract from incremental_decision if available
        decision = getattr(stats, "incremental_decision", None)
        if decision is not None:
            metrics.rebuild_count = len(decision.pages_to_build)
            metrics.skip_count = decision.pages_skipped_count
            metrics.rebuild_by_reason = decision.get_reason_summary()
        else:
            # No incremental_decision means either:
            # 1. Full build (all pages rebuilt)
            # 2. Build was skipped entirely (perfect cache hit)
            # Check cache_hits/cache_misses to distinguish
            if stats.cache_hits > 0 and stats.cache_misses == 0:
                # Perfect cache hit - build was skipped
                metrics.rebuild_count = 0
                metrics.skip_count = stats.cache_hits
                metrics.total_pages = stats.cache_hits  # Use cache_hits as total
            elif stats.cache_hits > 0 or stats.cache_misses > 0:
                # Partial cache usage (incremental without decision tracking)
                metrics.rebuild_count = stats.cache_misses
                metrics.skip_count = stats.cache_hits
                metrics.total_pages = stats.cache_hits + stats.cache_misses
            else:
                # Full build - all pages rebuilt
                metrics.rebuild_count = stats.total_pages
                metrics.skip_count = 0

        # Calculate cache hit rate
        if metrics.total_pages > 0:
            metrics.cache_hit_rate = (
                (metrics.total_pages - metrics.rebuild_count) / metrics.total_pages * 100
            )

        return metrics

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "scenario": self.scenario,
            "timestamp": self.timestamp,
            "rebuild_count": self.rebuild_count,
            "skip_count": self.skip_count,
            "total_pages": self.total_pages,
            "cache_hit_rate": round(self.cache_hit_rate, 1),
            "rebuild_by_reason": self.rebuild_by_reason,
            "build_time_ms": round(self.build_time_ms, 1),
        }

    def assert_efficiency(
        self,
        *,
        max_rebuilds: int | None = None,
        min_cache_hit_rate: float | None = None,
        expected_reasons: dict[str, int] | None = None,
    ) -> None:
        """
        Assert efficiency metrics meet expectations.

        Args:
            max_rebuilds: Maximum allowed rebuilds (None = no limit)
            min_cache_hit_rate: Minimum cache hit rate % (None = no limit)
            expected_reasons: Expected count by reason (allows +/- 20% tolerance)

        Raises:
            AssertionError: If efficiency expectations not met
        """
        errors = []

        if max_rebuilds is not None and self.rebuild_count > max_rebuilds:
            errors.append(
                f"Too many rebuilds: {self.rebuild_count} (max: {max_rebuilds}). "
                f"Breakdown: {self.rebuild_by_reason}"
            )

        if min_cache_hit_rate is not None and self.cache_hit_rate < min_cache_hit_rate:
            errors.append(
                f"Cache hit rate too low: {self.cache_hit_rate:.1f}% "
                f"(min: {min_cache_hit_rate}%)"
            )

        if expected_reasons:
            for reason, expected in expected_reasons.items():
                actual = self.rebuild_by_reason.get(reason, 0)
                tolerance = max(1, int(expected * 0.2))  # 20% tolerance, min 1
                if abs(actual - expected) > tolerance:
                    errors.append(
                        f"Reason '{reason}': expected ~{expected}, got {actual}"
                    )

        if errors:
            raise AssertionError(
                f"Efficiency check failed for '{self.scenario}':\n"
                + "\n".join(f"  - {e}" for e in errors)
            )


def _print_efficiency_report(metrics: EfficiencyMetrics) -> None:
    """Print a human-readable efficiency report."""
    print(f"\n{'='*60}")
    print(f"EFFICIENCY REPORT: {metrics.scenario}")
    print(f"{'='*60}")
    print(f"  Total pages:    {metrics.total_pages}")
    print(f"  Rebuilt:        {metrics.rebuild_count}")
    print(f"  Skipped:        {metrics.skip_count}")
    print(f"  Cache hit rate: {metrics.cache_hit_rate:.1f}%")
    print(f"  Build time:     {metrics.build_time_ms:.1f}ms")
    if metrics.rebuild_by_reason:
        print(f"\n  Rebuild reasons:")
        for reason, count in sorted(metrics.rebuild_by_reason.items()):
            print(f"    {reason}: {count}")
    print(f"{'='*60}\n")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def efficiency_site(tmp_path: Path):
    """
    Create a site for efficiency testing.

    Returns a function that creates sites with configurable page count.
    """
    from bengal.core.site import Site

    def _create(
        page_count: int = 20,
        *,
        with_tags: bool = False,
        with_sections: bool = False,
    ) -> tuple[Path, "Site"]:
        site_dir = tmp_path / "site"
        site_dir.mkdir(exist_ok=True)

        # Config
        config = """
[site]
title = "Efficiency Test Site"
baseURL = "/"

[build]
output_dir = "public"
"""
        if with_tags:
            config += "\n[taxonomies]\ntags = \"tags\"\n"

        (site_dir / "bengal.toml").write_text(config)

        # Content
        content_dir = site_dir / "content"
        content_dir.mkdir(exist_ok=True)

        # Home page
        (content_dir / "_index.md").write_text(
            "---\ntitle: Home\n---\n# Home"
        )

        # Create pages
        for i in range(page_count):
            section = f"section{i % 5}" if with_sections else ""
            if section:
                section_dir = content_dir / section
                section_dir.mkdir(exist_ok=True)
                if not (section_dir / "_index.md").exists():
                    (section_dir / "_index.md").write_text(
                        f"---\ntitle: Section {i % 5}\n---\n# Section"
                    )
                page_path = section_dir / f"page_{i}.md"
            else:
                page_path = content_dir / f"page_{i}.md"

            tags = f"tags:\n  - tag{i % 3}\n" if with_tags else ""
            page_path.write_text(
                f"---\ntitle: Page {i}\n{tags}---\n# Page {i}\n\nContent."
            )

        # Create and initialize site
        site = Site.from_config(site_dir)
        site.discover_content()
        site.discover_assets()

        return site_dir, site

    return _create


# =============================================================================
# EFFICIENCY TESTS
# =============================================================================


class TestWarmCacheEfficiency:
    """Tests that verify warm cache efficiency."""

    def test_warm_cache_zero_rebuilds(self, efficiency_site) -> None:
        """
        EFFICIENCY: Warm cache with no changes should rebuild 0 pages.

        This is the baseline efficiency test - if nothing changed,
        nothing should rebuild.
        """
        from bengal.orchestration.build.options import BuildOptions

        site_dir, site = efficiency_site(page_count=20)

        # Initial build (warms cache)
        options_full = BuildOptions(incremental=False, quiet=True)
        site.build(options=options_full)

        # Reload and incremental build
        from bengal.core.site import Site

        site2 = Site.from_config(site_dir)
        site2.discover_content()
        site2.discover_assets()

        options_incr = BuildOptions(incremental=True, quiet=True, explain=True)
        stats = site2.build(options=options_incr)

        # Extract metrics
        metrics = EfficiencyMetrics.from_build_stats(
            stats, scenario="warm_cache_no_changes"
        )
        _print_efficiency_report(metrics)

        # EFFICIENCY ASSERTION: Zero rebuilds on warm cache
        metrics.assert_efficiency(
            max_rebuilds=0,
            min_cache_hit_rate=100.0,
        )

    def test_single_page_change_minimal_rebuild(self, efficiency_site) -> None:
        """
        EFFICIENCY: Single page change should rebuild ~1-3 pages.

        When one page changes, we expect:
        - The changed page (1)
        - Maybe navigation-dependent siblings (0-2)

        Should NOT rebuild unrelated pages.
        """
        from bengal.orchestration.build.options import BuildOptions

        site_dir, site = efficiency_site(page_count=20)

        # Initial build
        options_full = BuildOptions(incremental=False, quiet=True)
        site.build(options=options_full)

        # Modify one page
        time.sleep(0.01)
        content_dir = site_dir / "content"
        (content_dir / "page_0.md").write_text(
            "---\ntitle: Page 0 Modified\n---\n# Modified\n\nChanged content."
        )

        # Reload and incremental build
        from bengal.core.site import Site

        site2 = Site.from_config(site_dir)
        site2.discover_content()
        site2.discover_assets()

        options_incr = BuildOptions(incremental=True, quiet=True, explain=True)
        stats = site2.build(options=options_incr)

        # Extract metrics
        metrics = EfficiencyMetrics.from_build_stats(
            stats, scenario="single_page_change"
        )
        _print_efficiency_report(metrics)

        # EFFICIENCY ASSERTION: At most 5 rebuilds for single page change
        # (page + potential nav siblings + section index)
        metrics.assert_efficiency(
            max_rebuilds=5,
            min_cache_hit_rate=75.0,  # At least 75% cache hit
        )

    def test_multiple_page_changes_proportional_rebuild(self, efficiency_site) -> None:
        """
        EFFICIENCY: Multiple page changes should scale proportionally.

        Changing 3 pages should rebuild ~3-9 pages (not all 20).
        """
        from bengal.orchestration.build.options import BuildOptions

        site_dir, site = efficiency_site(page_count=20)

        # Initial build
        options_full = BuildOptions(incremental=False, quiet=True)
        site.build(options=options_full)

        # Modify 3 pages
        time.sleep(0.01)
        content_dir = site_dir / "content"
        for i in [0, 5, 10]:
            (content_dir / f"page_{i}.md").write_text(
                f"---\ntitle: Page {i} Modified\n---\n# Modified {i}"
            )

        # Reload and incremental build
        from bengal.core.site import Site

        site2 = Site.from_config(site_dir)
        site2.discover_content()
        site2.discover_assets()

        options_incr = BuildOptions(incremental=True, quiet=True, explain=True)
        stats = site2.build(options=options_incr)

        metrics = EfficiencyMetrics.from_build_stats(
            stats, scenario="multiple_page_changes"
        )
        _print_efficiency_report(metrics)

        # EFFICIENCY ASSERTION: At most 15 rebuilds for 3 page changes
        # (changed pages + nav dependencies)
        metrics.assert_efficiency(
            max_rebuilds=15,
            min_cache_hit_rate=50.0,  # At least half should be cached
        )


class TestSectionEfficiency:
    """Tests for section-aware incremental builds."""

    def test_section_change_contained_to_section(self, efficiency_site) -> None:
        """
        EFFICIENCY: Section changes should be contained to that section.

        Changing a page in section0 should NOT rebuild pages in section1-4.
        """
        from bengal.orchestration.build.options import BuildOptions

        site_dir, site = efficiency_site(page_count=25, with_sections=True)

        # Initial build
        options_full = BuildOptions(incremental=False, quiet=True)
        site.build(options=options_full)

        # Modify one page in section0
        time.sleep(0.01)
        section_dir = site_dir / "content" / "section0"
        (section_dir / "page_0.md").write_text(
            "---\ntitle: Page 0 Modified\n---\n# Modified"
        )

        # Reload and incremental build
        from bengal.core.site import Site

        site2 = Site.from_config(site_dir)
        site2.discover_content()
        site2.discover_assets()

        options_incr = BuildOptions(incremental=True, quiet=True, explain=True)
        stats = site2.build(options=options_incr)

        metrics = EfficiencyMetrics.from_build_stats(
            stats, scenario="section_contained_change"
        )
        _print_efficiency_report(metrics)

        # EFFICIENCY ASSERTION: Should only rebuild ~5-10 pages (one section)
        # Not all 25+ pages
        metrics.assert_efficiency(
            max_rebuilds=12,  # Section (~5 pages) + section index + nav
            min_cache_hit_rate=50.0,
        )


class TestTaxonomyEfficiency:
    """Tests for taxonomy-aware incremental builds."""

    def test_tag_change_minimal_cascade(self, efficiency_site) -> None:
        """
        EFFICIENCY: Changing a page's tags should have minimal cascade.

        Adding/removing a tag should only rebuild:
        - The changed page
        - Affected tag pages
        - NOT unrelated content pages
        """
        from bengal.orchestration.build.options import BuildOptions

        site_dir, site = efficiency_site(page_count=20, with_tags=True)

        # Initial build
        options_full = BuildOptions(incremental=False, quiet=True)
        site.build(options=options_full)

        # Change tags on one page
        time.sleep(0.01)
        content_dir = site_dir / "content"
        (content_dir / "page_0.md").write_text(
            "---\ntitle: Page 0\ntags:\n  - new-tag\n---\n# Page 0"
        )

        # Reload and incremental build
        from bengal.core.site import Site

        site2 = Site.from_config(site_dir)
        site2.discover_content()
        site2.discover_assets()

        options_incr = BuildOptions(incremental=True, quiet=True, explain=True)
        stats = site2.build(options=options_incr)

        metrics = EfficiencyMetrics.from_build_stats(
            stats, scenario="tag_change_cascade"
        )
        _print_efficiency_report(metrics)

        # EFFICIENCY ASSERTION: Should rebuild changed page + tag pages
        # Not all 20+ content pages
        metrics.assert_efficiency(
            max_rebuilds=10,  # page + tag pages + index
            min_cache_hit_rate=50.0,
        )


class TestEfficiencyRegression:
    """
    Regression tests for known efficiency issues.

    These tests document specific efficiency bugs that were fixed
    and ensure they don't regress.
    """

    @pytest.mark.skip(reason="Add when specific regressions are identified")
    def test_autodoc_pages_not_always_rebuilt(self, efficiency_site) -> None:
        """
        REGRESSION: Autodoc pages should not rebuild on every build.

        Bug: 845 autodoc pages were rebuilding even when source didn't change.
        Fix: Proper fingerprinting of autodoc source files.
        """
        # TODO: Add test when autodoc efficiency is fixed
        pass


# =============================================================================
# METRICS EXPORT (for CI tracking)
# =============================================================================


@pytest.fixture(scope="session")
def metrics_collector():
    """Collect metrics across all efficiency tests for CI reporting."""
    metrics: list[EfficiencyMetrics] = []
    yield metrics

    # At end of session, write metrics to file
    if metrics:
        metrics_file = Path(".pytest_cache") / "efficiency_metrics.json"
        metrics_data = [m.to_dict() for m in metrics]
        metrics_file.write_text(json.dumps(metrics_data, indent=2))
        print(f"\nEfficiency metrics written to: {metrics_file}")
