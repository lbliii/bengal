from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NavNode:
    """
    Hierarchical navigation node for pre-computed trees.

    Designed for memory efficiency and Jinja2 compatibility.
    """

    id: str
    title: str
    url: str
    icon: str | None = None
    weight: int = 0
    children: list[NavNode] = field(default_factory=list)
    page: Page | None = None
    section: Section | None = None

    # State flags (populated by NavTreeContext)
    is_index: bool = False
    is_current: bool = False
    is_in_trail: bool = False
    is_expanded: bool = False

    _depth: int = 0

    @property
    def has_children(self) -> bool:
        """True if this node has child nodes."""
        return len(self.children) > 0

    @property
    def depth(self) -> int:
        """Nesting level (0 = top level)."""
        return self._depth

    def walk(self) -> Iterator[NavNode]:
        """Iterate over this node and all descendants."""
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, url: str) -> NavNode | None:
        """Find a node by URL in this subtree."""
        if self.url == url:
            return self
        for child in self.children:
            found = child.find(url)
            if found:
                return found
        return None

    # --- Jinja2 Compatibility (Dict-like access) ---

    def __getitem__(self, key: str) -> Any:
        """Allow node['attr'] in templates."""
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def get(self, key: str, default: Any = None) -> Any:
        """Allow node.get('attr', default) in templates."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Allow iteration over keys in templates."""
        return [
            "id",
            "title",
            "url",
            "icon",
            "weight",
            "children",
            "is_index",
            "is_current",
            "is_in_trail",
            "is_expanded",
            "has_children",
            "depth",
        ]


