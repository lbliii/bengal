"""
Validation result caching mixin for BuildCache.

Provides methods for caching and retrieving health check validation results.
Used as a mixin by the main BuildCache class.

Key Concepts:
    - Caches CheckResult objects per file and validator
    - Invalidates when file content changes
    - Supports partial invalidation (single file or all)

Related Modules:
    - bengal.cache.build_cache.core: Main BuildCache class
    - bengal.health.report: CheckResult dataclass
    - bengal.health.health_check: Health check runner
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class ValidationCacheMixin:
    """
    Mixin providing validation result caching.

    Requires these attributes on the host class:
        - validation_results: dict[str, dict[str, list[dict[str, Any]]]]
        - is_changed: Callable[[Path], bool]  (from FileTrackingMixin)
    """

    # Type hints for mixin attributes (provided by host class)
    validation_results: dict[str, dict[str, list[dict[str, Any]]]]

    def is_changed(self, file_path: Path) -> bool:
        """Check if file changed (provided by FileTrackingMixin)."""
        raise NotImplementedError("Must be provided by FileTrackingMixin")

    def get_cached_validation_results(
        self, file_path: Path, validator_name: str
    ) -> list[dict[str, Any]] | None:
        """
        Get cached validation results for a file and validator.

        Args:
            file_path: Path to file
            validator_name: Name of validator

        Returns:
            List of CheckResult dicts if cached and file unchanged, None otherwise
        """
        file_key = str(file_path)

        # Check if file has changed
        if self.is_changed(file_path):
            # File changed - invalidate cached results
            if file_key in self.validation_results:
                del self.validation_results[file_key]
            return None

        # File unchanged - return cached results if available
        file_results = self.validation_results.get(file_key, {})
        return file_results.get(validator_name)

    def cache_validation_results(
        self, file_path: Path, validator_name: str, results: list[Any]
    ) -> None:
        """
        Cache validation results for a file and validator.

        Args:
            file_path: Path to file
            validator_name: Name of validator
            results: List of CheckResult objects to cache
        """
        file_key = str(file_path)

        # Ensure file entry exists
        if file_key not in self.validation_results:
            self.validation_results[file_key] = {}

        # Serialize CheckResult objects to dicts
        from bengal.health.report import CheckResult

        serialized_results = []
        for result in results:
            if isinstance(result, CheckResult):
                serialized_results.append(result.to_cache_dict())
            elif isinstance(result, dict):
                # Already serialized
                serialized_results.append(result)
            else:
                # Fallback: try to serialize
                serialized_results.append(
                    result.to_cache_dict() if hasattr(result, "to_cache_dict") else {}
                )

        self.validation_results[file_key][validator_name] = serialized_results

    def invalidate_validation_results(self, file_path: Path | None = None) -> None:
        """
        Invalidate validation results for a file or all files.

        Args:
            file_path: Path to file (if None, invalidate all)
        """
        if file_path is None:
            # Invalidate all
            self.validation_results.clear()
        else:
            # Invalidate specific file
            file_key = str(file_path)
            if file_key in self.validation_results:
                del self.validation_results[file_key]
