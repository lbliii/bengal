"""Tests for generated artifact audits."""

from __future__ import annotations

from bengal.audit import audit_output_dir


def test_audit_passes_for_existing_internal_references(tmp_path):
    output = tmp_path / "public"
    (output / "docs").mkdir(parents=True)
    (output / "assets").mkdir()
    (output / "index.html").write_text(
        '<a href="/docs/">Docs</a><img src="/assets/logo.png">',
        encoding="utf-8",
    )
    (output / "docs" / "index.html").write_text("docs", encoding="utf-8")
    (output / "assets" / "logo.png").write_text("png", encoding="utf-8")

    report = audit_output_dir(output)

    assert report.passed is True
    assert report.summary.files_checked == 2
    assert report.summary.references_checked == 2
    assert report.findings == ()


def test_audit_reports_missing_internal_reference(tmp_path):
    output = tmp_path / "public"
    output.mkdir()
    (output / "index.html").write_text('<a href="/missing/">Missing</a>', encoding="utf-8")

    report = audit_output_dir(output)

    assert report.passed is False
    assert report.summary.broken_references == 1
    assert report.findings[0].artifact == "index.html"
    assert report.findings[0].reference == "/missing/"


def test_audit_resolves_relative_references_from_html_file(tmp_path):
    output = tmp_path / "public"
    (output / "docs").mkdir(parents=True)
    (output / "docs" / "index.html").write_text('<a href="./guide/">Guide</a>', encoding="utf-8")
    (output / "docs" / "guide").mkdir()
    (output / "docs" / "guide" / "index.html").write_text("guide", encoding="utf-8")

    report = audit_output_dir(output)

    assert report.passed is True


def test_audit_strips_baseurl_path(tmp_path):
    output = tmp_path / "public"
    (output / "docs").mkdir(parents=True)
    (output / "index.html").write_text('<a href="/repo/docs/">Docs</a>', encoding="utf-8")
    (output / "docs" / "index.html").write_text("docs", encoding="utf-8")

    report = audit_output_dir(output, baseurl="/repo")

    assert report.passed is True


def test_audit_envelope_uses_audit_schema(tmp_path):
    output = tmp_path / "public"
    output.mkdir()
    (output / "index.html").write_text('<a href="/missing/">Missing</a>', encoding="utf-8")

    envelope = audit_output_dir(output).to_envelope()

    assert envelope["schema_version"] == "bengal.audit.v1"
    assert envelope["status"] == "failed"
    assert envelope["summary"]["errors"] == 1
    assert envelope["findings"][0]["code"] == "A101"
