"""
Metrics computation for Knowledge Graph.

This module handles computing overall graph metrics and individual page
connectivity statistics from the knowledge graph data structures.

Extracted from knowledge_graph.py per RFC: rfc-modularize-large-files.

Classes:
MetricsCalculator: Computes graph metrics from graph data.

Data Classes:
GraphMetrics: Summary statistics about graph structure.
PageConnectivity: Connectivity details for a single page.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.protocols import PageLike
else:
    from bengal.protocols import PageLike


@dataclass
class GraphMetrics:
    """
    Metrics about the knowledge graph structure.
    
    Attributes:
        total_pages: Total number of pages analyzed
        total_links: Total number of links between pages
        avg_connectivity: Average connectivity score per page
        hub_count: Number of hub pages (highly connected)
        leaf_count: Number of leaf pages (low connectivity)
        orphan_count: Number of orphaned pages (no connections at all)
        
    """

    total_pages: int
    total_links: int
    avg_connectivity: float
    hub_count: int
    leaf_count: int
    orphan_count: int


@dataclass
class PageConnectivity:
    """
    Connectivity information for a single page.
    
    Attributes:
        page: The page object
        incoming_refs: Number of incoming references
        outgoing_refs: Number of outgoing references
        connectivity_score: Total connectivity (incoming + outgoing)
        is_hub: True if page has many incoming references
        is_leaf: True if page has few connections
        is_orphan: True if page has no connections at all
        
    """

    page: PageLike
    incoming_refs: int
    outgoing_refs: int
    connectivity_score: int
    is_hub: bool
    is_leaf: bool
    is_orphan: bool


class MetricsCalculator:
    """
    Computes metrics from knowledge graph data structures.
    
    Takes the populated graph data from GraphBuilder and computes
    overall statistics and per-page connectivity metrics.
    
    Attributes:
        incoming_refs: Dict mapping pages to incoming reference counts
        outgoing_refs: Dict mapping pages to sets of target pages
        hub_threshold: Minimum incoming refs to be considered a hub
        leaf_threshold: Maximum connectivity to be considered a leaf
    
    Example:
            >>> calculator = MetricsCalculator(
            ...     incoming_refs=builder.incoming_refs,
            ...     outgoing_refs=builder.outgoing_refs,
            ...     analysis_pages=builder.get_analysis_pages(),
            ...     hub_threshold=10,
            ...     leaf_threshold=2,
            ... )
            >>> metrics = calculator.compute_metrics()
            >>> connectivity = calculator.get_connectivity(some_page)
        
    """

    def __init__(
        self,
        incoming_refs: dict[PageLike, float],
        outgoing_refs: dict[PageLike, set[PageLike]],
        analysis_pages: list[PageLike],
        hub_threshold: int = 10,
        leaf_threshold: int = 2,
    ):
        """
        Initialize the metrics calculator.

        Args:
            incoming_refs: Dict mapping pages to incoming reference counts
            outgoing_refs: Dict mapping pages to sets of target pages
            analysis_pages: List of pages to analyze
            hub_threshold: Minimum incoming refs to be considered a hub
            leaf_threshold: Maximum connectivity to be considered a leaf
        """
        self.incoming_refs = incoming_refs
        self.outgoing_refs = outgoing_refs
        self.analysis_pages = analysis_pages
        self.hub_threshold = hub_threshold
        self.leaf_threshold = leaf_threshold

    def compute_metrics(self) -> GraphMetrics:
        """
        Compute overall graph metrics.

        Returns:
            GraphMetrics with summary statistics
        """
        total_pages = len(self.analysis_pages)
        total_links = sum(len(targets) for targets in self.outgoing_refs.values())

        hub_count = 0
        leaf_count = 0
        orphan_count = 0
        total_connectivity = 0.0

        for page in self.analysis_pages:
            incoming = self.incoming_refs.get(page, 0)
            outgoing = len(self.outgoing_refs.get(page, set()))
            connectivity = incoming + outgoing

            total_connectivity += connectivity

            if incoming >= self.hub_threshold:
                hub_count += 1

            if connectivity <= self.leaf_threshold:
                leaf_count += 1

            if incoming == 0 and outgoing == 0:
                orphan_count += 1

        avg_connectivity = total_connectivity / total_pages if total_pages > 0 else 0

        return GraphMetrics(
            total_pages=total_pages,
            total_links=total_links,
            avg_connectivity=avg_connectivity,
            hub_count=hub_count,
            leaf_count=leaf_count,
            orphan_count=orphan_count,
        )

    def get_connectivity(self, page: PageLike) -> PageConnectivity:
        """
        Get connectivity information for a specific page.

        Args:
            page: Page to analyze

        Returns:
            PageConnectivity with detailed metrics
        """
        incoming = int(self.incoming_refs.get(page, 0))
        outgoing = len(self.outgoing_refs.get(page, set()))
        connectivity = incoming + outgoing

        return PageConnectivity(
            page=page,
            incoming_refs=incoming,
            outgoing_refs=outgoing,
            connectivity_score=connectivity,
            is_hub=incoming >= self.hub_threshold,
            is_leaf=connectivity <= self.leaf_threshold,
            is_orphan=incoming == 0 and outgoing == 0,
        )

    def get_connectivity_score(self, page: PageLike) -> int:
        """
        Get total connectivity score for a page.

        Connectivity = incoming_refs + outgoing_refs

        Args:
            page: Page to analyze

        Returns:
            Connectivity score (higher = more connected)
        """
        incoming = self.incoming_refs.get(page, 0)
        outgoing = len(self.outgoing_refs.get(page, set()))
        return int(incoming + outgoing)
