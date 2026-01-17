"""
Health check data models.

This module provides the core data structures for health check results:
    CheckStatus: Severity enum (ERROR, WARNING, SUGGESTION, INFO, SUCCESS)
    CheckResult: Individual check result with status, message, recommendations
    ValidatorStats: Observability metrics for validator execution
    ValidatorReport: Results from a single validator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from bengal.output.icons import get_icon_set
from bengal.utils.observability.rich_console import should_use_emoji


class CheckStatus(Enum):
    """
    Severity level for a health check result.

    Severity levels are ordered from most to least critical. The build system
    uses these levels to determine exit codes and output formatting:

    Severity Levels:
        ERROR: Blocks builds in strict mode, must fix before shipping
        WARNING: Does not block but should fix, indicates potential problems
        SUGGESTION: Quality improvements, collapsed by default in output
        INFO: Contextual information, hidden unless verbose mode enabled
        SUCCESS: Check passed, typically not shown unless verbose

    Usage:
        Validators return CheckResult with appropriate status. Use factory
        methods like CheckResult.error() or CheckResult.warning() for clarity.

    """

    SUCCESS = "success"
    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    """
    Result of a single health check.

    CheckResult is the standard output from validators. Use factory methods
    (success, info, suggestion, warning, error) for cleaner construction.

    Attributes:
        status: Severity level (ERROR, WARNING, SUGGESTION, INFO, SUCCESS)
        message: Human-readable description of what was checked/found
        code: Optional health check code (e.g., "H101") for searchability and CI integration
        recommendation: Optional fix suggestion (shown for warnings/errors)
        details: Optional list of specific items (e.g., file paths, line numbers)
        validator: Name of validator that produced this result
        metadata: Optional dict for validator-specific data (cacheable, machine-readable)

    Code Ranges:
        H0xx: Core/Basic (Output, Config, URL Collisions, Ownership)
        H1xx: Links & Navigation
        H2xx: Directives
        H3xx: Taxonomy
        H4xx: Cache & Performance
        H5xx: Feeds (RSS, Sitemap)
        H6xx: Assets (Fonts, Images)
        H7xx: Graph & References (Connectivity, Anchors, Cross-refs)
        H8xx: Tracks
        H9xx: Accessibility

    Example:
            >>> result = CheckResult.error(
            ...     "Missing required frontmatter field",
            ...     code="H001",
            ...     recommendation="Add 'title' to frontmatter",
            ...     details=["content/post.md:1"],
            ... )

    """

    status: CheckStatus
    message: str
    code: str | None = None
    recommendation: str | None = None
    details: list[str] | None = None
    validator: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def success(cls, message: str, code: str | None = None, validator: str = "") -> CheckResult:
        """Create a success result."""
        return cls(CheckStatus.SUCCESS, message, code=code, validator=validator)

    @classmethod
    def info(
        cls,
        message: str,
        code: str | None = None,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create an info result."""
        return cls(
            CheckStatus.INFO,
            message,
            code=code,
            recommendation=recommendation,
            details=details,
            validator=validator,
            metadata=metadata,
        )

    @classmethod
    def suggestion(
        cls,
        message: str,
        code: str | None = None,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create a suggestion result (quality improvement, not a problem)."""
        return cls(
            CheckStatus.SUGGESTION,
            message,
            code=code,
            recommendation=recommendation,
            details=details,
            validator=validator,
            metadata=metadata,
        )

    @classmethod
    def warning(
        cls,
        message: str,
        code: str | None = None,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create a warning result."""
        return cls(
            CheckStatus.WARNING,
            message,
            code=code,
            recommendation=recommendation,
            details=details,
            validator=validator,
            metadata=metadata,
        )

    @classmethod
    def error(
        cls,
        message: str,
        code: str | None = None,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create an error result."""
        return cls(
            CheckStatus.ERROR,
            message,
            code=code,
            recommendation=recommendation,
            details=details,
            validator=validator,
            metadata=metadata,
        )

    def is_problem(self) -> bool:
        """Check if this is a warning or error (vs success/info/suggestion)."""
        return self.status in (CheckStatus.WARNING, CheckStatus.ERROR)

    def is_actionable(self) -> bool:
        """Check if this requires action (error, warning, or suggestion)."""
        return self.status in (CheckStatus.ERROR, CheckStatus.WARNING, CheckStatus.SUGGESTION)

    @property
    def formatted_message(self) -> str:
        """Get message with code prefix if available (e.g., '[H101] Message')."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

    def to_cache_dict(self) -> dict[str, Any]:
        """
        Serialize CheckResult to JSON-serializable dict for caching.

        Returns:
            Dictionary with all fields as JSON-serializable types
        """
        return {
            "status": self.status.value,  # Enum to string
            "message": self.message,
            "code": self.code,
            "recommendation": self.recommendation,
            "details": self.details,
            "validator": self.validator,
            "metadata": self.metadata,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> CheckResult:
        """
        Deserialize CheckResult from cached dict.

        Args:
            data: Dictionary from cache

        Returns:
            CheckResult instance
        """
        return cls(
            status=CheckStatus(data["status"]),  # String to enum
            message=data["message"],
            code=data.get("code"),
            recommendation=data.get("recommendation"),
            details=data.get("details"),
            validator=data.get("validator", ""),
            metadata=data.get("metadata"),
        )


@dataclass
class ValidatorStats:
    """
    Observability metrics for a validator run.

    Validators can optionally populate stats to provide visibility into
    execution performance, cache effectiveness, and skip reasons. Stats
    are displayed in verbose mode and logged for debugging.

    Follows the ComponentStats pattern from bengal.utils.observability but
    uses page-specific naming appropriate for validator contexts.

    Attributes:
        pages_total: Total pages available in site
        pages_processed: Number of pages actually validated
        pages_skipped: Dict mapping skip reason to count
        cache_hits: Count of results retrieved from cache
        cache_misses: Count of results computed fresh
        sub_timings: Dict mapping operation name to duration in ms
        metrics: Custom metrics dict (validator-specific)

    Example:
            >>> stats = ValidatorStats(
            ...     pages_total=100,
            ...     pages_processed=95,
            ...     pages_skipped={"draft": 5},
            ...     cache_hits=80,
            ...     cache_misses=15,
            ... )
            >>> print(stats.format_summary())

    See Also:
        bengal.utils.observability.ComponentStats for the generic pattern

    """

    pages_total: int = 0
    pages_processed: int = 0
    pages_skipped: dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    sub_timings: dict[str, float] = field(default_factory=dict)
    metrics: dict[str, int | float | str] = field(default_factory=dict)

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage (0-100)."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    @property
    def skip_rate(self) -> float:
        """Skip rate as percentage (0-100)."""
        if self.pages_total == 0:
            return 0.0
        skipped = sum(self.pages_skipped.values())
        return skipped / self.pages_total * 100

    @property
    def total_skipped(self) -> int:
        """Total number of skipped items across all reasons."""
        return sum(self.pages_skipped.values())

    def format_summary(self) -> str:
        """Format stats for debug output."""
        parts = [f"processed={self.pages_processed}/{self.pages_total}"]

        if self.pages_skipped:
            skip_str = ", ".join(f"{k}={v}" for k, v in self.pages_skipped.items())
            parts.append(f"skipped=[{skip_str}]")

        if self.cache_hits or self.cache_misses:
            total = self.cache_hits + self.cache_misses
            parts.append(f"cache={self.cache_hits}/{total} ({self.cache_hit_rate:.0f}%)")

        if self.sub_timings:
            timing_str = ", ".join(f"{k}={v:.0f}ms" for k, v in self.sub_timings.items())
            parts.append(f"timings=[{timing_str}]")

        if self.metrics:
            metrics_str = ", ".join(f"{k}={v}" for k, v in self.metrics.items())
            parts.append(f"metrics=[{metrics_str}]")

        return " | ".join(parts)

    def to_log_context(self) -> dict[str, int | float | str]:
        """
        Convert to flat dict for structured logging.

        Returns:
            Flat dictionary suitable for structured logging kwargs.
        """
        ctx: dict[str, int | float | str] = {
            "pages_total": self.pages_total,
            "pages_processed": self.pages_processed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "skip_rate": self.skip_rate,
        }

        # Flatten sub-timings
        for timing_key, timing_val in self.sub_timings.items():
            ctx[f"timing_{timing_key}_ms"] = timing_val

        # Flatten skip reasons
        for skip_key, skip_val in self.pages_skipped.items():
            ctx[f"skipped_{skip_key}"] = skip_val

        # Flatten metrics
        for metric_key, metric_val in self.metrics.items():
            ctx[f"metric_{metric_key}"] = metric_val

        return ctx


@dataclass
class ValidatorReport:
    """
    Report from a single validator's execution.

    Aggregates all CheckResult objects from one validator along with timing
    and optional observability stats. Used by HealthReport to build the
    complete validation picture.

    Attributes:
        validator_name: Human-readable name of the validator
        results: All CheckResult objects produced by this validator
        duration_ms: Wall-clock time for validator execution
        stats: Optional ValidatorStats for observability

    """

    validator_name: str
    results: list[CheckResult] = field(default_factory=list)
    duration_ms: float = 0.0
    stats: ValidatorStats | None = None
    # Cache for computed counts (invalidated when results list changes)
    _cached_counts: dict[str, int] | None = field(default=None, repr=False)
    _cached_results_id: int = field(default=0, repr=False)
    _cached_results_len: int = field(default=-1, repr=False)

    def _get_counts(self) -> dict[str, int]:
        """
        Get status counts, computing and caching on first call or after mutation.

        Optimization: Instead of O(R) per count property access, this computes
        all counts once and caches the result. Subsequent property accesses
        are O(1) dict lookups. Cache is invalidated when results list is
        replaced or its length changes.

        Returns:
            Dict mapping status names to counts.

        Complexity:
            First call or after mutation: O(R)
            Subsequent calls: O(1)
        """
        # Invalidate cache if results list changed (replacement or mutation)
        current_id = id(self.results)
        current_len = len(self.results)
        if (
            self._cached_counts is None
            or self._cached_results_id != current_id
            or self._cached_results_len != current_len
        ):
            counts = {
                "success": 0,
                "info": 0,
                "warning": 0,
                "suggestion": 0,
                "error": 0,
            }
            for r in self.results:
                counts[r.status.value] = counts.get(r.status.value, 0) + 1
            self._cached_counts = counts
            self._cached_results_id = current_id
            self._cached_results_len = current_len
        return self._cached_counts

    @property
    def passed_count(self) -> int:
        """Count of successful checks."""
        return self._get_counts()["success"]

    @property
    def info_count(self) -> int:
        """Count of info messages."""
        return self._get_counts()["info"]

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return self._get_counts()["warning"]

    @property
    def suggestion_count(self) -> int:
        """Count of suggestions (quality improvements)."""
        return self._get_counts()["suggestion"]

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return self._get_counts()["error"]

    @property
    def has_problems(self) -> bool:
        """Check if this validator found any warnings or errors."""
        counts = self._get_counts()
        return counts["warning"] > 0 or counts["error"] > 0

    @property
    def status_emoji(self) -> str:
        """Get icon representing overall status."""
        icons = get_icon_set(should_use_emoji())
        if self.error_count > 0:
            return icons.error
        elif self.warning_count > 0:
            return icons.warning
        elif self.suggestion_count > 0:
            return icons.tip
        elif self.info_count > 0:
            return icons.info
        else:
            return icons.success
