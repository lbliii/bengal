"""Versioned validation report envelope for CLI and machine output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import CheckStatus

if TYPE_CHECKING:
    from datetime import datetime

    from .health_report import HealthReport
    from .models import CheckResult


DEFAULT_CHECK_SCHEMA = "bengal.check.v1"


@dataclass(frozen=True, slots=True)
class ReportPolicy:
    """Policy used to decide whether a validation report fails."""

    errors_fail: bool = True
    warnings_fail: bool = False
    suggestions_fail: bool = False

    def status_for(self, *, errors: int, warnings: int, suggestions: int) -> str:
        """Return the policy status for the given summary counts."""
        if (self.errors_fail and errors) or (self.warnings_fail and warnings):
            return "failed"
        if self.suggestions_fail and suggestions:
            return "failed"
        if warnings:
            return "passed_with_warnings"
        if suggestions:
            return "passed_with_suggestions"
        return "passed"

    def to_dict(self) -> dict[str, bool]:
        """Serialize policy for JSON/Kida contexts."""
        return {
            "errors_fail": self.errors_fail,
            "warnings_fail": self.warnings_fail,
            "suggestions_fail": self.suggestions_fail,
        }


@dataclass(frozen=True, slots=True)
class ReportFinding:
    """Presentation-neutral finding adapted from a health check result."""

    severity: str
    message: str
    validator: str
    code: str | None = None
    recommendation: str | None = None
    details: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_check_result(cls, result: CheckResult, *, validator: str) -> ReportFinding:
        """Adapt an existing ``CheckResult`` without changing validator contracts."""
        return cls(
            severity=result.status.value,
            message=result.message,
            validator=result.validator or validator,
            code=result.code,
            recommendation=result.recommendation,
            details=tuple(result.details or ()),
            metadata=result.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize finding for JSON/Kida contexts."""
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "validator": self.validator,
            "recommendation": self.recommendation,
            "details": list(self.details),
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ReportEnvelope:
    """Versioned report envelope shared by check/audit CLI output."""

    schema_version: str
    command: str
    status: str
    policy: ReportPolicy
    summary: dict[str, Any]
    findings: tuple[ReportFinding, ...] = ()
    generated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize envelope for JSON/Kida contexts."""
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "command": self.command,
            "status": self.status,
            "policy": self.policy.to_dict(),
            "summary": dict(self.summary),
            "findings": [finding.to_dict() for finding in self.findings],
        }
        if self.generated_at is not None:
            data["generated_at"] = self.generated_at.isoformat()
        if self.metadata:
            data["metadata"] = dict(self.metadata)
        return data


def envelope_from_health_report(
    report: HealthReport,
    *,
    command: str = "check",
    schema_version: str = DEFAULT_CHECK_SCHEMA,
    policy: ReportPolicy | None = None,
    include_success: bool = False,
) -> ReportEnvelope:
    """Adapt a ``HealthReport`` to the versioned report envelope."""
    policy = policy or ReportPolicy()
    summary: dict[str, Any] = {
        "total_checks": report.total_checks,
        "passed": report.total_passed,
        "info": report.total_info,
        "suggestions": report.total_suggestions,
        "warnings": report.total_warnings,
        "errors": report.total_errors,
        "quality_score": report.build_quality_score(),
        "quality_rating": report.quality_rating(),
    }
    findings: list[ReportFinding] = []
    for validator_report in report.validator_reports:
        for result in validator_report.results:
            if result.status == CheckStatus.SUCCESS and not include_success:
                continue
            findings.append(
                ReportFinding.from_check_result(
                    result,
                    validator=validator_report.validator_name,
                )
            )

    return ReportEnvelope(
        schema_version=schema_version,
        command=command,
        status=policy.status_for(
            errors=report.total_errors,
            warnings=report.total_warnings,
            suggestions=report.total_suggestions,
        ),
        policy=policy,
        summary=summary,
        findings=tuple(findings),
        generated_at=report.timestamp,
    )
