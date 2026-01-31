"""
Link analysis subsystem for Bengal SSG.

This package provides link-related analysis including suggestions for
cross-linking, link pattern detection, and link type classification.

Components:
LinkSuggestionEngine: AI-powered cross-linking recommendations
LinkPatterns: Link pattern detection and analysis
LinkType: Link type classification (internal, external, anchor, etc.)
LinkMetrics: Link quality and distribution metrics

Related:
- bengal/analysis/graph/: Graph-based page relationship analysis
- bengal/health/validators/links.py: Link validation

"""

from bengal.analysis.links.patterns import LinkPatternAnalyzer, LinkPatternReport
from bengal.analysis.links.suggestions import LinkSuggestionEngine, LinkSuggestionResults
from bengal.analysis.links.types import LinkMetrics, LinkType

__all__ = [
    "LinkMetrics",
    "LinkPatternAnalyzer",
    "LinkPatternReport",
    "LinkSuggestionEngine",
    "LinkSuggestionResults",
    "LinkType",
]
