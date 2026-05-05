"""Helpers for shaping health check result streams."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.health.report import CheckResult, CheckStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

COMPACTED_SUCCESS_COUNT_KEY = "_bengal_compacted_success_count"


def compact_successes(
    results: Sequence[CheckResult],
    message: str,
    *,
    metadata_key: str = "checks",
    min_count: int = 2,
) -> list[CheckResult]:
    """Collapse repeated success rows into one aggregate success result."""
    successes = [result for result in results if result.status == CheckStatus.SUCCESS]
    if len(successes) < min_count:
        return list(results)

    compacted = [result for result in results if result.status != CheckStatus.SUCCESS]
    compacted.append(
        CheckResult(
            CheckStatus.SUCCESS,
            message,
            details=[result.message for result in successes],
            metadata={
                COMPACTED_SUCCESS_COUNT_KEY: len(successes),
                metadata_key: [
                    {
                        "message": result.message,
                        "code": result.code,
                        "details": result.details or [],
                        "metadata": result.metadata or {},
                    }
                    for result in successes
                ],
            },
        )
    )
    return compacted
