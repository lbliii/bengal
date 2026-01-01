"""
Navigation Scaffold Cache.

Provides cached static nav HTML generation without per-page active state.
The scaffold is rendered once per scope (section root + version) and reused
across all pages in that scope. Active state is applied client-side via JS.

This implements Phase 2 of the docs-nav rendering optimization RFC:
- Scaffold: Full nav tree HTML without active/trail classes
- Overlay: Client-side JS applies active state based on data attributes

Performance:
    - Scaffold is generated once per (site, version_id, root_url) tuple
    - Per-page rendering cost drops from O(N_nav) to O(1)
    - JS overlay is O(depth) for active trail application

Usage in templates:
    {% set scaffold = get_nav_scaffold(page, root_section=root_section) %}
    <nav data-current-path="{{ page._path }}"
         data-active-trail="{{ scaffold.active_trail_json }}">
      {{ scaffold.html | safe }}
    </nav>
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal.core.nav_tree import NavTreeCache
from bengal.utils.concurrent_locks import PerKeyLockManager
from bengal.utils.lru_cache import LRUCache

if TYPE_CHECKING:
    from bengal.core.nav_tree import NavTree, NavTreeNode
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


@dataclass
class NavScaffold:
    """
    Pre-rendered navigation scaffold with active trail data.

    The scaffold HTML is static (no active classes) and can be cached.
    Active state is applied client-side using the provided trail data.

    Attributes:
        html: Pre-rendered HTML of the navigation tree (static, no active state)
        active_trail: List of URLs in the active trail (current page to root)
        current_path: URL of the current page
        active_trail_json: JSON-encoded active trail for data attribute
    """

    html: str
    active_trail: list[str]
    current_path: str

    @property
    def active_trail_json(self) -> str:
        """JSON-encoded active trail for embedding in data attribute."""
        return json.dumps(self.active_trail)


class NavScaffoldCache:
    """
    Thread-safe LRU cache for pre-rendered nav scaffold HTML.

    Uses per-scaffold locking to prevent duplicate renders when multiple
    threads request the same scaffold simultaneously. Different scaffolds
    can still be rendered in parallel.

    Caches scaffold HTML per (site, version_id, root_url) scope.
    Invalidated when site object changes (new build session).

    Thread Safety:
        - Uses shared LRUCache with internal RLock
        - _render_locks: Per-scaffold locks to serialize renders for SAME scope
        - Different scaffolds render in parallel (no contention)
    """

    _cache: LRUCache[str, str] = LRUCache(maxsize=50, name="nav_scaffold")
    _lock = threading.Lock()
    _render_locks = PerKeyLockManager()  # Per-scaffold render serialization
    _site: Site | None = None

    @classmethod
    def _make_key(cls, version_id: str | None, root_url: str) -> str:
        """Make a string cache key from version_id and root_url."""
        return f"{version_id or '__default__'}:{root_url}"

    @classmethod
    def get_html(
        cls,
        site: Site,
        version_id: str | None,
        root_url: str,
        renderer: object,
    ) -> str:
        """
        Get cached scaffold HTML or render and cache it.

        Thread-safe: Multiple threads requesting the same scaffold will serialize
        on the render, with only one thread doing the actual work. Different
        scaffolds can be rendered in parallel.

        Args:
            site: Site instance
            version_id: Optional version ID for versioned docs
            root_url: Root section URL (scope boundary)
            renderer: Callable that renders the scaffold HTML

        Returns:
            Pre-rendered scaffold HTML (static, no active state)
        """
        cache_key = cls._make_key(version_id, root_url)

        # 1. Quick cache check (includes site change detection)
        with cls._lock:
            # Full invalidation if site object changed (new build session)
            if cls._site is not site:
                cls._cache.clear()
                cls._render_locks.clear()
                cls._site = site

        # Check cache first (LRU update happens inside get)
        cached = cls._cache.get(cache_key)
        if cached is not None:
            return cached

        # 2. Serialize renders for SAME scaffold (different scaffolds render in parallel)
        with cls._render_locks.get_lock(cache_key):
            # Double-check: another thread may have rendered while we waited
            cached = cls._cache.get(cache_key)
            if cached is not None:
                return cached

            # 3. Render outside cache lock (expensive operation)
            html = renderer()

            # 4. Store result (LRU eviction handled by LRUCache)
            cls._cache.set(cache_key, html)
            return html

    @classmethod
    def invalidate(cls, version_id: str | None = None, root_url: str | None = None) -> None:
        """Invalidate cached scaffolds."""
        if version_id is None and root_url is None:
            cls._cache.clear()
            cls._render_locks.clear()
        else:
            # For selective invalidation, we need to check keys
            # Since LRUCache doesn't expose iteration, clear matching keys by checking
            keys_to_remove = []
            for key in cls._cache:
                parts = key.split(":", 1)
                if len(parts) == 2:
                    key_version = None if parts[0] == "__default__" else parts[0]
                    key_root = parts[1]
                    if (version_id is None or key_version == version_id) and (
                        root_url is None or key_root == root_url
                    ):
                        keys_to_remove.append(key)
            for key in keys_to_remove:
                cls._cache.delete(key)

    @classmethod
    def clear_locks(cls) -> None:
        """
        Clear all render locks.

        Call this at the end of a build session to reset lock state.
        Safe to call when no threads are actively rendering.
        """
        cls._render_locks.clear()

    @classmethod
    def stats(cls) -> dict[str, Any]:
        """Get cache statistics."""
        return cls._cache.stats()


class ScaffoldNodeProxy:
    """
    Proxy for NavNode that always returns False for active state.

    Used when rendering the scaffold to produce static HTML without
    per-page active classes.

    PERFORMANCE: Properties are cached to avoid repeated computation.
    """

    __slots__ = ("_node", "_context", "_href_cached", "_children_cached")

    def __init__(self, node: NavTreeNode, context: ScaffoldContext) -> None:
        self._node = node
        self._context = context
        self._href_cached: str | None = None
        self._children_cached: list[ScaffoldNodeProxy] | None = None

    @property
    def href(self) -> str:
        """Get public URL with baseurl applied (cached)."""
        if self._href_cached is not None:
            return self._href_cached

        site_path = self._node._path

        # Get site from page context
        site = getattr(self._context.page, "_site", None)
        if not site:
            self._href_cached = site_path
            return site_path

        try:
            baseurl = (site.config.get("baseurl", "") or "").rstrip("/")
        except Exception:
            self._href_cached = site_path
            return site_path

        if not baseurl:
            self._href_cached = site_path
            return site_path

        if not site_path.startswith("/"):
            site_path = "/" + site_path

        if baseurl.startswith(("http://", "https://", "file://")):
            self._href_cached = f"{baseurl}{site_path}"
        else:
            base_path = "/" + baseurl.lstrip("/")
            self._href_cached = f"{base_path}{site_path}"

        return self._href_cached

    @property
    def _path(self) -> str:
        """Site-relative path (for data attributes)."""
        return self._node._path

    @property
    def is_current(self) -> bool:
        """Always False in scaffold mode."""
        return False

    @property
    def is_in_trail(self) -> bool:
        """Always False in scaffold mode."""
        return False

    @property
    def is_expanded(self) -> bool:
        """Always False in scaffold mode - JS will expand based on trail."""
        return False

    @property
    def is_section(self) -> bool:
        """True if this node represents a section."""
        return self._node.section is not None

    @property
    def children(self) -> list[ScaffoldNodeProxy]:
        """Wrap children with scaffold proxy (cached)."""
        if self._children_cached is not None:
            return self._children_cached
        self._children_cached = [
            ScaffoldNodeProxy(child, self._context) for child in self._node.children
        ]
        return self._children_cached

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the underlying node."""
        if name in ("href", "_path"):
            return self._node._path
        return getattr(self._node, name)

    def __getitem__(self, key: str) -> Any:
        """Dict-like access for templates."""
        if key == "href":
            return self.href
        if key == "_path":
            return self._path
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
        """Safe dict-like access."""
        try:
            return self[key]
        except KeyError:
            return default


