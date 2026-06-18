"""
Community Detection for Bengal SSG.

Discovers topical clusters in content using the Louvain method, a fast and
scalable algorithm for community detection. Communities represent natural
groupings of related pages based on link structure, useful for understanding
content organization and identifying topic areas.

Algorithm:
The Louvain method optimizes modularity (network clustering quality) in two phases:
1. Local optimization: Move nodes to communities that maximize modularity gain
2. Aggregation: Treat each community as a single node and repeat
Phases repeat until no further improvement is possible.

Key Concepts:
- Modularity: Quality metric for network partitions (-1.0 to 1.0, higher is better)
- Community: Group of densely connected pages sharing topics/themes
- Resolution: Parameter controlling community granularity (higher = more communities)

Classes:
Community: A detected group of related pages
CommunityDetectionResults: All communities with quality metrics
LouvainCommunityDetector: Main detection algorithm

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.detect_communities(resolution=1.0)
    >>> print(f"Found {len(results.communities)} communities")
    >>> for community in results.get_largest_communities(5):
    ...     print(f"Community {community.id}: {community.size} pages")

References:
Blondel, V. D., et al. (2008). Fast unfolding of communities in large networks.
Journal of Statistical Mechanics: Theory and Experiment.

See Also:
- bengal/analysis/knowledge_graph.py: Graph coordination

"""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.analysis.utils.pages import get_content_pages, stable_page_id
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
    from bengal.protocols import PageLike

logger = get_logger(__name__)

# Fixed default seed for the node-shuffle PRNG when no explicit seed is passed.
# Louvain's per-iteration shuffle MUST use a local seeded PRNG (never the global
# ``random`` module): community ids are baked into ``graph.json`` and the
# warm==cold byte-parity contract is CI-guarded, so the result has to be
# reproducible across builds. No build caller passes a seed, so this constant is
# what the build path actually uses.
_LOUVAIN_SEED = 42


@dataclass
class Community:
    """
    A community of related pages discovered through link structure.

    Represents a group of pages that are densely connected to each other
    and share similar topics or themes. Useful for understanding content
    organization and identifying topic clusters.

    Attributes:
        id: Unique community identifier
        pages: Set of pages belonging to this community
        size: Number of pages in the community
        density: Internal connection density (0.0-1.0)

    """

    id: int
    pages: set[PageLike]

    @property
    def size(self) -> int:
        """Number of pages in this community."""
        return len(self.pages)

    def get_top_pages_by_degree(self, limit: int = 5) -> list[PageLike]:
        """Get most connected pages in this community."""
        # Will be populated with degree info from the detector
        return list(self.pages)[:limit]


@dataclass
class CommunityDetectionResults:
    """
    Results from community detection analysis.

    Contains discovered communities and quality metrics. Communities
    represent natural groupings of related pages based on link structure.

    Attributes:
        communities: List of detected communities
        modularity: Modularity score (quality metric, -1.0 to 1.0, higher is better)
        num_communities: Total number of communities detected

    """

    communities: list[Community]
    modularity: float
    iterations: int

    def get_community_for_page(self, page: PageLike) -> Community | None:
        """Find which community a page belongs to."""
        for community in self.communities:
            if page in community.pages:
                return community
        return None

    def get_largest_communities(self, limit: int = 10) -> list[Community]:
        """Get largest communities by page count."""
        sorted_communities = sorted(self.communities, key=lambda c: c.size, reverse=True)
        return sorted_communities[:limit]

    def get_communities_above_size(self, min_size: int) -> list[Community]:
        """Get communities with at least min_size pages."""
        return [c for c in self.communities if c.size >= min_size]


