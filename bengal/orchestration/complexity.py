"""Page complexity estimation for optimal parallel dispatch ordering.

This module provides lightweight heuristics to estimate page rendering
complexity BEFORE rendering, enabling optimal work distribution across
parallel workers.

Design Goals:
    1. Fast: < 0.1ms per page (must not add significant overhead)
    2. Accurate enough: Relative ordering matters, not absolute accuracy
    3. Thread-safe: Uses only compiled regexes and immutable data

Key Insight:
    We don't need perfect predictions. We just need heavy pages to
    sort before light pages. Even rough estimates improve parallelism.

Algorithm:
    Implements Longest Processing Time First (LPT) scheduling by sorting
    pages descending by estimated complexity. LPT is optimal for 2 workers
    and achieves 4/3-approximation for m≥3 workers.

Example:
    >>> from bengal.orchestration.complexity import sort_by_complexity
    >>> sorted_pages = sort_by_complexity(pages)  # Heavy first
    >>> # Now dispatch to ThreadPoolExecutor
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page

__all__ = [
    "ComplexityScore",
    "estimate_complexity",
    "sort_by_complexity",
    "get_cached_score",
    "get_complexity_stats",
]


@dataclass(frozen=True, slots=True)
class ComplexityScore:
    """Lightweight complexity metrics for a page.

    Immutable and hashable for potential caching use cases.

    Attributes:
        content_bytes: Raw content length in bytes
        code_blocks: Count of fenced code blocks
        directives: Count of MyST/RST directives
        variables: Count of template variables ({{ var }})
    """

    content_bytes: int
    code_blocks: int
    directives: int
    variables: int

    @property
    def score(self) -> int:
        """Combined complexity score (higher = more complex).

        Weights are tuned based on profiling data:
        - Code blocks are most expensive (syntax highlighting)
        - Directives require additional processing
        - Content size is baseline indicator
        - Variables have minimal impact

        Note:
            Relative ordering matters more than absolute accuracy.
            Even rough estimates significantly improve parallelism.
        """
        return (
            self.content_bytes // 500  # ~1 point per 500 bytes
            + self.code_blocks * 10  # Code highlighting is expensive
            + self.directives * 3  # Directive processing
            + self.variables  # Variable substitution (minimal)
        )


# Compiled patterns for speed (module-level, computed once)
# These run in ~0.01ms for typical page content

_CODE_FENCE = re.compile(r"^\s*```", re.MULTILINE)
"""Matches fenced code block markers (opening AND closing).

Note: Matches both opening and closing ```, so we divide count by 2.
Also matches indented code blocks (e.g., in lists) via \\s* prefix.
"""

_DIRECTIVE_MYST = re.compile(r"^:::{?\w+", re.MULTILINE)
"""Matches MyST directive syntax (:::{name} or :::name)."""

_DIRECTIVE_RST = re.compile(r"^\.\. \w+::", re.MULTILINE)
"""Matches RST-style directive syntax (.. name::)."""

_VARIABLE = re.compile(r"\{\{")
"""Matches template variable openings."""


def estimate_complexity(content: str) -> ComplexityScore:
    """Estimate page rendering complexity from raw content.

    Designed to be fast (< 0.1ms per page) so sorting overhead
    doesn't exceed the parallelism benefits.

    Implementation uses findall() which is O(n) and creates minimal
    allocations due to regex engine optimizations.

    Args:
        content: Raw markdown content (before parsing)

    Returns:
        ComplexityScore with heuristic metrics

    Example:
        >>> score = estimate_complexity(page.content)
        >>> print(f"Complexity: {score.score}")
    """
    if not content:
        return ComplexityScore(0, 0, 0, 0)

    # Count patterns (each findall is O(n), total is O(n))
    # Divide fence count by 2 since we match both opening and closing ```
    code_fences = len(_CODE_FENCE.findall(content))
    code_blocks = code_fences // 2  # Each block has open + close

    directives = len(_DIRECTIVE_MYST.findall(content)) + len(_DIRECTIVE_RST.findall(content))
    variables = len(_VARIABLE.findall(content))

    return ComplexityScore(
        content_bytes=len(content),
        code_blocks=code_blocks,
        directives=directives,
        variables=variables,
    )


