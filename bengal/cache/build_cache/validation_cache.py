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

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.build.contracts.keys import CacheKey


class ValidationCacheMixin:
    """
    Mixin providing validation result caching.

    Requires these attributes on the host class:
        - validation_results: dict[str, dict[str, Any]]
        - is_changed: Callable[[Path], bool]  (from FileTrackingMixin)
        - _cache_key: Callable[[Path], str]  # Canonical path key

    """

    # Type hints for mixin attributes (provided by host class)
    validation_results: dict[str, dict[str, Any]]

    def is_changed(self, file_path: Path) -> bool:
        """Check if file changed (provided by FileTrackingMixin)."""
        raise NotImplementedError("Must be provided by FileTrackingMixin")

    def _cache_key(self, path: Path) -> CacheKey:
        """Return a canonical cache key (provided by host BuildCache)."""
        raise NotImplementedError("Must be provided by BuildCache")

    def get_cached_validation_results(
        self,
        file_path: Path,
        validator_name: str,
        cache_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get cached validation results for a file and validator.

        Args:
            file_path: Path to file
            validator_name: Name of validator
            cache_context: Optional context that must match cached metadata.

        Returns:
            List of CheckResult dicts if cached and file unchanged, None otherwise
        """
        file_key = self._cache_key(file_path)

        # Check if file has changed
        if self.is_changed(file_path):
            # File changed - invalidate cached results
            if file_key in self.validation_results:
                del self.validation_results[file_key]
            return None

        # File unchanged - return cached results if available
        file_results = self.validation_results.get(file_key, {})
        entry = file_results.get(validator_name)
        return _validation_results_from_entry(entry, cache_context)

    def cache_validation_results(
        self,
        file_path: Path,
        validator_name: str,
        results: list[Any],
        cache_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Cache validation results for a file and validator.

        Args:
            file_path: Path to file
            validator_name: Name of validator
            results: List of CheckResult objects to cache
            cache_context: Optional context required for future cache reuse
        """
        file_key = self._cache_key(file_path)

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

        if cache_context is None:
            self.validation_results[file_key][validator_name] = serialized_results
        else:
            self.validation_results[file_key][validator_name] = {
                "context": dict(cache_context),
                "results": serialized_results,
            }

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
            file_key = self._cache_key(file_path)
            if file_key in self.validation_results:
                del self.validation_results[file_key]


def _validation_results_from_entry(
    entry: Any,
    cache_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """Decode legacy or context-enveloped cached validation results."""
    if entry is None:
        return None

    if cache_context is None:
        if isinstance(entry, list):
            return entry
        if isinstance(entry, dict) and isinstance(entry.get("results"), list):
            return entry["results"]
        return None

    if not isinstance(entry, dict):
        return None
    if entry.get("context") != cache_context:
        return None
    results = entry.get("results")
    return results if isinstance(results, list) else None
