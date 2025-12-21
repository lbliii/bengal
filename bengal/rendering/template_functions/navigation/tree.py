"""
Navigation tree generation.

Provides get_nav_tree() for building hierarchical navigation with active trail.

Delegates to bengal.core.nav_tree for cached, pre-computed navigation trees.
The NavTree infrastructure provides O(1) lookups and avoids repeated
computation during template rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.nav_tree import NavTreeCache, NavTreeContext

if TYPE_CHECKING:
    from bengal.core.nav_tree import NavNodeProxy
    from bengal.core.page import Page
    from bengal.core.section import Section


def get_nav_tree(
    page: Page, mark_active_trail: bool = True, root_section: Section | None = None
) -> list[NavNodeProxy]:
    """
    Build navigation tree with active trail marking.

    Returns a list of NavNodeProxy items for the top-level sections.
    Uses cached NavTree infrastructure for O(1) lookups.

    Args:
        page: Current page for active trail detection
        mark_active_trail: Whether to mark active trail (default: True)
        root_section: Optional section to scope navigation to (default: None = all sections).
                     When provided, only shows this section and its descendants.
                     Typically set to `page._section.root` for docs-only navigation.

    Returns:
        List of NavNodeProxy items (top-level sections, or scoped to root_section)

    Example:
        {% for item in get_nav_tree(page) %}
          <a href="{{ item.href }}"
             class="{{ 'active' if item.is_current }}
                    {{ 'in-trail' if item.is_in_trail }}">
            {{ item.title }}
          </a>
          {% if item.children %}
            {% for child in item.children %}
              ...
            {% endfor %}
          {% endif %}
        {% endfor %}

    Example with scoping:
        {% set root = page._section.root if page._section else none %}
        {% for item in get_nav_tree(page, root_section=root) %}
          ...
        {% endfor %}
    """
    site = getattr(page, "_site", None)
    if site is None:
        return []

    version_id = None
    if getattr(site, "versioning_enabled", False):
        version_id = getattr(page, "version", None)

    tree = NavTreeCache.get(site, version_id)

    # If root_section is provided, scope navigation to only that section and its descendants.
    root_node = None
    if root_section is not None:
        root_url = getattr(root_section, "_path", None) or f"/{root_section.name}/"
        root_node = tree.find(root_url)
        if root_node is None:
            return []

    ctx = tree.context(page, mark_active_trail=mark_active_trail, root_node=root_node)
    return ctx["root"].children


def get_nav_context(page: Page, root_section: Section | None = None) -> NavTreeContext:
    """
    Get the full NavTreeContext for advanced navigation use cases.

    Args:
        page: Current page for active trail detection
        root_section: Optional section to scope navigation to (default: None = all sections).
                     When provided, only shows this section and its descendants.

    Returns:
        NavTreeContext with full tree access (or scoped to root_section)

    Example:
        {% set nav = get_nav_context(page) %}
        {% for section in nav['root'].children %}
          ...
        {% endfor %}

    Example with scoping:
        {% set root = page._section.root if page._section else none %}
        {% set nav = get_nav_context(page, root_section=root) %}
        {% for section in nav['root'].children %}
          ...
        {% endfor %}
    """
    site = getattr(page, "_site", None)
    if site is None:
        from bengal.errors import BengalRenderingError

        msg = "Page has no site reference. Ensure content discovery has run."
        raise BengalRenderingError(
            msg,
            suggestion="Ensure content discovery has run before accessing navigation tree",
        )

    version_id = None
    if getattr(site, "versioning_enabled", False):
        version_id = getattr(page, "version", None)

    tree = NavTreeCache.get(site, version_id)
    root_node = None
    if root_section is not None:
        root_url = getattr(root_section, "_path", None) or f"/{root_section.name}/"
        root_node = tree.find(root_url)
        if root_node is None:
            from bengal.errors import BengalRenderingError

            raise BengalRenderingError(
                f"Root section not found in NavTree: {root_url}",
                suggestion=f"Ensure section with URL '{root_url}' exists in the site",
            )

    return tree.context(page, mark_active_trail=True, root_node=root_node)
