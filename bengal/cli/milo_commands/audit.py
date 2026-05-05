"""Audit command — verify generated artifacts after build."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def _audit_display_context(
    report, *, focus: str = "", style: str = "dense", limit: int = 10
) -> dict:
    """Build template context for human audit output without changing the JSON envelope."""
    from bengal.cli.milo_commands._reports import bar, palette

    glyphs = palette(style)
    findings = []
    for index, finding in enumerate(report.findings, 1):
        display_code = f"{finding.code}-{index:03d}"
        findings.append(
            {
                **finding.to_dict(),
                "display_code": display_code,
                "glyph": glyphs["error"],
                "location": finding.artifact,
            }
        )

    total_findings = len(findings)
    total_checked = max(report.summary.references_checked, total_findings, 1)
    visible = findings if limit <= 0 else findings[:limit]
    hidden_count = 0 if limit <= 0 else max(0, total_findings - len(visible))
    focused = None
    focus_value = focus.strip().lower()
    if focus_value:
        focused = next(
            (
                item
                for item in findings
                if item["display_code"].lower() == focus_value
                or item["code"].lower() == focus_value
            ),
            None,
        )

    passed = report.passed
    verdict = "Artifact audit passed" if passed else "Publish blocked"
    detail = (
        f"{report.summary.files_checked} file(s), {report.summary.references_checked} reference(s)"
        if passed
        else f"{total_findings} broken reference(s)"
    )
    steps = (
        ["Build output is ready for artifact publication."]
        if passed
        else [
            "Run `bengal build` to regenerate generated artifacts.",
            "Fix the source content or template that emitted the broken reference.",
            "Re-run `bengal audit` before publishing.",
        ]
    )
    return {
        "title": "Artifact Audit",
        "ascii": style in {"ascii", "ci"},
        "verdict": verdict,
        "detail": detail,
        "output_dir": str(report.output_dir),
        "findings": visible,
        "focused_finding": focused,
        "focus": focus,
        "hidden_count": hidden_count,
        "next_focus": findings[len(visible)]["display_code"] if hidden_count else "",
        "meters": [
            {
                "glyph": glyphs["error"] if total_findings else glyphs["ok"],
                "label": "broken refs",
                "padding": " " * 3,
                "bar": bar(
                    total_findings,
                    total_checked,
                    fill=glyphs["fill"],
                    empty=glyphs["empty"],
                ),
                "value": total_findings,
            },
            {
                "glyph": glyphs["ok"],
                "label": "checked refs",
                "padding": " " * 2,
                "bar": bar(
                    report.summary.references_checked,
                    total_checked,
                    fill=glyphs["fill"],
                    empty=glyphs["empty"],
                ),
                "value": report.summary.references_checked,
            },
        ],
        "steps": steps,
    }


def audit(
    source: Annotated[str, Description("Source directory path")] = "",
    output: Annotated[str, Description("Output directory to audit")] = "",
    json: Annotated[bool, Description("Emit machine-readable JSON")] = False,
    focus: Annotated[str, Description("Show one finding by code, e.g. A101-001")] = "",
    style: Annotated[str, Description("Output style: dense, ascii, or ci")] = "dense",
    limit: Annotated[int, Description("Maximum findings to show in human output (0 = all)")] = 10,
) -> dict:
    """Audit generated output for missing internal artifact references."""
    import json as json_module
    from pathlib import Path

    from bengal.audit import audit_output_dir
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()
    if not json:
        if style not in {"dense", "ascii", "ci"}:
            cli.error(f"--style must be one of dense, ascii, or ci (got: {style!r})")
            cli.tip("Use --style ci for stable ASCII-safe output in automation logs.")
            raise SystemExit(2)
        if limit < 0:
            cli.error("--limit must be zero or greater")
            cli.tip("Use --limit 0 to show all findings.")
            raise SystemExit(2)

    with cli.output_mode("dense" if json else style):
        site = load_site_from_cli(
            source=source, config=None, environment=None, profile=None, cli=cli
        )
        output_dir = Path(output).resolve() if output else site.output_dir

        report = audit_output_dir(output_dir, baseurl=site.baseurl or "")
        envelope = report.to_envelope()

        if json:
            cli.render_write("json_output.kida", data=json_module.dumps(envelope, indent=2))
        else:
            context = _audit_display_context(report, focus=focus, style=style, limit=limit)
            if focus:
                focused = context["focused_finding"]
                if focused is None:
                    cli.error(f"Audit finding not found: {focus}")
                    cli.tip("Use a finding code from `bengal audit`, such as A101-001.")
                    raise SystemExit(2)
                cli.render_write(
                    "artifact_audit_focus.kida",
                    **{**context, "finding": focused},
                )
            else:
                cli.render_write("artifact_audit.kida", **context)

        if not report.passed:
            raise SystemExit(1)
        return envelope
