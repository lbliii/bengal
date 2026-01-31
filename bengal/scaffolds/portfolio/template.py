"""Portfolio site template.

Creates a simple portfolio with home, about, projects, and contact pages. Uses
light token substitution to inject the current date into example project pages.
"""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_portfolio_template() -> SiteTemplate:
    """Construct the portfolio template definition.

    Returns:
        A :class:`SiteTemplate` for a personal portfolio site.

    """
    files = [
        TemplateFile(
            relative_path="index.md",
            content=load_template_file(__file__, "index.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="about.md",
            content=load_template_file(__file__, "about.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="projects/index.md",
            content=load_template_file(__file__, "projects/index.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="projects/project-1.md",
            content=load_template_file(__file__, "projects/project-1.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="projects/project-2.md",
            content=load_template_file(__file__, "projects/project-2.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="contact.md",
            content=load_template_file(__file__, "contact.md", replace_date=True),
            target_dir="content",
        ),
    ]

    return SiteTemplate(
        id="portfolio",
        name="Portfolio",
        description="Portfolio site with projects showcase",
        files=files,
        additional_dirs=["content/projects"],
        menu_sections=["about", "projects", "contact"],
    )


# Export the template
TEMPLATE = _create_portfolio_template()
