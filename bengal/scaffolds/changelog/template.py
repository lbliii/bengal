"""Changelog template definition."""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_changelog_template() -> SiteTemplate:
    """Create the changelog site template."""
    files = [
        TemplateFile(
            relative_path="_index.md",
            content=load_template_file(__file__, "_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="changelog.yaml",
            content=load_template_file(__file__, "changelog.yaml", subdir="data"),
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
