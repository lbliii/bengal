"""
Template-safe proxy for NavNode that applies baseurl to URLs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .node import NavNode

if TYPE_CHECKING:
    from .context import NavTreeContext


class NavNodeProxy:
    """
    Transient proxy for NavNode that injects page-specific state.

    Used during template rendering to avoid mutating the cached NavTree.

    PERFORMANCE:
    ============
    Properties are cached on first access to avoid repeated computation.
    Templates may access is_current, is_in_trail, href multiple times per node.
    Without caching, this creates millions of redundant computations.

    URL CONVENTION:
    ===============
    NavNodeProxy provides two URL properties with distinct purposes:

    - `href`: Public URL with baseurl applied (for template href attributes)
              Example: "/bengal/docs/getting-started/" on GitHub Pages
              USE THIS IN TEMPLATES: <a href="{{ item.href }}">

    - `_path`: Site-relative path WITHOUT baseurl (for internal lookups)
               Example: "/docs/getting-started/"
               USE THIS FOR: Active trail detection, URL comparisons

    The cached NavTree stores _path internally for efficient lookups,
    but templates should always use .href for href attributes.

    Other Properties:
    - `is_current`: True if this node is the current page
    - `is_in_trail`: True if this node is in the path to current page
    - `is_expanded`: True if this node should be expanded
    - `is_section`: True if this node represents a section
    - `has_children`: True if this node has children
    - `absolute_href`: Fully-qualified URL for meta tags and sitemaps

    """

    __slots__ = (
        "_children_cached",
        "_context",
        "_href_cached",
        "_is_current_cached",
        "_is_expanded_cached",
        "_is_in_trail_cached",
        "_node",
    )

    def __init__(self, node: NavNode, context: NavTreeContext) -> None:
        self._node = node
        self._context = context
        # Cached values - None means not yet computed
        self._href_cached: str | None = None
        self._is_current_cached: bool | None = None
        self._is_in_trail_cached: bool | None = None
        self._is_expanded_cached: bool | None = None
        self._children_cached: list[NavNodeProxy] | None = None

    @property
    def href(self) -> str:
        """
        Get public URL with baseurl applied (cached).

        This is the URL for template href attributes. Automatically includes
        baseurl when configured (e.g., "/bengal/docs/foo/" for GitHub Pages).

        Use this in templates: <a href="{{ item.href }}">

        For internal comparisons or lookups, use _path instead.

        Cost: O(1) cached — computed once on first access, then returns cached value.
        """
        if self._href_cached is not None:
            return self._href_cached

        site_path = self._node._path  # NavNode stores site-relative path

        # Get site from page context
        site = getattr(self._context.page, "_site", None)
        if not site:
            self._href_cached = site_path
            return site_path

        # Get baseurl from site property - handles nested config structure
        try:
            baseurl = (site.baseurl or "").rstrip("/")
        except Exception:
            self._href_cached = site_path
            return site_path

        if not baseurl:
            self._href_cached = site_path
            return site_path

        # Ensure site_path starts with /
        if not site_path.startswith("/"):
            site_path = "/" + site_path

        # Handle absolute baseurl (e.g., https://example.com/subpath)
        if baseurl.startswith(("http://", "https://", "file://")):
            self._href_cached = f"{baseurl}{site_path}"
        else:
            # Path-only baseurl (e.g., /bengal)
            base_path = "/" + baseurl.lstrip("/")
            self._href_cached = f"{base_path}{site_path}"

        return self._href_cached

    @property
    def _path(self) -> str:
        """
        Get site-relative path WITHOUT baseurl.

        This is the canonical path for internal operations:
        - Active trail detection
        - URL comparisons
        - Cache lookups

        For template href attributes, use .href instead.

        Cost: O(1) — direct attribute read.
        """
        return self._node._path

    @property
    def absolute_href(self) -> str:
        """
        Fully-qualified URL for meta tags and sitemaps when available.

        If baseurl is absolute, returns href. Otherwise returns href as-is
        (root-relative) since no fully-qualified site origin is configured.

        Cost: O(1) — delegates to href (O(1) when href cached).
        """
        return self.href

    @property
    def is_current(self) -> bool:
        """True if this node is the current page (cached).

        Cost: O(1) cached — string comparison on first access, then cached.
        """
        if self._is_current_cached is not None:
            return self._is_current_cached
        self._is_current_cached = self._context.is_current(self._node)
        return self._is_current_cached

    @property
    def is_in_trail(self) -> bool:
        """True if this node is in the active trail (cached).

        Cost: O(1) cached — set membership on first access, then cached.
        """
        if self._is_in_trail_cached is not None:
            return self._is_in_trail_cached
        self._is_in_trail_cached = self._context.is_active(self._node)
        return self._is_in_trail_cached

    @property
    def is_expanded(self) -> bool:
        """True if this node should be expanded (cached).

        Cost: O(1) cached — delegates to is_active (set membership) on first access.
        """
        if self._is_expanded_cached is not None:
            return self._is_expanded_cached
        self._is_expanded_cached = self._context.is_expanded(self._node)
        return self._is_expanded_cached

    @property
    def is_section(self) -> bool:
        """True if this node represents a section (has section reference).

        Cost: O(1) — direct attribute read.
        """
        return self._node.section is not None

    @property
    def children(self) -> list[NavNodeProxy]:
        """Child nodes wrapped as proxies (cached).

        Cost: O(n) on first access (iterates children to wrap), O(1) cached thereafter.
        """
        if self._children_cached is not None:
            return self._children_cached
        self._children_cached = [self._context._wrap_node(child) for child in self._node.children]
        return self._children_cached

    def __getattr__(self, name: str) -> Any:
        # These attributes have @property implementations above, so __getattr__
        # should only be called if there's an issue accessing them. Delegate
        # directly to the node to avoid recursion.
        if name in ("href", "_path", "absolute_href"):
            # Should not reach here - these are @property methods.
            # Return node's _path as safe fallback.
            return self._node._path
        return getattr(self._node, name)

    def __getitem__(self, key: str) -> Any:
        if key == "href":
            return self.href
        if key == "_path":
            return self._path
        if key == "absolute_href":
            return self.absolute_href
        if key == "is_current":
            return self.is_current
        if key == "is_in_trail":
            return self.is_in_trail
        if key == "is_expanded":
            return self.is_expanded
        if key == "is_section":
            return self.is_section
        if key == "children":
            return self.children
        return self._node[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default