class ScaffoldContext:
    """
    Context that wraps NavTree for scaffold rendering.

    Returns ScaffoldNodeProxy instances that always have inactive state,
    producing static HTML that can be cached and reused.
    """

    def __init__(self, tree: NavTree, page: Page, root_node: NavTreeNode | None = None):
        self.tree = tree
        self.page = page
        self._root_node = root_node or tree.root

    def __contains__(self, key: str) -> bool:
        if key == "root":
            return True
        return hasattr(self.tree, key)

    def __getitem__(self, key: str) -> Any:
        if key == "root":
            return self._wrap_node(self._root_node)
        return getattr(self.tree, key)

    def _wrap_node(self, node: NavTreeNode) -> ScaffoldNodeProxy:
        return ScaffoldNodeProxy(node, self)


def get_nav_scaffold_context(
    page: Page,
    root_section: Section | None = None,
) -> ScaffoldContext:
    """
    Get a scaffold context for static nav rendering.

    The scaffold context returns proxy nodes that always have inactive state,
    producing HTML that can be cached across pages.

    Args:
        page: Current page (used for site/version context)
        root_section: Optional section to scope navigation to

    Returns:
        ScaffoldContext with static (inactive) node proxies
    """
    site = getattr(page, "_site", None)
    if site is None:
        from bengal.errors import BengalRenderingError, ErrorCode

        msg = "Page has no site reference for scaffold generation."
        raise BengalRenderingError(msg, code=ErrorCode.R008)

    version_id = None
    if getattr(site, "versioning_enabled", False):
        version_id = getattr(page, "version", None)

    tree = NavTreeCache.get(site, version_id)
    root_node = None
    if root_section is not None:
        root_url = getattr(root_section, "_path", None) or f"/{root_section.name}/"
        root_node = tree.find(root_url)

    return ScaffoldContext(tree, page, root_node=root_node)