def _get_content_safe(page: Page) -> str:
    """Get page content without triggering lazy loads on PageProxy.

    For PageProxy instances where content isn't loaded, returns empty
    string (treated as unknown/light complexity). This avoids disk I/O
    during sorting, which would negate the optimization benefits.

    For regular Page instances, content is always available.
    """
    # Check for PageProxy with unloaded content
    if hasattr(page, "_full_page") and page._full_page is None:
        # PageProxy without loaded content - treat as light
        return ""

    return getattr(page, "content", "") or ""


def get_cached_score(page: Page) -> int:
    """Get complexity score with caching on the page object.

    Caches the score on the page to avoid recomputation if called
    multiple times (e.g., in logging after sorting).
    """
    # Check for cached score first.
    # Use vars() to check actual instance dict, avoiding Mock auto-creation behavior.
    page_dict = vars(page) if hasattr(page, "__dict__") else {}
    if "_complexity_score" in page_dict:
        cached = page_dict["_complexity_score"]
        if isinstance(cached, int):
            return cached

    # Compute and cache
    content = _get_content_safe(page)
    score = estimate_complexity(content).score

    # Cache on page (safe - pages are mutable objects)
    # Use contextlib.suppress for cleaner handling of frozen dataclass or immutable objects
    with contextlib.suppress(AttributeError, TypeError):
        page._complexity_score = score  # type: ignore[attr-defined]

    return score


def sort_by_complexity(
    pages: list[Page],
    descending: bool = True,
) -> list[Page]:
    """Sort pages by estimated rendering complexity.

    For parallel rendering, descending=True (heavy first) is optimal.
    This ensures heavy pages start processing immediately while light
    pages fill in later, minimizing idle worker time.

    Thread-safe: creates new list, doesn't modify input.
    Uses Python's stable Timsort, so equal-complexity pages maintain
    their original relative order.

    Args:
        pages: List of Page objects to sort
        descending: If True, heaviest pages first (optimal for parallel)

    Returns:
        New sorted list (original unchanged)

    Performance:
        - Estimation: ~0.01ms per page
        - Sorting: O(n log n) with Timsort
        - Total for 1000 pages: ~10-20ms

    Note:
        PageProxy instances with unloaded content are treated as light
        pages to avoid triggering disk I/O during sorting.

    Example:
        >>> sorted_pages = sort_by_complexity(pages)
        >>> # First page is most complex
        >>> print(sorted_pages[0].source_path)
    """
    # Use (score, index) tuple to ensure stable sort without comparing pages directly.
    # The index acts as a tiebreaker, preserving original order for equal scores.
    # For descending, we negate the score; index stays positive to preserve order.
    if descending:
        decorated = [(-get_cached_score(page), i, page) for i, page in enumerate(pages)]
    else:
        decorated = [(get_cached_score(page), i, page) for i, page in enumerate(pages)]
    decorated.sort(key=lambda x: (x[0], x[1]))
    return [page for _, _, page in decorated]


def get_complexity_stats(pages: list[Page]) -> dict[str, int | float | list[int]]:
    """Get complexity distribution statistics for logging.

    Useful for understanding build characteristics and validating
    that complexity ordering is beneficial. High variance_ratio (>10)
    indicates the site will benefit significantly from ordering.

    Args:
        pages: List of pages to analyze

    Returns:
        Dictionary with distribution stats and top/bottom samples
    """
    if not pages:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "median": 0,
            "variance_ratio": 1.0,
            "top_5_scores": [],
            "bottom_5_scores": [],
        }

    # Use cached scores to avoid recomputation
    scores = [get_cached_score(page) for page in pages]
    scores_sorted = sorted(scores, reverse=True)
    n = len(scores)

    return {
        "count": n,
        "min": scores_sorted[-1],
        "max": scores_sorted[0],
        "mean": sum(scores) / n,
        "median": scores_sorted[n // 2],
        "variance_ratio": scores_sorted[0] / max(scores_sorted[-1], 1),
        "top_5_scores": scores_sorted[:5],  # Heaviest pages
        "bottom_5_scores": scores_sorted[-5:],  # Lightest pages
    }
