"""
Per-page context overlay for NavTree with active trail detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .node import NavNode
from .tree import NavTree

if TYPE_CHECKING:
    from bengal.core.page import Page

    from .proxy import NavNodeProxy


class NavTreeContext:
    """
    Per-page context overlay for a NavTree.

    Preserves immutability of the cached NavTree while providing
    page-specific state like 'is_current' and 'is_in_trail'.

    """

    def __init__(
        self,
        tree: NavTree,
        page: Page,
        *,
        mark_active_trail: bool = True,
        root_node: NavNode | None = None,
    ):
        self.tree = tree
        self.page = page
        # Use _path for consistent matching with nav tree nodes
        self.current_url = getattr(page, "_path", None) or getattr(page, "href", "/")
        self._mark_active_trail = mark_active_trail
        self._root_node = root_node or tree.root

        # Pre-compute active trail
        self.active_trail_urls: set[str] = set()
        if self._mark_active_trail:
            self._compute_active_trail()

    def _compute_active_trail(self) -> None:
        """Compute the set of URLs in the active trail for the current page."""
        # Start with current page
        self.active_trail_urls.add(self.current_url)

        # Walk up from current section (use _section - the private attribute)
        section = getattr(self.page, "_section", None)
        while section:
            self.active_trail_urls.add(getattr(section, "_path", None) or f"/{section.name}/")
            section = section.parent

    def is_active(self, node: NavNode) -> bool:
        """True if the node is in the active trail."""
        if not self._mark_active_trail:
            return False
        return node._path in self.active_trail_urls

    def is_current(self, node: NavNode) -> bool:
        """True if the node represents the current page."""
        return node._path == self.current_url

    def is_expanded(self, node: NavNode) -> bool:
        """True if the node should be expanded in the sidebar."""
        # Typically expanded if in active trail or has children and explicitly set
        return self.is_active(node)

    # --- Jinja2 Compatibility (Delegation to NavTree and compute state) ---

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for nav context access."""
        if key == "root":
            return True
        return hasattr(self.tree, key)

    def __getitem__(self, key: str) -> Any:
        """Allow nav['root'] access by delegating to tree or computing state."""
        if key == "root":
            return self._wrap_node(self._root_node)
        return getattr(self.tree, key)

    def _wrap_node(self, node: NavNode) -> NavNodeProxy:
        """Wrap a NavNode with page-specific state (with caching)."""
        from .proxy import NavNodeProxy

        return NavNodeProxy(node, self)
