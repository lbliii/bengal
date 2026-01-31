"""Default site template.

This module defines the minimal starter template shipped with Bengal. It
creates a single ``content/index.md`` file so users can bootstrap a site with
one command, and serves as a reference implementation for custom templates.

Exported objects:
- ``TEMPLATE``: the concrete :class:`~bengal.scaffolds.base.SiteTemplate`
  instance discovered by the template registry.
"""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_default_template() -> SiteTemplate:
    """Construct the default site template definition.

    The template provisions a single welcome page at ``content/index.md``.

    Returns:
        A fully populated :class:`SiteTemplate` instance.

    """
    files = [
        TemplateFile(
            relative_path="index.md",
            content=load_template_file(__file__, "index.md"),
            target_dir="content",
        ),
    ]

    return SiteTemplate(
        id="default",
        name="Default",
        description="Basic site structure",
        files=files,
        additional_dirs=[],
    )


# Export the template
TEMPLATE = _create_default_template()
