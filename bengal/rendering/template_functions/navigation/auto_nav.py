"""
Auto-navigation discovery functions.

Provides get_auto_nav() for automatic navigation from site sections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.rendering.template_functions.navigation.helpers import get_nav_title

if TYPE_CHECKING:
    from bengal.core.site import Site


def _build_section_menu_item(
    section: Any, site: Site, parent_identifier: str | None = None
) -> dict[str, Any] | None:
    """
    Build a menu item from a section, recursively including subsections.

    Args:
        section: Section to build menu item for
        site: Site instance
        parent_identifier: Identifier of parent menu item (if nested)

    Returns:
        Menu item dict or None if section should be hidden
    """
    # Skip sections without paths
    if not hasattr(section, "path") or not section.path:
        return None

    # Get section metadata from index page
    section_hidden = False
    section_title = get_nav_title(section, section.name.replace("-", " ").title())
    section_weight = getattr(section, "weight", 999)

    # Check if section has index page with metadata
    if hasattr(section, "index_page") and section.index_page:
        index_page = section.index_page
        metadata = getattr(index_page, "metadata", {})

        # Check if explicitly hidden from menu via legacy menu: false
        menu_setting = metadata.get("menu", True)
        if menu_setting is False or (
            isinstance(menu_setting, dict) and menu_setting.get("main") is False
        ):
            section_hidden = True

        # Check visibility system (hidden: true or visibility.menu: false)
        if hasattr(index_page, "visibility"):
            visibility = index_page.visibility
            if not visibility.get("menu", True):
                section_hidden = True

        # Get nav_title (short) or title from frontmatter if available
        # Prefer nav_title for navigation display
        section_title = get_nav_title(index_page, section_title)

        # Get weight from frontmatter if available
        if "weight" in metadata:
            section_weight = metadata["weight"]

    # Skip hidden sections
    if section_hidden:
        return None

    # Skip dev sections if they're being bundled into Dev dropdown
    if site._dev_menu_metadata is not None and site._dev_menu_metadata.get("exclude_sections"):
        excluded_sections = site._dev_menu_metadata["exclude_sections"]
        if section.name in excluded_sections:
            return None

    # Build nav item
    # Use _path for menu items (templates apply baseurl via | absolute_url filter)
    section_url = getattr(section, "_path", None) or f"/{section.name}/"
    section_identifier = section.name

    # Get section icon from Section.icon property (reads from _index.md frontmatter)
    section_icon = getattr(section, "icon", None)

    # Determine parent identifier from section.parent if not provided
    if parent_identifier is None and hasattr(section, "parent") and section.parent:
        parent_identifier = section.parent.name

    return {
        "name": section_title,
        "url": section_url,
        "weight": section_weight,
        "identifier": section_identifier,
        "parent": parent_identifier,
        "icon": section_icon,
    }


def get_auto_nav(site: Site) -> list[dict[str, Any]]:
    """
    Auto-discover hierarchical navigation from site sections.

    This function provides automatic navigation discovery similar to how
    sidebars and TOC work. It discovers sections and creates nav items
    automatically, respecting the section hierarchy.

    Features:
    - Auto-discovers all sections in content/ (not just top-level)
    - Builds hierarchical menu based on section.parent relationships
    - Respects section weight for ordering
    - Respects 'menu: false' in section _index.md to hide from nav
    - Returns empty list if manual [[menu.main]] config exists (hybrid mode)

    Args:
        site: Site instance

    Returns:
        List of navigation items with name, url, weight, parent (for hierarchy)

    Example:
        {# In nav template #}
        {% set auto_items = get_auto_nav() %}
        {% if auto_items %}
          {% for item in auto_items %}
            <a href="{{ item.href }}">{{ item.name }}</a>
          {% endfor %}
        {% endif %}

    Section _index.md frontmatter can control visibility:
        ---
        title: Secret Section
        menu: false  # Won't appear in auto-nav
        weight: 10   # Controls ordering
        ---
    """
    # Check if manual menu config exists - if so, don't auto-discover
    # This allows manual config to take precedence
    menu_config = site.config.get("menu", {})
    if menu_config and "main" in menu_config and menu_config["main"]:
        # Manual config exists and is non-empty, return empty (let manual config handle it)
        return []

    # Check if menu was already built (site.menu["main"] exists)
    # MenuOrchestrator builds auto menu directly, so if menu exists, don't return auto-nav
    if site.menu.get("main"):
        return []

    nav_items: list[dict[str, Any]] = []

    # Find all top-level sections (those with no parent)
    top_level_sections = []
    for section in site.sections:
        if not hasattr(section, "path") or not section.path:
            continue

        # Skip _versions and _shared directories (versioning internal directories)
        # These should not appear in navigation
        section_path_str = str(section.path)
        if "_versions" in section_path_str or "_shared" in section_path_str:
            # Check if this is a direct _versions or _shared section
            path_parts = section_path_str.replace("\\", "/").split("/")
            if "_versions" in path_parts or "_shared" in path_parts:
                continue

        # Check if section has a parent - if not, it's top-level
        if not hasattr(section, "parent") or section.parent is None:
            top_level_sections.append(section)

    # Recursively build menu items from top-level sections
    def _add_section_recursive(section: Any, parent_id: str | None = None) -> None:
        """Recursively add section and its subsections to nav_items."""
        # Skip _versions and _shared directories (versioning internal directories)
        if hasattr(section, "path") and section.path:
            section_path_str = str(section.path)
            path_parts = section_path_str.replace("\\", "/").split("/")
            if "_versions" in path_parts or "_shared" in path_parts:
                return

        item = _build_section_menu_item(section, site, parent_id)
        if item is None:
            return

        section_identifier = item["identifier"]
        nav_items.append(item)

        # Recursively add subsections
        if hasattr(section, "subsections"):
            for subsection in section.subsections:
                _add_section_recursive(subsection, section_identifier)

    # Build menu from all top-level sections
    for section in top_level_sections:
        _add_section_recursive(section, None)

    # Sort by weight (lower weights first)
    nav_items.sort(key=lambda x: (x["weight"], x["name"]))

    return nav_items
