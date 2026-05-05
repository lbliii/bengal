"""Tests for health result compaction helpers."""

from __future__ import annotations

from bengal.health.report import CheckResult, CheckStatus, ValidatorReport
from bengal.health.results import compact_successes


def test_compact_successes_preserves_problem_results() -> None:
    results = [
        CheckResult.success("First check passed"),
        CheckResult.warning("Problem", code="H999", details=["content/page.md"]),
        CheckResult.success("Second check passed"),
    ]

    compacted = compact_successes(results, "2 checks passed", metadata_key="checks")

    assert [result.status for result in compacted] == [CheckStatus.WARNING, CheckStatus.SUCCESS]
    assert compacted[0].message == "Problem"
    assert compacted[0].details == ["content/page.md"]
    assert compacted[1].message == "2 checks passed"
    assert compacted[1].details == ["First check passed", "Second check passed"]
    assert compacted[1].metadata == {
        "_bengal_compacted_success_count": 2,
        "checks": [
            {
                "message": "First check passed",
                "code": None,
                "details": [],
                "metadata": {},
            },
            {
                "message": "Second check passed",
                "code": None,
                "details": [],
                "metadata": {},
            },
        ],
    }


def test_compact_successes_leaves_single_success_alone() -> None:
    result = CheckResult.success("Only check passed")

    assert compact_successes([result], "1 check passed") == [result]


def test_compacted_successes_preserve_validator_counts() -> None:
    results = compact_successes(
        [
            CheckResult.success("First check passed"),
            CheckResult.success("Second check passed"),
            CheckResult.success("Third check passed"),
        ],
        "3 checks passed",
    )

    report = ValidatorReport("Example", results)

    assert len(report.results) == 1
    assert report.passed_count == 3
