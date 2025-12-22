"""
PageRank implementation for Bengal SSG.

Computes page importance scores using the iterative power method, the same
algorithm that powered early Google search. PageRank identifies influential
pages based on link structure, where a page is important if important pages
link to it.

Algorithm:
    PageRank iteratively distributes "importance" through the link graph:
    1. Initialize all pages with equal probability (1/N)
    2. Each iteration: pages pass their score to linked pages
    3. Damping factor (default 0.85) models random navigation jumps
    4. Continue until convergence or max iterations reached

Key Concepts:
    - Damping Factor: Probability of following links vs random jump (0.85 typical)
    - Convergence: Algorithm stops when max score change < threshold
    - Personalized PageRank: Bias toward seed pages for topic-focused ranking

Classes:
    PageRankResults: Scores and metadata from computation
    PageRankCalculator: Main algorithm implementation

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.compute_pagerank(damping=0.85)
    >>> top_pages = results.get_top_pages(10)
    >>> for page, score in top_pages:
    ...     print(f"{page.title}: {score:.4f}")

    >>> # Personalized PageRank for topic-focused ranking
    >>> python_posts = {p for p in site.pages if 'python' in p.tags}
    >>> results = graph.compute_personalized_pagerank(python_posts)

References:
    Brin, S., & Page, L. (1998). The anatomy of a large-scale hypertextual
    web search engine. Computer Networks and ISDN Systems.

See Also:
    - bengal/analysis/knowledge_graph.py: Graph coordination
    - bengal/analysis/link_suggestions.py: Uses PageRank for suggestions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.core.page import Page

logger = get_logger(__name__)


@dataclass
class PageRankResults:
    """
    Results from PageRank computation.

    Contains importance scores for all pages based on the link structure.
    Pages linked to by many important pages receive high scores.

    Attributes:
        scores: Map of pages to PageRank scores (normalized, sum to 1.0)
        iterations: Number of iterations until convergence
        converged: Whether the algorithm converged within max_iterations
    """

    scores: dict[Page, float]
    iterations: int
    converged: bool
    damping_factor: float

    def get_top_pages(self, limit: int = 20) -> list[tuple[Page, float]]:
        """
        Get top-ranked pages.

        Args:
            limit: Number of pages to return

        Returns:
            List of (page, score) tuples sorted by score descending
        """
        sorted_pages = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_pages[:limit]

    def get_pages_above_percentile(self, percentile: int) -> set[Page]:
        """
        Get pages above a certain percentile.

        Args:
            percentile: Percentile threshold (0-100)

        Returns:
            Set of pages above the threshold
        """
        if not self.scores:
            return set()

        scores_list = sorted(self.scores.values(), reverse=True)
        # Calculate how many pages to include based on percentile
        # e.g., 80th percentile means top 20% of pages
        n_pages = max(1, int(len(scores_list) * (100 - percentile) / 100))
        threshold_score = scores_list[n_pages - 1] if n_pages <= len(scores_list) else 0

        return {page for page, score in self.scores.items() if score >= threshold_score}

    def get_score(self, page: Page) -> float:
        """Get PageRank score for a specific page."""
        return self.scores.get(page, 0.0)


class PageRankCalculator:
    """
    Compute PageRank scores for pages in a site graph.

    PageRank is a link analysis algorithm that assigns numerical weights
    to pages based on their link structure. Pages that are linked to by
    many important pages receive high scores.

    The algorithm uses an iterative approach:
    1. Initialize all pages with equal probability (1/N)
    2. Iteratively update scores based on incoming links
    3. Continue until convergence or max iterations

    Example:
        >>> calculator = PageRankCalculator(knowledge_graph)
        >>> results = calculator.compute()
        >>> top_pages = results.get_top_pages(20)
        >>> print(f"Most important page: {top_pages[0][0].title}")
    """

    def __init__(
        self,
        graph: KnowledgeGraph,
        damping: float = 0.85,
        max_iterations: int = 100,
        convergence_threshold: float = 1e-6,
    ):
        """
        Initialize PageRank calculator.

        Args:
            graph: KnowledgeGraph with page connections
            damping: Probability of following links vs random jump (0-1)
                    Default 0.85 means 85% follow links, 15% random jump
            max_iterations: Maximum iterations before stopping
            convergence_threshold: Stop when max score change < this value
        """
        if not 0 < damping < 1:
            raise ValueError(f"Damping factor must be between 0 and 1, got {damping}")

        if max_iterations < 1:
            raise ValueError(f"Max iterations must be >= 1, got {max_iterations}")

        self.graph = graph
        self.damping = damping
        self.max_iterations = max_iterations
        self.threshold = convergence_threshold

    def compute(
        self, seed_pages: set[Page] | None = None, personalized: bool = False
    ) -> PageRankResults:
        """
        Compute PageRank scores for all pages.

        Args:
            seed_pages: Optional set of pages for personalized PageRank
                       Random jumps go only to these pages
            personalized: If True, use personalized PageRank

        Returns:
            PageRankResults with scores and metadata
        """
        # Use analysis pages from graph (excludes autodoc if configured)
        pages = self.graph.get_analysis_pages()
        # Also exclude generated pages
        pages = [p for p in pages if not p.metadata.get("_generated")]
        N = len(pages)

        if N == 0:
            logger.warning("pagerank_no_pages")
            return PageRankResults(
                scores={}, iterations=0, converged=True, damping_factor=self.damping
            )

        logger.info(
            "pagerank_start", total_pages=N, damping=self.damping, personalized=personalized
        )

        # Initialize: equal probability for all pages
        scores = {page: 1.0 / N for page in pages}

        # For personalized PageRank
        if personalized and seed_pages:
            personalization = {
                page: (1.0 / len(seed_pages) if page in seed_pages else 0.0) for page in pages
            }
        else:
            personalization = {page: 1.0 / N for page in pages}

        iterations_run = 0
        converged = False

        for iteration in range(self.max_iterations):
            new_scores = {}
            max_diff = 0.0

            for page in pages:
                # Base score: random jump probability
                if personalized and seed_pages:
                    base_score = (1 - self.damping) * personalization[page]
                else:
                    base_score = (1 - self.damping) / N

                # Add contributions from incoming links
                link_score = 0.0

                # Find pages linking to this one
                for source_page in pages:
                    outgoing_links = self.graph.outgoing_refs.get(source_page, set())

                    if page in outgoing_links:
                        # Page receives score proportional to linking page's score
                        # divided by linking page's outgoing link count
                        outgoing_count = len(outgoing_links)
                        if outgoing_count > 0:
                            link_score += scores[source_page] / outgoing_count

                new_score = base_score + self.damping * link_score
                new_scores[page] = new_score

                # Track convergence
                diff = abs(new_score - scores[page])
                max_diff = max(max_diff, diff)

            scores = new_scores
            iterations_run = iteration + 1

            # Check convergence
            if max_diff < self.threshold:
                converged = True
                logger.info("pagerank_converged", iterations=iterations_run, max_diff=max_diff)
                break

        if not converged:
            logger.warning("pagerank_max_iterations", iterations=iterations_run, max_diff=max_diff)

        logger.info(
            "pagerank_complete",
            iterations=iterations_run,
            converged=converged,
            top_score=max(scores.values()) if scores else 0,
        )

        return PageRankResults(
            scores=scores,
            iterations=iterations_run,
            converged=converged,
            damping_factor=self.damping,
        )

    def compute_personalized(self, seed_pages: set[Page]) -> PageRankResults:
        """
        Compute personalized PageRank from seed pages.

        Personalized PageRank biases random jumps toward seed pages,
        useful for finding pages related to a specific topic.

        Args:
            seed_pages: Set of pages to bias toward

        Returns:
            PageRankResults with personalized scores
        """
        if not seed_pages:
            raise ValueError("seed_pages cannot be empty for personalized PageRank")

        return self.compute(seed_pages=seed_pages, personalized=True)


def analyze_page_importance(
    graph: KnowledgeGraph, damping: float = 0.85, top_n: int = 20
) -> list[tuple[Page, float]]:
    """
    Convenience function to analyze page importance.

    Args:
        graph: KnowledgeGraph with page connections
        damping: Damping factor (default 0.85)
        top_n: Number of top pages to return

    Returns:
        List of (page, score) tuples for top N pages

    Example:
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> top_pages = analyze_page_importance(graph, top_n=10)
        >>> for page, score in top_pages:
        ...     print(f"{page.title}: {score:.4f}")
    """
    calculator = PageRankCalculator(graph, damping=damping)
    results = calculator.compute()
    return results.get_top_pages(top_n)
