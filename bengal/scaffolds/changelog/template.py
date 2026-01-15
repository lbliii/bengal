"""Changelog template definition."""

from __future__ import annotations

from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_file(filename: str, subdir: str = "pages") -> str:
    """Load a file from the template directory."""
    template_dir = Path(__file__).parent
    file_path = template_dir / subdir / filename

    with open(file_path) as f:
        return f.read()


def _create_changelog_template() -> SiteTemplate:
    """Create the changelog site template."""

    files = [
        TemplateFile(
            relative_path="_index.md",
            content=_load_file("_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="changelog.yaml",
            content=_load_file("changelog.yaml", subdir="data"),
            target_dir="data",
        ),
    ]

    return SiteTemplate(
        id="changelog",
        name="Changelog",
        description="Release notes and version history with timeline design",
        files=files,
        additional_dirs=["data"],
    )


# Export the template
TEMPLATE = _create_changelog_template()
