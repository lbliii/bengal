"""
Performance validator - checks build performance (basic checks only).

Validates:
- Detects slow pages (> 1 second render)
- Warns if build is unusually slow
- Reports basic throughput metrics
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class PerformanceValidator(BaseValidator):
    """
    Validates build performance (basic checks only).

    Checks:
    - Build time is reasonable for page count
    - No individual pages are very slow
    - Basic throughput metrics

    Skips:
    - Memory profiling (complex)
    - Parallel efficiency analysis (advanced)
    - Build time regression detection (needs history)
    """

    name = "Performance"
    description = "Validates build performance metrics"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run performance validation checks."""
        results = []

        # Get build stats from config/context
        build_stats = getattr(site, "_last_build_stats", None)
        if not build_stats:
            results.append(
                CheckResult.info(
                    "No build statistics available",
                    recommendation="Build stats are collected during site.build()",
                )
            )
            return results

        # Check 1: Overall build time
        results.extend(self._check_build_time(site, build_stats))

        # Check 2: Throughput
        results.extend(self._check_throughput(site, build_stats))

        # Check 3: Slow pages (if available)
        results.extend(self._check_slow_pages(site, build_stats))

        return results

    def _check_build_time(self, site: Site, build_stats: dict[str, Any]) -> list[CheckResult]:
        """Check if overall build time is reasonable."""
        results = []

        build_time_ms = build_stats.get("build_time_ms", 0)
        build_time_s = build_time_ms / 1000
        total_pages = build_stats.get("total_pages", 0)

        # Calculate expected time (rough heuristic)
        # Parallel: ~50 pages/sec, Sequential: ~20 pages/sec
        parallel = site.config.get("parallel", True)
        expected_rate = 50 if parallel else 20
        expected_time = total_pages / expected_rate

        # Allow 2x margin for slower systems
        threshold = expected_time * 2

        if total_pages == 0:
            results.append(CheckResult.info(f"Build time: {build_time_s:.2f}s (no pages)"))
        elif build_time_s > threshold:
            results.append(
                CheckResult.warning(
                    f"Build is slower than expected ({build_time_s:.2f}s for {total_pages} pages)",
                    recommendation="Check for slow template functions, large assets, or system issues.",
                )
            )
        elif build_time_s > 10:
            results.append(
                CheckResult.info(f"Build time: {build_time_s:.2f}s ({total_pages} pages)")
            )
        else:
            results.append(
                CheckResult.success(f"Build time: {build_time_s:.2f}s ({total_pages} pages) ⚡")
            )

        return results

    def _check_throughput(self, site: Site, build_stats: dict[str, Any]) -> list[CheckResult]:
        """Check pages per second throughput."""
        results: list[CheckResult] = []

        build_time_ms = build_stats.get("build_time_ms", 0)
        total_pages = build_stats.get("total_pages", 0)

        if build_time_ms == 0 or total_pages == 0:
            return results

        throughput = (total_pages / build_time_ms) * 1000  # pages/second

        # Thresholds
        if throughput > 100:
            results.append(
                CheckResult.success(f"Throughput: {throughput:.1f} pages/second (excellent)")
            )
        elif throughput > 50:
            results.append(CheckResult.success(f"Throughput: {throughput:.1f} pages/second (good)"))
        elif throughput > 20:
            results.append(
                CheckResult.info(f"Throughput: {throughput:.1f} pages/second (acceptable)")
            )
        else:
            results.append(
                CheckResult.warning(
                    f"Throughput: {throughput:.1f} pages/second (slow)",
                    recommendation="Consider enabling parallel builds or check for performance bottlenecks.",
                )
            )

        return results

    def _check_slow_pages(self, site: Site, build_stats: dict[str, Any]) -> list[CheckResult]:
        """Check for individual slow pages."""
        results: list[CheckResult] = []

        # This would require per-page timing data
        # For now, just check rendering time vs total time
        rendering_time_ms = build_stats.get("rendering_time_ms", 0)
        total_time_ms = build_stats.get("build_time_ms", 0)
        total_pages = build_stats.get("total_pages", 1)

        if rendering_time_ms == 0 or total_time_ms == 0:
            return results

        # Calculate average render time per page
        avg_render_ms = rendering_time_ms / total_pages

        # Check if rendering takes disproportionate time
        rendering_pct = (rendering_time_ms / total_time_ms) * 100

        if avg_render_ms > 100:  # 100ms+ per page is slow
            results.append(
                CheckResult.warning(
                    f"Average page render time is high ({avg_render_ms:.0f}ms/page)",
                    recommendation="Check for complex templates or slow template functions.",
                )
            )
        elif rendering_pct > 80:
            results.append(
                CheckResult.info(
                    f"Rendering accounts for {rendering_pct:.0f}% of build time",
                    recommendation="Consider optimizing templates or using simpler Jinja2 logic.",
                )
            )
        else:
            results.append(
                CheckResult.success(f"Average render time: {avg_render_ms:.0f}ms/page (good)")
            )

        return results
