"""
Feature detection for CSS optimization.

Detects features that require specific CSS from page content:
- Mermaid diagrams (```mermaid code blocks)
- Data tables (tabulator initialization)
- Graph visualizations (graph config)

This runs during content discovery to populate site.features_detected,
which the CSSOptimizer uses to include only necessary CSS.

Usage:
    from bengal.orchestration.feature_detector import FeatureDetector

    detector = FeatureDetector()
    features = detector.detect_features_in_content(content)
    # Returns: {"mermaid", "data_tables"} etc.

See Also:
    - bengal/orchestration/css_optimizer.py: Consumes detected features
    - plan/drafted/rfc-css-tree-shaking.md: Design rationale
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.protocols import PageLike


class FeatureDetector:
    """
    Detects CSS-requiring features in page content.

    This class analyzes page content to find features that need
    specific CSS files (mermaid, data_tables, etc.).

    Thread-safe: Can be used from parallel page parsing.

    Example:
        detector = FeatureDetector()
        features = detector.detect_features_in_content(page._source)

    """

    # Feature detection patterns
    PATTERNS: dict[str, re.Pattern[str]] = {
        # Mermaid diagram code blocks
        "mermaid": re.compile(r"```mermaid", re.IGNORECASE),
        # Data tables (tabulator)
        "data_tables": re.compile(
            r"(tabulator|DataTable|data-table|\.datatable)",
            re.IGNORECASE,
        ),
        # Graph/network visualization
        "graph": re.compile(
            r"(graph[-_]?vis|d3[-.]|force[-_]?graph|network[-_]?graph)", re.IGNORECASE
        ),
        # Interactive widgets
        "interactive": re.compile(r"(interactive|widget|marimo)", re.IGNORECASE),
        # Holographic card effects
        "holo_cards": re.compile(r"(holo[-_]?card|holographic)", re.IGNORECASE),
    }

    # Directive-based feature patterns (Bengal directives)
    DIRECTIVE_PATTERNS: dict[str, re.Pattern[str]] = {
        "mermaid": re.compile(r":::\{mermaid\}", re.IGNORECASE),
        "data_tables": re.compile(r":::\{(datatable|tabulator)\}", re.IGNORECASE),
    }

    def detect_features_in_content(self, content: str) -> set[str]:
        """
        Detect features in page content.

        Analyzes content for patterns that indicate specific CSS is needed.

        Args:
            content: Raw markdown content

        Returns:
            Set of detected feature names
        """
        features: set[str] = set()

        if not content:
            return features

        # Check content patterns
        for feature, pattern in self.PATTERNS.items():
            if pattern.search(content):
                features.add(feature)

        # Check directive patterns
        for feature, pattern in self.DIRECTIVE_PATTERNS.items():
            if pattern.search(content):
                features.add(feature)

        return features

    def detect_features_in_page(self, page: PageLike) -> set[str]:
        """
        Detect features in a page object.

        Checks both content and metadata for feature indicators.

        Args:
            page: Page object to analyze

        Returns:
            Set of detected feature names
        """
        features: set[str] = set()

        # Detect from content
        if page._source:
            features.update(self.detect_features_in_content(page._source))

        # Check metadata for explicit feature flags
        if page.metadata:
            # Check for mermaid in metadata
            if page.metadata.get("mermaid"):
                features.add("mermaid")

            # Check for interactive features
            if page.metadata.get("interactive"):
                features.add("interactive")

            # Check for graph features
            if page.metadata.get("graph"):
                features.add("graph")

        return features


def detect_site_features(site: Site) -> set[str]:
    """
    Detect all features used across a site.

    Convenience function to scan all pages and collect features.

    Args:
        site: Site with populated pages list

    Returns:
        Set of all detected features

    """
    detector = FeatureDetector()
    all_features: set[str] = set()

    for page in site.pages:
        features = detector.detect_features_in_page(page)
        all_features.update(features)

    return all_features
