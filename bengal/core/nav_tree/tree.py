"""
Pre-computed navigation tree with O(1) URL lookups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.core.diagnostics import emit
from bengal.core.utils.sorting import DEFAULT_WEIGHT

from .node import NavNode

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.protocols import PageLike, SectionLike, SiteLike

    from .context import NavTreeContext


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
                    emit(
                        self,
                        "warning",
                        "nav_url_collision",
                        url=url,
                        existing_id=existing.id,
                        existing_type="section" if existing_is_section else "page",
                        new_id=node.id,
                        new_type="section" if new_is_section else "page",
                        hint="Check for duplicate slugs or conflicting autodoc output",
                    )
            self._flat_nodes[url] = node
        self._urls = set(self._flat_nodes.keys())

    @property
    def flat_nodes(self) -> dict[str, NavNode]:
        """Dictionary of URL -> NavNode for all nodes in the tree.

        Cost: O(1) — returns cached dict reference.
        """
        return self._flat_nodes

    @property
    def urls(self) -> set[str]:
        """Set of all URLs present in this navigation tree.

        Cost: O(1) — returns cached set reference.
        """
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
        from .context import NavTreeContext

        return NavTreeContext(self, page, mark_active_trail=mark_active_trail, root_node=root_node)

    @classmethod
    def build(cls, site: SiteLike, version_id: str | None = None) -> NavTree:
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
    def _should_exclude_from_nav(cls, page: PageLike) -> bool:
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
    def _build_node_recursive(
        cls, section: SectionLike, version_id: str | None, depth: int
    ) -> NavNode:
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
            weight=section.metadata.get("weight", DEFAULT_WEIGHT),
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
                weight=page.metadata.get("weight", DEFAULT_WEIGHT),
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
