"""
Graph analysis subsystem for Bengal SSG.

This package provides graph-based analysis of page relationships including
knowledge graph construction, metrics calculation, visualization, and
community detection.

Components:
KnowledgeGraph: Central graph representation of page connections
GraphBuilder: Constructs knowledge graphs from site pages
GraphAnalyzer: Structural analysis (hubs, leaves, orphans, layers)
GraphMetrics: Connectivity metrics and PageConnectivity dataclass
GraphReporter: Human-readable insights and recommendations
GraphVisualizer: Interactive D3.js graph visualization
CommunityDetection: Louvain algorithm for topical clustering
PageRank: Page importance scoring based on link structure

Related:
- bengal/analysis/links/: Link suggestion and pattern analysis
- bengal/analysis/performance/: Performance analysis
- bengal/orchestration/streaming.py: Uses graph for build ordering

"""

from bengal.analysis.graph.analyzer import GraphAnalyzer
from bengal.analysis.graph.builder import GraphBuilder
from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
from bengal.analysis.graph.metrics import GraphMetrics, MetricsCalculator, PageConnectivity
from bengal.analysis.graph.reporter import GraphReporter
from bengal.analysis.graph.visualizer import GraphVisualizer

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