def get_active_trail(page: Page) -> list[str]:
    """
    Compute the active trail URLs for a page.

    Returns a list of URLs from the current page up to the root,
    used for client-side active state application.

    Args:
        page: Current page

    Returns:
        List of URLs in the active trail (current page first)
    """
    trail: list[str] = []

    # Add current page URL
    current_url = getattr(page, "_path", None) or getattr(page, "href", "/")
    trail.append(current_url)

    # Walk up from current section
    section = getattr(page, "_section", None)
    while section:
        section_url = getattr(section, "_path", None) or f"/{section.name}/"
        if section_url not in trail:
            trail.append(section_url)
        section = section.parent

    return trail


def render_scaffold_html(
    page: Page,
    root_section: Section | None = None,
    jinja_env: Any | None = None,
) -> str:
    """
    Render scaffold HTML for a scope (internal helper).

    This renders the tree-only template to a string.
    Called by get_cached_scaffold_html on cache miss.

    Args:
        page: Page for context (site, version)
        root_section: Optional root section for scoping
        jinja_env: Jinja2 environment (required for rendering)

    Returns:
        Rendered HTML string
    """
    if jinja_env is None:
        return ""

    try:
        template = jinja_env.get_template("partials/docs-nav-tree-only.html")
        scaffold_ctx = get_nav_scaffold_context(page, root_section=root_section)

        # Build minimal context for rendering
        context = {
            "scaffold_ctx": scaffold_ctx,
            "root_section": root_section,
            "show_nav_icons": True,
        }

        return template.render(**context)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to render scaffold: {e}")
        return ""


def get_cached_scaffold_html(
    page: Page,
    root_section: Section | None = None,
    jinja_env: Any | None = None,
) -> str:
    """
    Get cached scaffold HTML for a scope.

    This is the main function for getting pre-rendered scaffold HTML.
    On first call for a scope, renders and caches the HTML.
    Subsequent calls return the cached HTML.

    Args:
        page: Current page
        root_section: Optional root section for scoped navigation
        jinja_env: Jinja2 environment (from template globals)

    Returns:
        Cached HTML string for the scaffold tree

    Example (in template):
        {% set scaffold_html = get_cached_scaffold_html(page, root_section, _env) %}
        {{ scaffold_html | safe }}
    """
    site = getattr(page, "_site", None)
    if site is None:
        return ""

    version_id = None
    if getattr(site, "versioning_enabled", False):
        version_id = getattr(page, "version", None)

    # Compute scope key
    root_url = "/"
    if root_section is not None:
        root_url = getattr(root_section, "_path", None) or f"/{root_section.name}/"

    # Check cache
    def renderer() -> str:
        return render_scaffold_html(page, root_section, jinja_env)

    return NavScaffoldCache.get_html(site, version_id, root_url, renderer)


def get_nav_scaffold(
    page: Page,
    root_section: Section | None = None,
) -> NavScaffold:
    """
    Get navigation scaffold with active trail data.

    This is the main entry point for scaffold-based nav rendering.
    Returns a NavScaffold with per-page active trail data.

    Note: For cached HTML, use get_cached_scaffold_html() instead.
    This function provides trail data for JS active state application.

    Args:
        page: Current page
        root_section: Optional section to scope navigation to

    Returns:
        NavScaffold with active trail data

    Example:
        {% set scaffold = get_nav_scaffold(page, root_section=root_section) %}
        <nav class="docs-nav"
             data-bengal="docs-nav-scaffold"
             data-current-path="{{ page._path }}"
             data-active-trail="{{ scaffold.active_trail_json }}">
          {{ get_cached_scaffold_html(page, root_section, _env) | safe }}
        </nav>
    """
    current_path = getattr(page, "_path", None) or getattr(page, "href", "/")
    active_trail = get_active_trail(page)

    return NavScaffold(
        html="",  # Use get_cached_scaffold_html() for HTML
        active_trail=active_trail,
        current_path=current_path,
    )
