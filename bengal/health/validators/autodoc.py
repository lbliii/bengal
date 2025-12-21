"""
Autodoc HTML validator - checks autodoc page generation integrity.

Ensures all autodoc sections have HTML output files with correct page types.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus, ValidatorStats

if TYPE_CHECKING:
    from bengal.core.site import Site


class AutodocValidator(BaseValidator):
    """
    Validates autodoc HTML page generation.

    Checks:
    - All autodoc directories have index.html files
    - HTML and TXT file counts match (1:1 parity)
    - Page types are correctly set for nav tree
    - No orphan TXT files without corresponding HTML

    Implements HasStats protocol for observability.
    """

    name = "Autodoc"
    description = "Validates autodoc HTML page generation"
    enabled_by_default = True

    # Expected page types for each autodoc prefix
    EXPECTED_TYPES = {
        "api": "autodoc-python",
        "cli": "autodoc-cli",
    }

    # Store stats from last validation for observability
    last_stats: ValidatorStats | None = None

    @override
    def validate(self, site: Site, build_context: Any = None) -> list[CheckResult]:
        """
        Run autodoc HTML validation checks.

        Collects stats on:
        - Total autodoc directories checked
        - Missing HTML files
        - Type mismatches

        Args:
            site: Site instance to validate
            build_context: Optional BuildContext (unused)

        Returns:
            List of CheckResult objects
        """
        results: list[CheckResult] = []
        sub_timings: dict[str, float] = {}

        # Skip if autodoc not enabled
        autodoc_config = site.config.get("autodoc", {})
        if not autodoc_config:
            return results

        # Collect autodoc prefixes
        prefixes: list[str] = []
        if autodoc_config.get("python", {}).get("enabled", False):
            python_prefix = autodoc_config.get("python", {}).get("output_prefix", "")
            if not python_prefix:
                # Auto-derive from source_dirs
                source_dirs = autodoc_config.get("python", {}).get("source_dirs", [])
                if source_dirs:
                    from pathlib import Path

                    pkg_name = Path(source_dirs[0]).name
                    python_prefix = f"api/{pkg_name}"
                else:
                    python_prefix = "api/python"
            prefixes.append(python_prefix)

        if autodoc_config.get("cli", {}).get("enabled", False):
            cli_prefix = autodoc_config.get("cli", {}).get("output_prefix", "cli")
            prefixes.append(cli_prefix)

        if autodoc_config.get("openapi", {}).get("enabled", False):
            openapi_prefix = autodoc_config.get("openapi", {}).get("output_prefix", "")
            if openapi_prefix:
                prefixes.append(openapi_prefix)

        if not prefixes:
            return results

        stats = ValidatorStats(pages_total=0)

        # Check 1: HTML parity
        t0 = time.time()
        results.extend(self._check_html_parity(site, prefixes))
        sub_timings["html_parity"] = (time.time() - t0) * 1000

        # Check 2: Missing HTML directories
        t1 = time.time()
        results.extend(self._check_missing_html(site, prefixes))
        sub_timings["missing_html"] = (time.time() - t1) * 1000

        # Check 3: Page types
        t2 = time.time()
        results.extend(self._check_page_types(site, prefixes))
        sub_timings["page_types"] = (time.time() - t2) * 1000

        # Update stats
        stats.sub_timings = sub_timings
        self.last_stats = stats

        return results

    def _check_html_parity(self, site: Site, prefixes: list[str]) -> list[CheckResult]:
        """Check HTML and TXT file count parity."""
        results: list[CheckResult] = []

        for prefix in prefixes:
            prefix_dir = site.output_dir / prefix
            if not prefix_dir.exists():
                continue

            html_dirs = {p.parent for p in prefix_dir.rglob("index.html")}
            txt_dirs = {p.parent for p in prefix_dir.rglob("index.txt")}

            # Find orphan TXT files (TXT without HTML)
            orphans = txt_dirs - html_dirs

            if orphans:
                orphan_list = [str(p.relative_to(site.output_dir)) for p in list(orphans)[:5]]
                results.append(
                    CheckResult(
                        status=CheckStatus.ERROR,
                        message=f"Autodoc {prefix}: {len(orphans)} directories have TXT but no HTML",
                        details={
                            "prefix": prefix,
                            "orphan_count": len(orphans),
                            "sample": orphan_list,
                        },
                    )
                )

        return results

    def _check_missing_html(self, site: Site, prefixes: list[str]) -> list[CheckResult]:
        """Check for directories missing index.html."""
        results: list[CheckResult] = []

        for prefix in prefixes:
            prefix_dir = site.output_dir / prefix
            if not prefix_dir.exists():
                continue

            missing: list[str] = []
            for dir_path in prefix_dir.rglob("*"):
                if dir_path.is_dir() and not (dir_path / "index.html").exists():
                    missing.append(str(dir_path.relative_to(site.output_dir)))

            if missing:
                results.append(
                    CheckResult(
                        status=CheckStatus.ERROR,
                        message=f"Autodoc {prefix}: {len(missing)} directories missing index.html",
                        details={
                            "prefix": prefix,
                            "missing_count": len(missing),
                            "sample": missing[:10],
                        },
                    )
                )

        return results

    def _check_page_types(self, site: Site, prefixes: list[str]) -> list[CheckResult]:
        """Check page types are correctly set."""
        results: list[CheckResult] = []

        for prefix in prefixes:
            prefix_dir = site.output_dir / prefix
            if not prefix_dir.exists():
                continue

            # Determine expected type
            expected_type = None
            for type_prefix, etype in self.EXPECTED_TYPES.items():
                if prefix.startswith(type_prefix) or prefix == type_prefix:
                    expected_type = etype
                    break

            if not expected_type:
                continue

            # Check a sample of pages
            type_mismatches: list[str] = []
            sample_pages = list(prefix_dir.rglob("index.html"))[:20]

            for page_path in sample_pages:
                try:
                    html = page_path.read_text(encoding="utf-8")
                    if f'data-type="{expected_type}"' not in html:
                        import re

                        match = re.search(r'data-type="([^"]+)"', html)
                        actual = match.group(1) if match else "missing"
                        type_mismatches.append(
                            f"{page_path.relative_to(site.output_dir)}: got {actual}"
                        )
                except Exception:
                    pass

            if type_mismatches:
                results.append(
                    CheckResult(
                        status=CheckStatus.WARNING,
                        message=f"Autodoc {prefix}: {len(type_mismatches)} pages have wrong type (expected {expected_type})",
                        details={
                            "prefix": prefix,
                            "expected_type": expected_type,
                            "mismatch_count": len(type_mismatches),
                            "sample": type_mismatches[:5],
                        },
                    )
                )

        return results