class LouvainCommunityDetector:
    """
    Detect communities using the Louvain method.

    The Louvain algorithm is a greedy optimization method that attempts to
    optimize the modularity of a partition of the network. It runs in two phases:

    1. Modularity Optimization: Each node is moved to the community that yields
       the largest increase in modularity.

    2. Community Aggregation: A new network is built where nodes are communities
       and edges represent connections between communities.

    These phases are repeated until no further improvement is possible.

    Example:
            >>> detector = LouvainCommunityDetector(knowledge_graph)
            >>> results = detector.detect()
            >>> print(f"Found {len(results.communities)} communities")
            >>> for community in results.get_largest_communities(5):
            ...     print(f"Community {community.id}: {community.size} pages")

    """

    def __init__(
        self, graph: KnowledgeGraph, resolution: float = 1.0, random_seed: int | None = None
    ):
        """
        Initialize Louvain community detector.

        Args:
            graph: KnowledgeGraph with page connections
            resolution: Resolution parameter (higher = more communities)
            random_seed: Random seed for reproducibility
        """
        self.graph = graph
        self.resolution = resolution
        self.random_seed = random_seed

        # Local, deterministic PRNG — never the global ``random`` module, whose
        # state would leak across analyses and break reproducible output.
        self._rng = random.Random(random_seed if random_seed is not None else _LOUVAIN_SEED)

    def detect(self) -> CommunityDetectionResults:
        """
        Detect communities using Louvain method.

        Returns:
            CommunityDetectionResults with discovered communities
        """
        # Use content pages (excludes autodoc and generated pages)
        pages = get_content_pages(self.graph)

        if len(pages) == 0:
            logger.warning("community_detection_no_pages")
            return CommunityDetectionResults(communities=[], modularity=0.0, iterations=0)

        logger.info("community_detection_start", total_pages=len(pages), resolution=self.resolution)

        # Initialize: each page in its own community
        page_to_community: dict[PageLike, int] = {page: i for i, page in enumerate(pages)}

        # Build edge weights (use bidirectional edges for undirected graph)
        edge_weights = self._build_edge_weights(pages)
        total_weight = sum(edge_weights.values())

        if total_weight == 0:
            # No connections - each page is its own community
            logger.warning("community_detection_no_connections")
            communities = [Community(id=i, pages={page}) for i, page in enumerate(pages)]
            return CommunityDetectionResults(communities=communities, modularity=0.0, iterations=0)

        # Compute node degrees
        node_degrees = self._compute_node_degrees(pages, edge_weights)

        # Adjacency index (page -> [(neighbor, weight), ...]) and per-community
        # total degree, both maintained so each modularity-gain evaluation is
        # O(degree) instead of O(N). Without this the inner loop is
        # O(N^2 * degree * iterations): fine on tiny test graphs but tens of
        # minutes on a real docs site (1000+ pages) — and community detection is
        # now wired into every build, so this is load-bearing for build time.
        adjacency: dict[PageLike, list[tuple[PageLike, float]]] = {p: [] for p in pages}
        for edge, weight in edge_weights.items():
            members = list(edge)
            if len(members) == 2:
                a, b = members
                adjacency[a].append((b, weight))
                adjacency[b].append((a, weight))

        comm_degree: dict[int, float] = defaultdict(float)
        for p in pages:
            comm_degree[page_to_community[p]] += node_degrees.get(p, 0.0)

        # Louvain algorithm main loop
        iteration = 0
        improvement = True
        best_modularity = -1.0

        while improvement and iteration < 100:
            improvement = False
            iteration += 1

            # Randomize order to avoid bias (deterministic: local seeded PRNG).
            shuffled_pages = list(pages)
            self._rng.shuffle(shuffled_pages)

            # Phase 1: Move nodes to optimize modularity
            for page in shuffled_pages:
                current_community = page_to_community[page]
                k_i = node_degrees.get(page, 0.0)

                # Weight from this page into each neighboring community (O(degree)).
                weight_to_comm: dict[int, float] = defaultdict(float)
                for neighbor, w in adjacency.get(page, ()):
                    weight_to_comm[page_to_community[neighbor]] += w

                # Best move among neighboring communities (sorted candidate order
                # for a deterministic tie-break). The current community is the
                # baseline (gain 0); a candidate must beat it by > 1e-10. Since
                # `page` sits in current_community, comm_degree[cand] for cand !=
                # current is the correct sigma_tot (degree sum excluding page) —
                # identical to the previous O(N) recomputation, just incremental.
                best_community = current_community
                best_gain = 0.0
                for cand in sorted(weight_to_comm):
                    if cand == current_community:
                        continue
                    sigma_tot = comm_degree[cand]
                    gain = (
                        weight_to_comm[cand]
                        - self.resolution * sigma_tot * k_i / (2 * total_weight)
                    ) / total_weight
                    if gain > best_gain:
                        best_gain = gain
                        best_community = cand

                # Move to best community if improvement found; keep comm_degree in
                # sync so later moves this pass see the updated community totals.
                if best_community != current_community and best_gain > 1e-10:
                    comm_degree[current_community] -= k_i
                    comm_degree[best_community] += k_i
                    page_to_community[page] = best_community
                    improvement = True

            # Compute current modularity
            current_modularity = self._compute_modularity(
                page_to_community, edge_weights, node_degrees, total_weight
            )

            best_modularity = max(best_modularity, current_modularity)

            logger.debug(
                "community_detection_iteration",
                iteration=iteration,
                modularity=current_modularity,
                improvement=improvement,
            )

        # Convert to Community objects
        community_map: dict[int, set[PageLike]] = defaultdict(set)
        for page, community_id in page_to_community.items():
            community_map[community_id].add(page)

        # Renumber communities by a build-stable rank: largest first, ties broken
        # by the smallest member node-id. The internal community labels are
        # enumerate/shuffle-derived and therefore NOT stable to bake; this rank
        # is. It also gives downstream a deterministic ordering (community 0 =
        # biggest topic), which the visualizer uses to assign a stable color
        # index per community.
        site = getattr(self.graph, "site", None)

        def _min_member_id(pages_set: set[PageLike]) -> str:
            return min(stable_page_id(site, p) for p in pages_set)

        ordered = sorted(
            community_map.values(),
            key=lambda pages_set: (-len(pages_set), _min_member_id(pages_set)),
        )
        communities = [Community(id=i, pages=pages_set) for i, pages_set in enumerate(ordered)]

        logger.info(
            "community_detection_complete",
            total_communities=len(communities),
            iterations=iteration,
            modularity=best_modularity,
        )

        return CommunityDetectionResults(
            communities=communities, modularity=best_modularity, iterations=iteration
        )

    def _build_edge_weights(self, pages: Sequence[PageLike]) -> dict[frozenset[PageLike], float]:
        """
        Build edge weights from the graph.

        Uses frozenset to represent undirected edges.
        """
        edge_weights: dict[frozenset[PageLike], float] = defaultdict(float)

        for page in pages:
            outgoing = self.graph.outgoing_refs.get(page, set())
            for target in outgoing:
                if target in pages:  # Only consider pages in our set
                    edge = frozenset([page, target])
                    edge_weights[edge] += 1.0

        return edge_weights

    def _compute_node_degrees(
        self, pages: Sequence[PageLike], edge_weights: dict[frozenset[PageLike], float]
    ) -> dict[PageLike, float]:
        """Compute weighted degree for each node."""
        node_degrees: dict[PageLike, float] = defaultdict(float)

        for edge, weight in edge_weights.items():
            edge_list = list(edge)
            if len(edge_list) == 2:
                # Normal edge between two different nodes
                node_degrees[edge_list[0]] += weight
                node_degrees[edge_list[1]] += weight
            elif len(edge_list) == 1:
                # Self-loop
                node_degrees[edge_list[0]] += 2 * weight

        return node_degrees

    def _compute_modularity(
        self,
        page_to_community: dict[PageLike, int],
        edge_weights: dict[frozenset[PageLike], float],
        node_degrees: dict[PageLike, float],
        total_weight: float,
    ) -> float:
        """Compute Newman's modularity Q."""
        if total_weight == 0:
            return 0.0

        Q = 0.0

        for edge, weight in edge_weights.items():
            edge_list = list(edge)
            if len(edge_list) == 2:
                u, v = edge_list
                if page_to_community[u] == page_to_community[v]:
                    # Same community
                    k_u = node_degrees.get(u, 0.0)
                    k_v = node_degrees.get(v, 0.0)
                    Q += weight - self.resolution * k_u * k_v / (2 * total_weight)
            elif len(edge_list) == 1:
                # Self-loop
                u = edge_list[0]
                k_u = node_degrees.get(u, 0.0)
                Q += weight - self.resolution * k_u * k_u / (2 * total_weight)

        return Q / total_weight


def detect_communities(
    graph: KnowledgeGraph, resolution: float = 1.0, random_seed: int | None = None
) -> CommunityDetectionResults:
    """
    Convenience function to detect communities.

    Args:
        graph: KnowledgeGraph with page connections
        resolution: Resolution parameter (higher = more communities)
        random_seed: Random seed for reproducibility

    Returns:
        CommunityDetectionResults with discovered communities

    Example:
            >>> graph = KnowledgeGraph(site)
            >>> graph.build()
            >>> results = detect_communities(graph)
            >>> print(f"Found {len(results.communities)} communities")

    """
    detector = LouvainCommunityDetector(graph, resolution=resolution, random_seed=random_seed)
    return detector.detect()
