"""
Section Ergonomics Mixin - Theme developer helpers.

Provides convenience methods for common theme development patterns like
recent posts, tag filtering, featured posts, word counts, and reading time.

Required Host Attributes:
- name: str
- pages: list[Page]
- subsections: list[Section]
- metadata: dict[str, Any]
- index_page: Page | None
- sorted_pages: list[Page] (from SectionQueryMixin)
- regular_pages_recursive: list[Page] (from SectionQueryMixin)
- get_all_pages: Callable (from SectionQueryMixin)
- hierarchy: list[str] (from SectionHierarchyMixin)

Related Modules:
bengal.core.section: Section dataclass using this mixin
bengal.core.section.queries: Core page retrieval methods

Example:
    >>> section = site.get_section("blog")
    >>> section.recent_pages(5)
[<Page 'newest'>, <Page 'second'>, ...]
    >>> section.featured_posts(3)
[<Page 'featured1'>, <Page 'featured2'>, ...]

"""

from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.rendering.template_engine import TemplateEngine


class SectionErgonomicsMixin:
    """
    Theme developer helpers for common patterns.
    
    This mixin handles:
    - Content pages (alias for sorted_pages without index)
    - Recent pages by date
    - Tag filtering
    - Featured posts
    - Page/post counting
    - Word count and reading time aggregation
    - Content aggregation for analytics
    - Template application
        
    """

    # =========================================================================
    # HOST CLASS ATTRIBUTES
    # =========================================================================
    # Type hints for attributes provided by the host dataclass.
    # These are NOT defined here - they're declared for type checking only.

    name: str
    pages: list[Page]
    subsections: list[Section]
    metadata: dict[str, Any]
    index_page: Page | None

    # From other mixins - accessed via self but defined in other mixins
    # These are declared as properties to match the @cached_property definitions
    @property
    def sorted_pages(self) -> list[Page]:
        """Sorted pages - provided by SectionQueryMixin."""
        raise NotImplementedError

    @property
    def regular_pages_recursive(self) -> list[Page]:
        """Recursive pages - provided by SectionQueryMixin."""
        raise NotImplementedError

    @property
    def hierarchy(self) -> list[str]:
        """Hierarchy path - provided by SectionHierarchyMixin."""
        raise NotImplementedError

    @property
    def title(self) -> str:
        """Section title - must be provided by host class."""
        raise NotImplementedError

    def get_all_pages(self, recursive: bool = True) -> list[Page]:
        """Get all pages - must be provided by host class."""
        raise NotImplementedError

    # =========================================================================
    # CONTENT PAGE HELPERS
    # =========================================================================

    @cached_property
    def content_pages(self) -> list[Page]:
        """
        Get content pages (regular pages excluding index).

        This is useful for listing a section's pages without
        including the section's own index page in the list.

        Note:
            `sorted_pages` already excludes `_index.md`/`index.md` files
            (see sorted_pages implementation). This property is effectively
            an alias but provides semantic clarity for theme developers.

        Returns:
            Sorted list of pages, excluding the section's index page

        Example:
            {% for page in section.content_pages %}
              <a href="{{ page.href }}">{{ page.title }}</a>
            {% endfor %}
        """
        # sorted_pages already excludes index files, so this is a semantic alias
        return self.sorted_pages

    def recent_pages(self, limit: int = 10) -> list[Page]:
        """
        Get most recent pages by date.

        Returns pages that have a date, sorted newest first.
        Pages without dates are excluded.

        Args:
            limit: Maximum number of pages to return (default: 10)

        Returns:
            List of pages sorted by date descending

        Example:
            {% for post in section.recent_pages(5) %}
              <article>{{ post.title }} - {{ post.date }}</article>
            {% endfor %}
        """
        dated_pages = [p for p in self.sorted_pages if getattr(p, "date", None)]
        dated_pages.sort(key=lambda p: p.date or datetime.min, reverse=True)
        return dated_pages[:limit]

    def pages_with_tag(self, tag: str) -> list[Page]:
        """
        Get pages containing a specific tag.

        Filters sorted_pages to return only pages that have the given tag.
        Matching is case-insensitive.

        Args:
            tag: Tag to filter by (case-insensitive)

        Returns:
            Sorted list of pages with the tag

        Example:
            {% set python_posts = section.pages_with_tag('python') %}
            {% for post in python_posts %}
              <article>{{ post.title }}</article>
            {% endfor %}
        """
        tag_lower = tag.lower()
        return [
            p for p in self.sorted_pages if tag_lower in [t.lower() for t in getattr(p, "tags", [])]
        ]

    def featured_posts(self, limit: int = 5) -> list[Page]:
        """
        Get featured pages from this section.

        Returns pages that have `featured: true` in their frontmatter,
        sorted by date descending (newest first).

        Args:
            limit: Maximum number of pages to return (default: 5)

        Returns:
            List of featured pages sorted by date descending

        Example:
            {% for post in section.featured_posts(3) %}
              <article class="featured">{{ post.title }}</article>
            {% endfor %}
        """
        featured = [p for p in self.sorted_pages if p.metadata.get("featured")]
        # Sort by date if available, newest first
        featured.sort(key=lambda p: getattr(p, "date", None) or "", reverse=True)
        return featured[:limit]

    # =========================================================================
    # COUNTING PROPERTIES
    # =========================================================================

    @cached_property
    def post_count(self) -> int:
        """
        Get total number of content pages in this section (non-recursive).

        Returns:
            Count of pages (excluding index pages)

        Example:
            <span>{{ section.post_count }} articles</span>
        """
        return len(self.sorted_pages)

    @cached_property
    def post_count_recursive(self) -> int:
        """
        Get total number of content pages in this section and all subsections.

        Returns:
            Count of all descendant pages

        Example:
            <span>{{ section.post_count_recursive }} total articles</span>
        """
        return len(self.regular_pages_recursive)

    @cached_property
    def word_count(self) -> int:
        """
        Get total word count across all pages in this section.

        Counts words in rendered content (HTML stripped) for all pages.

        Returns:
            Total word count across all section pages

        Example:
            <span>{{ section.word_count | intcomma }} words</span>
        """
        import re

        total = 0
        for page in self.sorted_pages:
            content = getattr(page, "content", "")
            if content:
                # Strip HTML tags
                clean = re.sub(r"<[^>]+>", "", content)
                total += len(clean.split())
        return total

    @cached_property
    def total_reading_time(self) -> int:
        """
        Get total reading time for all pages in this section.

        Sums reading_time property from all pages.

        Returns:
            Total reading time in minutes

        Example:
            <span>{{ section.total_reading_time }} min total reading time</span>
        """
        return sum(getattr(p, "reading_time", 0) for p in self.sorted_pages)

    # =========================================================================
    # AGGREGATION AND TEMPLATING
    # =========================================================================

    def aggregate_content(self) -> dict[str, Any]:
        """
        Aggregate content from all pages in this section.

        Returns:
            Dictionary with aggregated content information
        """
        pages = self.get_all_pages(recursive=False)

        # Collect all tags
        all_tags = set()
        for page in pages:
            all_tags.update(page.tags)

        result = {
            "page_count": len(pages),
            "total_page_count": len(self.get_all_pages(recursive=True)),
            "subsection_count": len(self.subsections),
            "tags": sorted(all_tags),
            "title": self.title,
            "hierarchy": self.hierarchy,
        }

        return result

    def apply_section_template(self, template_engine: TemplateEngine) -> str:
        """
        Apply a section template to generate a section index page.

        Args:
            template_engine: Template engine instance

        Returns:
            Rendered HTML for the section index
        """
        {
            "section": self,
            "pages": self.pages,
            "subsections": self.subsections,
            "metadata": self.metadata,
            "aggregated": self.aggregate_content(),
        }

        # Use the index page if available, otherwise generate a listing
        if self.index_page:
            return self.index_page.rendered_html

        # Template rendering will be handled by the template engine
        return ""
