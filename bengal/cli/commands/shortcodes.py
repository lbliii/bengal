"""Shortcode and directive CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)


def _shortcode_names_from_dir(d: Path) -> set[str]:
    """Extract shortcode names from a templates/shortcodes directory."""
    names: set[str] = set()
    if not d.exists():
        return names
    for f in d.rglob("*.html"):
        try:
            rel = f.relative_to(d)
        except ValueError:
            continue
        name = str(rel.with_suffix("")).replace("\\", "/")
        if name and not name.startswith("_"):
            names.add(name)
    return names


@click.group(cls=BengalGroup)
def shortcodes_cli() -> None:
    """
    Shortcode and directive utilities.

    Commands:
        list        List available template shortcodes
        directives  List available MyST directives
        test        Render a directive in isolation
    """


@shortcodes_cli.command("list")
@command_metadata(
    category="content",
    description="List available template shortcodes",
    examples=[
        "bengal shortcodes list",
        "bengal shortcodes list --format json",
    ],
    requires_site=True,
    tags=["shortcodes", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def list_shortcodes(output_format: str, source: str) -> None:
    """
    List available template shortcodes from theme and project.

    Shows shortcodes from:
    - Project: templates/shortcodes/ (overrides theme)
    - Theme: theme's templates/shortcodes/

    Examples:
        bengal shortcodes list
        bengal shortcodes list --format json
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    root = Path(source)
    project_dir = root / "templates" / "shortcodes"
    project_names = _shortcode_names_from_dir(project_dir)
    theme_names: set[str] = set()
    theme = getattr(site, "theme", None)
    if theme:
        theme_templates = getattr(theme, "templates_path", None) or getattr(theme, "path", None)
        if theme_templates:
            theme_sc = Path(theme_templates) / "shortcodes"
            theme_names = _shortcode_names_from_dir(theme_sc)
    all_names = project_names | theme_names

    if output_format == "json":
        entries = []
        for name in sorted(all_names):
            src = "project" if name in project_names else "theme"
            override = name in project_names and name in theme_names
            entries.append({"name": name, "source": src, "overrides_theme": override})
        cli.console.print(json.dumps(entries, indent=2))
        return

    if not all_names:
        cli.info("  (no shortcodes found)")
        cli.tip("Create templates in templates/shortcodes/ to add shortcodes.")
        return

    cli.info(f"Template shortcodes ({len(all_names)}):")
    cli.blank()
    for name in sorted(all_names):
        src = "project" if name in project_names else "theme"
        override = " (overrides theme)" if name in project_names and name in theme_names else ""
        cli.info(f"  {name} [{src}]{override}")


@shortcodes_cli.command("directives")
@command_metadata(
    category="content",
    description="List available MyST directives",
    examples=[
        "bengal shortcodes directives",
        "bengal shortcodes directives --format json",
    ],
    requires_site=False,
    tags=["directives", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def list_directives(output_format: str) -> None:
    """
    List available MyST directives.

    Shows all built-in directives with their aliases and descriptions.

    Examples:
        bengal shortcodes directives
        bengal shortcodes directives --format json
    """
    from bengal.debug import ShortcodeSandbox

    cli = get_cli_output()
    sandbox = ShortcodeSandbox()
    directives = sandbox.list_directives()

    if output_format == "json":
        cli.console.print(json.dumps(directives, indent=2))
        return

    cli.info(f"Available directives ({len(directives)} types):")
    cli.blank()
    for d in directives:
        names = ", ".join(d["names"])
        desc = d["description"].split("\n")[0].strip() if d["description"] else ""
        if desc:
            cli.info(f"  {names} — {desc}")
        else:
            cli.info(f"  {names}")


@shortcodes_cli.command("test")
@command_metadata(
    category="content",
    description="Render a directive in isolation",
    examples=[
        "bengal shortcodes test '```{note}\nTest note.\n```'",
        "bengal shortcodes test --file test.md",
        "bengal shortcodes test --validate-only '```{tip}\nHello\n```'",
    ],
    requires_site=False,
    tags=["directives", "debug", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("content", required=False)
@click.option(
    "--file", "-f", "file_path", type=click.Path(exists=True), help="Read content from file"
)
@click.option("--validate-only", is_flag=True, help="Only validate syntax, don't render")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "html", "json"]),
    default="console",
    help="Output format",
)
def test_directive(
    content: str | None,
    file_path: str | None,
    validate_only: bool,
    output_format: str,
) -> None:
    """
    Render a directive in isolation for testing.

    Test directive syntax and rendering without a full site build.
    Useful for iterating on directive content.

    Examples:
        bengal shortcodes test '```{note}\\nThis is a note.\\n```'
        bengal shortcodes test --file test-directive.md
        bengal shortcodes test --validate-only '```{warning}\\nCaution!\\n```'
    """
    from bengal.debug import ShortcodeSandbox

    cli = get_cli_output()
    sandbox = ShortcodeSandbox()

    # Load content
    if file_path:
        content = Path(file_path).read_text(encoding="utf-8")
    elif content:
        content = content.replace("\\n", "\n")
    else:
        cli.warning("No content provided.")
        cli.info("Usage: bengal shortcodes test '<content>' or --file <path>")
        return

    if validate_only:
        validation = sandbox.validate(content)
        if output_format == "json":
            cli.console.print(
                json.dumps(
                    {
                        "valid": validation.valid,
                        "directive": validation.directive_name,
                        "errors": validation.errors,
                        "suggestions": validation.suggestions,
                    },
                    indent=2,
                )
            )
            return

        if validation.valid:
            cli.success(f"Valid syntax: {validation.directive_name or 'no directive'}")
        else:
            cli.error("Invalid syntax:")
            for err in validation.errors:
                cli.info(f"  {err}")
            for sug in validation.suggestions:
                cli.tip(sug)
        return

    result = sandbox.render(content)

    if output_format == "json":
        cli.console.print(
            json.dumps(
                {
                    "success": result.success,
                    "directive": result.directive_name,
                    "html": result.html,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "parse_time_ms": result.parse_time_ms,
                    "render_time_ms": result.render_time_ms,
                },
                indent=2,
            )
        )
        return

    if output_format == "html":
        cli.console.print(result.html)
        return

    # Console format
    if result.success:
        cli.success(f"Rendered: {result.directive_name}")
        cli.info(f"  Parse: {result.parse_time_ms:.2f}ms | Render: {result.render_time_ms:.2f}ms")
        cli.blank()
        cli.console.print(result.html)
    else:
        cli.error("Render failed:")
        for err in result.errors:
            cli.info(f"  {err}")
