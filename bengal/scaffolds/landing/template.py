"""Landing page template.

Scaffolds a marketing/landing site with a home page and common legal pages.
Performs simple ``{{date}}`` substitution for stamped content.
"""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_landing_template() -> SiteTemplate:
    """Construct the landing page template definition.

    Returns:
        A :class:`SiteTemplate` for a basic product landing site.

    """
    files = [
        TemplateFile(
            relative_path="index.md",
            content=load_template_file(__file__, "index.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="privacy.md",
            content=load_template_file(__file__, "privacy.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="terms.md",
            content=load_template_file(__file__, "terms.md", replace_date=True),
            target_dir="content",
        ),
    ]

    return SiteTemplate(
        id="landing",
        name="Landing",
        description="Landing page for products or services",
        files=files,
        additional_dirs=[],
        menu_sections=[],  # Landing pages typically use custom CTAs, not standard nav
    )


# Export the template
TEMPLATE = _create_landing_template()
