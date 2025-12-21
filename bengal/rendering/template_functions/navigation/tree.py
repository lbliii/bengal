"""
Navigation tree generation.

Provides get_nav_tree() for building hierarchical navigation with active trail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.rendering.template_functions.navigation.helpers import get_nav_title

if TYPE_CHECKING:
    from bengal.core.page import Page


def get_nav_tree(
    page: Page, root_section: Any | None = None, mark_active_trail: bool = True
) -> list[dict[str, Any]]:
    """
    Build navigation tree with active trail marking.

    This function builds a hierarchical navigation tree from sections and pages,
    automatically detecting which items are in the active trail (path to current
    page). Returns a flat list with depth information, making it easy to render
    with indentation or as nested structures.

    Args:
        page: Current page for active trail detection
        root_section: Section to build tree from (defaults to page's root section)
        mark_active_trail: Whether to mark active trail (default: True)

    Returns:
        List of navigation items, each with:
        - title: Display title
        - url: Link URL
        - is_current: True if this is the current page
        - is_in_active_trail: True if in path to current page
        - is_section: True if this is a section (vs regular page)
        - depth: Nesting level (0 = top level)
        - children: List of child items (for nested rendering)
        - has_children: Boolean shortcut

    Example (flat rendering with indentation):
        {% for item in get_nav_tree(page) %}
          <a href="{{ item.url }}"
             class="nav-link depth-{{ item.depth }}
                    {{ 'active' if item.is_current }}
                    {{ 'in-trail' if item.is_in_active_trail }}"
             style="padding-left: {{ item.depth * 20 }}px">
            {{ item.title }}
            {% if item.has_children %}
              <span class="has-children">▶</span>
            {% endif %}
          </a>
        {% endfor %}

    Example (nested rendering with macro):
        {% macro render_nav_item(item) %}
          <li class="{{ 'active' if item.is_current }}
                     {{ 'in-trail' if item.is_in_active_trail }}">
            <a href="{{ item.url }}">
              {% if item.is_section %}📁{% endif %}
              {{ item.title }}
            </a>
            {% if item.children %}
              <ul class="nav-children">
                {% for child in item.children %}
                  {{ render_nav_item(child) }}
                {% endfor %}
              </ul>
            {% endif %}
          </li>
        {% endmacro %}

        <ul class="nav-tree">
          {% for item in get_nav_tree(page) %}
            {{ render_nav_item(item) }}
          {% endfor %}
        </ul>
    """
    if not hasattr(page, "_section"):
        return []

    # Determine root section
    if root_section is None:
        if page._section and hasattr(page._section, "root"):
            root_section = page._section.root
        else:
            root_section = page._section

    if not root_section:
        return []

    # Build active trail (set of URLs in path to current page)
    active_trail: set[str] = set()
    if mark_active_trail and hasattr(page, "ancestors"):
        for ancestor in page.ancestors:
            if hasattr(ancestor, "url"):
                active_trail.add(ancestor.url)

    # Add current page URL to active trail
    if hasattr(page, "url"):
        active_trail.add(page.url)

    def build_tree_recursive(section: Any, depth: int = 0) -> list[dict[str, Any]]:
        """Recursively build navigation tree."""
        items: list[dict[str, Any]] = []

        # Add section's index page if it exists
        if hasattr(section, "index_page") and section.index_page:
            index_page = section.index_page
            index_url = getattr(index_page, "url", "")

            items.append(
                {
                    "title": get_nav_title(index_page),
                    "url": index_url,
                    "is_current": index_url == page.url if hasattr(page, "url") else False,
                    "is_in_active_trail": index_url in active_trail,
                    "is_section": False,
                    "depth": depth,
                    "children": [],
                    "has_children": False,
                }
            )

        # Add regular pages (excluding index page)
        if hasattr(section, "regular_pages"):
            for p in section.regular_pages:
                p_url = getattr(p, "url", "")

                # Skip index page (already added above)
                if (
                    hasattr(section, "index_page")
                    and section.index_page
                    and p_url == getattr(section.index_page, "url", "")
                ):
                    continue

                items.append(
                    {
                        "title": get_nav_title(p),
                        "url": p_url,
                        "is_current": p_url == page.url if hasattr(page, "url") else False,
                        "is_in_active_trail": p_url in active_trail,
                        "is_section": False,
                        "depth": depth,
                        "children": [],
                        "has_children": False,
                    }
                )

        # Add subsections recursively
        if hasattr(section, "sections"):
            for subsection in section.sections:
                subsection_url = getattr(subsection, "url", "")

                # Build children first
                children = build_tree_recursive(subsection, depth + 1)

                # Add subsection as a navigation item
                subsection_item = {
                    "title": get_nav_title(subsection),
                    "url": subsection_url,
                    "is_current": subsection_url == page.url if hasattr(page, "url") else False,
                    "is_in_active_trail": subsection_url in active_trail,
                    "is_section": True,
                    "depth": depth,
                    "children": children,
                    "has_children": len(children) > 0,
                }

                items.append(subsection_item)

        return items

    return build_tree_recursive(root_section)
