"""Blog template - no __init__.py in parent, tests nested grouping."""


class BlogTemplate:
    """Blog template class."""

    def render_post(self, title: str) -> str:
        """Render a blog post."""
        return f"<h1>{title}</h1>"
