"""
Link Suggestion Engine for Bengal SSG.

Generates intelligent cross-linking recommendations to improve site connectivity,
SEO, and content discoverability. The engine combines multiple signals to suggest
high-value links that would naturally fit in content.

Scoring Signals:
    - Topic Similarity (40%): Shared tags and categories indicate related content
    - Category Match (30%): Pages in the same category should link to each other
    - PageRank (20%): Prioritize linking to important pages
    - Centrality (10%): Link to bridge pages for better navigation
    - Underlink Bonus: Extra weight for orphaned or underlinked pages

Benefits:
    - Improved internal linking structure for SEO
    - Better content discoverability for users
    - Reduced orphan pages and dead ends
    - More cohesive topic coverage

Classes:
    LinkSuggestion: A single recommended link with score and reasons
    LinkSuggestionResults: All suggestions with filtering methods
    LinkSuggestionEngine: Main suggestion generator

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.suggest_links(min_score=0.3)
    >>> for suggestion in results.get_top_suggestions(20):
    ...     print(f"{suggestion.source.title} → {suggestion.target.title}")
    ...     print(f"  Score: {suggestion.score:.2f}, Reasons: {suggestion.reasons}")

See Also:
    - bengal/analysis/knowledge_graph.py: Graph coordination
    - bengal/analysis/page_rank.py: Importance scoring
    - bengal/analysis/path_analysis.py: Centrality metrics
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.core.page import Page

logger = get_logger(__name__)


@dataclass
class LinkSuggestion:
    """
    A suggested link between two pages.

    Represents a recommendation to add a link from source page to target page
    based on topic similarity, importance, and connectivity analysis.

    Attributes:
        source: Page where the link should be added
        target: Page that should be linked to
        score: Recommendation score (0.0-1.0, higher is better)
        reasons: List of reasons why this link is suggested
    """

    source: Page
    target: Page
    score: float
    reasons: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"LinkSuggestion({self.source.title} -> {self.target.title}, score={self.score:.3f})"


@dataclass
class LinkSuggestionResults:
    """
    Results from link suggestion analysis.

    Contains all link suggestions generated for the site, along with
    statistics and methods for querying suggestions.

    Attributes:
        suggestions: List of all link suggestions, sorted by score
        total_suggestions: Total number of suggestions generated
    """

    suggestions: list[LinkSuggestion]
    total_suggestions: int
    pages_analyzed: int

    def get_suggestions_for_page(self, page: Page, limit: int = 10) -> list[LinkSuggestion]:
        """
        Get link suggestions for a specific page.

        Args:
            page: Page to get suggestions for
            limit: Maximum number of suggestions

        Returns:
            List of LinkSuggestion objects sorted by score
        """
        page_suggestions = [s for s in self.suggestions if s.source == page]
        return sorted(page_suggestions, key=lambda x: x.score, reverse=True)[:limit]

    def get_top_suggestions(self, limit: int = 50) -> list[LinkSuggestion]:
        """Get top N suggestions across all pages."""
        return sorted(self.suggestions, key=lambda x: x.score, reverse=True)[:limit]

    def get_suggestions_by_target(self, target: Page) -> list[LinkSuggestion]:
        """Get all suggestions that point to a specific target page."""
        return [s for s in self.suggestions if s.target == target]


class LinkSuggestionEngine:
    """
    Generate smart link suggestions to improve site connectivity.

    Uses multiple signals to recommend links:
    1. Topic Similarity: Pages with shared tags/categories
    2. PageRank: Prioritize linking to important pages
    3. Navigation Value: Link to bridge pages
    4. Link Gaps: Find underlinked valuable content

    Example:
        >>> engine = LinkSuggestionEngine(knowledge_graph)
        >>> results = engine.generate_suggestions()
        >>> for suggestion in results.get_top_suggestions(20):
        ...     print(f"{suggestion.source.title} -> {suggestion.target.title}")
    """

    def __init__(
        self, graph: KnowledgeGraph, min_score: float = 0.3, max_suggestions_per_page: int = 10
    ):
        """
        Initialize link suggestion engine.

        Args:
            graph: KnowledgeGraph with page connections
            min_score: Minimum score threshold for suggestions
            max_suggestions_per_page: Maximum suggestions per page
        """
        self.graph = graph
        self.min_score = min_score
        self.max_suggestions_per_page = max_suggestions_per_page

    def generate_suggestions(self) -> LinkSuggestionResults:
        """
        Generate link suggestions for all pages.

        Returns:
            LinkSuggestionResults with all suggestions
        """
        # Use analysis pages from graph (excludes autodoc if configured)
        pages = self.graph.get_analysis_pages()
        # Also exclude generated pages
        pages = [p for p in pages if not p.metadata.get("_generated")]

        if len(pages) == 0:
            logger.warning("link_suggestions_no_pages")
            return LinkSuggestionResults(suggestions=[], total_suggestions=0, pages_analyzed=0)

        logger.info("link_suggestions_start", total_pages=len(pages))

        # Build tag/category mappings
        page_tags = self._build_tag_map(pages)
        page_categories = self._build_category_map(pages)

        # Get PageRank scores (if available)
        pagerank_scores = {}
        try:
            if hasattr(self.graph, "_pagerank_results") and self.graph._pagerank_results:
                pagerank_scores = self.graph._pagerank_results.scores
        except (AttributeError, TypeError):
            pass

        # Get centrality scores (if available)
        betweenness_scores = {}
        try:
            if hasattr(self.graph, "_path_results") and self.graph._path_results:
                betweenness_scores = self.graph._path_results.betweenness_centrality
        except (AttributeError, TypeError):
            pass

        # Generate suggestions
        all_suggestions: list[LinkSuggestion] = []

        for source_page in pages:
            suggestions = self._generate_suggestions_for_page(
                source_page, pages, page_tags, page_categories, pagerank_scores, betweenness_scores
            )
            all_suggestions.extend(suggestions)

        logger.info(
            "link_suggestions_complete",
            total_suggestions=len(all_suggestions),
            pages_analyzed=len(pages),
        )

        return LinkSuggestionResults(
            suggestions=all_suggestions,
            total_suggestions=len(all_suggestions),
            pages_analyzed=len(pages),
        )

    def _generate_suggestions_for_page(
        self,
        source: Page,
        all_pages: list[Page],
        page_tags: dict[Page, set[str]],
        page_categories: dict[Page, set[str]],
        pagerank_scores: dict[Page, float],
        betweenness_scores: dict[Page, float],
    ) -> list[LinkSuggestion]:
        """Generate link suggestions for a single page."""
        # Get existing links from this page
        existing_links = self.graph.outgoing_refs.get(source, set())

        candidates: list[tuple[Page, float, list[str]]] = []

        for target in all_pages:
            # Skip self-links and existing links
            if target == source or target in existing_links:
                continue

            # Calculate similarity score
            score, reasons = self._calculate_link_score(
                source, target, page_tags, page_categories, pagerank_scores, betweenness_scores
            )

            if score >= self.min_score:
                candidates.append((target, score, reasons))

        # Sort by score and take top N
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[: self.max_suggestions_per_page]

        # Convert to LinkSuggestion objects
        suggestions = [
            LinkSuggestion(source=source, target=target, score=score, reasons=reasons)
            for target, score, reasons in top_candidates
        ]

        return suggestions

    def _calculate_link_score(
        self,
        source: Page,
        target: Page,
        page_tags: dict[Page, set[str]],
        page_categories: dict[Page, set[str]],
        pagerank_scores: dict[Page, float],
        betweenness_scores: dict[Page, float],
    ) -> tuple[float, list[str]]:
        """
        Calculate link score between two pages.

        Returns:
            Tuple of (score, reasons)
        """
        score = 0.0
        reasons = []

        # 1. Topic similarity (tags)
        source_tags = page_tags.get(source, set())
        target_tags = page_tags.get(target, set())

        if source_tags and target_tags:
            common_tags = source_tags & target_tags
            if common_tags:
                tag_similarity = len(common_tags) / len(source_tags | target_tags)
                score += tag_similarity * 0.4  # 40% weight
                reasons.append(f"Shared tags: {', '.join(list(common_tags)[:3])}")

        # 2. Category similarity
        source_cats = page_categories.get(source, set())
        target_cats = page_categories.get(target, set())

        if source_cats and target_cats:
            common_cats = source_cats & target_cats
            if common_cats:
                cat_similarity = len(common_cats) / len(source_cats | target_cats)
                score += cat_similarity * 0.3  # 30% weight
                reasons.append(f"Shared categories: {', '.join(list(common_cats)[:2])}")

        # 3. Target PageRank (link to important pages)
        if pagerank_scores and isinstance(pagerank_scores, dict) and target in pagerank_scores:
            target_rank = pagerank_scores[target]
            # Normalize to 0-1 range (assuming typical PageRank values)
            normalized_rank = min(target_rank * 10, 1.0)
            score += normalized_rank * 0.2  # 20% weight
            if target_rank > 0.01:  # Only mention if significant
                reasons.append(f"High importance (rank: {target_rank:.4f})")

        # 4. Target betweenness (link to bridge pages)
        if (
            betweenness_scores
            and isinstance(betweenness_scores, dict)
            and target in betweenness_scores
        ):
            target_between = betweenness_scores[target]
            # Normalize (typical betweenness is 0-0.1)
            normalized_between = min(target_between * 10, 1.0)
            score += normalized_between * 0.1  # 10% weight
            if target_between > 0.01:
                reasons.append(f"Bridge page (betweenness: {target_between:.4f})")

        # 5. Underlinked bonus (pages with few incoming links)
        incoming_count = self.graph.incoming_refs.get(target, 0)
        if incoming_count < 3:
            underlink_bonus = (3 - incoming_count) * 0.1
            score += underlink_bonus
            if incoming_count == 0:
                reasons.append("Orphan page (no incoming links)")
            elif incoming_count < 3:
                reasons.append(f"Underlinked ({incoming_count} incoming links)")

        return score, reasons

    def _build_tag_map(self, pages: list[Page]) -> dict[Page, set[str]]:
        """Build mapping of page -> set of tags."""
        tag_map = {}
        for page in pages:
            tags = set()
            if hasattr(page, "tags") and page.tags:
                tags = {tag.lower().replace(" ", "-") for tag in page.tags}
            tag_map[page] = tags
        return tag_map

    def _build_category_map(self, pages: list[Page]) -> dict[Page, set[str]]:
        """Build mapping of page -> set of categories."""
        category_map = {}
        for page in pages:
            categories = set()
            if hasattr(page, "category") and page.category:
                categories = {page.category.lower().replace(" ", "-")}
            elif hasattr(page, "categories") and page.categories:
                categories = {cat.lower().replace(" ", "-") for cat in page.categories}
            category_map[page] = categories
        return category_map


def suggest_links(
    graph: KnowledgeGraph, min_score: float = 0.3, max_suggestions_per_page: int = 10
) -> LinkSuggestionResults:
    """
    Convenience function for link suggestions.

    Args:
        graph: KnowledgeGraph with page connections
        min_score: Minimum score threshold
        max_suggestions_per_page: Max suggestions per page

    Returns:
        LinkSuggestionResults with all suggestions

    Example:
        >>> graph = KnowledgeGraph(site)
        >>> graph.build()
        >>> results = suggest_links(graph)
        >>> for suggestion in results.get_top_suggestions(20):
        ...     print(f"{suggestion.source.title} -> {suggestion.target.title}")
    """
    engine = LinkSuggestionEngine(
        graph, min_score=min_score, max_suggestions_per_page=max_suggestions_per_page
    )
    return engine.generate_suggestions()
