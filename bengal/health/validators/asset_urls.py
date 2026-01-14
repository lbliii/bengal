"""
Asset URL validation for production builds.

Validates that asset URLs in rendered HTML actually resolve to files
in the output directory. Catches fingerprinting mismatches before deploy.

This validator runs post-render and checks:
1. CSS/JS references in HTML resolve to actual files
2. Fingerprinted assets have corresponding manifest entries
3. No broken asset references exist in rendered output
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext

logger = get_logger(__name__)


class AssetURLValidator(BaseValidator):
    """
    Validates that asset URLs in rendered HTML resolve to actual files.
    
    This catches fingerprinting issues before deployment. Critical for
    production builds where fingerprinting is enabled.
    
    Checks:
    - CSS/JS links in HTML point to existing files
    - Detects when HTML uses non-fingerprinted URLs but only fingerprinted files exist
    - Samples HTML files for performance
        
    """

    name = "Asset URLs"
    description = "Validates asset references resolve to actual files"
    enabled_by_default = True

    # Pattern to match asset URLs in href/src attributes
    ASSET_PATTERN = re.compile(
        r'(?:href|src)=["\']([^"\']*?/assets/[^"\']+)["\']',
        re.IGNORECASE,
    )

    # How many HTML files to sample
    MAX_SAMPLE_FILES = 50

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run asset URL validation checks."""
        results: list[CheckResult] = []
        output_dir = site.output_dir

        if not output_dir.exists():
            return results

        # Find all HTML files (sample for performance)
        html_files = list(output_dir.rglob("*.html"))[: self.MAX_SAMPLE_FILES]

        if not html_files:
            return results

        missing_assets: list[dict[str, Any]] = []
        checked = 0

        # Get baseurl for path normalization
        baseurl = (site.baseurl or "").strip("/")

        for html_file in html_files:
            try:
                content = html_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for match in self.ASSET_PATTERN.finditer(content):
                asset_url = match.group(1)
                checked += 1

                # Normalize URL to file path
                asset_path = asset_url
                if baseurl and asset_path.startswith(f"/{baseurl}/"):
                    asset_path = asset_path[len(baseurl) + 1 :]
                elif asset_path.startswith("/"):
                    asset_path = asset_path[1:]

                # Check if file exists
                full_path = output_dir / asset_path
                if not full_path.exists():
                    # Check if it's a fingerprinting issue
                    fingerprinted_exists = self._check_fingerprinted_version(full_path)

                    missing_assets.append(
                        {
                            "url": asset_url,
                            "expected_file": str(asset_path),
                            "html_file": str(html_file.relative_to(output_dir)),
                            "fingerprinted_exists": fingerprinted_exists,
                        }
                    )
                else:
                    # File exists, but check case sensitivity
                    case_issue = self._check_case_sensitivity(full_path, asset_path)
                    if case_issue:
                        missing_assets.append(
                            {
                                "url": asset_url,
                                "expected_file": str(asset_path),
                                "html_file": str(html_file.relative_to(output_dir)),
                                "case_mismatch": case_issue,
                            }
                        )

        # Dedupe by URL
        seen_urls: set[str] = set()
        unique_missing: list[dict[str, Any]] = []
        for item in missing_assets:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                unique_missing.append(item)

        # Report fingerprint mismatches as errors (these break production!)
        fingerprint_issues = [m for m in unique_missing if m.get("fingerprinted_exists")]
        if fingerprint_issues:
            sample = fingerprint_issues[:3]
            urls = [m["url"] for m in sample]
            results.append(
                CheckResult(
                    name="asset_url_fingerprint_mismatch",
                    status=CheckStatus.ERROR,
                    message=f"{len(fingerprint_issues)} asset URL(s) reference non-fingerprinted files but only fingerprinted versions exist",
                    details={
                        "count": len(fingerprint_issues),
                        "sample_urls": urls,
                        "hint": "asset_url() should resolve to fingerprinted paths via manifest lookup",
                    },
                    recommendations=[
                        "Check that asset manifest is loaded during template rendering",
                        "Verify asset_url() uses manifest for fingerprint resolution",
                        "Run `make deploy-test` to catch this locally before pushing",
                    ],
                )
            )

        # Report case sensitivity issues (breaks on Linux CI!)
        case_issues = [m for m in unique_missing if m.get("case_mismatch")]
        if case_issues:
            sample = case_issues[:3]
            details = [f"{m['url']} -> actual: {m['case_mismatch']}" for m in sample]
            results.append(
                CheckResult(
                    name="asset_url_case_mismatch",
                    status=CheckStatus.WARNING,
                    message=f"{len(case_issues)} asset URL(s) have case mismatches - will break on case-sensitive systems (Linux CI)",
                    details={
                        "count": len(case_issues),
                        "sample_mismatches": details,
                        "warning": "Works on macOS but FAILS on Linux/GitHub Actions",
                    },
                    recommendations=[
                        "Fix the case in asset URLs to match actual file names exactly",
                        "Most themes use lowercase: css/, js/, not CSS/, JS/",
                    ],
                )
            )

        # Report other missing assets as warnings
        other_missing = [
            m
            for m in unique_missing
            if not m.get("fingerprinted_exists") and not m.get("case_mismatch")
        ]
        if other_missing:
            sample = other_missing[:3]
            urls = [m["url"] for m in sample]
            results.append(
                CheckResult(
                    name="asset_url_missing",
                    status=CheckStatus.WARNING,
                    message=f"{len(other_missing)} asset URL(s) reference files that don't exist",
                    details={
                        "count": len(other_missing),
                        "sample_urls": urls,
                    },
                    recommendations=[
                        "Check that referenced assets exist in theme or site assets",
                        "Verify asset paths are correct in templates",
                    ],
                )
            )

        # Success if no issues
        if not unique_missing:
            results.append(
                CheckResult(
                    name="asset_urls_valid",
                    status=CheckStatus.SUCCESS,
                    message=f"All {checked} asset references resolve to existing files",
                )
            )

        return results

    def _check_fingerprinted_version(self, full_path: Path) -> bool:
        """Check if a fingerprinted version of the file exists.

        Args:
            full_path: Expected file path (non-fingerprinted)

        Returns:
            True if a fingerprinted version exists (e.g., style.abc123.css)
        """
        parent = full_path.parent
        stem = full_path.stem
        suffix = full_path.suffix

        if not parent.exists():
            return False

        # Look for files matching pattern: stem.*.suffix
        return any(f.suffix == suffix and f.stem.startswith(stem + ".") for f in parent.iterdir())

    def _check_case_sensitivity(self, full_path: Path, asset_path: str) -> str | None:
        """Check if file exists but with different case.

        On case-insensitive filesystems (macOS, Windows), a file will be found
        even if the case doesn't match. On case-sensitive systems (Linux),
        it will 404. This detects mismatches early.

        Args:
            full_path: The resolved path (which exists on case-insensitive FS)
            asset_path: The original asset path from HTML

        Returns:
            The actual file name if there's a case mismatch, None otherwise
        """
        try:
            # Get the canonical path with correct case
            # resolve() gives the real path, which has the actual case on disk
            canonical = full_path.resolve()

            # Compare the asset_path parts with the canonical path parts
            asset_parts = Path(asset_path).parts
            canonical_parts = canonical.parts

            # We only care about the tail (relative part under output_dir)
            # Find where the asset path appears in canonical path
            if len(canonical_parts) >= len(asset_parts):
                tail_canonical = canonical_parts[-len(asset_parts) :]

                # Compare each component
                for expected, actual in zip(asset_parts, tail_canonical, strict=False):
                    if expected != actual and expected.lower() == actual.lower():
                        # Case mismatch found!
                        return str(Path(*tail_canonical))

            return None
        except (OSError, ValueError):
            return None
