"""
Analysis module for Bengal SSG.

Provides comprehensive tools for analyzing site structure, content relationships,
and navigation patterns. The analysis suite helps optimize site architecture,
improve internal linking, and understand content organization.

Sub-Packages:
    graph/: Graph-based page relationship analysis
        - KnowledgeGraph: Central graph representation
        - GraphAnalyzer: Structural analysis (hubs, leaves, orphans)
        - GraphReporter: Human-readable insights
        - GraphVisualizer: D3.js visualization
        - PageRank: Page importance scoring
        - CommunityDetection: Topical clustering
    links/: Link analysis and suggestions
        - LinkSuggestionEngine: Cross-linking recommendations
        - LinkPatterns: Link pattern detection
        - LinkTypes: Link classification
    performance/: Build performance analysis
        - PerformanceAdvisor: Optimization tips
        - PathAnalyzer: Centrality metrics

Example:
    >>> from bengal.analysis import KnowledgeGraph, GraphAnalyzer
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> # Get hub pages
    >>> hubs = graph.get_hubs(threshold=10)
    >>> # Find orphaned pages
    >>> orphans = graph.get_orphans()
    >>> # Compute PageRank
    >>> results = graph.compute_pagerank()
    >>> top_pages = results.get_top_pages(10)

See Also:
- bengal/analysis/graph/: Graph analysis subpackage
- bengal/analysis/links/: Link analysis subpackage
- bengal/analysis/performance/: Performance analysis subpackage

"""

# Re-export from graph subpackage for convenience
from bengal.analysis.graph import (
    GraphAnalyzer,
    GraphBuilder,
    GraphMetrics,
    GraphReporter,
    GraphVisualizer,
    KnowledgeGraph,
    MetricsCalculator,
    PageConnectivity,
)

__all__ = [
    "GraphAnalyzer",
    "GraphBuilder",
    "GraphMetrics",
    "GraphReporter",
    "GraphVisualizer",
    "KnowledgeGraph",
    "MetricsCalculator",
    "PageConnectivity",
]
