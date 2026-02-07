"""
Score sorting and ranking utilities for analysis modules.

Provides common operations for working with score dictionaries,
such as getting top-N items by score.

This centralizes scoring logic that was previously duplicated in:
- PageRankResults.get_top_pages()
- PathAnalysisResults.get_top_bridges()
- PathAnalysisResults.get_most_accessible()
- CommunityDetectionResults.get_largest_communities()
- LinkSuggestionResults.get_top_suggestions()

Example:
    >>> from bengal.analysis.utils import top_n_by_score
    >>> top_pages = top_n_by_score(pagerank_scores, limit=10)

"""


def top_n_by_score[T](
    scores: dict[T, float],
    limit: int = 20,
    *,
    reverse: bool = True,
) -> list[tuple[T, float]]:
    """
    Get top N items from a score dictionary.

    Args:
        scores: Dictionary mapping items to their scores
        limit: Maximum number of items to return (default: 20)
        reverse: If True (default), return highest scores first.
                If False, return lowest scores first.

    Returns:
        List of (item, score) tuples, sorted by score.

    Example:
        >>> scores = {page_a: 0.5, page_b: 0.8, page_c: 0.3}
        >>> top_n_by_score(scores, limit=2)
        [(page_b, 0.8), (page_a, 0.5)]

        >>> # Get lowest scores
        >>> top_n_by_score(scores, limit=2, reverse=False)
        [(page_c, 0.3), (page_a, 0.5)]

    """
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=reverse)
    return sorted_items[:limit]


def items_above_percentile[T](
    scores: dict[T, float],
    percentile: int,
) -> set[T]:
    """
    Get items above a certain percentile threshold.

    Args:
        scores: Dictionary mapping items to their scores
        percentile: Percentile threshold (0-100). For example, 80 means
                   return items in the top 20%.

    Returns:
        Set of items whose scores are at or above the percentile threshold.

    Example:
        >>> # Get pages in top 20% by PageRank
        >>> top_pages = items_above_percentile(pagerank_scores, 80)

    """
    if not scores:
        return set()

    scores_list = sorted(scores.values(), reverse=True)

    # Calculate how many items to include
    # e.g., 80th percentile means top 20% of items
    n_items = max(1, int(len(scores_list) * (100 - percentile) / 100))

    # Get the threshold score
    threshold_score = scores_list[n_items - 1] if n_items <= len(scores_list) else 0

    return {item for item, score in scores.items() if score >= threshold_score}


def normalize_scores[T](
    scores: dict[T, float],
    *,
    min_val: float = 0.0,
    max_val: float = 1.0,
) -> dict[T, float]:
    """
    Normalize scores to a given range.

    Args:
        scores: Dictionary mapping items to their scores
        min_val: Minimum value in output range (default: 0.0)
        max_val: Maximum value in output range (default: 1.0)

    Returns:
        Dictionary with scores normalized to [min_val, max_val].
        If all scores are equal, all output values will be min_val.

    Example:
        >>> scores = {page_a: 10, page_b: 50, page_c: 30}
        >>> normalize_scores(scores)
        {page_a: 0.0, page_b: 1.0, page_c: 0.5}

    """
    if not scores:
        return {}

    score_values = list(scores.values())
    score_min = min(score_values)
    score_max = max(score_values)

    # Handle case where all scores are equal
    if score_max == score_min:
        return dict.fromkeys(scores, min_val)

    # Linear normalization
    scale = (max_val - min_val) / (score_max - score_min)
    return {item: min_val + (score - score_min) * scale for item, score in scores.items()}
