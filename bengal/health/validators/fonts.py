"""
Font validator - checks font downloads and CSS generation.

Validates:
- Font files downloaded successfully
- CSS generated correctly
- Font variants match config
- No broken font references
- Reasonable font file sizes
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.utils.build_context import BuildContext

if TYPE_CHECKING:
    from bengal.core.site import Site


class FontValidator(BaseValidator):
    """
    Validates font downloads and CSS generation.

    Checks:
    - Font configuration is valid
    - Font files downloaded (if fonts configured)
    - CSS generated with correct @font-face rules
    - Font file sizes are reasonable
    - No broken font references in CSS
    """

    name = "Fonts"
    description = "Validates font downloads and CSS generation"
    enabled_by_default = True

    # Max font file size (500 KB is reasonable for a single font variant)
    MAX_FONT_SIZE_KB = 500

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run font validation checks."""
        results = []

        # Check if fonts are configured
        font_config = site.config.get("fonts", {})

        if not font_config:
            results.append(
                CheckResult.info(
                    "No fonts configured",
                    recommendation="Add [fonts] section to bengal.toml to use custom fonts.",
                )
            )
            return results

        # Check 1: Font CSS exists
        fonts_css_path = site.output_dir / "assets" / "fonts.css"
        if not fonts_css_path.exists():
            results.append(
                CheckResult.warning(
                    "fonts.css not generated despite font configuration",
                    recommendation="Check if FontHelper.process() is called during build.",
                )
            )
            return results

        # Check 2: Font files exist
        fonts_dir = site.output_dir / "assets" / "fonts"
        results.extend(self._check_font_files(fonts_dir, font_config))

        # Check 3: CSS structure
        results.extend(self._check_font_css(fonts_css_path, fonts_dir))

        # Check 4: Font file sizes
        results.extend(self._check_font_sizes(fonts_dir))

        return results

    def _check_font_files(self, fonts_dir: Path, font_config: dict[str, Any]) -> list[CheckResult]:
        """Check font files are downloaded."""
        results = []

        if not fonts_dir.exists():
            results.append(
                CheckResult.error(
                    "Fonts directory does not exist",
                    recommendation="Font files should be in assets/fonts/. Check FontHelper.process().",
                )
            )
            return results

        # Count font files
        font_files = list(fonts_dir.glob("*.woff2")) + list(fonts_dir.glob("*.ttf"))

        if not font_files:
            results.append(
                CheckResult.error(
                    "No font files found in assets/fonts/",
                    recommendation="Font download may have failed. Check FontHelper and network connectivity.",
                )
            )
            return results

        # Estimate expected number of font files
        # Each font family typically has 1-4 variants (weights/styles)
        num_families = len([k for k in font_config if k != "config"])
        expected_min = num_families  # At least 1 file per family

        if len(font_files) < expected_min:
            results.append(
                CheckResult.warning(
                    f"Found {len(font_files)} font file(s) but configured {num_families} font familie(s)",
                    recommendation="Some fonts may not have downloaded. Check for download errors in logs.",
                )
            )
        # No success message - if fonts downloaded, silence is golden

        return results

    def _check_font_css(self, fonts_css_path: Path, fonts_dir: Path) -> list[CheckResult]:
        """Check font CSS structure and references."""
        results = []

        try:
            css_content = fonts_css_path.read_text(encoding="utf-8")
        except Exception as e:
            results.append(
                CheckResult.error(
                    f"Cannot read fonts.css: {e}",
                    recommendation="Check file permissions and encoding.",
                )
            )
            return results

        # Check for @font-face rules
        font_face_count = css_content.count("@font-face")

        if font_face_count == 0:
            results.append(
                CheckResult.error(
                    "fonts.css has no @font-face rules",
                    recommendation="CSS should contain @font-face declarations. Check FontCSSGenerator.",
                )
            )
            return results

        # Check for broken font references
        broken_refs = self._check_font_references(css_content, fonts_dir)

        if broken_refs:
            results.append(
                CheckResult.error(
                    f"{len(broken_refs)} font reference(s) point to missing files",
                    recommendation="Font files referenced in CSS don't exist. Check font download.",
                    details=broken_refs[:5],
                )
            )
        # No success message - if references are valid, silence is golden

        return results

    def _check_font_references(self, css_content: str, fonts_dir: Path) -> list[str]:
        """Check if font files referenced in CSS exist."""
        broken = []

        # Find all url() references in CSS
        # Pattern: url('/fonts/font-name.woff2')
        url_pattern = r'url\([\'"]?/fonts/([^\'"()]+)[\'"]?\)'

        for match in re.finditer(url_pattern, css_content):
            filename = match.group(1)
            font_file = fonts_dir / filename

            if not font_file.exists():
                broken.append(filename)

        return broken

    def _check_font_sizes(self, fonts_dir: Path) -> list[CheckResult]:
        """Check font file sizes are reasonable."""
        results: list[CheckResult] = []

        if not fonts_dir.exists():
            return results

        font_files = list(fonts_dir.glob("*.woff2")) + list(fonts_dir.glob("*.ttf"))

        if not font_files:
            return results

        # Check for oversized fonts
        oversized = []
        total_size_kb: float = 0

        for font_file in font_files:
            size_kb = font_file.stat().st_size / 1024
            total_size_kb += size_kb

            if size_kb > self.MAX_FONT_SIZE_KB:
                oversized.append(f"{font_file.name}: {size_kb:.0f} KB")

        if oversized:
            results.append(
                CheckResult.warning(
                    f"{len(oversized)} font file(s) are very large (>{self.MAX_FONT_SIZE_KB} KB)",
                    recommendation="Large font files slow page load. Consider using fewer weights or variable fonts.",
                    details=oversized[:3],
                )
            )

        # Report total font size
        if total_size_kb > 1000:  # > 1 MB
            results.append(
                CheckResult.warning(
                    f"Total font size is {total_size_kb:.0f} KB ({total_size_kb / 1024:.1f} MB)",
                    recommendation="Consider reducing number of font weights to improve performance.",
                )
            )
        # No success message - if sizes are reasonable, silence is golden

        return results
