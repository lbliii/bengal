"""
Analysis module for Bengal SSG.

Provides comprehensive tools for analyzing site structure, content relationships,
and navigation patterns. The analysis suite helps optimize site architecture,
improve internal linking, and understand content organization.

Core Components:
    KnowledgeGraph: Central graph representation of page connections.
        Builds a connectivity graph from internal links, taxonomies,
        related posts, and menu items. Foundation for all analysis.

    GraphAnalyzer: Structural analysis of the knowledge graph.
        Identifies hubs (highly connected pages), leaves (isolated pages),
        orphans (no connections), and partitions pages into layers for
        streaming builds.

    GraphReporter: Human-readable insights and recommendations.
        Generates statistics, SEO insights, content gap detection,
        and actionable recommendations for improving site structure.

    GraphVisualizer: Interactive D3.js graph visualization.
        Creates standalone HTML files with force-directed layouts,
        search/filtering, and Obsidian-style graph exploration.

Analysis Capabilities:
    - PageRank: Compute page importance scores based on link structure
    - Community Detection: Discover topical clusters using Louvain algorithm
    - Path Analysis: Compute centrality metrics (betweenness, closeness)
    - Link Suggestions: AI-powered cross-linking recommendations
    - Performance Advisor: Build performance analysis and optimization tips

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
    - bengal/analysis/knowledge_graph.py: Main graph implementation
    - bengal/analysis/page_rank.py: PageRank algorithm
    - bengal/analysis/community_detection.py: Louvain community detection
    - bengal/analysis/path_analysis.py: Centrality metrics
    - bengal/analysis/link_suggestions.py: Cross-linking recommendations
"""

from __future__ import annotations

from .graph_analysis import GraphAnalyzer
from .graph_reporting import GraphReporter
from .graph_visualizer import GraphVisualizer
from .knowledge_graph import KnowledgeGraph

__all__ = ["GraphAnalyzer", "GraphReporter", "GraphVisualizer", "KnowledgeGraph"]
