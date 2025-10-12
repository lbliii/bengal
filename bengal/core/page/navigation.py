"""
Page Navigation Mixin - Navigation and hierarchy relationships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page


class PageNavigationMixin:
    """
    Mixin providing navigation capabilities for pages.

    This mixin handles:
    - Site-level navigation: next, prev
    - Section-level navigation: next_in_section, prev_in_section
    - Hierarchy: parent, ancestors
    """

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
        Get the next page within the same section.

        Returns:
            Next page in section or None

        Example:
            {% if page.next_in_section %}
              <a href="{{ url_for(page.next_in_section) }}">Next in section →</a>
            {% endif %}
        """
        if not self._section or not hasattr(self._section, "pages"):
            return None

        try:
            section_pages = self._section.pages
            idx = section_pages.index(self)
            if idx < len(section_pages) - 1:
                return section_pages[idx + 1]
        except (ValueError, IndexError):
            pass

        return None

    @property
    def prev_in_section(self) -> Page | None:
        """
        Get the previous page within the same section.

        Returns:
            Previous page in section or None

        Example:
            {% if page.prev_in_section %}
              <a href="{{ url_for(page.prev_in_section) }}">← Prev in section</a>
            {% endif %}
        """
        if not self._section or not hasattr(self._section, "pages"):
            return None

        try:
            section_pages = self._section.pages
            idx = section_pages.index(self)
            if idx > 0:
                return section_pages[idx - 1]
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
