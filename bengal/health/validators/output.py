"""
Output validator - checks generated pages and assets.

Provides observability stats for output validation performance tracking.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, ValidatorStats

if TYPE_CHECKING:
    from bengal.core.site import Site


class OutputValidator(BaseValidator):
    """
    Validates build output quality.

    Checks:
    - Page sizes (detect suspiciously small pages)
    - Asset presence (CSS/JS files)
    - Output directory structure

    Implements HasStats protocol for observability.
    """

    name = "Output"
    description = "Validates generated pages and assets"
    enabled_by_default = True

    MIN_SIZE = 1000  # Configurable via site.config

    # Store stats from last validation for observability
    last_stats: ValidatorStats | None = None

    @override
    def validate(self, site: Site, build_context: Any = None) -> list[CheckResult]:
        """
        Run output validation checks.

        Collects stats on:
        - Total HTML files checked
        - Files validated
        - Sub-timings for page size, asset, and directory checks

        Args:
            site: Site instance to validate
            build_context: Optional BuildContext (unused)

        Returns:
            List of CheckResult objects
        """
        results = []
        sub_timings: dict[str, float] = {}

        # Count HTML files for stats
        html_files = list(site.output_dir.rglob("*.html")) if site.output_dir.exists() else []
        stats = ValidatorStats(pages_total=len(html_files))

        # Check 1: Page sizes
        t0 = time.time()
        results.extend(self._check_page_sizes(site))
        sub_timings["page_sizes"] = (time.time() - t0) * 1000

        # Check 2: Asset presence
        t1 = time.time()
        results.extend(self._check_assets(site))
        sub_timings["assets"] = (time.time() - t1) * 1000

        # Check 3: Output directory exists
        t2 = time.time()
        results.extend(self._check_output_directory(site))
        sub_timings["directory"] = (time.time() - t2) * 1000

        # Update stats
        stats.pages_processed = len(html_files)
        stats.sub_timings = sub_timings

        # Track asset counts as metrics
        if site.output_dir.exists():
            assets_dir = site.output_dir / "assets"
            if assets_dir.exists():
                css_count = len(list(assets_dir.glob("css/*.css")))
                js_count = len(list(assets_dir.glob("js/*.js")))
                stats.metrics["css_files"] = css_count
                stats.metrics["js_files"] = js_count

        self.last_stats = stats

        return results

    def _check_page_sizes(self, site: Site) -> list[CheckResult]:
        """Check if any pages are suspiciously small."""
        results = []
        min_size = site.config.get("min_page_size", 1000)
        small_pages = []

        for page in site.pages:
            if page.output_path and page.output_path.exists():
                size = page.output_path.stat().st_size
                if size < min_size:
                    try:
                        relative_path = page.output_path.relative_to(site.output_dir)
                    except ValueError:
                        # output_path not under output_dir (e.g., '.' or absolute path)
                        relative_path = page.output_path
                    small_pages.append(f"{relative_path} ({size} bytes)")

        if small_pages:
            results.append(
                CheckResult.warning(
                    f"{len(small_pages)} page(s) are suspiciously small (< {min_size} bytes)",
                    recommendation="Small pages may indicate fallback HTML from rendering errors. Review these pages.",
                    details=small_pages[:5],  # Show first 5
                )
            )
        # No success message - if pages are adequate size, silence is golden

        return results

    def _check_assets(self, site: Site) -> list[CheckResult]:
        """Check if theme assets are present in output."""
        results = []
        assets_dir = site.output_dir / "assets"

        if not assets_dir.exists():
            results.append(
                CheckResult.error(
                    "No assets directory found in output",
                    recommendation="Check that theme assets are being discovered and copied. Theme may not be properly configured.",
                )
            )
            return results

        # Check CSS files
        css_count = len(list(assets_dir.glob("css/*.css")))
        if css_count == 0:
            results.append(
                CheckResult.warning(
                    "No CSS files found in output",
                    recommendation="Theme may not be applied. Check theme configuration and asset discovery.",
                )
            )
        # No success message for CSS - if present, silence is golden

        # Check JS files (only warn for default theme)
        js_count = len(list(assets_dir.glob("js/*.js")))
        if js_count == 0 and site.config.get("theme") == "default":
            results.append(
                CheckResult.warning(
                    "No JS files found in output",
                    recommendation="Default theme expects JavaScript files. Check asset discovery.",
                )
            )
        # No success message for JS - if present, silence is golden

        return results

    def _check_output_directory(self, site: Site) -> list[CheckResult]:
        """Check output directory structure."""
        results = []

        if not site.output_dir.exists():
            results.append(
                CheckResult.error(
                    f"Output directory does not exist: {site.output_dir}",
                    recommendation="This should not happen after a build. Check build process.",
                )
            )
        # No success message for output dir - if exists, silence is golden

        return results
