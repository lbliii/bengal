"""
Path Analysis for Bengal SSG.

Analyzes navigation patterns and page accessibility through centrality metrics.
Identifies bridge pages (critical for navigation), accessible pages (easy to
reach), and computes network-wide statistics like diameter and average path length.

Centrality Metrics:
    - Betweenness: How often a page appears on shortest paths between others.
      High betweenness indicates bridge pages that connect different site areas.
    - Closeness: How close a page is to all other pages (average distance).
      High closeness indicates easily accessible, well-connected pages.

Network Metrics:
    - Diameter: Longest shortest path (maximum clicks between any two pages)
    - Average Path Length: Mean shortest path length across all page pairs

Performance:
    For large sites (>500 pages by default), automatically uses pivot-based
    approximation for O(k*N) complexity instead of O(N²). This provides
    ~100x speedup for 10K page sites while maintaining accurate rankings.

Classes:
    PathAnalysisResults: Centrality scores and network metrics
    PathSearchResult: Results from path finding with safety metadata
    PathAnalyzer: Main analysis algorithms

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.analyze_paths()
    >>> bridges = results.get_top_bridges(10)
    >>> accessible = results.get_most_accessible(10)
    >>> print(f"Diameter: {results.diameter} clicks")
    >>> print(f"Approximate: {results.is_approximate}")

References:
    Brandes, U. (2001). A faster algorithm for betweenness centrality.
    Journal of Mathematical Sociology.

    Bader, D. A., et al. (2007). Approximating betweenness centrality.
    Algorithms and Models for the Web-Graph.

See Also:
    - bengal/analysis/knowledge_graph.py: Graph coordination
    - bengal/analysis/link_suggestions.py: Uses centrality for suggestions
"""

from __future__ import annotations

import random
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.core.page import Page

logger = get_logger(__name__)

# Type alias for progress callback: (current, total, phase_name) -> None
type ProgressCallback = Callable[[int, int, str], None]


@dataclass
class PathAnalysisResults:
    """
    Results from path analysis and centrality computations.

    Contains centrality metrics that identify important pages in the
    site's link structure. High betweenness indicates bridge pages,
    high closeness indicates easily accessible pages.

    Attributes:
        betweenness_centrality: Map of pages to betweenness scores (0.0-1.0)
        closeness_centrality: Map of pages to closeness scores (0.0-1.0)
        diameter: Network diameter (longest shortest path)
        avg_path_length: Average shortest path length between all page pairs
        is_approximate: True if approximation was used (for large sites)
        pivots_used: Number of pivot nodes used (if approximate)
    """

    betweenness_centrality: dict[Page, float]
    closeness_centrality: dict[Page, float]
    avg_path_length: float
    diameter: int  # Longest shortest path
    is_approximate: bool = False
    pivots_used: int = 0

    def get_top_bridges(self, limit: int = 20) -> list[tuple[Page, float]]:
        """
        Get pages with highest betweenness centrality (bridge pages).

        Args:
            limit: Number of pages to return

        Returns:
            List of (page, centrality) tuples sorted by centrality descending
        """
        sorted_pages = sorted(self.betweenness_centrality.items(), key=lambda x: x[1], reverse=True)
        return sorted_pages[:limit]

    def get_most_accessible(self, limit: int = 20) -> list[tuple[Page, float]]:
        """
        Get most accessible pages (highest closeness centrality).

        Args:
            limit: Number of pages to return

        Returns:
            List of (page, centrality) tuples sorted by centrality descending
        """
        sorted_pages = sorted(self.closeness_centrality.items(), key=lambda x: x[1], reverse=True)
        return sorted_pages[:limit]

    def get_betweenness(self, page: Page) -> float:
        """Get betweenness centrality for specific page."""
        return self.betweenness_centrality.get(page, 0.0)

    def get_closeness(self, page: Page) -> float:
        """Get closeness centrality for specific page."""
        return self.closeness_centrality.get(page, 0.0)


