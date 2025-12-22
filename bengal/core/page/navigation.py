"""
Page Navigation Mixin - Navigation and hierarchy relationships.

This mixin provides navigation capabilities for pages, enabling sequential
browsing (next/prev) and hierarchical navigation (parent/ancestors).

Key Properties:
    - next, prev: Sequential navigation through site pages
    - next_in_section, prev_in_section: Navigation within current section
    - parent: Parent section of the page
    - ancestors: List of ancestor sections to root

Related Modules:
    - bengal.core.section: Section class with page containment
    - bengal.rendering.template_functions.navigation: Template navigation helpers

See Also:
    - bengal/core/page/__init__.py: Page class that uses this mixin
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class PageNavigationMixin:
    """
    Mixin providing navigation capabilities for pages.

    This mixin handles:
    - Site-level navigation: next, prev
    - Section-level navigation: next_in_section, prev_in_section
    - Hierarchy: parent, ancestors
    """

    # Declare attributes that will be provided by the dataclass this mixin is mixed into
    _site: Site | None
    _section: Section | None
    _section_path: Path | None

    @property
    def next(self) -> Page | None:
        """
        Get the next page in the site's collection of pages.

        Returns:
            Next page or None if this is the last page

        Example:
            {% if page.next %}
              <a href="{{ url_for(page.next) }}">{{ page.next.title }} →</a>
            {% endif %}
        """
        if not self._site or not hasattr(self._site, "pages"):
            return None

        try:
            pages = self._site.pages
            idx = pages.index(self)
            if idx < len(pages) - 1:
                return pages[idx + 1]
        except (ValueError, IndexError):
            pass

        return None

    @property
    def prev(self) -> Page | None:
        """
        Get the previous page in the site's collection of pages.

        Returns:
            Previous page or None if this is the first page

        Example:
            {% if page.prev %}
              <a href="{{ url_for(page.prev) }}">← {{ page.prev.title }}</a>
            {% endif %}
        """
        if not self._site or not hasattr(self._site, "pages"):
            return None

        try:
            pages = self._site.pages
            idx = pages.index(self)
            if idx > 0:
                return pages[idx - 1]
        except (ValueError, IndexError):
            pass

        return None

    @property
    def next_in_section(self) -> Page | None:
        """
        Get the next page within the same section, respecting weight order.

        Pages are ordered by weight (ascending), then alphabetically by title.
        Pages without weight are treated as weight=999999 (appear at end).
        Index pages (_index.md, index.md) are skipped in navigation.

        Returns:
            Next page in section or None if this is the last page

        Example:
            {% if page.next_in_section %}
              <a href="{{ url_for(page.next_in_section) }}">Next in section →</a>
            {% endif %}
        """
        if not self._section or not hasattr(self._section, "sorted_pages"):
            return None

        try:
            # Use sorted_pages to respect weight ordering
            sorted_pages = self._section.sorted_pages
            idx = sorted_pages.index(self)

            # Find next non-index page
            next_idx = idx + 1
            while next_idx < len(sorted_pages):
                next_page = sorted_pages[next_idx]
                # Skip index pages
                if next_page.source_path.stem not in ("_index", "index"):
                    return next_page
                next_idx += 1
        except (ValueError, IndexError):
            pass

        return None

    @property
    def prev_in_section(self) -> Page | None:
        """
        Get the previous page within the same section, respecting weight order.

        Pages are ordered by weight (ascending), then alphabetically by title.
        Pages without weight are treated as weight=999999 (appear at end).
        Index pages (_index.md, index.md) are skipped in navigation.

        Returns:
            Previous page in section or None if this is the first page

        Example:
            {% if page.prev_in_section %}
              <a href="{{ url_for(page.prev_in_section) }}">← Prev in section</a>
            {% endif %}
        """
        if not self._section or not hasattr(self._section, "sorted_pages"):
            return None

        try:
            # Use sorted_pages to respect weight ordering
            sorted_pages = self._section.sorted_pages
            idx = sorted_pages.index(self)

            # Find previous non-index page
            prev_idx = idx - 1
            while prev_idx >= 0:
                prev_page = sorted_pages[prev_idx]
                # Skip index pages
                if prev_page.source_path.stem not in ("_index", "index"):
                    return prev_page
                prev_idx -= 1
        except (ValueError, IndexError):
            pass

        return None

    @property
    def parent(self) -> Any | None:
        """
        Get the parent section of this page.

        Returns:
            Parent section or None

        Example:
            {% if page.parent %}
              <a href="{{ url_for(page.parent) }}">{{ page.parent.title }}</a>
            {% endif %}
        """
        return self._section

    @property
    def ancestors(self) -> list[Any]:
        """
        Get all ancestor sections of this page.

        Returns:
            List of ancestor sections from immediate parent to root

        Example:
            {% for ancestor in page.ancestors | reverse %}
              <a href="{{ url_for(ancestor) }}">{{ ancestor.title }}</a> /
            {% endfor %}
        """
        result = []
        current = self._section

        while current:
            result.append(current)
            current = getattr(current, "parent", None)

        return result
