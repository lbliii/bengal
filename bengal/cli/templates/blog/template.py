"""Blog site template.

Provides a starter blog with a landing page, an about page, and two example
posts. Demonstrates how templates can perform simple token substitution (e.g.
injecting the current date) when loading bundled content files.

Exported objects:
- ``TEMPLATE``: the concrete :class:`~bengal.cli.templates.base.SiteTemplate`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_template_file(relative_path: str) -> str:
    """Load and lightly render a page from the template's ``pages/`` dir.

    Replaces ``{{date}}`` placeholders with today's date (``YYYY-MM-DD``).

    Args:
        relative_path: Path inside this template's ``pages/`` directory.

    Returns:
        The file contents with simple substitutions applied.
    """
    template_dir = Path(__file__).parent
    file_path = template_dir / "pages" / relative_path

    with open(file_path) as f:
        content = f.read()

    # Replace template variables
    current_date = datetime.now().strftime("%Y-%m-%d")
    content = content.replace("{{date}}", current_date)

    return content


def _create_blog_template() -> SiteTemplate:
    """Construct the blog template definition.

    Returns:
        A :class:`SiteTemplate` that scaffolds a minimal blog.
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
            relative_path="posts/first-post.md",
            content=_load_template_file("posts/first-post.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="posts/second-post.md",
            content=_load_template_file("posts/second-post.md"),
            target_dir="content",
        ),
    ]

    return SiteTemplate(
        id="blog",
        name="Blog",
        description="A blog with posts, tags, and categories",
        files=files,
        additional_dirs=["content/posts", "content/drafts"],
        menu_sections=["posts", "about"],  # Sections to auto-generate menu for
    )


# Export the template
TEMPLATE = _create_blog_template()
