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
    - bengal/analysis/graph_builder.py: GraphBuilder implementation
    - bengal/analysis/graph_metrics.py: MetricsCalculator implementation
    - bengal/analysis/graph_analysis.py: GraphAnalyzer implementation
    - bengal/analysis/graph_reporting.py: GraphReporter implementation
    - bengal/analysis/link_types.py: Semantic link type definitions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.analysis.graph_analysis import GraphAnalyzer
from bengal.analysis.graph_builder import GraphBuilder
from bengal.analysis.graph_metrics import GraphMetrics, MetricsCalculator, PageConnectivity
from bengal.analysis.graph_reporting import GraphReporter
from bengal.analysis.link_types import (
    DEFAULT_THRESHOLDS,
    DEFAULT_WEIGHTS,
    ConnectivityLevel,
    ConnectivityReport,
    LinkMetrics,
    LinkType,
)
from bengal.errors import BengalError, ErrorCode
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

# Re-export for backward compatibility
__all__ = ["GraphMetrics", "KnowledgeGraph", "PageConnectivity"]


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

        # Graph data structures (populated by GraphBuilder)
        self.incoming_refs: dict[Page, float] = {}
        self.outgoing_refs: dict[Page, set[Page]] = {}
        self.link_metrics: dict[Page, LinkMetrics] = {}
        self.link_types: dict[tuple[Page | None, Page], LinkType] = {}
        # Reverse adjacency list for O(E) PageRank iteration
        # Maps each page to the list of pages that link TO it
        # RFC: rfc-analysis-algorithm-optimization
        self.incoming_edges: dict[Page, list[Page]] = {}

        # Analysis results
        self.metrics: GraphMetrics | None = None
        self._built = False

        # Analysis results cache
        self._pagerank_results: PageRankResults | None = None
        self._community_results: CommunityDetectionResults | None = None
        self._path_results: PathAnalysisResults | None = None
        self._link_suggestions: LinkSuggestionResults | None = None

        # Delegated components (initialized after build)
        self._builder: GraphBuilder | None = None
        self._metrics_calculator: MetricsCalculator | None = None
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

        # Initialize and run the builder
        self._builder = GraphBuilder(self.site, exclude_autodoc=self.exclude_autodoc)

        analysis_pages = self._builder.get_analysis_pages()
        total_analysis_pages = len(analysis_pages)
        excluded_count = len(self.site.pages) - total_analysis_pages

        logger.info(
            "knowledge_graph_build_start",
            total_pages=len(self.site.pages),
            analysis_pages=total_analysis_pages,
            excluded_autodoc=excluded_count if self.exclude_autodoc else 0,
        )

        # Build the graph
        self._builder.build()

        # Copy data from builder to self (for backward compatibility)
        self.incoming_refs = dict(self._builder.incoming_refs)
        self.outgoing_refs = dict(self._builder.outgoing_refs)
        self.link_metrics = dict(self._builder.link_metrics)
        self.link_types = dict(self._builder.link_types)
        # Copy reverse adjacency list for O(E) PageRank
        self.incoming_edges = dict(self._builder.incoming_edges)

        # Initialize metrics calculator
        self._metrics_calculator = MetricsCalculator(
            incoming_refs=self.incoming_refs,
            outgoing_refs=self.outgoing_refs,
            analysis_pages=analysis_pages,
            hub_threshold=self.hub_threshold,
            leaf_threshold=self.leaf_threshold,
        )

        # Compute metrics
        self.metrics = self._metrics_calculator.compute_metrics()

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
        if self._builder:
            return self._builder.get_analysis_pages()

        # Fallback if build() not called yet
        from bengal.utils.autodoc import is_autodoc_page

        if not self.exclude_autodoc:
            return list(self.site.pages)
        return [p for p in self.site.pages if not is_autodoc_page(p)]

    def get_connectivity(self, page: Page) -> PageConnectivity:
        """
        Get connectivity information for a specific page.

        Args:
            page: Page to analyze

        Returns:
            PageConnectivity with detailed metrics

        Raises:
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before accessing connectivity data",
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
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting hub pages",
            )
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
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting leaf pages",
            )
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
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting orphan pages",
            )
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
            BengalError: If graph hasn't been built yet

        Example:
            >>> graph.build()
            >>> report = graph.get_connectivity_report()
            >>> print(f"Isolated: {len(report.isolated)}")
            >>> print(f"Distribution: {report.get_distribution()}")
        """
        if not self._built:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting connectivity report",
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
            BengalError: If graph hasn't been built yet
        """
        if not self._built:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting link metrics",
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
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting connectivity score",
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
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._analyzer is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting page layers",
            )
        return self._analyzer.get_layers()

    def get_metrics(self) -> GraphMetrics:
        """
        Get overall graph metrics.

        Returns:
            GraphMetrics with summary statistics

        Raises:
            BengalError: If graph hasn't been built yet
        """
        if not self._built:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting metrics",
            )

        # After build(), metrics is guaranteed to be set
        assert self.metrics is not None, "metrics should be computed after build()"
        return self.metrics

    def format_stats(self) -> str:
        """
        Format graph statistics as a human-readable string.

        Returns:
            Formatted statistics string

        Raises:
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before formatting stats",
            )
        return self._reporter.format_stats()

    def get_actionable_recommendations(self) -> list[str]:
        """
        Generate actionable recommendations for improving site structure.

        Returns:
            List of recommendation strings with emoji prefixes

        Raises:
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting recommendations",
            )
        return self._reporter.get_actionable_recommendations()

    def get_seo_insights(self) -> list[str]:
        """
        Generate SEO-focused insights about site structure.

        Returns:
            List of SEO insight strings with emoji prefixes

        Raises:
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting SEO insights",
            )
        return self._reporter.get_seo_insights()

    def get_content_gaps(self) -> list[str]:
        """
        Identify content gaps based on link structure and taxonomies.

        Returns:
            List of content gap descriptions

        Raises:
            BengalError: If graph hasn't been built yet
        """
        if not self._built or self._reporter is None:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before getting content gaps",
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
            BengalError: If graph hasn't been built yet

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = graph.compute_pagerank()
            >>> top_pages = results.get_top_pages(10)
        """
        if not self._built:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before computing PageRank",
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
            BengalError: If graph hasn't been built yet or seed_pages is empty

        Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> # Find pages related to Python posts
            >>> python_posts = {p for p in site.pages if 'python' in p.tags}
            >>> results = graph.compute_personalized_pagerank(python_posts)
            >>> related = results.get_top_pages(10)
        """
        if not self._built:
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before computing PageRank",
            )

        if not seed_pages:
            raise BengalError(
                "Personalized PageRank requires at least one seed page",
                code=ErrorCode.G002,
                suggestion="Provide at least one seed page to bias the ranking",
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
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before detecting communities",
            )

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
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before analyzing paths",
            )

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
            raise BengalError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion="Call graph.build() before generating link suggestions",
            )

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
