"""
Cache validator - checks incremental build cache integrity.

Validates:
- Cache file exists and is readable
- Cache is not corrupted
- Cache size is reasonable
- Basic dependency tracking works
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext

logger = get_logger(__name__)


class CacheValidator(BaseValidator):
    """
    Validates build cache integrity (essential checks only).

    Checks:
    - Cache file exists and is readable
    - Cache format is valid JSON
    - Cache size is reasonable (not corrupted/bloated)
    - Has expected structure (file_hashes, dependencies)

    Skips:
    - Deep dependency graph validation (complex)
    - File hash verification (too slow)
    - Advanced corruption detection (overkill)
    """

    name = "Cache Integrity"
    description = "Validates incremental build cache"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run cache validation checks."""
        results = []

        # Skip if incremental builds not used
        if not site.config.get("incremental", False):
            results.append(
                CheckResult.info(
                    "Incremental builds not enabled",
                    recommendation="Enable with 'incremental = true' in config for faster rebuilds.",
                )
            )
            return results

        # Check 1: Cache location (new location since v0.1.2)
        cache_path = site.paths.build_cache

        # Check for old cache location (migration needed)
        old_cache_path = site.output_dir / ".bengal-cache.json"
        if old_cache_path.exists() and not cache_path.exists():
            results.append(
                CheckResult.warning(
                    "Cache at legacy location (public/.bengal-cache.json)",
                    recommendation="Run 'bengal build' to migrate cache to .bengal/cache.json automatically.",
                )
            )
            # Validate the old cache for now
            cache_path = old_cache_path

        if not cache_path.exists():
            results.append(
                CheckResult.info(
                    "No cache file found (first build or cache cleared)",
                    recommendation="Cache will be created after first build at .bengal/cache.json",
                )
            )
            return results

        # Check 2: Cache file readable
        cache_readable, cache_data = self._check_cache_readable(cache_path)
        if not cache_readable:
            results.append(
                CheckResult.error(
                    f"Cache file exists but cannot be read: {cache_path}",
                    recommendation="Delete cache and rebuild: 'bengal clean --cache && bengal build'",
                )
            )
            return results

        results.append(
            CheckResult.success(f"Cache file readable at {cache_path.relative_to(site.root_path)}")
        )

        # Check 3: Cache structure valid
        structure_valid, structure_issues = self._check_cache_structure(cache_data)
        if not structure_valid:
            results.append(
                CheckResult.error(
                    f"Cache structure invalid: {', '.join(structure_issues)}",
                    recommendation="Cache may be corrupted: 'bengal clean --cache && bengal build'",
                )
            )
        else:
            results.append(CheckResult.success("Cache structure valid"))

        # Check 4: Cache size reasonable
        results.extend(self._check_cache_size(cache_path, cache_data))

        # Check 5: Cache location correctness (new check for v0.1.2+)
        if cache_path == site.paths.build_cache:
            results.append(CheckResult.success("Cache at correct location (.bengal/)"))
        else:
            results.append(
                CheckResult.info(
                    "Cache at legacy location (will be migrated on next build)",
                    recommendation="Run 'bengal build' to migrate automatically",
                )
            )

        # Check 5: Basic dependency tracking
        results.extend(self._check_dependencies(cache_data))

        return results

    def _check_cache_readable(self, cache_path: Path) -> tuple[bool, dict[str, Any]]:
        """Check if cache file is readable and valid JSON."""
        try:
            with open(cache_path, encoding="utf-8") as f:
                cache_data = json.load(f)
            return True, cache_data
        except json.JSONDecodeError as e:
            logger.debug(
                "health_cache_json_decode_failed",
                cache_path=str(cache_path),
                error=str(e),
                action="returning_unreadable",
            )
            return False, {}
        except Exception as e:
            logger.debug(
                "health_cache_read_failed",
                cache_path=str(cache_path),
                error=str(e),
                error_type=type(e).__name__,
                action="returning_unreadable",
            )
            return False, {}

    def _check_cache_structure(self, cache_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Check if cache has expected structure."""
        issues = []

        # Check for expected top-level keys
        expected_keys = ["file_hashes", "dependencies"]
        for key in expected_keys:
            if key not in cache_data:
                issues.append(f"missing '{key}'")

        # Check that values are dicts
        if "file_hashes" in cache_data and not isinstance(cache_data["file_hashes"], dict):
            issues.append("'file_hashes' is not a dict")

        if "dependencies" in cache_data and not isinstance(cache_data["dependencies"], dict):
            issues.append("'dependencies' is not a dict")

        return len(issues) == 0, issues

    def _check_cache_size(self, cache_path: Path, cache_data: dict[str, Any]) -> list[CheckResult]:
        """Check if cache size is reasonable."""
        results = []

        # Get file size
        size_bytes = cache_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        # Check if unreasonably large
        if size_mb > 50:
            results.append(
                CheckResult.warning(
                    f"Cache file is very large ({size_mb:.1f} MB)",
                    recommendation="Large cache may indicate excessive file tracking. Consider cleaning old entries.",
                )
            )
        elif size_mb > 10:
            results.append(CheckResult.info(f"Cache file size: {size_mb:.1f} MB"))
        else:
            results.append(CheckResult.success(f"Cache file size: {size_mb:.1f} MB (reasonable)"))

        # Check entry counts
        file_count = len(cache_data.get("file_hashes", {}))
        dep_count = len(cache_data.get("dependencies", {}))

        if file_count > 10000:
            results.append(
                CheckResult.warning(
                    f"Cache tracking {file_count:,} files (very large)",
                    recommendation="Consider checking for unnecessary file tracking.",
                )
            )
        else:
            results.append(
                CheckResult.info(f"Cache tracking {file_count:,} files, {dep_count:,} dependencies")
            )

        return results

    def _check_dependencies(self, cache_data: dict[str, Any]) -> list[CheckResult]:
        """Check basic dependency tracking."""
        results = []

        dependencies = cache_data.get("dependencies", {})

        if not dependencies:
            results.append(
                CheckResult.info(
                    "No dependencies tracked yet",
                    recommendation="Dependencies are tracked during builds.",
                )
            )
            return results

        # Check for orphaned dependencies (files that don't exist)
        orphaned = []
        for source_file in list(dependencies.keys())[:10]:  # Sample first 10
            source_path = Path(source_file)
            if not source_path.exists():
                orphaned.append(source_file)

        if orphaned:
            results.append(
                CheckResult.warning(
                    f"Found {len(orphaned)} dependency reference(s) to missing files",
                    recommendation="Normal if files were deleted. Cache will clean up on next build.",
                    details=[str(Path(f).name) for f in orphaned[:3]],
                )
            )
        else:
            results.append(CheckResult.success("Dependency tracking appears valid"))

        return results
