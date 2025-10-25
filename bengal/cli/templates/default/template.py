"""Default site template.

This module defines the minimal starter template shipped with Bengal. It
creates a single ``content/index.md`` file so users can bootstrap a site with
one command, and serves as a reference implementation for custom templates.

Exported objects:
- ``TEMPLATE``: the concrete :class:`~bengal.cli.templates.base.SiteTemplate`
  instance discovered by the template registry.
"""

from __future__ import annotations

from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_template_file(relative_path: str) -> str:
    """Load a static page stub bundled with this template.

    Args:
        relative_path: Path inside this template's ``pages/`` directory.

    Returns:
        The raw file contents for inclusion in a :class:`TemplateFile`.
    """
    template_dir = Path(__file__).parent
    file_path = template_dir / "pages" / relative_path

    with open(file_path) as f:
        return f.read()


def _create_default_template() -> SiteTemplate:
    """Construct the default site template definition.

    The template provisions a single welcome page at ``content/index.md``.

    Returns:
        A fully populated :class:`SiteTemplate` instance.
    """

    files = [
        TemplateFile(
            relative_path="index.md",
            content=_load_template_file("index.md"),
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
