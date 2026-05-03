"""Tests for versioned health report envelopes."""

from __future__ import annotations

from bengal.health.report import CheckResult, HealthReport, ReportPolicy, ValidatorReport


def test_health_report_envelope_adapts_existing_results():
    report = HealthReport()
    report.validator_reports.append(
        ValidatorReport(
            validator_name="Links",
            results=[
                CheckResult.success("OK"),
                CheckResult.warning(
                    "One link is soft-broken",
                    code="H101",
                    recommendation="Fix the internal link.",
                    details=["content/index.md: ./missing"],
                ),
            ],
        )
    )

    envelope = report.format_envelope()

    assert envelope["schema_version"] == "bengal.check.v1"
    assert envelope["command"] == "check"
    assert envelope["status"] == "passed_with_warnings"
    assert envelope["policy"] == {
        "errors_fail": True,
        "warnings_fail": False,
        "suggestions_fail": False,
    }
    assert envelope["summary"]["warnings"] == 1
    assert envelope["summary"]["passed"] == 1
    assert envelope["findings"] == [
        {
            "severity": "warning",
            "code": "H101",
            "message": "One link is soft-broken",
            "validator": "Links",
            "recommendation": "Fix the internal link.",
            "details": ["content/index.md: ./missing"],
            "metadata": None,
        }
    ]


def test_report_policy_can_fail_on_warnings():
    policy = ReportPolicy(warnings_fail=True)

    assert policy.status_for(errors=0, warnings=1, suggestions=0) == "failed"


def test_validation_report_context_includes_envelope_fields():
    report = HealthReport()
    report.validator_reports.append(
        ValidatorReport(
            validator_name="Config",
            results=[CheckResult.error("Missing title", code="H001")],
        )
    )

    context = report.format_validation_report()

    assert context["schema_version"] == "bengal.check.v1"
    assert context["status"] == "failed"
    assert context["summary"]["errors"] == 1
    assert context["findings"][0]["validator"] == "Config"
