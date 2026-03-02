"""Shortcode-related CLI commands."""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import get_cli_output, handle_cli_errors, load_site_from_cli


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
    """Shortcode utilities (list available shortcodes)."""


@shortcodes_cli.command("list")
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
def list_shortcodes(source: str) -> None:
    """
    List available shortcodes from theme and project.

    Shows shortcodes from:
    - Project: templates/shortcodes/ (overrides theme)
    - Theme: theme's templates/shortcodes/
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
    for name in sorted(all_names):
        src = "project" if name in project_names else "theme"
        cli.info(f"  {name} ({src})")
    if not all_names:
        cli.info("  (no shortcodes found)")
