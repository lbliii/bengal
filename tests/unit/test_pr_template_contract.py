"""Guards for PR evidence template requirements."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / ".github" / "pull_request_template.md"

REQUIRED_PERFORMANCE_FIELDS = [
    "Benchmark matrix row",
    "Command",
    "Python build",
    "Machine/OS",
    "Baseline commit or saved result",
    "Current commit or saved result",
    "Artifact path",
    "Interpretation",
]


def test_pr_template_requires_performance_evidence_receipts() -> None:
    content = TEMPLATE.read_text(encoding="utf-8")

    assert "## Performance Evidence" in content
    for field in REQUIRED_PERFORMANCE_FIELDS:
        assert f"- {field}:" in content


def test_pr_template_mentions_not_applicable_escape_hatch() -> None:
    content = TEMPLATE.read_text(encoding="utf-8")

    assert "not applicable" in content
    assert "performance-sensitive behavior" in content
