"""
Navigation Tree Models.

Provides hierarchical navigation with O(1) lookups and baseurl-aware URLs.
Pre-computed navigation trees enable fast sidebar and menu rendering.

Public API:
    NavNode: Single navigation node (title, URL, children, state flags)
    NavTree: Pre-computed navigation tree with O(1) URL lookups
    NavTreeContext: Per-page context overlay for active trail detection
    NavNodeProxy: Template-safe proxy that applies baseurl to URLs
    NavTreeCache: Thread-safe cache for NavTree instances by version

URL Naming Convention:
    _path: Site-relative path WITHOUT baseurl (e.g., "/docs/foo/")
           Used for internal lookups, active trail detection, caching.

    href: Public URL WITH baseurl applied (e.g., "/bengal/docs/foo/")
          Used for template href attributes and external links.

    When baseurl is configured (e.g., "/bengal" for GitHub Pages),
    NavNodeProxy.href automatically includes it. Templates should always
    use .href for links.

Template Usage:
    {% for item in get_nav_tree(page) %}
      <a href="{{ item.href }}">{{ item.title }}</a>
      {% if item.is_in_trail %}class="active"{% endif %}
    {% endfor %}

Internal Usage:
    if page._path in nav_tree.active_trail_urls:
        mark_active()

Performance:
    - O(1) URL lookup via NavTree.flat_nodes dict
    - Tree built once per version, cached in NavTreeCache
    - NavNodeProxy wraps nodes without copying for template state

Related Packages:
    bengal.core.site: Site object that holds the NavTree
    bengal.core.section: Section objects that form the tree structure
    bengal.rendering.template_functions.navigation: Template functions
"""

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

    IMPORTANT: The `_path` field stores site_path (WITHOUT baseurl) for cache
    efficiency and internal lookups. Templates should use NavNodeProxy.href
    which applies baseurl automatically.
    """

    id: str
    title: str
    _path: str  # NOTE: This is site_path (without baseurl). See NavNodeProxy.href for public URL.
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
        if self._path == url:
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
            "_path",
            "href",  # For templates (via NavNodeProxy)
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
        """Initialize lookup indices with collision detection and merging."""
        self._flat_nodes = {}
        for node in self.root.walk():
            url = node._path
            if url in self._flat_nodes:
                existing = self._flat_nodes[url]

                # When a section and page share the same URL, merge them:
                # - Section + Page → Section wins (page becomes section's content)
                # - Page + Section → Section wins (same as above)
                # This is expected for autodoc-generated pages that document
                # CLI command groups (e.g., /cli/assets/ is both a section and a page)
                existing_is_section = existing.section is not None
                new_is_section = node.section is not None

                if existing_is_section and not new_is_section:
                    # Existing is section, new is page - merge page into section
                    # Section keeps priority, but inherit page reference if missing
                    if existing.page is None:
                        existing.page = node.page
                    # Skip adding the page node (section already represents this URL)
                    continue
                elif new_is_section and not existing_is_section:
                    # New is section, existing is page - section takes over
                    # Merge the page into the section node
                    if node.page is None:
                        node.page = existing.page
                    # Replace with section node
                    self._flat_nodes[url] = node
                    continue
                else:
                    # Both are same type (section+section or page+page) - real collision
                    logger.warning(
                        "NavTree URL collision detected: url=%s | "
                        "existing_id=%s (type=%s) | new_id=%s (type=%s) | "
                        "Tip: Check for duplicate slugs or conflicting autodoc output",
                        url,
                        existing.id,
                        "section" if existing_is_section else "page",
                        node.id,
                        "section" if new_is_section else "page",
                    )
            self._flat_nodes[url] = node
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
            _path="/",
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
    def _should_exclude_from_nav(cls, page: Page) -> bool:
        """
        Determine if a page should be excluded from navigation.

        Different autodoc types have different navigation expectations:

        - **Python API pages**: INCLUDE - Users expect to navigate to individual
          modules within packages.

        - **CLI command pages**: INCLUDE - Users expect to navigate to individual
          commands like 'bengal build' or 'bengal serve'.

        - **OpenAPI endpoint pages**: EXCLUDE - Too many endpoints.
          Users typically browse by tag/category.

        - **Regular content pages**: INCLUDE - Always shown in nav.

        Args:
            page: Page to check

        Returns:
            True if page should be excluded from navigation
        """
        metadata = getattr(page, "metadata", {}) or {}
        page_type = metadata.get("type", "")

        # CLI command pages should be shown in navigation
        # Users expect to navigate to individual commands
        if page_type.startswith("cli-") or page_type == "autodoc-cli":
            return False

        # Python API pages (modules) should be shown in navigation
        # Users expect to navigate to individual modules within packages
        if page_type.startswith("python-") or page_type == "autodoc-python":
            return False

        # OpenAPI endpoint pages - exclude by default (too many endpoints)
        if page_type.startswith("openapi-") or page_type == "autodoc-rest":
            return True

        # For other autodoc indicators, use the general check as fallback
        # If it's autodoc but we couldn't determine the type, exclude it
        # Regular content pages (not autodoc) are always shown
        from bengal.utils.autodoc import is_autodoc_page

        return is_autodoc_page(page)

    @classmethod
    def _build_node_recursive(cls, section: Section, version_id: str | None, depth: int) -> NavNode:
        """Recursively build NavNode tree from sections and pages."""
        # Create node for the section itself (using its index page if available)
        node_url = getattr(section, "_path", None) or f"/{section.name}/"
        node_title = section.nav_title
        node_icon = section.icon

        node = NavNode(
            id=f"section-{section.name}",
            title=node_title,
            _path=node_url,
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

            # Skip Python autodoc pages (too granular - hundreds of classes/functions)
            # BUT include CLI command pages (users expect to navigate to commands)
            if cls._should_exclude_from_nav(page):
                continue

            # Use _path for nav tree (without baseurl) for consistent lookups
            page_url = getattr(page, "_path", None) or getattr(page, "href", "/")

            # Skip pages with the same URL as the section (they're section index content)
            # This prevents section+page collisions from autodoc-generated content
            if page_url == node_url:
                # Merge page into section node (section represents this URL)
                node.page = page
                continue

            page_node = NavNode(
                id=f"page-{page_url}",
                title=getattr(page, "nav_title", page.title),
                _path=page_url,
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
        """Wrap a NavNode with page-specific state."""
        return NavNodeProxy(node, self)


@dataclass(slots=True)
class NavNodeProxy:
    """
    Transient proxy for NavNode that injects page-specific state.

    Used during template rendering to avoid mutating the cached NavTree.

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

    _node: NavNode
    _context: NavTreeContext

    @property
    def href(self) -> str:
        """
        Get public URL with baseurl applied.

        This is the URL for template href attributes. Automatically includes
        baseurl when configured (e.g., "/bengal/docs/foo/" for GitHub Pages).

        Use this in templates: <a href="{{ item.href }}">

        For internal comparisons or lookups, use _path instead.
        """
        site_path = self._node._path  # NavNode stores site-relative path

        # Get site from page context
        site = getattr(self._context.page, "_site", None)
        if not site:
            return site_path

        # Get baseurl from config
        try:
            baseurl = (site.config.get("baseurl", "") or "").rstrip("/")
        except Exception:
            return site_path

        if not baseurl:
            return site_path

        # Ensure site_path starts with /
        if not site_path.startswith("/"):
            site_path = "/" + site_path

        # Handle absolute baseurl (e.g., https://example.com/subpath)
        if baseurl.startswith(("http://", "https://", "file://")):
            return f"{baseurl}{site_path}"

        # Path-only baseurl (e.g., /bengal)
        base_path = "/" + baseurl.lstrip("/")
        return f"{base_path}{site_path}"

    @property
    def _path(self) -> str:
        """
        Get site-relative path WITHOUT baseurl.

        This is the canonical path for internal operations:
        - Active trail detection
        - URL comparisons
        - Cache lookups

        For template href attributes, use .href instead.
        """
        return self._node._path

    @property
    def absolute_href(self) -> str:
        """
        Fully-qualified URL for meta tags and sitemaps when available.

        If baseurl is absolute, returns href. Otherwise returns href as-is
        (root-relative) since no fully-qualified site origin is configured.
        """
        return self.href

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


class NavTreeCache:
    """
    Thread-safe cache for NavTree instances.

    Memory leak prevention: Cache is limited to 20 entries. When limit is reached,
    oldest entries are evicted (FIFO). This prevents unbounded growth if many
    version_ids are created.
    """

    _trees: dict[str | None, NavTree] = {}
    _lock = threading.Lock()
    _site: Site | None = None
    _MAX_CACHE_SIZE = 20

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
                # Evict oldest entry if cache is full (prevent memory leak)
                if len(cls._trees) >= cls._MAX_CACHE_SIZE:
                    oldest_key = next(iter(cls._trees))
                    cls._trees.pop(oldest_key, None)
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