@dataclass(slots=True)
class NavTree:
    """
    Pre-computed navigation tree for a specific version.

    This object is immutable and cached per version.
    """

    root: NavNode
    version_id: str | None
    versions: list[str] = field(default_factory=list)
    current_version: str | None = None

    _flat_nodes: dict[str, NavNode] = field(init=False, repr=False)
    _urls: set[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize lookup indices."""
        self._flat_nodes = {node.url: node for node in self.root.walk()}
        self._urls = set(self._flat_nodes.keys())

    @property
    def flat_nodes(self) -> dict[str, NavNode]:
        """Dictionary of URL -> NavNode for all nodes in the tree."""
        return self._flat_nodes

    @property
    def urls(self) -> set[str]:
        """Set of all URLs present in this navigation tree."""
        return self._urls

    def find(self, url: str) -> NavNode | None:
        """Find a node by URL in O(1) time."""
        return self._flat_nodes.get(url)

    def context(
        self,
        page: Page,
        *,
        mark_active_trail: bool = True,
        root_node: NavNode | None = None,
    ) -> NavTreeContext:
        """
        Create a per-page context overlay for this tree.

        This preserves immutability of the cached NavTree while providing:
        - Optional active trail state (is_in_trail / is_expanded)
        - Optional root scoping (useful for docs-only sidebars)
        """
        return NavTreeContext(self, page, mark_active_trail=mark_active_trail, root_node=root_node)

    @classmethod
    def build(cls, site: Site, version_id: str | None = None) -> NavTree:
        """
        Build a NavTree from the site's section hierarchy.

        Handles version filtering and shared content injection.

        Args:
            site: Site with discovered content (sections must be populated)
            version_id: Optional version ID for version-aware navigation

        Returns:
            NavTree with root node containing all top-level sections
        """
        # Create synthetic root node containing all top-level sections
        nav_root = NavNode(
            id="nav-root",
            title=site.title or "Site",
            url="/",
            is_index=True,
            _depth=0,
        )

        # Add top-level sections
        for section in site.sections:
            # Filter by version if applicable - use has_content_for_version for accurate filtering
            if version_id is not None and not section.has_content_for_version(version_id):
                # Check if section has any content for this version (index page, pages, or subsections)
                continue

            section_node = cls._build_node_recursive(section, version_id, depth=1)
            # Only add section node if it has children (pages or subsections) or is an index page
            # This ensures we show sections even if they only have an index page for this version
            if section_node.children or (
                section.index_page and getattr(section.index_page, "version", None) == version_id
            ):
                nav_root.children.append(section_node)

        # Sort top-level by weight, then title
        nav_root.children.sort(key=lambda n: (n.weight, n.title))

        # Get all versions for the version switcher
        # site.versions returns list of dicts with 'id' key
        versions = []
        if site.versioning_enabled:
            versions = [v["id"] for v in site.versions]

        return cls(
            root=nav_root, version_id=version_id, versions=versions, current_version=version_id
        )

    @classmethod
    def _build_node_recursive(cls, section: Section, version_id: str | None, depth: int) -> NavNode:
        """Recursively build NavNode tree from sections and pages."""
        # Create node for the section itself (using its index page if available)
        node_url = section.relative_url
        node_title = section.nav_title
        node_icon = section.icon

        node = NavNode(
            id=f"section-{section.name}",
            title=node_title,
            url=node_url,
            icon=node_icon,
            weight=section.metadata.get("weight", 0),
            section=section,
            is_index=True,
            _depth=depth,
        )

        # Add pages matching version
        for page in section.pages_for_version(version_id):
            # Skip the index page itself as it's represented by the section node
            if page == section.index_page:
                continue

            # Skip autodoc pages (excluded from navigation by default)
            # This centralizes exclusion logic so themes don't need to filter
            from bengal.utils.autodoc import is_autodoc_page

            if is_autodoc_page(page):
                continue

            page_node = NavNode(
                id=f"page-{page.url}",
                title=getattr(page, "nav_title", page.title),
                url=page.url,
                icon=getattr(page, "icon", None),
                weight=page.metadata.get("weight", 0),
                page=page,
                _depth=depth + 1,
            )
            node.children.append(page_node)

        # Add subsections matching version
        for subsection in section.subsections_for_version(version_id):
            sub_node = cls._build_node_recursive(subsection, version_id, depth + 1)
            node.children.append(sub_node)

        # Sort children by weight, then title
        node.children.sort(key=lambda n: (n.weight, n.title))

        return node


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
        self.current_url = page.url
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
            self.active_trail_urls.add(section.relative_url)
            section = section.parent

    def is_active(self, node: NavNode) -> bool:
        """True if the node is in the active trail."""
        if not self._mark_active_trail:
            return False
        return node.url in self.active_trail_urls

    def is_current(self, node: NavNode) -> bool:
        """True if the node represents the current page."""
        return node.url == self.current_url

    def is_expanded(self, node: NavNode) -> bool:
        """True if the node should be expanded in the sidebar."""
        # Typically expanded if in active trail or has children and explicitly set
        return self.is_active(node)

    # --- Jinja2 Compatibility (Delegation to NavTree and compute state) ---

    def __getitem__(self, key: str) -> Any:
        """Allow nav['root'] access by delegating to tree or computing state."""
        if key == "root":
            return self._wrap_node(self._root_node)
        return getattr(self.tree, key)

    def _wrap_node(self, node: NavNode) -> NavNodeProxy:
        """Wrap a NavNode with page-specific state."""
        return NavNodeProxy(node, self)


@dataclass(slots=True)
class NavNodeProxy:
    """
    Transient proxy for NavNode that injects page-specific state.

    Used during template rendering to avoid mutating the cached NavTree.

    Properties:
    - `is_current`: True if this node is the current page
    - `is_in_trail`: True if this node is in the path to current page
    - `is_expanded`: True if this node should be expanded
    - `is_section`: True if this node represents a section
    - `has_children`: True if this node has children
    """

    _node: NavNode
    _context: NavTreeContext

    @property
    def is_current(self) -> bool:
        return self._context.is_current(self._node)

    @property
    def is_in_trail(self) -> bool:
        return self._context.is_active(self._node)

    @property
    def is_expanded(self) -> bool:
        return self._context.is_expanded(self._node)

    @property
    def is_section(self) -> bool:
        """True if this node represents a section (has section reference)."""
        return self._node.section is not None

    @property
    def children(self) -> list[NavNodeProxy]:
        return [self._context._wrap_node(child) for child in self._node.children]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._node, name)

    def __getitem__(self, key: str) -> Any:
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


class NavTreeCache:
    """
    Thread-safe cache for NavTree instances.
    """

    _trees: dict[str | None, NavTree] = {}
    _lock = threading.Lock()
    _site: Site | None = None

    @classmethod
    def get(cls, site: Site, version_id: str | None = None) -> NavTree:
        """Get a cached NavTree or build it if missing."""
        # 1. Quick check with lock for existing tree
        with cls._lock:
            # Full invalidation if site object changed (new build session)
            if cls._site is not site:
                cls._trees.clear()
                cls._site = site

            if version_id in cls._trees:
                return cls._trees[version_id]

        # 2. Build outside the main lock to avoid blocking other versions,
        # but we need a way to prevent concurrent builds for the SAME version.
        # For Phase 1 simplification, we'll build and then update.
        # In a high-concurrency production environment, we'd use a per-version lock.
        tree = NavTree.build(site, version_id)

        with cls._lock:
            # Double-check if another thread built it while we were building
            if version_id not in cls._trees:
                cls._trees[version_id] = tree
            return cls._trees[version_id]

    @classmethod
    def invalidate(cls, version_id: str | None = None) -> None:
        """Invalidate the cache for a specific version or all."""
        with cls._lock:
            if version_id is None:
                cls._trees.clear()
            else:
                cls._trees.pop(version_id, None)
