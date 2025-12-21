"""
Section lookup helper functions.

Provides convenience wrappers for section access in templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


def get_section(path: str, site: Site) -> Section | None:
    """
    Get a section by its path.

    Convenience wrapper around site.get_section_by_path() with
    path normalization.

    Args:
        path: Section path (e.g., 'docs', 'blog/tutorials')
        site: Site instance

    Returns:
        Section object if found, None otherwise

    Example:
        {% set docs = get_section('docs') %}
        {% if docs %}
          {% for page in docs.pages | sort_by('weight') %}
            <a href="{{ page.href }}">{{ page.title }}</a>
          {% endfor %}
        {% endif %}
    """
    if not path:
        return None
    normalized = path.strip("/").replace("\\", "/")
    return site.get_section_by_path(normalized)


def section_pages(path: str, site: Site, recursive: bool = False) -> list[Page]:
    """
    Get pages in a section.

    Convenience function combining get_section() with pages access.

    Args:
        path: Section path (e.g., 'docs', 'blog')
        site: Site instance
        recursive: Include pages from subsections (default: False)

    Returns:
        List of pages (empty if section not found)

    Example:
        {% for page in section_pages('docs') | sort_by('weight') %}
          <a href="{{ page.href }}">{{ page.title }}</a>
        {% endfor %}
    """
    section = get_section(path, site)
    if not section:
        return []
    return list(section.get_all_pages(recursive=True)) if recursive else list(section.pages)
