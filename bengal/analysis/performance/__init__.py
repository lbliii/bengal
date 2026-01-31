"""
Performance analysis subsystem for Bengal SSG.

This package provides build performance analysis, path centrality metrics,
and optimization recommendations.

Components:
PerformanceAdvisor: Build performance analysis and optimization tips
PathAnalyzer: Centrality metrics (betweenness, closeness)

Related:
- bengal/analysis/graph/: Graph structure analysis
- bengal/orchestration/summary.py: Uses for build summaries

"""

from __future__ import annotations

from bengal.analysis.performance.advisor import PerformanceAdvisor, analyze_build
from bengal.analysis.performance.path_analysis import PathAnalysisResults, PathAnalyzer

__all__ = [
    "PathAnalysisResults",
    "PathAnalyzer",
    "PerformanceAdvisor",
    "analyze_build",
]
