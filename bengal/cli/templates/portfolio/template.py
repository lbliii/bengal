"""Portfolio site template.

Creates a simple portfolio with home, about, projects, and contact pages. Uses
light token substitution to inject the current date into example project pages.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_template_file(relative_path: str) -> str:
    """Load and lightly render a page from the ``pages/`` directory.

    Args:
        relative_path: Path inside this template's ``pages/`` directory.

    Returns:
        File contents with ``{{date}}`` placeholders resolved.
    """
    template_dir = Path(__file__).parent
    file_path = template_dir / "pages" / relative_path

    with open(file_path) as f:
        content = f.read()

    # Replace template variables
    current_date = datetime.now().strftime("%Y-%m-%d")
    content = content.replace("{{date}}", current_date)

    return content


def _create_portfolio_template() -> SiteTemplate:
    """Construct the portfolio template definition.

    Returns:
        A :class:`SiteTemplate` for a personal portfolio site.
    """

    files = [
        TemplateFile(
            relative_path="index.md",
            content=_load_template_file("index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="about.md",
            content=_load_template_file("about.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="projects/index.md",
            content=_load_template_file("projects/index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="projects/project-1.md",
            content=_load_template_file("projects/project-1.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="projects/project-2.md",
            content=_load_template_file("projects/project-2.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="contact.md",
            content=_load_template_file("contact.md"),
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
