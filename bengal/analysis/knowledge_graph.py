"""
Knowledge Graph Analysis for Bengal SSG.

The knowledge graph is the foundation of Bengal's site analysis capabilities.
It models the site as a directed graph where pages are nodes and links are edges,
enabling structural analysis, importance ranking, and navigation optimization.

Data Sources:
    The graph aggregates connections from multiple sources:
    - Cross-references: Internal markdown links between pages
    - Taxonomies: Shared tags and categories
    - Related posts: Algorithm-computed relationships
    - Menu items: Navigation structure
    - Section hierarchy: Parent-child relationships

Key Capabilities:
    - Hub detection: Find highly-connected important pages
    - Orphan detection: Identify pages with no incoming links
    - Connectivity scoring: Weighted semantic link analysis
    - Layer partitioning: Group pages for streaming builds
    - Delegated analysis: PageRank, communities, paths, suggestions

Classes:
    GraphMetrics: Summary statistics about the graph structure
    PageConnectivity: Connectivity details for a single page
    KnowledgeGraph: Main graph builder and analysis coordinator

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site, exclude_autodoc=True)
    >>> graph.build()
    >>> # Basic analysis
    >>> print(graph.format_stats())
    >>> # Advanced analysis
    >>> pagerank = graph.compute_pagerank()
    >>> communities = graph.detect_communities()
    >>> paths = graph.analyze_paths()
    >>> suggestions = graph.suggest_links()

See Also:
    - bengal/analysis/graph_analysis.py: GraphAnalyzer implementation
    - bengal/analysis/graph_reporting.py: GraphReporter implementation
    - bengal/analysis/link_types.py: Semantic link type definitions
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.analysis.graph_analysis import GraphAnalyzer
from bengal.analysis.graph_reporting import GraphReporter
from bengal.analysis.link_types import (
    DEFAULT_THRESHOLDS,
    DEFAULT_WEIGHTS,
    ConnectivityLevel,
    ConnectivityReport,
    LinkMetrics,
    LinkType,
)
from bengal.utils.autodoc import is_autodoc_page
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.community_detection import CommunityDetectionResults
    from bengal.analysis.link_suggestions import LinkSuggestionResults
    from bengal.analysis.page_rank import PageRankResults
    from bengal.analysis.path_analysis import PathAnalysisResults
    from bengal.analysis.results import PageLayers
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

        # Semantic link tracking (NEW)
        self.link_metrics: dict[Page, LinkMetrics] = {}  # page -> detailed link breakdown
        self.link_types: dict[tuple[Page, Page], LinkType] = {}  # (source, target) -> link type

        # Analysis results
        self.metrics: GraphMetrics | None = None
        self._built = False

        # Analysis results cache
        self._pagerank_results: PageRankResults | None = None
        self._community_results: CommunityDetectionResults | None = None
        self._path_results: PathAnalysisResults | None = None
        self._link_suggestions: LinkSuggestionResults | None = None

        # Delegated analyzers (initialized after build)
        self._analyzer: GraphAnalyzer | None = None
        self._reporter: GraphReporter | None = None

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

        # Semantic link analysis (NEW) - track structural relationships
        self._analyze_section_hierarchy()
        self._analyze_navigation_links()

        # Build link metrics for each page
        self._build_link_metrics()

        # Compute metrics
        self.metrics = self._compute_metrics()

        self._built = True

        # Initialize delegated analyzers
        self._analyzer = GraphAnalyzer(self)
        self._reporter = GraphReporter(self)

        logger.info(
            "knowledge_graph_build_complete",
            total_pages=self.metrics.total_pages,
            total_links=self.metrics.total_links,
            hubs=self.metrics.hub_count,
            leaves=self.metrics.leaf_count,
            orphans=self.metrics.orphan_count,
        )

    def get_analysis_pages(self) -> list[Page]:
        """
        Get list of pages to analyze, excluding autodoc pages if configured.

        Returns:
            List of pages to include in graph analysis
        """
        if not self.exclude_autodoc:
            return list(self.site.pages)

        return [p for p in self.site.pages if not is_autodoc_page(p)]

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
                except (AttributeError, TypeError) as e:
                    # Specific error handling for missing content
                    logger.warning(
                        "knowledge_graph_link_extraction_error",
                        page=str(page.source_path),
                        error=str(e),
                        type=type(e).__name__,
                    )
                except Exception as e:
                    # Log but don't fail - some pages might not have extractable links
                    logger.debug(
                        "knowledge_graph_link_extraction_failed",
                        page=str(page.source_path),
                        error=str(e),
                        exc_info=True,
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
                    # Track link type
                    self.link_types[(page, target)] = LinkType.EXPLICIT

    def _resolve_link(self, link: str) -> Page | None:
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
            page = xref.get("by_id", {}).get(link[3:])
            return page if page is not None else None

        # Try by path
        if "/" in link or link.endswith(".md"):
            clean_link = link.replace(".md", "").strip("/")
            page = xref.get("by_path", {}).get(clean_link)
            return page if page is not None else None

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
                        # Track link type (None source = taxonomy)
                        self.link_types[(None, page)] = LinkType.TAXONOMY

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
                    # Track link type
                    self.link_types[(page, related)] = LinkType.RELATED

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
                    # Track link type
                    self.link_types[(None, item.page)] = LinkType.MENU

    def _analyze_section_hierarchy(self) -> None:
        """
        Analyze implicit section links (parent _index.md → children).

        Section index pages implicitly link to all child pages in their
        directory. This represents topical containment—the parent page
        defines the topic, children belong to that topic.

        Weight: 0.5 (structural but semantically meaningful)
        """
        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        for page in analysis_pages:
            # Only process index pages (detect by filename stem)
            is_index = hasattr(page, "source_path") and page.source_path.stem in ("_index", "index")
            if not is_index:
                continue

            # Get the section this index belongs to via the _section property
            section = getattr(page, "_section", None)
            if not section:
                continue

            # Link to all child pages in this section
            section_pages = getattr(section, "pages", [])
            for child in section_pages:
                if child != page and child in analysis_pages_set:
                    # Topical link: parent defines topic, child belongs to it
                    # Use reduced weight (0.5) compared to explicit links
                    self.incoming_refs[child] += 0.5
                    self.outgoing_refs[page].add(child)
                    # Track link type
                    self.link_types[(page, child)] = LinkType.TOPICAL

        logger.debug(
            "knowledge_graph_section_hierarchy_complete",
            topical_links=sum(1 for lt in self.link_types.values() if lt == LinkType.TOPICAL),
        )

    def _analyze_navigation_links(self) -> None:
        """
        Analyze next/prev sequential relationships.

        Pages in a section often have prev/next relationships representing
        a reading order or logical sequence (e.g., tutorial steps, changelogs).

        Weight: 0.25 (pure navigation, lowest editorial intent)
        """
        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        for page in analysis_pages:
            # Check next_in_section
            next_page = getattr(page, "next_in_section", None)
            if next_page and next_page in analysis_pages_set:
                self.incoming_refs[next_page] += 0.25
                self.outgoing_refs[page].add(next_page)
                self.link_types[(page, next_page)] = LinkType.SEQUENTIAL

            # Check prev_in_section (bidirectional)
            prev_page = getattr(page, "prev_in_section", None)
            if prev_page and prev_page in analysis_pages_set:
                self.incoming_refs[prev_page] += 0.25
                self.outgoing_refs[page].add(prev_page)
                self.link_types[(page, prev_page)] = LinkType.SEQUENTIAL

        logger.debug(
            "knowledge_graph_navigation_links_complete",
            sequential_links=sum(1 for lt in self.link_types.values() if lt == LinkType.SEQUENTIAL),
        )

    def _build_link_metrics(self) -> None:
        """
        Build detailed link metrics for each page.

        Aggregates links by type into LinkMetrics objects for
        weighted connectivity scoring.
        """
        analysis_pages = self.get_analysis_pages()

        for page in analysis_pages:
            metrics = LinkMetrics()

            # Count links by type from link_types tracking
            for (_source, target), link_type in self.link_types.items():
                if target == page:
                    if link_type == LinkType.EXPLICIT:
                        metrics.explicit += 1
                    elif link_type == LinkType.MENU:
                        metrics.menu += 1
                    elif link_type == LinkType.TAXONOMY:
                        metrics.taxonomy += 1
                    elif link_type == LinkType.RELATED:
                        metrics.related += 1
                    elif link_type == LinkType.TOPICAL:
                        metrics.topical += 1
                    elif link_type == LinkType.SEQUENTIAL:
                        metrics.sequential += 1

            # Fallback: count untracked incoming refs as explicit
            # (for backward compatibility with existing link tracking)
            total_tracked = metrics.total_links()
            total_incoming = int(self.incoming_refs[page])
            untracked = max(0, total_incoming - total_tracked)
            metrics.explicit += untracked

            self.link_metrics[page] = metrics

        logger.debug(
            "knowledge_graph_link_metrics_built",
            pages_with_metrics=len(self.link_metrics),
        )

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
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before getting connectivity."
            )
        return self._analyzer.get_connectivity(page)

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
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise RuntimeError("KnowledgeGraph is not built. Call .build() before getting hubs.")
        return self._analyzer.get_hubs(threshold)

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
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise RuntimeError("KnowledgeGraph is not built. Call .build() before getting leaves.")
        return self._analyzer.get_leaves(threshold)

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
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise RuntimeError("KnowledgeGraph is not built. Call .build() before getting orphans.")
        return self._analyzer.get_orphans()

    def get_connectivity_report(
        self,
        thresholds: dict[str, float] | None = None,
        weights: dict[LinkType, float] | None = None,
    ) -> ConnectivityReport:
        """
        Get comprehensive connectivity report with pages grouped by level.

        Uses weighted scoring based on semantic link types to provide
        nuanced analysis beyond binary orphan detection.

        Args:
            thresholds: Custom thresholds for connectivity levels.
                        Defaults to DEFAULT_THRESHOLDS.
            weights: Custom weights for link types.
                     Defaults to DEFAULT_WEIGHTS.

        Returns:
            ConnectivityReport with pages grouped by level and statistics.

        Raises:
            RuntimeError: If graph hasn't been built yet

        Example:
            >>> graph.build()
            >>> report = graph.get_connectivity_report()
            >>> print(f"Isolated: {len(report.isolated)}")
            >>> print(f"Distribution: {report.get_distribution()}")
        """
        if not self._built:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before getting connectivity report."
            )

        t = thresholds or DEFAULT_THRESHOLDS
        w = weights or DEFAULT_WEIGHTS

        report = ConnectivityReport()
        analysis_pages = self.get_analysis_pages()
        total_score = 0.0

        for page in analysis_pages:
            metrics = self.link_metrics.get(page, LinkMetrics())
            score = metrics.connectivity_score(w)
            total_score += score

            level = ConnectivityLevel.from_score(score, t)

            if level == ConnectivityLevel.ISOLATED:
                report.isolated.append(page)
            elif level == ConnectivityLevel.LIGHTLY_LINKED:
                report.lightly_linked.append(page)
            elif level == ConnectivityLevel.ADEQUATELY_LINKED:
                report.adequately_linked.append(page)
            else:  # WELL_CONNECTED
                report.well_connected.append(page)

        report.total_pages = len(analysis_pages)
        report.avg_score = total_score / len(analysis_pages) if analysis_pages else 0.0

        # Sort each list by path for consistent output
        for page_list in [
            report.isolated,
            report.lightly_linked,
            report.adequately_linked,
            report.well_connected,
        ]:
            page_list.sort(key=lambda p: str(p.source_path))

        return report

    def get_page_link_metrics(self, page: Page) -> LinkMetrics:
        """
        Get detailed link metrics for a specific page.

        Args:
            page: Page to get metrics for

        Returns:
            LinkMetrics with breakdown by link type

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before getting link metrics."
            )
        return self.link_metrics.get(page, LinkMetrics())

    def get_connectivity_score(self, page: Page) -> int:
        """
        Get total connectivity score for a page.

        Connectivity = incoming_refs + outgoing_refs

        Args:
            page: Page to analyze

        Returns:
            Connectivity score (higher = more connected)

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before getting connectivity score."
            )
        return self._analyzer.get_connectivity_score(page)

    def get_layers(self) -> PageLayers:
        """
        Partition pages into three layers by connectivity.

        Layers enable hub-first streaming builds:
        - Layer 0 (Hubs): High connectivity, process first, keep in memory
        - Layer 1 (Mid-tier): Medium connectivity, batch processing
        - Layer 2 (Leaves): Low connectivity, stream and release

        Returns:
            PageLayers dataclass with hubs, mid_tier, and leaves attributes
            (supports tuple unpacking for backward compatibility)

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise RuntimeError("KnowledgeGraph is not built. Call .build() before getting layers.")
        return self._analyzer.get_layers()

    def get_metrics(self) -> GraphMetrics:
        """
        Get overall graph metrics.

        Returns:
            GraphMetrics with summary statistics

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built:
            raise RuntimeError("KnowledgeGraph is not built. Call .build() before getting metrics.")

        # After build(), metrics is guaranteed to be set
        assert self.metrics is not None, "metrics should be computed after build()"
        return self.metrics

    def format_stats(self) -> str:
        """
        Format graph statistics as a human-readable string.

        Returns:
            Formatted statistics string

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before formatting stats."
            )
        return self._reporter.format_stats()

    def get_actionable_recommendations(self) -> list[str]:
        """
        Generate actionable recommendations for improving site structure.

        Returns:
            List of recommendation strings with emoji prefixes

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before getting recommendations."
            )
        return self._reporter.get_actionable_recommendations()

    def get_seo_insights(self) -> list[str]:
        """
        Generate SEO-focused insights about site structure.

        Returns:
            List of SEO insight strings with emoji prefixes

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before getting SEO insights."
            )
        return self._reporter.get_seo_insights()

    def get_content_gaps(self) -> list[str]:
        """
        Identify content gaps based on link structure and taxonomies.

        Returns:
            List of content gap descriptions

        Raises:
            RuntimeError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before getting content gaps."
            )
        return self._reporter.get_content_gaps()

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

        Raises:
            RuntimeError: If graph hasn't been built yet

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = graph.compute_pagerank()
            >>> top_pages = results.get_top_pages(10)
        """
        if not self._built:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before computing PageRank."
            )

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

        Raises:
            RuntimeError: If graph hasn't been built yet
            ValueError: If seed_pages is empty

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> # Find pages related to Python posts
            >>> python_posts = {p for p in site.pages if 'python' in p.tags}
            >>> results = graph.compute_personalized_pagerank(python_posts)
            >>> related = results.get_top_pages(10)
        """
        if not self._built:
            raise RuntimeError(
                "KnowledgeGraph is not built. Call .build() before computing PageRank."
            )

        if not seed_pages:
            raise ValueError(
                "Personalized PageRank requires at least one seed page to bias the ranking."
            )

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

        if self._pagerank_results is None:
            return []
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

        if self._pagerank_results is None:
            return 0.0
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

        if self._community_results is None:
            return None
        community = self._community_results.get_community_for_page(page)
        return community.id if community else None

    def analyze_paths(
        self,
        force_recompute: bool = False,
        k_pivots: int = 100,
        seed: int = 42,
        auto_approximate_threshold: int = 500,
    ) -> PathAnalysisResults:
        """
        Analyze navigation paths and centrality metrics.

        Computes:
        - Betweenness centrality: Pages that act as bridges
        - Closeness centrality: Pages that are easily accessible
        - Network diameter and average path length

        For large sites (> auto_approximate_threshold pages), uses pivot-based
        approximation for O(k*N) complexity instead of O(N²).

        Args:
            force_recompute: If True, recompute even if cached
            k_pivots: Number of pivot nodes for approximation (default: 100)
            seed: Random seed for deterministic results (default: 42)
            auto_approximate_threshold: Use exact if pages <= this (default: 500)

        Returns:
            PathAnalysisResults with centrality metrics

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = graph.analyze_paths()
            >>> bridges = results.get_top_bridges(10)
            >>> print(f"Approximate: {results.is_approximate}")
        """
        if not self._built:
            raise RuntimeError("Must call build() before analyzing paths")

        # Return cached results unless forced
        if self._path_results and not force_recompute:
            logger.debug("path_analysis_cached", action="returning cached results")
            return self._path_results

        # Import here to avoid circular dependency
        from bengal.analysis.path_analysis import PathAnalyzer

        analyzer = PathAnalyzer(
            graph=self,
            k_pivots=k_pivots,
            seed=seed,
            auto_approximate_threshold=auto_approximate_threshold,
        )
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

        if self._path_results is None:
            return 0.0
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

        if self._path_results is None:
            return 0.0
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

        if self._link_suggestions is None:
            return []
        suggestions = self._link_suggestions.get_suggestions_for_page(page, limit)
        return [(s.target, s.score, s.reasons) for s in suggestions]
