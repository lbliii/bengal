"""
Graph reporting module for Bengal SSG.

Transforms raw graph analysis into actionable insights for content strategy,
SEO optimization, and site architecture improvements. The reporter generates
human-readable statistics, identifies content gaps, and provides prioritized
recommendations.

Report Types:
    - Statistics: Page counts, link density, connectivity distribution
    - Recommendations: Prioritized actions for improving site structure
    - SEO Insights: Link depth analysis, link equity flow, orphan risks
    - Content Gaps: Missing cross-links, underlinked sections, tag coverage

Classes:
    GraphReporter: Main reporter that delegates from KnowledgeGraph

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> # Reporting is typically accessed via KnowledgeGraph methods
    >>> print(graph.format_stats())
    >>> recommendations = graph.get_actionable_recommendations()
    >>> seo_insights = graph.get_seo_insights()
    >>> content_gaps = graph.get_content_gaps()

See Also:
    - bengal/analysis/knowledge_graph.py: Main graph coordinator
    - bengal/analysis/graph_analysis.py: Underlying analysis
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.core.page import Page

logger = get_logger(__name__)


class GraphReporter:
    """
    Generates reports and insights from knowledge graph analysis.

    Provides methods for:
    - Formatted statistics output
    - Actionable recommendations for site structure
    - SEO-focused insights
    - Content gap detection

    Example:
        >>> from bengal.analysis import KnowledgeGraph
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> reporter = GraphReporter(graph)
        >>> print(reporter.format_stats())
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        """
        Initialize the graph reporter.

        Args:
            graph: Knowledge graph to report on (must be built)
        """
        self._graph = graph

    def _ensure_built(self) -> None:
        """Verify the graph has been built before reporting."""
        if not self._graph._built:
            raise ValueError("Must call graph.build() before reporting")

    def format_stats(self) -> str:
        """
        Format graph statistics as a human-readable string.

        Returns:
            Formatted statistics string

        Raises:
            ValueError: If graph hasn't been built yet
        """
        self._ensure_built()

        m = self._graph.metrics
        assert m is not None, "metrics should not be None after _ensure_built()"
        hubs = self._graph.get_hubs()
        orphans = self._graph.get_orphans()

        output = []
        output.append("\n📊 Knowledge Graph Statistics")
        output.append("=" * 60)
        output.append(f"Total pages:        {m.total_pages}")
        output.append(f"Total links:        {m.total_links}")
        output.append(f"Average links:      {m.avg_connectivity:.1f} per page")
        output.append("")
        output.append("Connectivity Distribution:")
        output.append(
            f"  Hubs (>{self._graph.hub_threshold} refs):  "
            f"{m.hub_count} pages ({m.hub_count / m.total_pages * 100:.1f}%)"
        )
        mid_count = m.total_pages - m.hub_count - m.leaf_count
        output.append(
            f"  Mid-tier (3-{self._graph.hub_threshold}):  "
            f"{mid_count} pages ({mid_count / m.total_pages * 100:.1f}%)"
        )
        output.append(
            f"  Leaves (≤{self._graph.leaf_threshold}):    "
            f"{m.leaf_count} pages ({m.leaf_count / m.total_pages * 100:.1f}%)"
        )
        output.append("")

        # Show top hubs
        output.append("Top Hubs:")
        for i, page in enumerate(hubs[:5], 1):
            refs = self._graph.incoming_refs[page]
            output.append(f"  {i}. {page.title:<40} {refs} refs")

        if len(hubs) > 5:
            output.append(f"  ... and {len(hubs) - 5} more")

        # Show orphans
        output.append("")
        if orphans:
            output.append(f"Orphaned Pages ({len(orphans)} with 0 incoming refs):")
            for orphan in orphans[:5]:
                output.append(f"  • {orphan.source_path}")
            if len(orphans) > 5:
                output.append(f"  ... and {len(orphans) - 5} more")
        else:
            output.append("Orphaned Pages: None ✓")

        # Insights
        output.append("")
        output.append("💡 Insights:")
        leaf_pct = m.leaf_count / m.total_pages * 100 if m.total_pages > 0 else 0
        output.append(f"  • {leaf_pct:.0f}% of pages are leaves (could stream for memory savings)")

        if orphans:
            output.append(
                f"  • {len(orphans)} pages have no incoming links (consider adding navigation)"
            )

        # Add actionable recommendations
        recommendations = self.get_actionable_recommendations()
        if recommendations:
            output.append("")
            output.append("🎯 Actionable Recommendations:")
            for rec in recommendations:
                output.append(f"  {rec}")

        # Add SEO insights
        seo_insights = self.get_seo_insights()
        if seo_insights:
            output.append("")
            output.append("🎯 SEO Insights:")
            for insight in seo_insights:
                output.append(f"  {insight}")

        # Add content gap detection
        content_gaps = self.get_content_gaps()
        if content_gaps:
            output.append("")
            output.append("🔍 Content Gaps:")
            for gap in content_gaps[:5]:  # Limit to top 5
                output.append(f"  {gap}")
            if len(content_gaps) > 5:
                output.append(f"  ... and {len(content_gaps) - 5} more gaps")

        output.append("")

        return "\n".join(output)

    def get_actionable_recommendations(self) -> list[str]:
        """
        Generate actionable recommendations for improving site structure.

        Returns:
            List of recommendation strings with emoji prefixes
        """
        self._ensure_built()

        recommendations = []
        m = self._graph.metrics
        assert m is not None, "metrics should not be None after _ensure_built()"
        orphans = self._graph.get_orphans()

        # Orphaned pages recommendation
        if len(orphans) > 10:
            top_orphans = orphans[:5]
            orphan_titles = ", ".join(p.title for p in top_orphans)
            if len(orphans) > 5:
                orphan_titles += f", ... ({len(orphans) - 5} more)"
            recommendations.append(
                f"🔗 Link {len(orphans)} orphaned pages. Start with: {orphan_titles}"
            )
        elif len(orphans) > 0:
            orphan_titles = ", ".join(p.title for p in orphans[:3])
            recommendations.append(f"🔗 Link {len(orphans)} orphaned pages: {orphan_titles}")

        # Underlinked valuable content (only if PageRank computed)
        try:
            if not self._graph._pagerank_results:
                # Compute PageRank if not already computed
                self._graph.compute_pagerank()

            if self._graph._pagerank_results is None:
                return []

            # Get average PageRank to identify high-value pages
            all_scores = list(self._graph._pagerank_results.scores.values())
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

            # Find orphans with above-average PageRank (these are valuable but unlinked)
            high_pagerank_orphans = [
                p for p in orphans if self._graph._pagerank_results.get_score(p) > avg_score * 1.5
            ]
            if high_pagerank_orphans and len(high_pagerank_orphans) < len(orphans):
                top_underlinked = high_pagerank_orphans[:3]
                titles = ", ".join(p.title for p in top_underlinked)
                recommendations.append(
                    f"⭐ {len(high_pagerank_orphans)} high-value pages are underlinked. "
                    f"Consider adding navigation or cross-links: {titles}"
                )
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.debug(
                "pagerank_recommendation_skipped",
                error=str(e),
                reason="PageRank computation unavailable for underlinked analysis",
            )

        # Link density recommendation
        if m.avg_connectivity < 2.0:
            recommendations.append(
                f"📊 Low link density ({m.avg_connectivity:.1f} links/page). "
                f"Consider adding more internal links for better SEO and discoverability."
            )
        elif m.avg_connectivity > 5.0:
            recommendations.append(
                f"✅ Good link density ({m.avg_connectivity:.1f} links/page). "
                f"Your site has strong internal linking."
            )

        # Bridge pages recommendation (only if path analysis computed)
        try:
            if not self._graph._path_results:
                # Compute path analysis if not already computed
                self._graph.analyze_paths()

            if self._graph._path_results is None:
                return []

            bridges = self._graph._path_results.get_top_bridges(5)
            if bridges and bridges[0][1] > 0.001:
                top_bridges = bridges[:3]
                bridge_titles = ", ".join(p.title for p, _ in top_bridges)
                recommendations.append(
                    f"🌉 Top bridge pages: {bridge_titles}. "
                    f"These are critical for navigation - ensure they're prominent in menus."
                )
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.debug(
                "path_analysis_recommendation_skipped",
                error=str(e),
                reason="Path analysis unavailable for bridge page detection",
            )

        # Hub pages recommendation
        hubs = self._graph.get_hubs()
        if len(hubs) > 0:
            top_hubs = hubs[:3]
            hub_titles = ", ".join(p.title for p in top_hubs)
            recommendations.append(
                f"🏆 Hub pages ({len(hubs)} total): {hub_titles}. "
                f"These are your most important pages - keep them updated and well-linked."
            )

        # Performance optimization
        leaf_pct = m.leaf_count / m.total_pages * 100 if m.total_pages > 0 else 0
        if leaf_pct > 70:
            recommendations.append(
                f"⚡ {leaf_pct:.0f}% of pages are leaves - great for performance! "
                f"Consider lazy-loading these pages to reduce memory usage."
            )

        return recommendations

    def get_seo_insights(self) -> list[str]:
        """
        Generate SEO-focused insights about site structure.

        Returns:
            List of SEO insight strings with emoji prefixes
        """
        self._ensure_built()

        insights = []
        m = self._graph.metrics
        assert m is not None, "metrics should not be None after _ensure_built()"
        analysis_pages = getattr(
            self._graph, "_analysis_pages_cache", self._graph.get_analysis_pages()
        )

        # Link depth analysis (from homepage)
        try:
            if not self._graph._path_results:
                self._graph.analyze_paths()

            # Find homepage
            homepage = self._find_homepage(analysis_pages)

            if homepage:
                # Calculate average link depth from homepage
                from bengal.analysis.path_analysis import PathAnalyzer

                analyzer = PathAnalyzer(self._graph)
                distances = analyzer._bfs_distances(homepage, analysis_pages)
                reachable = [d for d in distances.values() if d > 0]
                if reachable:
                    avg_depth = sum(reachable) / len(reachable)
                    max_depth = max(reachable)
                    insights.append(f"📏 Average link depth from homepage: {avg_depth:.1f} clicks")
                    insights.append(f"📏 Maximum link depth: {max_depth} clicks")
                    if max_depth > 4:
                        insights.append(
                            "⚠️  Deep pages (>4 clicks) may be hard to discover. "
                            "Consider shortening paths."
                        )
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.debug(
                "link_depth_analysis_skipped",
                error=str(e),
                reason="Path analysis unavailable for link depth calculation",
            )

        # Link equity flow analysis
        try:
            if not self._graph._pagerank_results:
                self._graph.compute_pagerank()

            if self._graph._pagerank_results is None:
                return []

            # Find pages with high PageRank but few outgoing links
            high_pagerank_low_outgoing = []
            for page in analysis_pages:
                pagerank = self._graph._pagerank_results.get_score(page)
                outgoing = len(self._graph.outgoing_refs.get(page, set()))
                if pagerank > 0.001 and outgoing < 3:
                    high_pagerank_low_outgoing.append((page, pagerank, outgoing))

            if high_pagerank_low_outgoing:
                high_pagerank_low_outgoing.sort(key=lambda x: x[1], reverse=True)
                top_pages = high_pagerank_low_outgoing[:3]
                titles = ", ".join(p.title for p, _, _ in top_pages)
                insights.append(
                    f"🔗 {len(high_pagerank_low_outgoing)} pages should pass more link equity "
                    f"(high PageRank, few outgoing links): {titles}"
                )
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.debug(
                "link_equity_analysis_skipped",
                error=str(e),
                reason="PageRank computation unavailable for link equity analysis",
            )

        # Orphan page SEO risk
        orphans = self._graph.get_orphans()
        if len(orphans) > m.total_pages * 0.1:
            insights.append(
                f"⚠️  {len(orphans)} orphaned pages ({len(orphans) / m.total_pages * 100:.0f}%) - "
                f"SEO risk: search engines may not discover these pages"
            )

        # Internal linking structure
        if m.avg_connectivity < 2.0:
            insights.append(
                f"🔗 Low internal linking ({m.avg_connectivity:.1f} links/page). "
                f"Internal links help SEO and user navigation."
            )
        elif m.avg_connectivity >= 3.0:
            insights.append(
                f"✅ Good internal linking ({m.avg_connectivity:.1f} links/page). "
                f"Strong structure for SEO."
            )

        # Hub page optimization
        hubs = self._graph.get_hubs()
        if len(hubs) > 0:
            insights.append(
                f"🏆 {len(hubs)} hub pages identified. These are your most important pages - "
                f"ensure they're optimized and well-linked."
            )

        return insights

    def _find_homepage(self, analysis_pages: list[Page]) -> Page | None:
        """Find the homepage from a list of pages."""
        for page in analysis_pages:
            if (
                page.metadata.get("is_home")
                or page.slug == "index"
                or str(page.source_path).endswith("index.md")
                or str(page.source_path).endswith("_index.md")
            ):
                return page
        return None

    def get_content_gaps(self) -> list[str]:
        """
        Identify content gaps based on link structure and taxonomies.

        Returns:
            List of content gap descriptions
        """
        self._ensure_built()

        gaps = []
        analysis_pages = getattr(
            self._graph, "_analysis_pages_cache", self._graph.get_analysis_pages()
        )

        # Missing bridge pages: Topics that should connect but don't
        try:
            if not self._graph._path_results:
                self._graph.analyze_paths()

            # Find pages with shared tags but no links
            from collections import defaultdict

            tag_to_pages: dict[str, list[Page]] = defaultdict(list)
            for page in analysis_pages:
                if hasattr(page, "tags") and page.tags:
                    for tag in page.tags:
                        tag_to_pages[tag].append(page)

            # Find tags with multiple pages but low cross-linking
            for tag, pages in tag_to_pages.items():
                if len(pages) >= 3:
                    # Count links between pages with this tag
                    links_within_tag = 0
                    for page in pages:
                        outgoing = self._graph.outgoing_refs.get(page, set())
                        links_within_tag += sum(1 for target in outgoing if target in pages)

                    # Expected links: at least 1 link per 2 pages
                    expected_links = len(pages) // 2
                    if links_within_tag < expected_links:
                        gap_pages = [p.title for p in pages[:3]]
                        gaps.append(
                            f"🔗 Tag '{tag}' has {len(pages)} pages but only "
                            f"{links_within_tag} cross-links. "
                            f"Consider linking: {', '.join(gap_pages)}"
                        )
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.debug(
                "tag_crosslink_analysis_skipped",
                error=str(e),
                reason="Tag analysis unavailable for content gap detection",
            )

        # Underlinked sections
        try:
            from collections import defaultdict

            section_to_pages: dict[str, list[Page]] = defaultdict(list)
            for page in analysis_pages:
                section = getattr(page, "_section", None)
                if section:
                    section_name = getattr(section, "name", str(section))
                    section_to_pages[section_name].append(page)

            for section_name, pages in section_to_pages.items():
                if len(pages) >= 5:
                    # Check if section has an index page
                    has_index = any(p.source_path.stem in ("_index", "index") for p in pages)

                    # Count links within section
                    links_within_section = 0
                    for page in pages:
                        outgoing = self._graph.outgoing_refs.get(page, set())
                        links_within_section += sum(1 for target in outgoing if target in pages)

                    if not has_index and links_within_section < len(pages):
                        gaps.append(
                            f"📑 Section '{section_name}' ({len(pages)} pages) lacks an index "
                            f"page and has low internal linking ({links_within_section} links). "
                            f"Consider creating an index page."
                        )
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.debug(
                "section_linking_analysis_skipped",
                error=str(e),
                reason="Section analysis unavailable for content gap detection",
            )

        return gaps
