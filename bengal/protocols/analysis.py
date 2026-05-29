"""Protocol definitions for analysis modules.

Provides protocol definitions for analysis components to break circular
imports between knowledge_graph and analysis modules.

Protocols:
    KnowledgeGraphProtocol: Protocol for knowledge graph access

Note:
    This module was created to fix circular import cycles between:
    - knowledge_graph ↔ graph_analysis
    - knowledge_graph ↔ graph_reporting
    - graph_reporting ↔ path_analysis

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.analysis.links.types import LinkMetrics, LinkType
    from bengal.core.site import Site
    from bengal.protocols.core import PageLike


@runtime_checkable
class KnowledgeGraphProtocol(Protocol):
    """Protocol for knowledge graph access.

    Defines the interface that analysis modules can depend on without
    importing the concrete KnowledgeGraph class. This breaks circular
    imports while maintaining type safety.

    Example:
        def analyze(graph: KnowledgeGraphProtocol) -> dict:
            hubs = graph.get_hubs()
            orphans = graph.get_orphans()
            return {"hubs": len(hubs), "orphans": len(orphans)}

    """

    # Core data structures
    site: Site
    incoming_refs: dict[PageLike, float]
    outgoing_refs: dict[PageLike, set[PageLike]]
    link_metrics: dict[PageLike, LinkMetrics]
    link_types: dict[tuple[PageLike | None, PageLike], LinkType]
    incoming_edges: dict[PageLike, list[PageLike]]

    # Configuration
    hub_threshold: int
    leaf_threshold: int
    exclude_autodoc: bool

    # State
    _built: bool

    # Core methods
    def build(self) -> None:
        """Build the knowledge graph from site data."""
        ...

    def get_hubs(self, threshold: int | None = None) -> list[PageLike]:
        """Get pages with high incoming references (hubs).

        Args:
            threshold: Minimum incoming refs (defaults to hub_threshold)

        Returns:
            List of hub pages
        """
        ...

    def get_orphans(self) -> list[PageLike]:
        """Get pages with no incoming references.

        Returns:
            List of orphaned pages
        """
        ...

    def get_leaves(self, threshold: int | None = None) -> list[PageLike]:
        """Get pages with low connectivity (leaf nodes).

        Args:
            threshold: Maximum connectivity (defaults to leaf_threshold)

        Returns:
            List of leaf pages
        """
        ...

    def get_bridges(self) -> list[PageLike]:
        """Get pages that connect different parts of the graph.

        Returns:
            List of bridge pages
        """
        ...

    def get_page_connectivity(self, page: PageLike) -> tuple[float, str]:
        """Get connectivity score and level for a page.

        Args:
            page: Page to analyze

        Returns:
            Tuple of (score, level_name)
        """
        ...

    def get_incoming_links(self, page: PageLike) -> list[PageLike]:
        """Get pages that link TO the given page.

        Args:
            page: Target page

        Returns:
            List of pages linking to this page
        """
        ...

    def get_outgoing_links(self, page: PageLike) -> set[PageLike]:
        """Get pages that this page links TO.

        Args:
            page: Source page

        Returns:
            Set of pages this page links to
        """
        ...

    # Formatting
    def format_stats(self) -> str:
        """Format graph statistics as human-readable string.

        Returns:
            Formatted stats string
        """
        ...
