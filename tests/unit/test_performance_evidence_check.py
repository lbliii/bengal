"""Tests for PR performance evidence validation."""

from __future__ import annotations

import json

import scripts.check_performance_evidence as performance_evidence
from scripts.check_performance_evidence import (
    REQUIRED_FIELDS,
    body_from_github_event,
    changed_files_from_file,
    changed_files_from_github_event,
    has_performance_sensitive_changes,
    is_performance_sensitive_file,
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


def test_performance_evidence_accepts_prose_not_applicable() -> None:
    body = (
        "## Performance Evidence\n\n"
        "not applicable — CLI-only change with no hot-path performance claim.\n"
    )

    assert missing_evidence_fields(body) == ()


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


def test_performance_evidence_skips_docs_only_changes() -> None:
    assert (
        missing_evidence_fields(
            "## Summary\n\n- docs only",
            changed_files=("plan/README.md", "site/content/index.md", "CHANGELOG.md"),
        )
        == ()
    )


def test_performance_evidence_skips_non_hot_code_changes() -> None:
    assert (
        missing_evidence_fields(
            "## Summary\n\n- test helper changed",
            changed_files=("tests/unit/test_performance_evidence_check.py",),
        )
        == ()
    )


def test_performance_evidence_requires_section_for_hot_path_changes() -> None:
    assert missing_evidence_fields(
        "## Summary\n\n- cache changed",
        changed_files=("bengal/cache/parsed_output.py",),
    ) == ("Performance Evidence",)


def test_performance_evidence_treats_unknown_change_set_as_sensitive() -> None:
    assert has_performance_sensitive_changes(()) is True


def test_performance_evidence_treats_force_run_as_sensitive() -> None:
    assert is_performance_sensitive_file("FORCE_RUN") is True
    assert has_performance_sensitive_changes(("FORCE_RUN",)) is True


def test_performance_evidence_marks_benchmarks_sensitive() -> None:
    assert is_performance_sensitive_file("benchmarks/render.py") is True
    assert is_performance_sensitive_file("tests/performance/test_build.py") is True


def test_changed_files_from_file(tmp_path) -> None:
    changed_path = tmp_path / "changed-files.txt"
    changed_path.write_text("plan/README.md\n\nscripts/check_performance_evidence.py\n")

    assert changed_files_from_file(changed_path) == (
        "plan/README.md",
        "scripts/check_performance_evidence.py",
    )


def test_changed_files_from_github_event_fetches_paginated_files(tmp_path, monkeypatch) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": {"url": "https://api.github.test/repos/o/r/pulls/1"}}),
        encoding="utf-8",
    )

    def fake_github_api_json(url: str) -> object:
        if url.endswith("page=1"):
            return [{"filename": f"plan/file-{index}.md"} for index in range(100)]
        return [{"filename": "bengal/cache/parsed_output.py"}]

    monkeypatch.setattr(performance_evidence, "_github_api_json", fake_github_api_json)

    assert changed_files_from_github_event(event_path) == (
        *(f"plan/file-{index}.md" for index in range(100)),
        "bengal/cache/parsed_output.py",
    )
