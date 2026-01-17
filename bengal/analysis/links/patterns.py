"""
Link Pattern Analyzer for Document Applications.

Analyzes link patterns across the site to optimize speculation rules
and prefetching strategies.

Features:
- Identifies high-traffic navigation paths
- Detects common link patterns (nav, related content)
- Suggests optimal eagerness levels based on link frequency
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

__all__ = [
    "LinkPatternAnalyzer",
    "LinkPatternReport",
    "analyze_link_patterns",
]

logger = get_logger(__name__)


@dataclass
class LinkPatternReport:
    """
    Report of link pattern analysis.
    
    Attributes:
        total_internal_links: Count of all internal links
        total_external_links: Count of all external links
        link_frequency: Counter of internal link targets
        hot_paths: Most frequently linked internal paths
        section_traffic: Estimated traffic per section
        recommended_prerender: Paths recommended for prerender
        recommended_prefetch: Paths recommended for prefetch
        
    """

    total_internal_links: int = 0
    total_external_links: int = 0
    link_frequency: Counter = field(default_factory=Counter)
    hot_paths: list[str] = field(default_factory=list)
    section_traffic: dict[str, int] = field(default_factory=dict)
    recommended_prerender: list[str] = field(default_factory=list)
    recommended_prefetch: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "total_internal_links": self.total_internal_links,
            "total_external_links": self.total_external_links,
            "hot_paths": self.hot_paths[:20],  # Top 20
            "section_traffic": dict(self.section_traffic),
            "recommended_prerender": self.recommended_prerender,
            "recommended_prefetch": self.recommended_prefetch,
        }


class LinkPatternAnalyzer:
    """
    Analyzes link patterns across a site.
    
    Uses the site's content graph and page metadata to identify
    navigation patterns and recommend speculation strategies.
    
    Example usage:
        analyzer = LinkPatternAnalyzer(site)
        report = analyzer.analyze()
        print(f"Hot paths: {report.hot_paths}")
        
    """

    def __init__(self, site: SiteLike):
        """
        Initialize the analyzer.

        Args:
            site: The Bengal site instance
        """
        self.site = site

    def analyze(self) -> LinkPatternReport:
        """
        Perform link pattern analysis.

        Returns:
            LinkPatternReport with analysis results
        """
        report = LinkPatternReport()

        # Analyze all pages
        for page in self.site.pages:
            self._analyze_page_links(page, report)

        # Calculate hot paths
        report.hot_paths = [path for path, _ in report.link_frequency.most_common(20)]

        # Calculate section traffic
        for path, count in report.link_frequency.items():
            section = self._get_section(path)
            if section:
                report.section_traffic[section] = report.section_traffic.get(section, 0) + count

        # Generate recommendations
        self._generate_recommendations(report)

        return report

    def _analyze_page_links(self, page: Any, report: LinkPatternReport) -> None:
        """
        Analyze links on a single page.

        Args:
            page: The page to analyze
            report: Report to update
        """
        # Get outgoing links from page metadata or content
        outgoing_links = getattr(page, "outgoing_links", [])
        if not outgoing_links and hasattr(page, "metadata"):
            outgoing_links = page.metadata.get("outgoing_links", [])

        for link in outgoing_links:
            href = link if isinstance(link, str) else link.get("href", "")
            if not href:
                continue

            if self._is_internal_link(href):
                report.total_internal_links += 1
                normalized = self._normalize_path(href)
                report.link_frequency[normalized] += 1
            else:
                report.total_external_links += 1

    def _is_internal_link(self, href: str) -> bool:
        """Check if a link is internal."""
        if not href:
            return False

        # External if starts with protocol
        if href.startswith(("http://", "https://", "//")):
            baseurl = self.site.baseurl or ""
            return bool(baseurl and href.startswith(baseurl))

        # Fragment-only links are internal
        if href.startswith("#"):
            return True

        # Relative and absolute paths are internal
        return True

    def _normalize_path(self, href: str) -> str:
        """Normalize a path for comparison."""
        # Remove fragment
        path = href.split("#")[0]

        # Remove query string
        path = path.split("?")[0]

        # Ensure leading slash
        if not path.startswith("/"):
            path = "/" + path

        # Remove trailing index.html
        if path.endswith("/index.html"):
            path = path[:-10]

        # Ensure trailing slash for directories
        if not path.endswith("/") and "." not in path.split("/")[-1]:
            path += "/"

        return path

    def _get_section(self, path: str) -> str | None:
        """Extract section from a path."""
        parts = path.strip("/").split("/")
        if len(parts) > 0 and parts[0]:
            return f"/{parts[0]}/"
        return None

    def _generate_recommendations(self, report: LinkPatternReport) -> None:
        """
        Generate prefetch/prerender recommendations.

        High-frequency paths get prerender recommendations.
        Medium-frequency paths get prefetch recommendations.

        Args:
            report: Report to update with recommendations
        """
        if not report.link_frequency:
            return

        # Calculate thresholds
        counts = list(report.link_frequency.values())
        if not counts:
            return

        max_count = max(counts)
        high_threshold = max_count * 0.6
        medium_threshold = max_count * 0.2

        for path, count in report.link_frequency.items():
            if count >= high_threshold:
                report.recommended_prerender.append(path)
            elif count >= medium_threshold:
                report.recommended_prefetch.append(path)


def analyze_link_patterns(site: SiteLike) -> LinkPatternReport:
    """
    Convenience function to analyze link patterns.
    
    Args:
        site: The Bengal site instance
    
    Returns:
        LinkPatternReport with analysis results
        
    """
    analyzer = LinkPatternAnalyzer(site)
    return analyzer.analyze()
