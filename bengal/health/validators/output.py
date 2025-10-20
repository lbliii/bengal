"""
Output validator - checks generated pages and assets.

Migrated from Site._validate_build_health() with improvements.
"""


from __future__ import annotations

from typing import TYPE_CHECKING, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site


class OutputValidator(BaseValidator):
    """
    Validates build output quality.

    Checks:
    - Page sizes (detect suspiciously small pages)
    - Asset presence (CSS/JS files)
    - Output directory structure
    """

    name = "Output"
    description = "Validates generated pages and assets"
    enabled_by_default = True

    MIN_SIZE = 1000  # Configurable via site.config

    @override
    def validate(self, site: Site) -> list[CheckResult]:
        """Run output validation checks."""
        results = []

        # Check 1: Page sizes
        results.extend(self._check_page_sizes(site))

        # Check 2: Asset presence
        results.extend(self._check_assets(site))

        # Check 3: Output directory exists
        results.extend(self._check_output_directory(site))

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
                    relative_path = page.output_path.relative_to(site.output_dir)
                    small_pages.append(f"{relative_path} ({size} bytes)")

        if small_pages:
            results.append(
                CheckResult.warning(
                    f"{len(small_pages)} page(s) are suspiciously small (< {min_size} bytes)",
                    recommendation="Small pages may indicate fallback HTML from rendering errors. Review these pages.",
                    details=small_pages[:5],  # Show first 5
                )
            )
        else:
            results.append(
                CheckResult.success(f"All pages are adequately sized (>= {min_size} bytes)")
            )

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
        else:
            results.append(CheckResult.success(f"{css_count} CSS file(s) in output"))

        # Check JS files (only warn for default theme)
        js_count = len(list(assets_dir.glob("js/*.js")))
        if js_count == 0 and site.config.get("theme") == "default":
            results.append(
                CheckResult.warning(
                    "No JS files found in output",
                    recommendation="Default theme expects JavaScript files. Check asset discovery.",
                )
            )
        elif js_count > 0:
            results.append(CheckResult.success(f"{js_count} JavaScript file(s) in output"))

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
        else:
            # Count files in output
            file_count = sum(1 for _ in site.output_dir.rglob("*") if _.is_file())
            results.append(CheckResult.success(f"Output directory exists with {file_count} files"))

        return results
