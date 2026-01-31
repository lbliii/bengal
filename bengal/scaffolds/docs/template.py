"""Documentation site template.

Seeds a docs site with top‑level sections (Getting Started, Guides, API).
"""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_docs_template() -> SiteTemplate:
    """Construct the documentation site template definition.

    Returns:
        A :class:`SiteTemplate` with common docs scaffolding.

    """
    files = [
        TemplateFile(
            relative_path="_index.md",
            content=load_template_file(__file__, "_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="getting-started/_index.md",
            content=load_template_file(__file__, "getting-started/_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="getting-started/installation.md",
            content=load_template_file(__file__, "getting-started/installation.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="getting-started/quickstart.md",
            content=load_template_file(__file__, "getting-started/quickstart.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="guides/_index.md",
            content=load_template_file(__file__, "guides/_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="api/_index.md",
            content=load_template_file(__file__, "api/_index.md"),
            target_dir="content",
        ),
    ]

    return SiteTemplate(
        id="docs",
        name="Docs",
        description="Technical documentation with navigation and sections",
        files=files,
        additional_dirs=[
            "content/getting-started",
            "content/guides",
            "content/api",
            "content/advanced",
        ],
        menu_sections=["getting-started", "guides", "api"],
    )


# Export the template
TEMPLATE = _create_docs_template()
