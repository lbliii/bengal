"""Documentation site template.

Seeds a docs site with top‑level sections (Getting Started, Guides, API).
"""

from __future__ import annotations

from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_template_file(relative_path: str) -> str:
    """Load a static page stub bundled with this template.

    Args:
        relative_path: Path inside this template's ``pages/`` directory.

    Returns:
        The raw file contents to write.
    """
    template_dir = Path(__file__).parent
    file_path = template_dir / "pages" / relative_path

    with open(file_path) as f:
        return f.read()


def _create_docs_template() -> SiteTemplate:
    """Construct the documentation site template definition.

    Returns:
        A :class:`SiteTemplate` with common docs scaffolding.
    """

    files = [
        TemplateFile(
            relative_path="_index.md",
            content=_load_template_file("_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="getting-started/_index.md",
            content=_load_template_file("getting-started/_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="getting-started/installation.md",
            content=_load_template_file("getting-started/installation.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="getting-started/quickstart.md",
            content=_load_template_file("getting-started/quickstart.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="guides/_index.md",
            content=_load_template_file("guides/_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="api/_index.md",
            content=_load_template_file("api/_index.md"),
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
