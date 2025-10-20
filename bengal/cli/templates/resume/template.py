"""Resume template definition."""


from __future__ import annotations

from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_file(filename: str, subdir: str = "pages") -> str:
    """Load a file from the template directory."""
    template_dir = Path(__file__).parent
    file_path = template_dir / subdir / filename

    with open(file_path) as f:
        return f.read()


def _create_resume_template() -> SiteTemplate:
    """Create the resume site template."""

    files = [
        TemplateFile(
            relative_path="_index.md",
            content=_load_file("_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="resume.yaml",
            content=_load_file("resume.yaml", subdir="data"),
            target_dir="data",
        ),
    ]

    return SiteTemplate(
        id="resume",
        name="Resume",
        description="Professional resume/CV site with structured data",
        files=files,
        additional_dirs=["data"],
    )


# Export the template
TEMPLATE = _create_resume_template()
