"""
Path Analysis for Bengal SSG.

Implements algorithms for understanding navigation patterns and page accessibility:
- Shortest paths between pages (BFS-based)
- Betweenness centrality (identifies bridge pages)
- Closeness centrality (measures accessibility)

These metrics help optimize navigation structure and identify critical pages.

References:
    - Brandes, U. (2001). A faster algorithm for betweenness centrality.
      Journal of Mathematical Sociology.
"""


from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.core.page import Page

logger = get_logger(__name__)


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
    """

    betweenness_centrality: dict[Page, float]
    closeness_centrality: dict[Page, float]
    avg_path_length: float
    diameter: int  # Longest shortest path

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


class PathAnalyzer:
    """
    Analyze navigation paths and page accessibility.

    Computes centrality metrics to identify:
    - Bridge pages (high betweenness): Pages that connect different parts of the site
    - Accessible pages (high closeness): Pages that are easy to reach from anywhere
    - Navigation bottlenecks: Critical pages for site navigation

    Uses Brandes' algorithm for efficient betweenness centrality computation.

    Example:
        >>> analyzer = PathAnalyzer(knowledge_graph)
        >>> results = analyzer.analyze()
        >>> bridges = results.get_top_bridges(10)
        >>> print(f"Top bridge: {bridges[0][0].title}")
    """

    def __init__(self, graph: KnowledgeGraph):
        """
        Initialize path analyzer.

        Args:
            graph: KnowledgeGraph with page connections
        """
        self.graph = graph

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

    def analyze(self) -> PathAnalysisResults:
        """
        Compute path-based centrality metrics.

        Computes:
        - Betweenness centrality: How often a page appears on shortest paths
        - Closeness centrality: How close a page is to all other pages
        - Network diameter: Longest shortest path
        - Average path length

        Returns:
            PathAnalysisResults with all metrics
        """
        pages = [p for p in self.graph.site.pages if not p.metadata.get("_generated")]

        if len(pages) == 0:
            logger.warning("path_analysis_no_pages")
            return PathAnalysisResults(
                betweenness_centrality={}, closeness_centrality={}, avg_path_length=0.0, diameter=0
            )

        logger.info("path_analysis_start", total_pages=len(pages))

        # Compute betweenness centrality using Brandes' algorithm
        betweenness = self._compute_betweenness_centrality(pages)

        # Compute closeness centrality
        closeness, avg_path_length, diameter = self._compute_closeness_centrality(pages)

        logger.info("path_analysis_complete", avg_path_length=avg_path_length, diameter=diameter)

        return PathAnalysisResults(
            betweenness_centrality=betweenness,
            closeness_centrality=closeness,
            avg_path_length=avg_path_length,
            diameter=diameter,
        )

    def _compute_betweenness_centrality(self, pages: list[Page]) -> dict[Page, float]:
        """
        Compute betweenness centrality using Brandes' algorithm.

        Betweenness measures how often a page appears on shortest paths between
        other pages. High betweenness indicates a "bridge" page.
        """
        betweenness: dict[Page, float] = {page: 0.0 for page in pages}

        # For each page as source
        for source in pages:
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
                    delta[pred] += (sigma[pred] / sigma[current]) * (1 + delta[current])

                if current != source:
                    betweenness[current] += delta[current]

        # Normalize by dividing by (n-1)(n-2) for directed graphs
        n = len(pages)
        if n > 2:
            normalization = (n - 1) * (n - 2)
            betweenness = {p: c / normalization for p, c in betweenness.items()}

        return betweenness

    def _compute_closeness_centrality(
        self, pages: list[Page]
    ) -> tuple[dict[Page, float], float, int]:
        """
        Compute closeness centrality and network metrics.

        Closeness measures how close a page is to all other pages.
        Higher closeness = more accessible.

        Returns:
            Tuple of (closeness_dict, avg_path_length, diameter)
        """
        closeness: dict[Page, float] = {}
        all_distances: list[int] = []
        max_distance = 0

        for page in pages:
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
        self, source: Page, target: Page, max_length: int = 10
    ) -> list[list[Page]]:
        """
        Find all simple paths between two pages (up to max_length).

        Warning: Can be expensive for highly connected graphs.

        Args:
            source: Starting page
            target: Destination page
            max_length: Maximum path length to search

        Returns:
            List of paths (each path is a list of pages)
        """
        if source == target:
            return [[source]]

        all_paths: list[list[Page]] = []

        def dfs(current: Page, path: list[Page], visited: set[Page]) -> None:
            if len(path) > max_length:
                return

            if current == target:
                all_paths.append(path.copy())
                return

            neighbors = self.graph.outgoing_refs.get(current, set())
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        dfs(source, [source], {source})
        return all_paths


def analyze_paths(graph: KnowledgeGraph) -> PathAnalysisResults:
    """
    Convenience function for path analysis.

    Args:
        graph: KnowledgeGraph with page connections

    Returns:
        PathAnalysisResults with centrality metrics

    Example:
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> results = analyze_paths(graph)
        >>> bridges = results.get_top_bridges(10)
    """
    analyzer = PathAnalyzer(graph)
    return analyzer.analyze()
