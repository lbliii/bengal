"""
Knowledge Graph Analysis for Bengal SSG.

Analyzes page connectivity, identifies hubs and leaves, finds orphaned pages,
and provides insights for optimization and content strategy.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.community_detection import CommunityDetectionResults
    from bengal.analysis.link_suggestions import LinkSuggestionResults
    from bengal.analysis.page_rank import PageRankResults
    from bengal.analysis.path_analysis import PathAnalysisResults
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


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

    page: Page
    incoming_refs: int
    outgoing_refs: int
    connectivity_score: int
    is_hub: bool
    is_leaf: bool
    is_orphan: bool


class KnowledgeGraph:
    """
    Analyzes the connectivity structure of a Bengal site.

    Builds a graph of all pages and their connections through:
    - Internal links (cross-references)
    - Taxonomies (tags, categories)
    - Related posts
    - Menu items

    Provides insights for:
    - Content strategy (find orphaned pages)
    - Performance optimization (hub-first streaming)
    - Navigation design (understand structure)
    - SEO improvements (link structure)

    Example:
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> hubs = graph.get_hubs(threshold=10)
        >>> orphans = graph.get_orphans()
        >>> print(f"Found {len(orphans)} orphaned pages")
    """

    def __init__(
        self,
        site: Site,
        hub_threshold: int = 10,
        leaf_threshold: int = 2,
        exclude_autodoc: bool = True,
    ):
        """
        Initialize knowledge graph analyzer.

        Args:
            site: Site instance to analyze
            hub_threshold: Minimum incoming refs to be considered a hub
            leaf_threshold: Maximum connectivity to be considered a leaf
            exclude_autodoc: If True, exclude autodoc/API reference pages from analysis (default: True)
        """
        self.site = site
        self.hub_threshold = hub_threshold
        self.leaf_threshold = leaf_threshold
        self.exclude_autodoc = exclude_autodoc

        # Graph data structures - now using pages directly as keys (hashable!)
        self.incoming_refs: dict[Page, int] = defaultdict(int)  # page -> count
        self.outgoing_refs: dict[Page, set[Page]] = defaultdict(set)  # page -> target pages
        # Note: page_by_id no longer needed - pages are directly hashable

        # Analysis results
        self.metrics: GraphMetrics = None
        self._built = False

        # Analysis results cache
        self._pagerank_results: PageRankResults | None = None
        self._community_results: CommunityDetectionResults | None = None
        self._path_results: PathAnalysisResults | None = None
        self._link_suggestions: LinkSuggestionResults | None = None

    def build(self) -> None:
        """
        Build the knowledge graph by analyzing all page connections.

        This analyzes:
        1. Cross-references (internal links between pages)
        2. Taxonomy references (pages grouped by tags/categories)
        3. Related posts (pre-computed relationships)
        4. Menu items (navigation references)

        Call this before using any analysis methods.
        """
        if self._built:
            logger.debug("knowledge_graph_already_built", action="skipping")
            return

        # Get pages to analyze (excluding autodoc if configured)
        analysis_pages = self.get_analysis_pages()
        total_analysis_pages = len(analysis_pages)
        excluded_count = len(self.site.pages) - total_analysis_pages

        logger.info(
            "knowledge_graph_build_start",
            total_pages=len(self.site.pages),
            analysis_pages=total_analysis_pages,
            excluded_autodoc=excluded_count if self.exclude_autodoc else 0,
        )

        # No need to build page ID mapping - pages are directly hashable!

        # Ensure links are extracted from pages we'll analyze
        # (links are normally extracted during rendering, but we need them for graph analysis)
        self._ensure_links_extracted()

        # Count references from different sources (only from analysis pages)
        self._analyze_cross_references()
        self._analyze_taxonomies()
        self._analyze_related_posts()
        self._analyze_menus()

        # Compute metrics
        self.metrics = self._compute_metrics()

        self._built = True

        logger.info(
            "knowledge_graph_build_complete",
            total_pages=self.metrics.total_pages,
            total_links=self.metrics.total_links,
            hubs=self.metrics.hub_count,
            leaves=self.metrics.leaf_count,
            orphans=self.metrics.orphan_count,
        )

    def _is_autodoc_page(self, page: Page) -> bool:
        """
        Check if a page is an autodoc/API reference page that should be excluded.

        Args:
            page: Page to check

        Returns:
            True if page should be excluded from analysis
        """
        if not self.exclude_autodoc:
            return False

        # Check metadata types
        page_type = page.metadata.get("type", "")
        if page_type in ("api-reference", "python-module", "cli-reference"):
            return True

        # Check for autodoc markers
        if page.metadata.get("_api_doc") is not None:
            return True

        # Check if path is under /api/ directory
        path_str = str(page.source_path)
        return "/api/" in path_str or path_str.endswith("/api")

    def get_analysis_pages(self) -> list[Page]:
        """
        Get list of pages to analyze, excluding autodoc pages if configured.

        Returns:
            List of pages to include in graph analysis
        """
        if not self.exclude_autodoc:
            return list(self.site.pages)

        return [p for p in self.site.pages if not self._is_autodoc_page(p)]

    def _ensure_links_extracted(self) -> None:
        """
        Extract links from all pages if not already extracted.

        Links are normally extracted during rendering, but graph analysis
        needs them before rendering happens. This ensures links are available.
        """
        # Only extract links from pages we'll analyze
        analysis_pages = self.get_analysis_pages()
        for page in analysis_pages:
            # Extract links if not already extracted
            if not hasattr(page, "links") or not page.links:
                try:
                    page.extract_links()
                except Exception as e:
                    # Log but don't fail - some pages might not have extractable links
                    logger.debug(
                        "knowledge_graph_link_extraction_failed",
                        page=str(page.source_path),
                        error=str(e),
                    )

    def _analyze_cross_references(self) -> None:
        """
        Analyze cross-references (internal links between pages).

        Uses the site's xref_index to find all internal links.
        Only analyzes links from/to pages included in analysis (excludes autodoc).
        """
        if not hasattr(self.site, "xref_index") or not self.site.xref_index:
            logger.debug("knowledge_graph_no_xref_index", action="skipping cross-ref analysis")
            return

        # Get pages to analyze (excluding autodoc)
        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        # The xref_index maps paths/slugs/IDs to pages
        # We need to analyze which pages link to which
        for page in analysis_pages:
            # Analyze outgoing links from this page
            for link in getattr(page, "links", []):
                # Try to resolve the link to a target page
                target = self._resolve_link(link)
                # Only count links to pages we're analyzing (exclude autodoc targets)
                if target and target != page and target in analysis_pages_set:
                    self.incoming_refs[target] += 1  # Direct page reference
                    self.outgoing_refs[page].add(target)  # Direct page reference

    def _resolve_link(self, link: str) -> Page:
        """
        Resolve a link string to a target page.

        Args:
            link: Link string (path, slug, or ID)

        Returns:
            Target page or None if not found
        """
        if not hasattr(self.site, "xref_index") or not self.site.xref_index:
            return None

        # Try different lookup strategies
        xref = self.site.xref_index

        # Try by ID
        if link.startswith("id:"):
            return xref.get("by_id", {}).get(link[3:])

        # Try by path
        if "/" in link or link.endswith(".md"):
            clean_link = link.replace(".md", "").strip("/")
            return xref.get("by_path", {}).get(clean_link)

        # Try by slug
        pages = xref.get("by_slug", {}).get(link, [])
        return pages[0] if pages else None

    def _analyze_taxonomies(self) -> None:
        """
        Analyze taxonomy references (pages grouped by tags/categories).

        Pages in the same taxonomy group reference each other implicitly.
        Only includes pages in analysis (excludes autodoc).
        """
        if not hasattr(self.site, "taxonomies") or not self.site.taxonomies:
            logger.debug("knowledge_graph_no_taxonomies", action="skipping taxonomy analysis")
            return

        # Get pages to analyze (excluding autodoc)
        analysis_pages_set = set(self.get_analysis_pages())

        # For each taxonomy (tags, categories, etc.)
        for _taxonomy_name, taxonomy_dict in self.site.taxonomies.items():
            # For each term in the taxonomy (e.g., 'python', 'tutorial')
            for _term_slug, term_data in taxonomy_dict.items():
                # Get pages with this term
                pages = term_data.get("pages", [])

                # Each page in the group has incoming refs from the taxonomy
                # Only count pages we're analyzing
                for page in pages:
                    if page in analysis_pages_set:
                        # Each page in a taxonomy gets a small boost
                        # (exists in this conceptual grouping)
                        self.incoming_refs[page] += 1  # Direct page reference

    def _analyze_related_posts(self) -> None:
        """
        Analyze related posts (pre-computed relationships).

        Related posts are pages that share tags or other criteria.
        Only includes pages in analysis (excludes autodoc).
        """
        # Get pages to analyze (excluding autodoc)
        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        for page in analysis_pages:
            if not hasattr(page, "related_posts") or not page.related_posts:
                continue

            # Each related post is an outgoing reference
            # Only count links to pages we're analyzing
            for related in page.related_posts:
                if related != page and related in analysis_pages_set:
                    self.incoming_refs[related] += 1  # Direct page reference
                    self.outgoing_refs[page].add(related)  # Direct page reference

    def _analyze_menus(self) -> None:
        """
        Analyze menu items (navigation references).

        Pages in menus get a significant boost in importance.
        Only includes pages in analysis (excludes autodoc).
        """
        if not hasattr(self.site, "menu") or not self.site.menu:
            logger.debug("knowledge_graph_no_menus", action="skipping menu analysis")
            return

        # Get pages to analyze (excluding autodoc)
        analysis_pages_set = set(self.get_analysis_pages())

        # For each menu (main, footer, etc.)
        for _menu_name, menu_items in self.site.menu.items():
            for item in menu_items:
                # Check if menu item has a page reference
                if hasattr(item, "page") and item.page and item.page in analysis_pages_set:
                    # Menu items get a significant boost (10 points)
                    self.incoming_refs[item.page] += 10  # Direct page reference

    def _compute_metrics(self) -> GraphMetrics:
        """
        Compute overall graph metrics.

        Returns:
            GraphMetrics with summary statistics
        """
        # Use analysis pages, not all pages
        analysis_pages = self.get_analysis_pages()
        total_pages = len(analysis_pages)
        total_links = sum(len(targets) for targets in self.outgoing_refs.values())

        # Count hubs, leaves, orphans
        hub_count = 0
        leaf_count = 0
        orphan_count = 0
        total_connectivity = 0

        for page in analysis_pages:
            incoming = self.incoming_refs[page]  # Direct page lookup
            outgoing = len(self.outgoing_refs[page])  # Direct page lookup
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

    def get_connectivity(self, page: Page) -> PageConnectivity:
        """
        Get connectivity information for a specific page.

        Args:
            page: Page to analyze

        Returns:
            PageConnectivity with detailed metrics

        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting connectivity")

        incoming = self.incoming_refs[page]  # Direct page lookup
        outgoing = len(self.outgoing_refs[page])  # Direct page lookup
        connectivity = incoming + outgoing

        return PageConnectivity(
            page=page,
            incoming_refs=incoming,
            outgoing_refs=outgoing,
            connectivity_score=connectivity,
            is_hub=incoming >= self.hub_threshold,
            is_leaf=connectivity <= self.leaf_threshold,
            is_orphan=(incoming == 0 and outgoing == 0),
        )

    def get_hubs(self, threshold: int | None = None) -> list[Page]:
        """
        Get hub pages (highly connected pages).

        Hubs are pages with many incoming references. These are typically:
        - Index pages
        - Popular articles
        - Core documentation

        Args:
            threshold: Minimum incoming refs (defaults to self.hub_threshold)

        Returns:
            List of hub pages sorted by incoming references (descending)

        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting hubs")

        threshold = threshold if threshold is not None else self.hub_threshold

        hubs = [page for page in self.site.pages if self.incoming_refs[page] >= threshold]

        # Sort by incoming refs (descending)
        hubs.sort(key=lambda p: self.incoming_refs[p], reverse=True)

        return hubs

    def get_leaves(self, threshold: int | None = None) -> list[Page]:
        """
        Get leaf pages (low connectivity pages).

        Leaves are pages with few connections. These are typically:
        - One-off blog posts
        - Changelog entries
        - Niche content

        Args:
            threshold: Maximum connectivity (defaults to self.leaf_threshold)

        Returns:
            List of leaf pages sorted by connectivity (ascending)

        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting leaves")

        threshold = threshold if threshold is not None else self.leaf_threshold

        leaves = [
            page for page in self.site.pages if self.get_connectivity_score(page) <= threshold
        ]

        # Sort by connectivity (ascending)
        leaves.sort(key=lambda p: self.get_connectivity_score(p))

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
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting orphans")

        # Get analysis pages (already excludes autodoc)
        analysis_pages = self.get_analysis_pages()
        orphans = [
            page
            for page in analysis_pages
            if self.incoming_refs[page] == 0
            and len(self.outgoing_refs[page]) == 0
            and not page.metadata.get("_generated")  # Exclude generated pages
        ]

        # Sort by slug for consistent ordering
        orphans.sort(key=lambda p: p.slug)

        return orphans

    def get_connectivity_score(self, page: Page) -> int:
        """
        Get total connectivity score for a page.

        Connectivity = incoming_refs + outgoing_refs

        Args:
            page: Page to analyze

        Returns:
            Connectivity score (higher = more connected)

        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting connectivity score")

        return self.incoming_refs[page] + len(self.outgoing_refs[page])  # Direct page lookup

    def get_layers(self) -> tuple[list[Page], list[Page], list[Page]]:
        """
        Partition pages into three layers by connectivity.

        Layers enable hub-first streaming builds:
        - Layer 0 (Hubs): High connectivity, process first, keep in memory
        - Layer 1 (Mid-tier): Medium connectivity, batch processing
        - Layer 2 (Leaves): Low connectivity, stream and release

        Returns:
            Tuple of (hubs, mid_tier, leaves)

        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting layers")

        # Sort all pages by connectivity (descending)
        sorted_pages = sorted(
            self.site.pages, key=lambda p: self.get_connectivity_score(p), reverse=True
        )

        total = len(sorted_pages)

        # Layer thresholds (configurable)
        hub_cutoff = int(total * 0.10)  # Top 10%
        mid_cutoff = int(total * 0.40)  # Next 30%

        hubs = sorted_pages[:hub_cutoff]
        mid_tier = sorted_pages[hub_cutoff:mid_cutoff]
        leaves = sorted_pages[mid_cutoff:]

        return hubs, mid_tier, leaves

    def get_metrics(self) -> GraphMetrics:
        """
        Get overall graph metrics.

        Returns:
            GraphMetrics with summary statistics

        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before getting metrics")

        return self.metrics

    def format_stats(self) -> str:
        """
        Format graph statistics as a human-readable string.

        Returns:
            Formatted statistics string

        Raises:
            ValueError: If graph hasn't been built yet
        """
        if not self._built:
            raise ValueError("Must call build() before formatting stats")

        m = self.metrics
        hubs = self.get_hubs()
        orphans = self.get_orphans()

        output = []
        output.append("\n📊 Knowledge Graph Statistics")
        output.append("=" * 60)
        output.append(f"Total pages:        {m.total_pages}")
        output.append(f"Total links:        {m.total_links}")
        output.append(f"Average links:      {m.avg_connectivity:.1f} per page")
        output.append("")
        output.append("Connectivity Distribution:")
        output.append(
            f"  Hubs (>{self.hub_threshold} refs):  {m.hub_count} pages ({m.hub_count / m.total_pages * 100:.1f}%)"
        )
        mid_count = m.total_pages - m.hub_count - m.leaf_count
        output.append(
            f"  Mid-tier (3-{self.hub_threshold}):  {mid_count} pages ({mid_count / m.total_pages * 100:.1f}%)"
        )
        output.append(
            f"  Leaves (≤{self.leaf_threshold}):    {m.leaf_count} pages ({m.leaf_count / m.total_pages * 100:.1f}%)"
        )
        output.append("")

        # Show top hubs
        output.append("Top Hubs:")
        for i, page in enumerate(hubs[:5], 1):
            refs = self.incoming_refs[page]
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
        if not self._built:
            raise ValueError("Must call build() before getting recommendations")

        recommendations = []
        m = self.metrics
        orphans = self.get_orphans()

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
            if not self._pagerank_results:
                # Compute PageRank if not already computed
                self.compute_pagerank()

            # Get average PageRank to identify high-value pages
            all_scores = list(self._pagerank_results.scores.values())
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

            # Find orphans with above-average PageRank (these are valuable but unlinked)
            high_pagerank_orphans = [
                p
                for p in orphans
                if self._pagerank_results.get_score(p) > avg_score * 1.5  # 50% above average
            ]
            if high_pagerank_orphans and len(high_pagerank_orphans) < len(orphans):
                top_underlinked = high_pagerank_orphans[:3]
                titles = ", ".join(p.title for p in top_underlinked)
                recommendations.append(
                    f"⭐ {len(high_pagerank_orphans)} high-value pages are underlinked. "
                    f"Consider adding navigation or cross-links: {titles}"
                )
        except Exception:
            # Skip if PageRank computation fails
            pass

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
            if not self._path_results:
                # Compute path analysis if not already computed
                self.analyze_paths()

            bridges = self._path_results.get_top_bridges(5)
            if bridges and bridges[0][1] > 0.001:  # Check if top bridge has meaningful score
                top_bridges = bridges[:3]
                bridge_titles = ", ".join(p.title for p, _ in top_bridges)
                recommendations.append(
                    f"🌉 Top bridge pages: {bridge_titles}. "
                    f"These are critical for navigation - ensure they're prominent in menus."
                )
        except Exception:
            # Skip if path analysis computation fails
            pass

        # Hub pages recommendation
        hubs = self.get_hubs()
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
        if not self._built:
            raise ValueError("Must call build() before getting SEO insights")

        insights = []
        m = self.metrics

        # Link depth analysis (from homepage)
        try:
            if not self._path_results:
                self.analyze_paths()

            # Find homepage (usually index page or page with slug "index" or "/")
            homepage = None
            analysis_pages = getattr(self, "_analysis_pages_cache", self.get_analysis_pages())
            for page in analysis_pages:
                if (
                    page.metadata.get("is_home")
                    or page.slug == "index"
                    or str(page.source_path).endswith("index.md")
                    or str(page.source_path).endswith("_index.md")
                ):
                    homepage = page
                    break

            if homepage:
                # Calculate average link depth from homepage
                from bengal.analysis.path_analysis import PathAnalyzer

                analyzer = PathAnalyzer(self)
                distances = analyzer._bfs_distances(homepage, analysis_pages)
                reachable = [d for d in distances.values() if d > 0]
                if reachable:
                    avg_depth = sum(reachable) / len(reachable)
                    max_depth = max(reachable)
                    insights.append(f"📏 Average link depth from homepage: {avg_depth:.1f} clicks")
                    insights.append(f"📏 Maximum link depth: {max_depth} clicks")
                    if max_depth > 4:
                        insights.append(
                            "⚠️  Deep pages (>4 clicks) may be hard to discover. Consider shortening paths."
                        )
        except Exception:
            # Skip if path analysis fails
            pass

        # Link equity flow analysis
        try:
            if not self._pagerank_results:
                self.compute_pagerank()

            # Find pages with high PageRank but few outgoing links (should pass more equity)
            high_pagerank_low_outgoing = []
            for page in analysis_pages:
                pagerank = self._pagerank_results.get_score(page)
                outgoing = len(self.outgoing_refs.get(page, set()))
                # High PageRank (>75th percentile) but low outgoing (<3 links)
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
        except Exception:
            pass

        # Orphan page SEO risk
        orphans = self.get_orphans()
        if len(orphans) > m.total_pages * 0.1:  # More than 10% orphaned
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
        hubs = self.get_hubs()
        if len(hubs) > 0:
            insights.append(
                f"🏆 {len(hubs)} hub pages identified. These are your most important pages - "
                f"ensure they're optimized and well-linked."
            )

        return insights

    def get_content_gaps(self) -> list[str]:
        """
        Identify content gaps based on link structure and taxonomies.

        Returns:
            List of content gap descriptions
        """
        if not self._built:
            raise ValueError("Must call build() before getting content gaps")

        gaps = []
        analysis_pages = getattr(self, "_analysis_pages_cache", self.get_analysis_pages())

        # Missing bridge pages: Topics that should connect but don't
        try:
            if not self._path_results:
                self.analyze_paths()

            # Find pages with shared tags but no links
            from collections import defaultdict

            tag_to_pages: dict[str, list[Page]] = defaultdict(list)
            for page in analysis_pages:
                if hasattr(page, "tags") and page.tags:
                    for tag in page.tags:
                        tag_to_pages[tag].append(page)

            # Find tags with multiple pages but low cross-linking
            for tag, pages in tag_to_pages.items():
                if len(pages) >= 3:  # At least 3 pages with this tag
                    # Count links between pages with this tag
                    links_within_tag = 0
                    for page in pages:
                        outgoing = self.outgoing_refs.get(page, set())
                        links_within_tag += sum(1 for target in outgoing if target in pages)

                    # Expected links: at least 1 link per 2 pages
                    expected_links = len(pages) // 2
                    if links_within_tag < expected_links:
                        gap_pages = [p.title for p in pages[:3]]
                        gaps.append(
                            f"🔗 Tag '{tag}' has {len(pages)} pages but only {links_within_tag} cross-links. "
                            f"Consider linking: {', '.join(gap_pages)}"
                        )
        except Exception:
            # Skip if tag extraction fails (e.g., pages don't have tags attribute)
            pass

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
                if len(pages) >= 5:  # Sections with 5+ pages
                    # Check if section has an index page
                    has_index = any(p.source_path.stem in ("_index", "index") for p in pages)

                    # Count links within section
                    links_within_section = 0
                    for page in pages:
                        outgoing = self.outgoing_refs.get(page, set())
                        links_within_section += sum(1 for target in outgoing if target in pages)

                    if not has_index and links_within_section < len(pages):
                        gaps.append(
                            f"📑 Section '{section_name}' ({len(pages)} pages) lacks an index page "
                            f"and has low internal linking ({links_within_section} links). "
                            f"Consider creating an index page."
                        )
        except Exception:
            pass

        return gaps

    def compute_pagerank(
        self, damping: float = 0.85, max_iterations: int = 100, force_recompute: bool = False
    ) -> PageRankResults:
        """
        Compute PageRank scores for all pages in the graph.

        PageRank assigns importance scores based on link structure.
        Pages that are linked to by many important pages get high scores.

        Args:
            damping: Probability of following links vs random jump (default 0.85)
            max_iterations: Maximum iterations before stopping (default 100)
            force_recompute: If True, recompute even if cached

        Returns:
            PageRankResults with scores and metadata

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = graph.compute_pagerank()
            >>> top_pages = results.get_top_pages(10)
        """
        if not self._built:
            raise RuntimeError("Must call build() before computing PageRank")

        # Return cached results unless forced
        if self._pagerank_results and not force_recompute:
            logger.debug("pagerank_cached", action="returning cached results")
            return self._pagerank_results

        # Import here to avoid circular dependency
        from bengal.analysis.page_rank import PageRankCalculator

        calculator = PageRankCalculator(graph=self, damping=damping, max_iterations=max_iterations)

        self._pagerank_results = calculator.compute()
        return self._pagerank_results

    def compute_personalized_pagerank(
        self, seed_pages: set[Page], damping: float = 0.85, max_iterations: int = 100
    ) -> PageRankResults:
        """
        Compute personalized PageRank from seed pages.

        Personalized PageRank biases random jumps toward seed pages,
        useful for finding pages related to a specific topic or set of pages.

        Args:
            seed_pages: Set of pages to bias toward
            damping: Probability of following links vs random jump
            max_iterations: Maximum iterations before stopping

        Returns:
            PageRankResults with personalized scores

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> # Find pages related to Python posts
            >>> python_posts = {p for p in site.pages if 'python' in p.tags}
            >>> results = graph.compute_personalized_pagerank(python_posts)
            >>> related = results.get_top_pages(10)
        """
        if not self._built:
            raise RuntimeError("Must call build() before computing PageRank")

        if not seed_pages:
            raise ValueError("seed_pages cannot be empty")

        # Import here to avoid circular dependency
        from bengal.analysis.page_rank import PageRankCalculator

        calculator = PageRankCalculator(graph=self, damping=damping, max_iterations=max_iterations)

        return calculator.compute_personalized(seed_pages)

    def get_top_pages_by_pagerank(self, limit: int = 20) -> list[tuple[Page, float]]:
        """
        Get top-ranked pages by PageRank score.

        Automatically computes PageRank if not already computed.

        Args:
            limit: Number of pages to return

        Returns:
            List of (page, score) tuples sorted by score descending

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> top_pages = graph.get_top_pages_by_pagerank(10)
            >>> print(f"Most important: {top_pages[0][0].title}")
        """
        if not self._pagerank_results:
            self.compute_pagerank()

        return self._pagerank_results.get_top_pages(limit)

    def get_pagerank_score(self, page: Page) -> float:
        """
        Get PageRank score for a specific page.

        Automatically computes PageRank if not already computed.

        Args:
            page: Page to get score for

        Returns:
            PageRank score (0.0 if page not found)

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> score = graph.get_pagerank_score(some_page)
            >>> print(f"Importance score: {score:.4f}")
        """
        if not self._pagerank_results:
            self.compute_pagerank()

        return self._pagerank_results.get_score(page)

    def detect_communities(
        self, resolution: float = 1.0, random_seed: int | None = None, force_recompute: bool = False
    ) -> CommunityDetectionResults:
        """
        Detect topical communities using Louvain method.

        Discovers natural clusters of related pages based on link structure.
        Communities represent topic areas or content groups.

        Args:
            resolution: Resolution parameter (higher = more communities, default 1.0)
            random_seed: Random seed for reproducibility
            force_recompute: If True, recompute even if cached

        Returns:
            CommunityDetectionResults with discovered communities

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = graph.detect_communities()
            >>> for community in results.get_largest_communities(5):
            ...     print(f"Community {community.id}: {community.size} pages")
        """
        if not self._built:
            raise RuntimeError("Must call build() before detecting communities")

        # Return cached results unless forced
        if self._community_results and not force_recompute:
            logger.debug("community_detection_cached", action="returning cached results")
            return self._community_results

        # Import here to avoid circular dependency
        from bengal.analysis.community_detection import LouvainCommunityDetector

        detector = LouvainCommunityDetector(
            graph=self, resolution=resolution, random_seed=random_seed
        )

        self._community_results = detector.detect()
        return self._community_results

    def get_community_for_page(self, page: Page) -> int | None:
        """
        Get community ID for a specific page.

        Automatically detects communities if not already computed.

        Args:
            page: Page to get community for

        Returns:
            Community ID or None if page not found

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> community_id = graph.get_community_for_page(some_page)
            >>> print(f"Page belongs to community {community_id}")
        """
        if not self._community_results:
            self.detect_communities()

        community = self._community_results.get_community_for_page(page)
        return community.id if community else None

    def analyze_paths(self, force_recompute: bool = False) -> PathAnalysisResults:
        """
        Analyze navigation paths and centrality metrics.

        Computes:
        - Betweenness centrality: Pages that act as bridges
        - Closeness centrality: Pages that are easily accessible
        - Network diameter and average path length

        Args:
            force_recompute: If True, recompute even if cached

        Returns:
            PathAnalysisResults with centrality metrics

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = graph.analyze_paths()
            >>> bridges = results.get_top_bridges(10)
        """
        if not self._built:
            raise RuntimeError("Must call build() before analyzing paths")

        # Return cached results unless forced
        if self._path_results and not force_recompute:
            logger.debug("path_analysis_cached", action="returning cached results")
            return self._path_results

        # Import here to avoid circular dependency
        from bengal.analysis.path_analysis import PathAnalyzer

        analyzer = PathAnalyzer(graph=self)
        self._path_results = analyzer.analyze()
        return self._path_results

    def get_betweenness_centrality(self, page: Page) -> float:
        """
        Get betweenness centrality for a specific page.

        Automatically analyzes paths if not already computed.

        Args:
            page: Page to get centrality for

        Returns:
            Betweenness centrality score
        """
        if not self._path_results:
            self.analyze_paths()

        return self._path_results.get_betweenness(page)

    def get_closeness_centrality(self, page: Page) -> float:
        """
        Get closeness centrality for a specific page.

        Automatically analyzes paths if not already computed.

        Args:
            page: Page to get centrality for

        Returns:
            Closeness centrality score
        """
        if not self._path_results:
            self.analyze_paths()

        return self._path_results.get_closeness(page)

    def suggest_links(
        self,
        min_score: float = 0.3,
        max_suggestions_per_page: int = 10,
        force_recompute: bool = False,
    ) -> LinkSuggestionResults:
        """
        Generate smart link suggestions to improve site connectivity.

        Uses multiple signals:
        - Topic similarity (shared tags/categories)
        - PageRank importance
        - Betweenness centrality (bridge pages)
        - Link gaps (underlinked content)

        Args:
            min_score: Minimum score threshold for suggestions
            max_suggestions_per_page: Maximum suggestions per page
            force_recompute: If True, recompute even if cached

        Returns:
            LinkSuggestionResults with all suggestions

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = graph.suggest_links()
            >>> for suggestion in results.get_top_suggestions(20):
            ...     print(f"{suggestion.source.title} -> {suggestion.target.title}")
        """
        if not self._built:
            raise RuntimeError("Must call build() before generating link suggestions")

        # Return cached results unless forced
        if self._link_suggestions and not force_recompute:
            logger.debug("link_suggestions_cached", action="returning cached results")
            return self._link_suggestions

        # Import here to avoid circular dependency
        from bengal.analysis.link_suggestions import LinkSuggestionEngine

        engine = LinkSuggestionEngine(
            graph=self, min_score=min_score, max_suggestions_per_page=max_suggestions_per_page
        )

        self._link_suggestions = engine.generate_suggestions()
        return self._link_suggestions

    def get_suggestions_for_page(
        self, page: Page, limit: int = 10
    ) -> list[tuple[Page, float, list[str]]]:
        """
        Get link suggestions for a specific page.

        Automatically generates suggestions if not already computed.

        Args:
            page: Page to get suggestions for
            limit: Maximum number of suggestions

        Returns:
            List of (target_page, score, reasons) tuples
        """
        if not self._link_suggestions:
            self.suggest_links()

        suggestions = self._link_suggestions.get_suggestions_for_page(page, limit)
        return [(s.target, s.score, s.reasons) for s in suggestions]
