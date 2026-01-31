"""
Ergonomic helper methods mixin for Site.

Provides convenience methods for theme developers and template authors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


class SiteHelpersMixin:
    """
    Mixin providing ergonomic helper methods for Site.

    These methods are designed for theme developers and provide convenient
    access to site content for use in templates.
    """

    # These attributes are defined on the Site dataclass
    pages: list[Page]
    sections: list[Section]
    assets: list[Any]

    def get_section_by_name(self, name: str) -> Section | None:
        """
        Get a section by its name.

        Searches top-level sections for a matching name. Returns the first
        match or None if not found.

        Args:
            name: Section name to find (e.g., 'blog', 'docs', 'api')

        Returns:
            Section if found, None otherwise

        Example:
            {% set blog = site.get_section_by_name('blog') %}
            {% if blog %}
              {{ blog.title }} has {{ blog.pages | length }} posts
            {% endif %}
        """
        for section in self.sections:
            if section.name == name:
                return section
        return None

    def pages_by_section(self, section_name: str) -> list[Page]:
        """
        Get all pages belonging to a section by name.

        Filters site.pages to return only pages whose section matches
        the given name. Useful for archive and taxonomy templates.

        Args:
            section_name: Section name to filter by (e.g., 'blog', 'docs')

        Returns:
            List of pages in that section (empty list if section not found)

        Example:
            {% set blog_posts = site.pages_by_section('blog') %}
            {% for post in blog_posts %}
              <article>{{ post.title }}</article>
            {% endfor %}
        """
        result: list[Page] = []
        for p in self.pages:
            section = getattr(p, "_section", None)
            if section is not None and section.name == section_name:
                result.append(p)
        return result

    def get_version_target_url(
        self, page: Page | None, target_version: dict[str, Any] | None
    ) -> str:
        """
        Get the best URL for a page in the target version.

        Computes a fallback cascade at build time:
        1. If exact equivalent page exists → return that URL
        2. If section index exists → return section index URL
        3. Otherwise → return version root URL

        This is engine-agnostic and works with any template engine (Jinja2,
        Mako, or any BYORenderer).

        Args:
            page: Current page object (may be None for edge cases)
            target_version: Target version dict with 'id', 'url_prefix', 'latest' keys

        Returns:
            Best URL to navigate to (guaranteed to exist, never 404)

        Example (Jinja2):
            {% for v in versions %}
            <option data-target="{{ site.get_version_target_url(page, v) }}">
              {{ v.label }}
            </option>
            {% endfor %}

        Example (Mako):
            % for v in versions:
            <option data-target="${site.get_version_target_url(page, v)}">
              ${v['label']}
            </option>
            % endfor
        """
        # Delegate to core logic (engine-agnostic pure Python)
        from bengal.rendering.template_functions.version_url import (
            get_version_target_url as _get_version_target_url,
        )

        return _get_version_target_url(page, target_version, self)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        pages = len(self.pages)
        sections = len(self.sections)
        assets = len(self.assets)
        return f"Site(pages={pages}, sections={sections}, assets={assets})"
