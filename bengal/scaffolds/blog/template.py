"""Blog site template.

Provides a starter blog with a landing page, an about page, and two example
posts. Demonstrates how templates can perform simple token substitution (e.g.
injecting the current date) when loading bundled content files.

Exported objects:
- ``TEMPLATE``: the concrete :class:`~bengal.scaffolds.base.SiteTemplate`.
"""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_blog_template() -> SiteTemplate:
    """Construct the blog template definition.

    Returns:
        A :class:`SiteTemplate` that scaffolds a minimal blog.

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
            relative_path="posts/first-post.md",
            content=load_template_file(__file__, "posts/first-post.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="posts/second-post.md",
            content=load_template_file(__file__, "posts/second-post.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="authors.yml",
            content=load_template_file(__file__, "authors.yml", subdir="data"),
            target_dir="data",
        ),
    ]

    return SiteTemplate(
        id="blog",
        name="Blog",
        description="A blog with posts, tags, and categories",
        files=files,
        additional_dirs=["content/posts", "content/drafts", "data"],
        menu_sections=["posts", "about"],
    )


# Export the template
TEMPLATE = _create_blog_template()
