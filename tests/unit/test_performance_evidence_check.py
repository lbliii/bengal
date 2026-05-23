"""Tests for PR performance evidence validation."""

from __future__ import annotations

import json

from scripts.check_performance_evidence import (
    REQUIRED_FIELDS,
    body_from_github_event,
    missing_evidence_fields,
)


def _body(field_values: dict[str, str]) -> str:
    lines = ["## Summary", "", "-", "", "## Performance Evidence", ""]
    lines.extend(f"- {field}: {field_values.get(field, '')}" for field in REQUIRED_FIELDS)
    lines.extend(["", "## Steward Notes", "", "-"])
    return "\n".join(lines)


def test_performance_evidence_accepts_complete_receipts() -> None:
    values = {field: f"value for {field}" for field in REQUIRED_FIELDS}

    assert missing_evidence_fields(_body(values)) == ()


def test_performance_evidence_accepts_explicit_not_applicable() -> None:
    assert missing_evidence_fields(_body({"Benchmark matrix row": "not applicable"})) == ()


def test_performance_evidence_rejects_blank_template_values() -> None:
    assert missing_evidence_fields(_body({})) == REQUIRED_FIELDS


def test_performance_evidence_template_mode_requires_field_labels() -> None:
    assert missing_evidence_fields(_body({}), allow_template=True) == ()
    assert missing_evidence_fields("## Performance Evidence\n", allow_template=True) == (
        "Performance Evidence",
    )


def test_performance_evidence_reads_github_event(tmp_path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": {"body": _body({"Command": "not applicable"})}}),
        encoding="utf-8",
    )

    assert missing_evidence_fields(body_from_github_event(event_path)) == ()
