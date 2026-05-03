"""Audit command — verify generated artifacts after build."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def audit(
    source: Annotated[str, Description("Source directory path")] = "",
    output: Annotated[str, Description("Output directory to audit")] = "",
    json: Annotated[bool, Description("Emit machine-readable JSON")] = False,
) -> dict:
    """Audit generated output for missing internal artifact references."""
    import json as json_module
    from pathlib import Path

    from bengal.audit import audit_output_dir
    from bengal.cli.utils import get_cli_output, load_site_from_cli

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    output_dir = Path(output).resolve() if output else site.output_dir

    report = audit_output_dir(output_dir, baseurl=site.baseurl or "")
    envelope = report.to_envelope()

    if json:
        cli.render_write("json_output.kida", data=json_module.dumps(envelope, indent=2))
    else:
        cli.render_write("validation_report.kida", **report.format_validation_report())

    if not report.passed:
        cli.error(f"Artifact audit failed: {report.summary.broken_references} broken reference(s)")
        cli.tip("Run `bengal build` again, then audit the generated output directory.")
        raise SystemExit(1)

    cli.success("Artifact audit passed")
    return envelope

