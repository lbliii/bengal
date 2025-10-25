"""Resume site template.

Provides a resume/CV scaffold with a data file and a homepage configured to
use the resume layout.
"""

from __future__ import annotations

from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_file(filename: str, subdir: str = "pages") -> str:
    """Load a file from this template's directory.

    Args:
        filename: File name within the subdirectory.
        subdir: Subdirectory under this template (``pages`` or ``data``).

    Returns:
        The file contents as a string.
    """
    template_dir = Path(__file__).parent
    file_path = template_dir / subdir / filename

    with open(file_path) as f:
        return f.read()


def _create_resume_template() -> SiteTemplate:
    """Construct the resume template definition.

    Returns:
        A :class:`SiteTemplate` for a data‑driven resume/CV site.
    """

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
