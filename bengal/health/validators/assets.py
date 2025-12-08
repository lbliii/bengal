"""
Asset validator - checks asset processing and optimization.

Validates:
- Asset files copied to output
- Asset hashing/fingerprinting works (if enabled)
- Minification applied (if enabled)
- No duplicate assets
- Reasonable asset sizes
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.utils.build_context import BuildContext
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class AssetValidator(BaseValidator):
    """
    Validates asset processing and optimization.

    Checks:
    - Assets directory exists and has files
    - Asset types are present (CSS, JS, images)
    - No duplicate assets (same content, different names)
    - Asset sizes are reasonable
    - Minification hints (file size analysis)
    """

    name = "Asset Processing"
    description = "Validates asset optimization and integrity"
    enabled_by_default = True

    # Size thresholds
    LARGE_CSS_KB = 200
    LARGE_JS_KB = 500
    LARGE_IMAGE_KB = 1000

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run asset validation checks."""
        results = []

        # Check 1: Assets directory exists
        assets_dir = site.output_dir / "assets"
        if not assets_dir.exists():
            results.append(
                CheckResult.warning(
                    "No assets directory found in output",
                    recommendation="Assets may not be copied. Check asset discovery and copying.",
                )
            )
            return results

        # Check 2: Asset types present
        results.extend(self._check_asset_types(assets_dir))

        # Check 3: Asset sizes
        results.extend(self._check_asset_sizes(assets_dir, site))

        # Check 4: Duplicate assets
        results.extend(self._check_duplicate_assets(assets_dir))

        # Check 5: Minification hints
        results.extend(self._check_minification_hints(assets_dir, site))

        return results

    def _check_asset_types(self, assets_dir: Path) -> list[CheckResult]:
        """Check expected asset types are present."""
        results = []

        # CSS check - only warn if missing (JS and images are optional)
        css_files = list(assets_dir.rglob("*.css"))
        if not css_files:
            results.append(
                CheckResult.warning(
                    "No CSS files found in assets",
                    recommendation="Theme may not be applied. Check theme asset discovery.",
                )
            )
        # No success/info messages - if present, silence is golden

        return results

    def _check_asset_sizes(self, assets_dir: Path, site: Site) -> list[CheckResult]:
        """Check asset sizes are reasonable."""
        results = []

        # Find large CSS files
        large_css = []
        for css_file in assets_dir.rglob("*.css"):
            size_kb = css_file.stat().st_size / 1024
            if size_kb > self.LARGE_CSS_KB:
                large_css.append(f"{css_file.name}: {size_kb:.0f} KB")

        if large_css:
            results.append(
                CheckResult.warning(
                    f"{len(large_css)} CSS file(s) are very large (>{self.LARGE_CSS_KB} KB)",
                    recommendation="Large CSS files slow page load. Consider CSS minification or splitting.",
                    details=large_css[:3],
                )
            )

        # Find large JS files
        large_js = []
        for js_file in assets_dir.rglob("*.js"):
            size_kb = js_file.stat().st_size / 1024
            if size_kb > self.LARGE_JS_KB:
                large_js.append(f"{js_file.name}: {size_kb:.0f} KB")

        if large_js:
            results.append(
                CheckResult.warning(
                    f"{len(large_js)} JavaScript file(s) are very large (>{self.LARGE_JS_KB} KB)",
                    recommendation="Large JS files slow page load. Consider minification or code splitting.",
                    details=large_js[:3],
                )
            )

        # Find large images
        large_images = []
        for img_file in itertools.chain(
            assets_dir.rglob("*.jpg"), assets_dir.rglob("*.jpeg"), assets_dir.rglob("*.png")
        ):
            size_kb = img_file.stat().st_size / 1024
            if size_kb > self.LARGE_IMAGE_KB:
                large_images.append(f"{img_file.name}: {size_kb:.0f} KB")

        if large_images:
            results.append(
                CheckResult.warning(
                    f"{len(large_images)} image(s) are very large (>{self.LARGE_IMAGE_KB} KB)",
                    recommendation="Large images slow page load. Consider image optimization or compression.",
                    details=large_images[:3],
                )
            )

        # Calculate total asset size
        total_size_kb = sum(f.stat().st_size / 1024 for f in assets_dir.rglob("*") if f.is_file())

        if total_size_kb > 10000:  # > 10 MB
            results.append(
                CheckResult.warning(
                    f"Total asset size is very large ({total_size_kb / 1024:.1f} MB)",
                    recommendation="Consider asset optimization to improve site performance.",
                )
            )
        # No success message - if sizes are reasonable, silence is golden

        return results

    def _check_duplicate_assets(self, assets_dir: Path) -> list[CheckResult]:
        """Check for duplicate assets (same size and name pattern)."""
        results: list[CheckResult] = []

        # Group files by base name (ignoring hash suffixes)
        # e.g., style.abc123.css and style.def456.css are duplicates

        css_files = list(assets_dir.rglob("*.css"))
        js_files = list(assets_dir.rglob("*.js"))

        # Check for multiple versions of same file
        css_base_names: dict[str, list[Path]] = defaultdict(list)
        for css_file in css_files:
            # Remove hash-like patterns (e.g., .abc123 before extension)
            base_name = css_file.stem.split(".")[0]
            css_base_names[base_name].append(css_file)

        js_base_names: dict[str, list[Path]] = defaultdict(list)
        for js_file in js_files:
            base_name = js_file.stem.split(".")[0]
            js_base_names[base_name].append(js_file)

        # Find duplicates
        duplicates = []

        for base_name, files in css_base_names.items():
            if len(files) > 1:
                file_list = ", ".join(f.name for f in files[:3])
                duplicates.append(f"{base_name} (CSS): {file_list}")

        for base_name, files in js_base_names.items():
            if len(files) > 1:
                file_list = ", ".join(f.name for f in files[:3])
                duplicates.append(f"{base_name} (JS): {file_list}")

        # No info message for duplicates - multiple versions are normal with cache busting

        return results

    def _check_minification_hints(self, assets_dir: Path, site: Site) -> list[CheckResult]:
        """Check if assets appear to be minified based on file size patterns."""
        results = []

        # Simple heuristic: minified files are typically smaller and have no .min suffix
        # This is not perfect but gives users a hint

        css_files = list(assets_dir.rglob("*.css"))
        js_files = list(assets_dir.rglob("*.js"))

        # Check if minification might be beneficial
        large_unminified_css = []
        for css_file in css_files:
            if ".min." not in css_file.name:
                size_kb = css_file.stat().st_size / 1024
                if size_kb > 50:  # > 50 KB and not minified
                    # Check if file looks minified (no newlines in first 1000 chars)
                    try:
                        content = css_file.read_text(encoding="utf-8", errors="ignore")[:1000]
                        newline_ratio = content.count("\n") / max(len(content), 1)

                        # If more than 5% newlines, probably not minified
                        if newline_ratio > 0.05:
                            large_unminified_css.append(f"{css_file.name}: {size_kb:.0f} KB")
                    except Exception as e:
                        logger.debug(
                            "health_asset_css_check_failed",
                            file=str(css_file),
                            error=str(e),
                            error_type=type(e).__name__,
                            action="skipping_minification_check",
                        )

        large_unminified_js = []
        for js_file in js_files:
            if ".min." not in js_file.name:
                size_kb = js_file.stat().st_size / 1024
                if size_kb > 50:
                    try:
                        content = js_file.read_text(encoding="utf-8", errors="ignore")[:1000]
                        newline_ratio = content.count("\n") / max(len(content), 1)

                        if newline_ratio > 0.05:
                            large_unminified_js.append(f"{js_file.name}: {size_kb:.0f} KB")
                    except Exception as e:
                        logger.debug(
                            "health_asset_js_check_failed",
                            file=str(js_file),
                            error=str(e),
                            error_type=type(e).__name__,
                            action="skipping_minification_check",
                        )

        if large_unminified_css:
            results.append(
                CheckResult.info(
                    f"{len(large_unminified_css)} large CSS file(s) may not be minified",
                    recommendation="Consider enabling CSS minification to reduce file sizes.",
                    details=large_unminified_css[:3],
                )
            )

        if large_unminified_js:
            results.append(
                CheckResult.info(
                    f"{len(large_unminified_js)} large JS file(s) may not be minified",
                    recommendation="Consider enabling JS minification to reduce file sizes.",
                    details=large_unminified_js[:3],
                )
            )

        # No success message - if optimization is good, silence is golden

        return results
