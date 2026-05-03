"""Tests for structured linkcheck reporting."""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.health.linkcheck.models import (
    LinkCheckResult,
    LinkCheckSummary,
    LinkKind,
    LinkStatus,
)
from bengal.health.linkcheck.orchestrator import LinkCheckOrchestrator


def test_format_validation_report_for_broken_links():
    """Linkcheck exposes Kida-ready report context without console formatting."""
    orchestrator = LinkCheckOrchestrator(MagicMock(), check_internal=False, check_external=False)
    results = [
        LinkCheckResult(
            url="/missing/",
            kind=LinkKind.INTERNAL,
            status=LinkStatus.BROKEN,
            first_ref="index.html",
            reason="Page not found",
        )
    ]
    summary = LinkCheckSummary(total_checked=1, broken_count=1, duration_ms=12.34)

    context = orchestrator.format_validation_report(results, summary)

    assert context["title"] == "Link Check"
    assert context["summary"] == {"errors": 1, "warnings": 0, "passed": 0}
    assert any(issue["level"] == "error" for issue in context["issues"])
    assert any(issue["message"] == "/missing/" for issue in context["issues"])
    assert any("Referenced in: index.html" in issue["detail"] for issue in context["issues"])


def test_format_validation_report_for_passing_links():
    """Passing linkcheck reports one success issue with aggregate counts."""
    orchestrator = LinkCheckOrchestrator(MagicMock(), check_internal=False, check_external=False)
    summary = LinkCheckSummary(total_checked=2, ok_count=2, duration_ms=5.0)

    context = orchestrator.format_validation_report([], summary)

    assert context["summary"] == {"errors": 0, "warnings": 0, "passed": 1}
    assert context["issues"] == [
        {
            "level": "success",
            "message": "All 2 checked link(s) are valid",
            "detail": "2 ok, 0 broken, 0 errors, 0 ignored, 5.00ms",
        }
    ]
