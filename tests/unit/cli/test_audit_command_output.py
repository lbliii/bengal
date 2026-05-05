"""Tests for verdict-first artifact audit CLI output."""

from __future__ import annotations

import pytest


class _FakeSite:
    def __init__(self, output_dir) -> None:
        self.output_dir = output_dir
        self.baseurl = ""


def test_audit_renders_verdict_first_report(monkeypatch, tmp_path, capsys):
    """Broken generated references should render as bounded issue cards."""
    from bengal.cli.milo_commands.audit import audit

    output = tmp_path / "public"
    output.mkdir()
    (output / "index.html").write_text('<a href="/missing/">Missing</a>', encoding="utf-8")
    monkeypatch.setattr("bengal.cli.utils.load_site_from_cli", lambda **_: _FakeSite(output))

    with pytest.raises(SystemExit) as exc:
        audit(source=str(tmp_path), output=str(output), limit=1)

    assert exc.value.code == 1
    text = capsys.readouterr().out
    assert text.startswith("ᓚᘏᗢ Artifact Audit")
    assert "Publish blocked - 1 broken reference(s)" in text
    assert "A101-001 index.html" in text
    assert "target  /missing/" in text
    assert "Next steps" in text


def test_audit_focus_renders_single_finding(monkeypatch, tmp_path, capsys):
    """Focus mode should drill into one stable display code."""
    from bengal.cli.milo_commands.audit import audit

    output = tmp_path / "public"
    output.mkdir()
    (output / "index.html").write_text(
        '<a href="/missing-one/">One</a><a href="/missing-two/">Two</a>',
        encoding="utf-8",
    )
    monkeypatch.setattr("bengal.cli.utils.load_site_from_cli", lambda **_: _FakeSite(output))

    with pytest.raises(SystemExit) as exc:
        audit(source=str(tmp_path), output=str(output), focus="A101-002")

    assert exc.value.code == 1
    text = capsys.readouterr().out
    assert "A101-002 index.html" in text
    assert "/missing-two/" in text
    assert "A101-001" not in text


def test_audit_ci_style_uses_ascii_glyphs(monkeypatch, tmp_path, capsys):
    """CI style should avoid Unicode status glyphs in dynamic audit rows."""
    from bengal.cli.milo_commands.audit import audit

    output = tmp_path / "public"
    output.mkdir()
    (output / "index.html").write_text('<a href="/missing/">Missing</a>', encoding="utf-8")
    monkeypatch.setattr("bengal.cli.utils.load_site_from_cli", lambda **_: _FakeSite(output))

    with pytest.raises(SystemExit):
        audit(source=str(tmp_path), output=str(output), style="ci", limit=1)

    text = capsys.readouterr().out
    assert text.startswith("Bengal Artifact Audit")
    assert "x broken refs" in text
    assert "v checked refs" in text
    assert "-- x A101-001" in text
    assert "ᓚᘏᗢ" not in text
    assert "╭" not in text


def test_audit_ci_style_does_not_leak_to_later_invocations(monkeypatch, tmp_path, capsys):
    """Direct in-process command calls should restore the previous output mode."""
    from bengal.cli.milo_app import cli as milo_cli
    from bengal.cli.milo_commands.audit import audit

    output = tmp_path / "public"
    output.mkdir()
    (output / "index.html").write_text('<a href="/missing/">Missing</a>', encoding="utf-8")
    monkeypatch.setattr("bengal.cli.utils.load_site_from_cli", lambda **_: _FakeSite(output))

    with pytest.raises(SystemExit):
        audit(source=str(tmp_path), output=str(output), style="ci", limit=1)
    capsys.readouterr()

    result = milo_cli.invoke(["content", "sources", "--source", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output.startswith("ᓚᘏᗢ Content Sources")


def test_output_mode_context_restores_after_exception(capsys, monkeypatch):
    """CI-safe output should be scoped even when the command exits early."""
    from bengal.output import get_cli_output, reset_cli_output

    monkeypatch.delenv("BENGAL_CLI_ASCII", raising=False)
    monkeypatch.delenv("BENGAL_CLI_NO_COLOR", raising=False)
    reset_cli_output()
    cli = get_cli_output()

    def fail_inside_ci_mode() -> None:
        with cli.output_mode("ci"):
            cli.success("Done")
            raise RuntimeError("stop")

    with pytest.raises(RuntimeError):
        fail_inside_ci_mode()

    cli.success("Done again")

    text = capsys.readouterr().out
    assert "\x1b[" not in text
    assert "v Done" in text
    assert "✓ Done again" in text
    reset_cli_output()


def test_milo_registry_exposes_mcp_annotations():
    """Commands should advertise read/write intent to MCP clients."""
    from bengal.cli.milo_app import cli

    assert cli._commands["audit"].annotations["readOnlyHint"] is True
    assert cli._commands["clean"].annotations["destructiveHint"] is True
    assert cli._commands["fix"].annotations["destructiveHint"] is True
    assert cli._groups["cache"].commands["inputs"].annotations["readOnlyHint"] is True
    assert cli._groups["config"].commands["init"].annotations["destructiveHint"] is True


class _FakeHealthReport:
    def format_envelope(self, command: str = "check") -> dict:
        return {
            "command": command,
            "summary": {
                "total_checks": 3,
                "passed": 1,
                "info": 0,
                "suggestions": 1,
                "warnings": 1,
                "errors": 1,
            },
            "findings": [
                {
                    "severity": "error",
                    "code": "H101",
                    "message": "Missing title",
                    "validator": "frontmatter",
                    "recommendation": "Add title frontmatter.",
                    "details": ["content/index.md", "title"],
                    "metadata": None,
                },
                {
                    "severity": "warning",
                    "code": "H202",
                    "message": "Long description",
                    "validator": "seo",
                    "recommendation": "Shorten the description.",
                    "details": ["content/about.md", "description"],
                    "metadata": None,
                },
                {
                    "severity": "suggestion",
                    "code": "H303",
                    "message": "Add summary",
                    "validator": "quality",
                    "recommendation": "Add a summary.",
                    "details": ["content/about.md", "summary"],
                    "metadata": None,
                },
            ],
        }


def test_check_report_context_supports_focus_and_ci_style():
    """Health check output should share the audit report primitives."""
    from bengal.cli.milo_commands.check import _check_display_context

    context = _check_display_context(
        _FakeHealthReport(),
        focus="H202-002",
        style="ci",
        suggestions=True,
    )

    assert context["verdict"] == "Validation failed"
    assert context["ascii"] is True
    assert context["focused_finding"]["display_code"] == "H202-002"
    assert context["focused_finding"]["glyph"] == "!"
    assert context["meters"][0]["glyph"] == "x"
    assert context["meters"][2]["glyph"] == "^"


def test_check_display_codes_are_stable_when_suggestions_hidden():
    """Focus codes should not change when optional severities are filtered."""
    from bengal.cli.milo_commands.check import _check_display_context

    class ReportWithSuggestionBeforeWarning:
        def format_envelope(self, command: str = "check") -> dict:
            envelope = _FakeHealthReport().format_envelope(command)
            envelope["findings"][1], envelope["findings"][2] = (
                envelope["findings"][2],
                envelope["findings"][1],
            )
            return envelope

    context = _check_display_context(ReportWithSuggestionBeforeWarning(), suggestions=False)

    warning = next(finding for finding in context["findings"] if finding["code"] == "H202")
    assert warning["display_code"] == "H202-003"
