"""
Navigation tree generation.

Provides get_nav_tree() for building hierarchical navigation with active trail.

Delegates to bengal.core.nav_tree for cached, pre-computed navigation trees.
The NavTree infrastructure provides O(1) lookups and avoids repeated
computation during template rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
          <a href="{{ item.url }}"
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
    ctx = tree.with_active_trail(page) if mark_active_trail else _EmptyTrailContext(tree, page)

    # If root_section is provided, filter to only that section and its descendants
    if root_section is not None:
        root_url = root_section.relative_url
        # Find the node matching the root section
        root_node = tree.find(root_url)
        if root_node is not None:
            # Return this section's children (scoped view - shows only descendants)
            return [ctx._wrap_node(child) for child in root_node.children]
        # Fallback: if root section not found, return empty list
        return []

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
        msg = "Page has no site reference. Ensure content discovery has run."
        raise ValueError(msg)

    version_id = None
    if getattr(site, "versioning_enabled", False):
        version_id = getattr(page, "version", None)

    tree = NavTreeCache.get(site, version_id)
    ctx = tree.with_active_trail(page)

    # If root_section is provided, create a scoped context
    if root_section is not None:
        root_url = root_section.relative_url
        root_node = tree.find(root_url)
        if root_node is not None:
            # Return a scoped context that shows only this section as root
            return _ScopedNavContext(ctx, root_node)
        # Fallback: return empty context if root section not found
        return _EmptyScopedContext(ctx)

    return ctx


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
        if key in ("is_current", "is_in_trail", "is_expanded", "is_section"):
            return getattr(self, key)
        if key == "children":
            return self.children
        return self._node[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


class _ScopedNavContext:
    """Context wrapper that scopes navigation to a specific root section."""

    def __init__(self, base_context: NavTreeContext, root_node: Any) -> None:
        self.base_context = base_context
        self.root_node = root_node
        self._root_proxy: Any = None

    def __getitem__(self, key: str) -> Any:
        if key == "root":
            if self._root_proxy is None:
                self._root_proxy = self.base_context._wrap_node(self.root_node)
            return self._root_proxy
        return getattr(self.base_context.tree, key)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base_context, name)


class _EmptyScopedContext:
    """Empty context when root section is not found."""

    def __init__(self, base_context: NavTreeContext) -> None:
        self.base_context = base_context
        self._root_proxy: _NoTrailNodeProxy | None = None

    def __getitem__(self, key: str) -> Any:
        if key == "root":
            if self._root_proxy is None:
                # Create an empty root node
                from bengal.core.nav_tree import NavNode

                empty_root = NavNode(
                    id="empty-root",
                    title="",
                    url="/",
                    _depth=0,
                )
                self._root_proxy = _NoTrailNodeProxy(empty_root, self)
            return self._root_proxy
        return getattr(self.base_context.tree, key)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base_context, name)
