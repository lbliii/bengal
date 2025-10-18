"""Section Index - Index pages by section."""

from pathlib import Path
from typing import Any

from bengal.cache.query_index import QueryIndex


class SectionIndex(QueryIndex):
    """
    Index pages by section (directory).

    Provides O(1) lookup of all pages in a section:
        site.indexes.section.get('blog')        # All blog posts
        site.indexes.section.get('docs')        # All docs pages

    Example frontmatter:
        # Section is automatically detected from directory structure
        # content/blog/post.md → section = 'blog'
        # content/docs/guide.md → section = 'docs'
    """

    def __init__(self, cache_path: Path):
        super().__init__("section", cache_path)

    def extract_keys(self, page) -> list[tuple[str, dict[str, Any]]]:
        """Extract section name from page."""
        # Get section from page._section
        if hasattr(page, "_section") and page._section:
            section_name = page._section.name
            section_title = getattr(page._section, "title", section_name)

            return [(section_name, {"title": section_title})]

        return []
