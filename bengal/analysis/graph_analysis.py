"""
Graph analysis module for Bengal SSG.

Provides structural analysis of knowledge graphs to understand site architecture
and optimize build performance. The analyzer identifies important pages (hubs),
isolated content (leaves/orphans), and partitions pages into layers for
efficient streaming builds.

Key Concepts:
    - Connectivity Score: Sum of incoming and outgoing references for a page
    - Hubs: Pages with many incoming references (index pages, popular articles)
    - Leaves: Pages with few total connections (blog posts, changelog entries)
    - Orphans: Pages with zero connections (forgotten or draft content)
    - Layers: Page partitions for hub-first streaming (hubs → mid-tier → leaves)

Classes:
    GraphAnalyzer: Main analyzer that delegates from KnowledgeGraph

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> # Analysis is typically accessed via KnowledgeGraph methods
    >>> hubs = graph.get_hubs(threshold=10)
    >>> orphans = graph.get_orphans()
    >>> layers = graph.get_layers()

See Also:
    - bengal/analysis/knowledge_graph.py: Main graph coordinator
    - bengal/analysis/results.py: PageLayers result dataclass
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph, PageConnectivity
    from bengal.analysis.results import PageLayers
    from bengal.core.page import Page


class GraphAnalyzer:
    """
    Analyzes knowledge graph structure for page connectivity insights.

    Provides methods for:
    - Connectivity scoring (incoming + outgoing refs)
    - Hub detection (highly connected pages)
    - Leaf detection (low connectivity pages)
    - Orphan detection (no connections)
    - Layer partitioning (for hub-first streaming builds)

    Example:
        >>> from bengal.analysis import KnowledgeGraph
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> analyzer = GraphAnalyzer(graph)
        >>> hubs = analyzer.get_hubs(threshold=10)
        >>> orphans = analyzer.get_orphans()
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        """
        Initialize the graph analyzer.

        Args:
            graph: Knowledge graph to analyze (must be built)
        """
        self._graph = graph

    def _ensure_built(self) -> None:
        """Verify the graph has been built before analysis."""
        if not self._graph._built:
            raise RuntimeError("KnowledgeGraph is not built. Call .build() before analysis.")

    def get_connectivity(self, page: Page) -> PageConnectivity:
        """
        Get connectivity information for a specific page.

        Args:
            page: Page to analyze

        Returns:
            PageConnectivity with detailed metrics

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        from bengal.analysis.knowledge_graph import PageConnectivity

        self._ensure_built()

        incoming = self._graph.incoming_refs[page]
        outgoing = len(self._graph.outgoing_refs[page])
        connectivity = incoming + outgoing

        return PageConnectivity(
            page=page,
            incoming_refs=incoming,
            outgoing_refs=outgoing,
            connectivity_score=connectivity,
            is_hub=incoming >= self._graph.hub_threshold,
            is_leaf=connectivity <= self._graph.leaf_threshold,
            is_orphan=(incoming == 0 and outgoing == 0),
        )

    def get_connectivity_score(self, page: Page) -> int:
        """
        Get total connectivity score for a page.

        Connectivity = incoming_refs + outgoing_refs

        Args:
            page: Page to analyze

        Returns:
            Connectivity score (higher = more connected)

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        self._ensure_built()
        return self._graph.incoming_refs[page] + len(self._graph.outgoing_refs[page])

    def get_hubs(self, threshold: int | None = None) -> list[Page]:
        """
        Get hub pages (highly connected pages).

        Hubs are pages with many incoming references. These are typically:
        - Index pages
        - Popular articles
        - Core documentation

        Args:
            threshold: Minimum incoming refs (defaults to graph.hub_threshold)

        Returns:
            List of hub pages sorted by incoming references (descending)

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        self._ensure_built()

        threshold = threshold if threshold is not None else self._graph.hub_threshold

        hubs = [
            page for page in self._graph.site.pages if self._graph.incoming_refs[page] >= threshold
        ]

        # Sort by incoming refs (descending)
        hubs.sort(key=lambda p: self._graph.incoming_refs[p], reverse=True)

        return hubs

    def get_leaves(self, threshold: int | None = None) -> list[Page]:
        """
        Get leaf pages (low connectivity pages).

        Leaves are pages with few connections. These are typically:
        - One-off blog posts
        - Changelog entries
        - Niche content

        Args:
            threshold: Maximum connectivity (defaults to graph.leaf_threshold)

        Returns:
            List of leaf pages sorted by connectivity (ascending)

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        self._ensure_built()

        threshold = threshold if threshold is not None else self._graph.leaf_threshold

        leaves = [
            page
            for page in self._graph.site.pages
            if self.get_connectivity_score(page) <= threshold
        ]

        # Sort by connectivity (ascending)
        leaves.sort(key=self.get_connectivity_score)

        return leaves

    def get_orphans(self) -> list[Page]:
        """
        Get orphaned pages (no connections at all).

        Orphans are pages with no incoming or outgoing references. These might be:
        - Forgotten content
        - Draft pages
        - Pages that should be linked from navigation

        Returns:
            List of orphaned pages sorted by slug

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        self._ensure_built()

        # Get analysis pages (already excludes autodoc)
        analysis_pages = self._graph.get_analysis_pages()
        orphans = [
            page
            for page in analysis_pages
            if self._graph.incoming_refs[page] == 0
            and len(self._graph.outgoing_refs[page]) == 0
            and not page.metadata.get("_generated")  # Exclude generated pages
        ]

        # Sort by slug for consistent ordering
        orphans.sort(key=lambda p: p.slug)

        return orphans

    def get_layers(self) -> PageLayers:
        """
        Partition pages into three layers by connectivity.

        Layers enable hub-first streaming builds:
        - Layer 0 (Hubs): High connectivity, process first, keep in memory
        - Layer 1 (Mid-tier): Medium connectivity, batch processing
        - Layer 2 (Leaves): Low connectivity, stream and release

        Returns:
            PageLayers dataclass with hubs, mid_tier, and leaves attributes
            (supports tuple unpacking for backward compatibility)

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        from bengal.analysis.results import PageLayers

        self._ensure_built()

        # Sort all pages by connectivity (descending)
        sorted_pages = sorted(
            self._graph.site.pages,
            key=self.get_connectivity_score,
            reverse=True,
        )

        total = len(sorted_pages)

        # Layer thresholds (configurable)
        hub_cutoff = int(total * 0.10)  # Top 10%
        mid_cutoff = int(total * 0.40)  # Next 30%

        hubs = sorted_pages[:hub_cutoff]
        mid_tier = sorted_pages[hub_cutoff:mid_cutoff]
        leaves = sorted_pages[mid_cutoff:]

        return PageLayers(hubs=hubs, mid_tier=mid_tier, leaves=leaves)
