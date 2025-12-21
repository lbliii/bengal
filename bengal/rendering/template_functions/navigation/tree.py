"""
Navigation tree generation.

Provides get_nav_tree() for building hierarchical navigation with active trail.

This module delegates to bengal.core.nav_tree for cached, pre-computed navigation
trees. The NavTree infrastructure provides O(1) lookups and avoids repeated
computation during template rendering.

Falls back to legacy implementation when NavTree infrastructure is unavailable
(e.g., in tests with Mock objects or when root_section is explicitly provided).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.core.nav_tree import NavTreeCache, NavTreeContext
from bengal.rendering.template_functions.navigation.helpers import get_nav_title

if TYPE_CHECKING:
    from bengal.core.page import Page


def get_nav_tree(
    page: Page, root_section: Any | None = None, mark_active_trail: bool = True
) -> list[Any]:
    """
    Build navigation tree with active trail marking.

    This function builds a hierarchical navigation tree from sections and pages,
    automatically detecting which items are in the active trail (path to current
    page). Returns a list of navigation items for rendering.

    Uses cached NavTree infrastructure for O(1) lookups on repeated access.
    Falls back to legacy dict-based implementation when root_section is provided
    or NavTree infrastructure is unavailable.

    Args:
        page: Current page for active trail detection
        root_section: Section to build tree from. If provided, uses legacy
            implementation. If None, uses NavTree cache.
        mark_active_trail: Whether to mark active trail (default: True).
            If False, is_in_active_trail will always be False.

    Returns:
        List of navigation items (NavNodeProxy or dict), each with:
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
    # If root_section is explicitly provided, use legacy implementation
    # This maintains backward compatibility with tests and custom usage
    if root_section is not None:
        return _get_nav_tree_legacy(page, root_section, mark_active_trail)

    # Try NavTree-based implementation
    site = getattr(page, "_site", None)
    if site is None:
        return []

    # Check if site has proper sections attribute (not a Mock)
    if not hasattr(site, "sections") or not isinstance(getattr(site, "sections", None), list):
        # Fall back to legacy if site doesn't have proper sections
        section = getattr(page, "_section", None)
        if section and hasattr(section, "root"):
            return _get_nav_tree_legacy(page, section.root, mark_active_trail)
        elif section:
            return _get_nav_tree_legacy(page, section, mark_active_trail)
        return []

    # Determine version_id for version-aware navigation
    version_id = None
    if getattr(site, "versioning_enabled", False):
        version_id = getattr(page, "version", None)

    # Get cached NavTree (O(1) after first build)
    tree = NavTreeCache.get(site, version_id)

    # Create context with active trail for this page
    # If mark_active_trail is False, use minimal context without trail computation
    ctx = tree.with_active_trail(page) if mark_active_trail else _EmptyTrailContext(tree, page)

    # Return top-level section children (the root is synthetic)
    return ctx["root"].children


def _get_nav_tree_legacy(
    page: Any, root_section: Any, mark_active_trail: bool = True
) -> list[dict[str, Any]]:
    """
    Legacy implementation of get_nav_tree using dict-based items.

    Used for backward compatibility with tests and when root_section is provided.
    """
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


def get_nav_context(page: Page) -> NavTreeContext:
    """
    Get the full NavTreeContext for advanced navigation use cases.

    This provides access to the complete navigation tree with active trail
    marking. Use this when you need:
    - Access to the root node (`ctx['root']`)
    - Version information (`ctx.tree.versions`)
    - Custom traversal patterns

    Args:
        page: Current page for active trail detection

    Returns:
        NavTreeContext with full tree access

    Example:
        {% set nav = get_nav_context(page) %}
        {% set root = nav['root'] %}
        <nav>
          {% for section in root.children %}
            ...
          {% endfor %}
        </nav>
    """
    site = getattr(page, "_site", None)
    if site is None:
        msg = "Page has no site reference. Ensure content discovery has run."
        raise ValueError(msg)

    version_id = None
    if getattr(site, "versioning_enabled", False):
        version_id = getattr(page, "version", None)

    tree = NavTreeCache.get(site, version_id)
    return tree.with_active_trail(page)


class _EmptyTrailContext:
    """Minimal context that returns nodes without active trail marking."""

    def __init__(self, tree: Any, page: Page) -> None:
        self.tree = tree
        self.page = page
        self._root_proxy: _NoTrailNodeProxy | None = None

    def __getitem__(self, key: str) -> Any:
        if key == "root":
            if self._root_proxy is None:
                self._root_proxy = _NoTrailNodeProxy(self.tree.root, self)
            return self._root_proxy
        return getattr(self.tree, key)


class _NoTrailNodeProxy:
    """NavNode proxy that always returns False for trail properties."""

    def __init__(self, node: Any, context: _EmptyTrailContext) -> None:
        self._node = node
        self._context = context

    @property
    def is_current(self) -> bool:
        return self._node.url == self._context.page.url

    @property
    def is_in_trail(self) -> bool:
        return False

    @property
    def is_in_active_trail(self) -> bool:
        return False

    @property
    def is_expanded(self) -> bool:
        return False

    @property
    def is_section(self) -> bool:
        return self._node.section is not None

    @property
    def children(self) -> list[_NoTrailNodeProxy]:
        return [_NoTrailNodeProxy(child, self._context) for child in self._node.children]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._node, name)

    def __getitem__(self, key: str) -> Any:
        if key in ("is_current", "is_in_trail", "is_in_active_trail", "is_expanded", "is_section"):
            return getattr(self, key)
        if key == "children":
            return self.children
        return self._node[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default
