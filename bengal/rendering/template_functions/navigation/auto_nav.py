"""
Auto-navigation discovery functions.

Provides get_auto_nav() for automatic navigation from site sections and
root-level pages.

Performance:
    get_auto_nav() is memoized per-build since the result is identical
    for all pages. This avoids re-computing navigation for every page
    render (~225x speedup for a 225-page site).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.rendering.template_functions.memo import site_scoped_memoize
from bengal.rendering.template_functions.navigation.helpers import get_nav_title
from bengal.utils.paths.normalize import to_posix

if TYPE_CHECKING:
    from bengal.protocols import SiteLike


def _build_section_menu_item(
    section: Any, site: SiteLike, parent_identifier: str | None = None
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
    # Skip sections without paths (unless virtual)
    if not section.path and not getattr(section, "_virtual", False):
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


def _is_root_level_page(page: Any, content_dir: Path) -> bool:
    """
    Check if a page is at content root (e.g. content/about.md, not content/posts/foo.md).

    Excludes index.md (homepage) and section indices (_index.md).
    """
    try:
        src = Path(page.source_path)
        if src.is_absolute():
            rel = src.relative_to(content_dir)
        else:
            rel_str = to_posix(str(src))
            rel = Path(rel_str[8:]) if rel_str.startswith("content/") else Path(rel_str)
        parts = to_posix(str(rel)).split("/")
        return len(parts) == 1 and parts[0] not in ("index.md", "_index.md")
    except (ValueError, AttributeError):
        return False


def _build_root_page_menu_item(page: Any) -> dict[str, Any] | None:
    """
    Build a menu item from a root-level page (opt-out: include unless menu: false).
    """
    metadata = getattr(page, "metadata", {})
    menu_setting = metadata.get("menu", True)
    if menu_setting is False or (
        isinstance(menu_setting, dict) and menu_setting.get("main") is False
    ):
        return None
    if hasattr(page, "visibility") and page.visibility and not page.visibility.get("menu", True):
        return None
    page_url = getattr(page, "_path", None) or "/"
    page_title = get_nav_title(page, getattr(page, "title", "Untitled"))
    page_weight = metadata.get("weight", 999)
    slug = getattr(page, "slug", None) or Path(str(page.source_path)).stem
    return {
        "name": page_title,
        "url": page_url,
        "weight": page_weight,
        "identifier": f"page-{slug}",
        "parent": None,
        "icon": None,
    }


@site_scoped_memoize("auto_nav")
def get_auto_nav(site: SiteLike) -> list[dict[str, Any]]:
    """
    Auto-discover hierarchical navigation from site sections and root-level pages.

    This function provides automatic navigation discovery similar to how
    sidebars and TOC work. It discovers sections and root-level pages,
    creating nav items automatically.

    Features:
    - Auto-discovers all sections in content/ (not just top-level)
    - Auto-discovers root-level pages (e.g. content/about.md) - opt-out via menu: false
    - Builds hierarchical menu based on section.parent relationships
    - Respects section weight for ordering
    - Respects 'menu: false' in section _index.md to hide from nav
    - Root-level pages: include by default, exclude with menu: false
    - Returns empty list if manual [[menu.main]] config exists (hybrid mode)
    - **Memoized**: Result cached per-build (same for all pages)

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

    Performance:
        Memoized via @site_scoped_memoize - computed once per build,
        not once per page. ~225x speedup for a 225-page site.

    """
    # Check if manual menu config exists - if so, don't auto-discover
    # This allows manual config to take precedence
    menu_config = site.config.get("menu", {})
    if menu_config and "main" in menu_config and menu_config["main"]:
        # Manual config exists and is non-empty, return empty (let manual config handle it)
        return []

    # Note: The check for site.menu.get("main") was removed to ensure
    # that auto-navigation is always discoverable, especially for virtual
    # sections like those used by autodoc. MenuOrchestrator and templates
    # can then decide how to use these items.

    nav_items: list[dict[str, Any]] = []

    # Find all top-level sections (those with no parent)
    top_level_sections = []
    for section in site.sections:
        # Skip sections without paths (unless virtual)
        if not section.path and not getattr(section, "_virtual", False):
            continue

        # Skip _versions and _shared directories (versioning internal directories)
        # These should not appear in navigation
        section_path_str = str(section.path)
        if "_versions" in section_path_str or "_shared" in section_path_str:
            # Check if this is a direct _versions or _shared section
            path_parts = to_posix(section_path_str).split("/")
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
            path_parts = to_posix(section_path_str).split("/")
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

    # Auto-discover root-level pages (opt-out: include unless menu: false)
    root_path = getattr(site, "root_path", None)
    if root_path:
        content_dir = root_path / "content"
        for page in site.pages:
            if _is_root_level_page(page, content_dir):
                item = _build_root_page_menu_item(page)
                if item:
                    nav_items.append(item)

    # Sort by weight (lower weights first)
    nav_items.sort(key=lambda x: (x["weight"], x["name"]))

    return nav_items
