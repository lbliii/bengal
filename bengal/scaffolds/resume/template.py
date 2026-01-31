"""Resume site template.

Provides a resume/CV scaffold with a data file and a homepage configured to
use the resume layout.
"""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_resume_template() -> SiteTemplate:
    """Construct the resume template definition.

    Returns:
        A :class:`SiteTemplate` for a data‑driven resume/CV site.

    """
    files = [
        TemplateFile(
            relative_path="_index.md",
            content=load_template_file(__file__, "_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="resume.yaml",
            content=load_template_file(__file__, "resume.yaml", subdir="data"),
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
