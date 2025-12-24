"""
Type definitions for health check system.

This module provides TypedDict definitions for health check results, validator
outputs, and report serialization. These complement the dataclasses in
bengal.health.report by providing dict-based types for JSON serialization
and configuration.

Note:
    Core health types (CheckResult, CheckStatus, HealthReport) are dataclasses
    in bengal.health.report. This module provides complementary TypedDicts
    for dict-based patterns like cache serialization and config.

See Also:
    - :mod:`bengal.health.report`: Core dataclasses (CheckResult, HealthReport)
    - :mod:`bengal.health.base`: Validator base class
    - :mod:`bengal.health.health_check`: Health check orchestrator
"""

from __future__ import annotations

from typing import Literal, Protocol, TypedDict, runtime_checkable

# =============================================================================
# Check Result Types (dict form for serialization)
# =============================================================================

# Status literal type matching CheckStatus enum
CheckStatusLiteral = Literal["success", "info", "suggestion", "warning", "error"]


class CheckResultDict(TypedDict, total=False):
    """Serialized form of CheckResult for caching/JSON."""

    status: CheckStatusLiteral
    message: str
    code: str | None
    recommendation: str | None
    details: list[str] | None
    validator: str
    metadata: dict[str, str | int | float | bool | None]


class ValidatorIssue(TypedDict):
    """Single validation issue (simplified form for reporting)."""

    severity: CheckStatusLiteral
    message: str
    file: str | None
    line: int | None
    code: str  # Issue code like "H101"


# =============================================================================
# Validator Statistics Types
# =============================================================================


class ValidatorStatsDict(TypedDict, total=False):
    """Serialized form of ValidatorStats."""

    pages_total: int
    pages_processed: int
    pages_skipped: dict[str, int]
    cache_hits: int
    cache_misses: int
    sub_timings: dict[str, float]
    metrics: dict[str, int | float | str]


class ValidatorResultDict(TypedDict, total=False):
    """Result from a single validator execution."""

    validator: str
    passed: bool
    results: list[CheckResultDict]
    duration_ms: float
    stats: ValidatorStatsDict | None
    cached: bool


# =============================================================================
# Health Report Types
# =============================================================================


class HealthReportDict(TypedDict, total=False):
    """Serialized form of HealthReport."""

    total_validators: int
    passed: int
    failed: int
    warnings_count: int
    errors_count: int
    suggestions_count: int
    duration_ms: float
    generated_at: str
    validators: list[ValidatorResultDict]
    quality_score: int
    quality_rating: Literal["Excellent", "Good", "Fair", "Needs Improvement"]


class HealthSummary(TypedDict):
    """Quick summary of health check results."""

    passed: bool
    errors: int
    warnings: int
    suggestions: int
    score: int
    rating: str


# =============================================================================
# Autofix Types
# =============================================================================


class FixAction(TypedDict, total=False):
    """A single fix action from autofix system."""

    type: Literal["add", "remove", "replace", "insert", "delete"]
    file: str
    line: int | None
    original: str | None
    replacement: str | None
    description: str


class DirectiveInfo(TypedDict, total=False):
    """Information about a directive for autofix."""

    name: str
    line: int
    file: str
    type: str
    options: dict[str, str]
    content: str | None


class AutofixResult(TypedDict, total=False):
    """Result of an autofix operation."""

    success: bool
    actions_applied: int
    actions_failed: int
    files_modified: list[str]
    errors: list[str]
    backup_path: str | None


class AutofixConfig(TypedDict, total=False):
    """Configuration for autofix behavior."""

    dry_run: bool
    backup: bool
    interactive: bool
    fix_types: list[str]  # Which fix types to apply


# =============================================================================
# Validator Configuration Types
# =============================================================================


class ValidatorConfig(TypedDict, total=False):
    """Configuration for a validator."""

    enabled: bool
    strict: bool
    exclude_patterns: list[str]
    include_patterns: list[str]
    thresholds: dict[str, int | float]
    options: dict[str, str | int | float | bool]


class HealthCheckConfig(TypedDict, total=False):
    """Configuration for health check system."""

    enabled: bool
    verbose: bool
    strict_mode: bool
    validators: dict[str, ValidatorConfig]
    build_validators: list[str]
    full_validators: list[str]
    ci_validators: list[str]
    quality_thresholds: QualityThresholds


class QualityThresholds(TypedDict, total=False):
    """Thresholds for quality scoring."""

    excellent: int  # Score >= this = Excellent
    good: int  # Score >= this = Good
    fair: int  # Score >= this = Fair
    # Below fair = Needs Improvement


# =============================================================================
# Validator Protocol
# =============================================================================


@runtime_checkable
class ValidatorProtocol(Protocol):
    """
    Protocol for health validators.

    All validators implement this interface, enabling polymorphic
    validation orchestration.
    """

    @property
    def name(self) -> str:
        """Validator name for display and configuration."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    def validate(self, site: object) -> list[object]:
        """
        Run validation and return results.

        Args:
            site: Site object to validate

        Returns:
            List of CheckResult objects
        """
        ...


# =============================================================================
# Link Validation Types
# =============================================================================


class BrokenLink(TypedDict):
    """A broken link found during validation."""

    source_file: str
    source_line: int | None
    target: str
    link_type: Literal["internal", "external", "anchor"]
    error: str


class LinkValidationResult(TypedDict, total=False):
    """Result of link validation."""

    total_links: int
    valid_links: int
    broken_links: list[BrokenLink]
    skipped_links: int
    external_checked: int
    external_errors: int


# =============================================================================
# Connectivity Types
# =============================================================================


class ConnectivityScore(TypedDict):
    """Connectivity score for a page."""

    page_path: str
    score: float
    level: Literal["well_connected", "adequately_linked", "lightly_linked", "isolated"]
    inbound_links: int
    outbound_links: int
    menu_links: int
    taxonomy_links: int


class ConnectivityReport(TypedDict, total=False):
    """Report on site connectivity."""

    total_pages: int
    well_connected: int
    adequately_linked: int
    lightly_linked: int
    isolated: int
    average_score: float
    isolated_pages: list[str]


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Check result types
    "CheckStatusLiteral",
    "CheckResultDict",
    "ValidatorIssue",
    # Validator stats
    "ValidatorStatsDict",
    "ValidatorResultDict",
    # Health report
    "HealthReportDict",
    "HealthSummary",
    # Autofix
    "FixAction",
    "DirectiveInfo",
    "AutofixResult",
    "AutofixConfig",
    # Configuration
    "ValidatorConfig",
    "HealthCheckConfig",
    "QualityThresholds",
    # Protocol
    "ValidatorProtocol",
    # Link validation
    "BrokenLink",
    "LinkValidationResult",
    # Connectivity
    "ConnectivityScore",
    "ConnectivityReport",
]
