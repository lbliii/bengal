"""
Serialization functions for health reports.

This module provides JSON export and CI integration formats for health
reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import ValidatorReport


def format_report_json(
    validator_reports: list[ValidatorReport],
    timestamp: datetime,
    build_stats: dict[str, Any] | None,
    total_checks: int,
    total_passed: int,
    total_info: int,
    total_warnings: int,
    total_errors: int,
    quality_score: int,
    quality_rating: str,
) -> dict[str, Any]:
    """
    Format report as JSON-serializable dictionary.

    Args:
        validator_reports: List of ValidatorReport objects
        timestamp: When the health check was executed
        build_stats: Optional build statistics dict
        total_checks: Total checks run
        total_passed: Total passed checks
        total_info: Total info messages
        total_warnings: Total warnings
        total_errors: Total errors
        quality_score: Quality score (0-100)
        quality_rating: Quality rating string

    Returns:
        Dictionary suitable for json.dumps()
    """
    return {
        "timestamp": timestamp.isoformat(),
        "summary": {
            "total_checks": total_checks,
            "passed": total_passed,
            "info": total_info,
            "warnings": total_warnings,
            "errors": total_errors,
            "quality_score": quality_score,
            "quality_rating": quality_rating,
        },
        "validators": [
            {
                "name": vr.validator_name,
                "duration_ms": vr.duration_ms,
                "summary": {
                    "passed": vr.passed_count,
                    "info": vr.info_count,
                    "warnings": vr.warning_count,
                    "errors": vr.error_count,
                },
                "results": [
                    {
                        "status": r.status.value,
                        "code": r.code,
                        "message": r.message,
                        "recommendation": r.recommendation,
                        "details": r.details,
                        "metadata": r.metadata,
                    }
                    for r in vr.results
                ],
            }
            for vr in validator_reports
        ],
        "build_stats": build_stats,
    }