@dataclass
class PathSearchResult:
    """
    Result from find_all_paths including metadata about the search.

    Attributes:
        paths: List of paths found (each path is a list of pages)
        complete: True if search completed, False if terminated early
        termination_reason: Reason for early termination (if any)
    """

    paths: list[list[Page]] = field(default_factory=list)
    complete: bool = True
    termination_reason: str | None = None


class PathAnalyzer:
    """
    Analyze navigation paths and page accessibility.

    Computes centrality metrics to identify:
    - Bridge pages (high betweenness): Pages that connect different parts of the site
    - Accessible pages (high closeness): Pages that are easy to reach from anywhere
    - Navigation bottlenecks: Critical pages for site navigation

    For large sites (>500 pages by default), uses pivot-based approximation
    to achieve O(k*N) complexity instead of O(N²). This provides ~100x speedup
    for 10k page sites while maintaining accurate relative rankings.

    Example:
        >>> analyzer = PathAnalyzer(knowledge_graph, k_pivots=100)
        >>> results = analyzer.analyze(progress_callback=lambda c, t, p: print(f"{p}: {c}/{t}"))
        >>> bridges = results.get_top_bridges(10)
        >>> print(f"Top bridge: {bridges[0][0].title}")
        >>> print(f"Approximate: {results.is_approximate}")
    """

    # Default configuration
    DEFAULT_K_PIVOTS = 100
    DEFAULT_SEED = 42
    DEFAULT_AUTO_THRESHOLD = 500

    def __init__(
        self,
        graph: KnowledgeGraph,
        k_pivots: int = DEFAULT_K_PIVOTS,
        seed: int = DEFAULT_SEED,
        auto_approximate_threshold: int = DEFAULT_AUTO_THRESHOLD,
    ):
        """
        Initialize path analyzer.

        Args:
            graph: KnowledgeGraph with page connections
            k_pivots: Number of pivot nodes to use for approximation (default: 100)
            seed: Random seed for deterministic pivot selection (default: 42)
            auto_approximate_threshold: Use exact algorithm if page count <= this (default: 500)
        """
        self.graph = graph
        self.k_pivots = k_pivots
        self.seed = seed
        self.auto_approximate_threshold = auto_approximate_threshold

    def find_shortest_path(self, source: Page, target: Page) -> list[Page] | None:
        """
        Find shortest path between two pages using BFS.

        Args:
            source: Starting page
            target: Destination page

        Returns:
            List of pages representing the path, or None if no path exists

        Example:
            >>> path = analyzer.find_shortest_path(page_a, page_b)
            >>> if path:
            ...     print(f"Path length: {len(path) - 1}")
        """
        if source == target:
            return [source]

        # BFS
        queue: deque[Page] = deque([source])
        visited: set[Page] = {source}
        parent: dict[Page, Page] = {}

        while queue:
            current = queue.popleft()

            # Check neighbors
            neighbors = self.graph.outgoing_refs.get(current, set())
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append(neighbor)

                    if neighbor == target:
                        # Reconstruct path
                        path = [target]
                        node = target
                        while node != source:
                            node = parent[node]
                            path.append(node)
                        return list(reversed(path))

        return None  # No path found

    def analyze(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> PathAnalysisResults:
        """
        Compute path-based centrality metrics.

        Computes:
        - Betweenness centrality: How often a page appears on shortest paths
        - Closeness centrality: How close a page is to all other pages
        - Network diameter: Longest shortest path
        - Average path length

        For large sites, automatically uses pivot-based approximation for
        O(k*N) complexity instead of O(N²).

        Args:
            progress_callback: Optional callback for progress updates.
                Called as callback(current, total, phase) where phase is
                "betweenness" or "closeness".

        Returns:
            PathAnalysisResults with all metrics
        """
        # Use analysis pages from graph (excludes autodoc if configured)
        pages = self.graph.get_analysis_pages()
        # Also exclude generated pages
        pages = [p for p in pages if not p.metadata.get("_generated")]

        if len(pages) == 0:
            logger.warning("path_analysis_no_pages")
            return PathAnalysisResults(
                betweenness_centrality={},
                closeness_centrality={},
                avg_path_length=0.0,
                diameter=0,
            )

        # Determine if we should use approximation
        use_approximate = len(pages) > self.auto_approximate_threshold
        pivots_used = 0

        if use_approximate:
            pivots_used = min(self.k_pivots, len(pages))
            logger.info(
                "path_analysis_start_approximate",
                total_pages=len(pages),
                pivots=pivots_used,
                threshold=self.auto_approximate_threshold,
            )
        else:
            logger.info("path_analysis_start_exact", total_pages=len(pages))

        # Compute betweenness centrality
        betweenness = self._compute_betweenness_centrality(
            pages, use_approximate, progress_callback
        )

        # Compute closeness centrality
        closeness, avg_path_length, diameter = self._compute_closeness_centrality(
            pages, use_approximate, progress_callback
        )

        logger.info(
            "path_analysis_complete",
            avg_path_length=avg_path_length,
            diameter=diameter,
            approximate=use_approximate,
        )

        return PathAnalysisResults(
            betweenness_centrality=betweenness,
            closeness_centrality=closeness,
            avg_path_length=avg_path_length,
            diameter=diameter,
            is_approximate=use_approximate,
            pivots_used=pivots_used if use_approximate else len(pages),
        )

    def _compute_betweenness_centrality(
        self,
        pages: list[Page],
        use_approximate: bool,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[Page, float]:
        """
        Compute betweenness centrality using Brandes' algorithm.

        Betweenness measures how often a page appears on shortest paths between
        other pages. High betweenness indicates a "bridge" page.

        For large sites, uses pivot-based approximation: only compute from
        k randomly selected source nodes and scale results.

        Args:
            pages: List of pages to analyze
            use_approximate: If True, use pivot-based approximation
            progress_callback: Optional progress callback

        Returns:
            Dictionary mapping pages to betweenness centrality scores
        """
        betweenness: dict[Page, float] = {page: 0.0 for page in pages}

        # Select sources (all pages for exact, k pivots for approximate)
        if use_approximate:
            rng = random.Random(self.seed)
            sources = rng.sample(pages, min(self.k_pivots, len(pages)))
        else:
            sources = pages

        total_sources = len(sources)

        # For each selected source
        for i, source in enumerate(sources):
            if progress_callback:
                progress_callback(i + 1, total_sources, "betweenness")

            # BFS to find shortest paths
            stack: list[Page] = []
            predecessors: dict[Page, list[Page]] = {p: [] for p in pages}
            sigma: dict[Page, int] = {p: 0 for p in pages}
            sigma[source] = 1
            distance: dict[Page, int] = {p: -1 for p in pages}
            distance[source] = 0

            queue: deque[Page] = deque([source])

            while queue:
                current = queue.popleft()
                stack.append(current)

                neighbors = self.graph.outgoing_refs.get(current, set())
                for neighbor in neighbors:
                    if neighbor not in pages:
                        continue

                    # First time we see this neighbor
                    if distance[neighbor] < 0:
                        queue.append(neighbor)
                        distance[neighbor] = distance[current] + 1

                    # Shortest path to neighbor via current
                    if distance[neighbor] == distance[current] + 1:
                        sigma[neighbor] += sigma[current]
                        predecessors[neighbor].append(current)

            # Accumulation (back-propagation)
            delta: dict[Page, float] = {p: 0.0 for p in pages}

            while stack:
                current = stack.pop()
                for pred in predecessors[current]:
                    if sigma[current] > 0:
                        delta[pred] += (sigma[pred] / sigma[current]) * (1 + delta[current])

                if current != source:
                    betweenness[current] += delta[current]

        # Normalize
        n = len(pages)
        if n > 2:
            if use_approximate:
                # Scale by ratio of total pages to pivots, then normalize
                scale = n / len(sources)
                normalization = (n - 1) * (n - 2)
                betweenness = {p: (c * scale) / normalization for p, c in betweenness.items()}
            else:
                # Standard normalization for directed graphs
                normalization = (n - 1) * (n - 2)
                betweenness = {p: c / normalization for p, c in betweenness.items()}

        return betweenness

    def _compute_closeness_centrality(
        self,
        pages: list[Page],
        use_approximate: bool,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[dict[Page, float], float, int]:
        """
        Compute closeness centrality and network metrics.

        Closeness measures how close a page is to all other pages.
        Higher closeness = more accessible.

        For large sites, uses pivot-based approximation: only compute
        distances from k randomly selected source nodes.

        Args:
            pages: List of pages to analyze
            use_approximate: If True, use pivot-based approximation
            progress_callback: Optional progress callback

        Returns:
            Tuple of (closeness_dict, avg_path_length, diameter)
        """
        # Select sample pages (all for exact, k pivots for approximate)
        if use_approximate:
            rng = random.Random(self.seed + 1)  # Different seed from betweenness
            sample_pages = rng.sample(pages, min(self.k_pivots, len(pages)))
        else:
            sample_pages = pages

        total_samples = len(sample_pages)

        # For approximate mode, we compute distances FROM pivots TO all nodes
        # Then estimate closeness based on average distance from pivots
        all_distances: list[int] = []
        max_distance = 0

        if use_approximate:
            # Compute distances from each pivot to all nodes
            pivot_distances: dict[Page, list[int]] = {page: [] for page in pages}

            for i, pivot in enumerate(sample_pages):
                if progress_callback:
                    progress_callback(i + 1, total_samples, "closeness")

                distances = self._bfs_distances(pivot, pages)

                for page, dist in distances.items():
                    if dist > 0:
                        pivot_distances[page].append(dist)
                        all_distances.append(dist)
                        max_distance = max(max_distance, dist)

            # Estimate closeness: 1 / average distance from pivots
            closeness: dict[Page, float] = {}
            for page in pages:
                dists = pivot_distances[page]
                if dists:
                    avg_distance = sum(dists) / len(dists)
                    closeness[page] = 1.0 / avg_distance
                else:
                    closeness[page] = 0.0
        else:
            # Exact computation: distances from each node to all others
            closeness = {}

            for i, page in enumerate(pages):
                if progress_callback:
                    progress_callback(i + 1, total_samples, "closeness")

                # BFS from this page to compute distances
                distances = self._bfs_distances(page, pages)

                # Closeness = 1 / (average distance to all reachable pages)
                reachable_distances = [d for d in distances.values() if d > 0]

                if reachable_distances:
                    avg_distance = sum(reachable_distances) / len(reachable_distances)
                    closeness[page] = 1.0 / avg_distance
                    all_distances.extend(reachable_distances)
                    max_distance = max(max_distance, *reachable_distances)
                else:
                    # Isolated page
                    closeness[page] = 0.0

        # Network-level metrics
        avg_path_length = sum(all_distances) / len(all_distances) if all_distances else 0.0
        diameter = max_distance

        return closeness, avg_path_length, diameter

    def _bfs_distances(self, source: Page, pages: list[Page]) -> dict[Page, int]:
        """Compute shortest path distances from source to all other pages."""
        distances: dict[Page, int] = {p: -1 for p in pages}
        distances[source] = 0

        queue: deque[Page] = deque([source])

        while queue:
            current = queue.popleft()
            current_dist = distances[current]

            neighbors = self.graph.outgoing_refs.get(current, set())
            for neighbor in neighbors:
                if neighbor in distances and distances[neighbor] < 0:
                    distances[neighbor] = current_dist + 1
                    queue.append(neighbor)

        return distances

    def find_all_paths(
        self,
        source: Page,
        target: Page,
        max_length: int = 10,
        max_paths: int = 1000,
        timeout_seconds: float | None = 30.0,
    ) -> PathSearchResult:
        """
        Find all simple paths between two pages with safety limits.

        This operation can be expensive for highly connected graphs.
        Safety limits prevent runaway computation:
        - max_length: Maximum path length to consider
        - max_paths: Stop after finding this many paths
        - timeout_seconds: Stop after this many seconds

        Args:
            source: Starting page
            target: Destination page
            max_length: Maximum path length to search (default: 10)
            max_paths: Maximum number of paths to find (default: 1000)
            timeout_seconds: Maximum time in seconds (default: 30.0, None for no limit)

        Returns:
            PathSearchResult with paths found and completion status

        Example:
            >>> result = analyzer.find_all_paths(page_a, page_b, max_paths=100)
            >>> if not result.complete:
            ...     print(f"Search stopped: {result.termination_reason}")
            >>> print(f"Found {len(result.paths)} paths")
        """
        if source == target:
            return PathSearchResult(paths=[[source]], complete=True)

        all_paths: list[list[Page]] = []
        start_time = time.monotonic()
        termination_reason: str | None = None

        def dfs(current: Page, path: list[Page], visited: set[Page]) -> bool:
            """DFS helper. Returns False to signal early termination."""
            nonlocal termination_reason

            # Check timeout
            if timeout_seconds is not None:
                elapsed = time.monotonic() - start_time
                if elapsed > timeout_seconds:
                    termination_reason = f"timeout after {timeout_seconds}s"
                    return False

            # Check path count limit
            if len(all_paths) >= max_paths:
                termination_reason = f"reached max_paths limit ({max_paths})"
                return False

            # Check path length
            if len(path) > max_length:
                return True  # Continue searching other branches

            if current == target:
                all_paths.append(path.copy())
                return True

            neighbors = self.graph.outgoing_refs.get(current, set())
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    if not dfs(neighbor, path, visited):
                        return False  # Propagate termination signal
                    path.pop()
                    visited.remove(neighbor)

            return True

        complete = dfs(source, [source], {source})

        return PathSearchResult(
            paths=all_paths,
            complete=complete and termination_reason is None,
            termination_reason=termination_reason,
        )

    def find_all_paths_simple(
        self,
        source: Page,
        target: Page,
        max_length: int = 10,
    ) -> list[list[Page]]:
        """
        Find all simple paths between two pages (legacy API).

        This is the original API preserved for backward compatibility.
        For new code, prefer find_all_paths() which includes safety limits.

        Args:
            source: Starting page
            target: Destination page
            max_length: Maximum path length to search

        Returns:
            List of paths (each path is a list of pages)
        """
        result = self.find_all_paths(
            source, target, max_length=max_length, max_paths=10000, timeout_seconds=60.0
        )
        return result.paths


def analyze_paths(
    graph: KnowledgeGraph,
    k_pivots: int = PathAnalyzer.DEFAULT_K_PIVOTS,
    seed: int = PathAnalyzer.DEFAULT_SEED,
    auto_approximate_threshold: int = PathAnalyzer.DEFAULT_AUTO_THRESHOLD,
    progress_callback: ProgressCallback | None = None,
) -> PathAnalysisResults:
    """
    Convenience function for path analysis.

    Args:
        graph: KnowledgeGraph with page connections
        k_pivots: Number of pivot nodes for approximation (default: 100)
        seed: Random seed for deterministic results (default: 42)
        auto_approximate_threshold: Use exact if pages <= this (default: 500)
        progress_callback: Optional progress callback

    Returns:
        PathAnalysisResults with centrality metrics

    Example:
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> results = analyze_paths(graph, k_pivots=50)
        >>> bridges = results.get_top_bridges(10)
        >>> print(f"Approximate: {results.is_approximate}")
    """
    analyzer = PathAnalyzer(
        graph,
        k_pivots=k_pivots,
        seed=seed,
        auto_approximate_threshold=auto_approximate_threshold,
    )
    return analyzer.analyze(progress_callback=progress_callback)
