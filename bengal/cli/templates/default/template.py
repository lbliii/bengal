"""Default template definition."""


from __future__ import annotations

from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_template_file(relative_path: str) -> str:
    """Load a template file from the pages directory."""
    template_dir = Path(__file__).parent
    file_path = template_dir / "pages" / relative_path

    with open(file_path) as f:
        return f.read()


def _create_default_template() -> SiteTemplate:
    """Create the default site template."""

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
