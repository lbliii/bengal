"""Tests for complexity estimation and LPT scheduling.

Tests the bengal.orchestration.complexity module which provides:
- Page complexity estimation from raw content
- Complexity-based sorting for optimal parallel dispatch (LPT algorithm)
- Statistics for build analysis
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bengal.orchestration.complexity import (
    ComplexityScore,
    estimate_complexity,
    get_cached_score,
    get_complexity_stats,
    sort_by_complexity,
)


class TestComplexityScore:
    """Tests for ComplexityScore dataclass."""

    def test_score_calculation(self):
        """Score combines all factors with proper weights."""
        score = ComplexityScore(
            content_bytes=1000,  # 1000/500 = 2 points
            code_blocks=5,  # 5 * 10 = 50 points
            directives=3,  # 3 * 3 = 9 points
            variables=4,  # 4 * 1 = 4 points
        )
        # Total: 2 + 50 + 9 + 4 = 65
        assert score.score == 65

    def test_zero_content(self):
        """Zero content has zero score."""
        score = ComplexityScore(0, 0, 0, 0)
        assert score.score == 0

    def test_code_blocks_dominate(self):
        """Code blocks should be the most significant factor."""
        # 10 code blocks = 100 points
        code_heavy = ComplexityScore(0, 10, 0, 0)
        # 50KB content = 100 points
        content_heavy = ComplexityScore(50000, 0, 0, 0)

        # Equal points, but code blocks are counted more per unit
        assert code_heavy.score == content_heavy.score

    def test_frozen_and_hashable(self):
        """ComplexityScore should be immutable and hashable."""
        score = ComplexityScore(100, 5, 2, 1)

        # Should be hashable (for potential caching)
        assert hash(score) is not None

        # Should be frozen (immutable)
        with pytest.raises(AttributeError):
            score.content_bytes = 200  # type: ignore[misc]


class TestEstimateComplexity:
    """Tests for estimate_complexity function."""

    def test_empty_content(self):
        """Empty content has zero complexity."""
        score = estimate_complexity("")
        assert score.score == 0
        assert score.code_blocks == 0
        assert score.directives == 0
        assert score.variables == 0

    def test_code_blocks_counted_correctly(self):
        """Code blocks are counted as pairs (open + close)."""
        # One complete code block = 2 fence markers = 1 block
        content = "```python\nprint('hi')\n```"
        score = estimate_complexity(content)
        assert score.code_blocks == 1

        # Three complete code blocks
        content = "```\na\n```\n\n```\nb\n```\n\n```\nc\n```"
        score = estimate_complexity(content)
        assert score.code_blocks == 3

    def test_indented_code_blocks(self):
        """Indented code blocks (in lists) are detected."""
        content = """\
- Item with code:
    ```python
    print("hi")
    ```
"""
        score = estimate_complexity(content)
        assert score.code_blocks == 1

    def test_code_blocks_weighted_heavily(self):
        """Code blocks should dominate scoring over prose."""
        prose = "Hello world " * 100  # 1200 bytes, ~2 points
        code = "```python\nprint('hi')\n```"  # ~30 bytes + 10 points

        prose_score = estimate_complexity(prose)
        code_score = estimate_complexity(code)

        assert code_score.score > prose_score.score

    def test_myst_directives(self):
        """MyST directives are counted."""
        content = """\
:::{note}
This is a note.
:::

:::{warning}
This is a warning.
:::
"""
        score = estimate_complexity(content)
        assert score.directives == 2

    def test_myst_directive_with_braces(self):
        """MyST directive syntax with braces is detected."""
        content = ":::{admonition} Title\nContent\n:::"
        score = estimate_complexity(content)
        assert score.directives == 1

    def test_rst_directives(self):
        """RST-style directives are counted."""
        content = """\
.. note::
   This is a note.

.. warning::
   This is a warning.
"""
        score = estimate_complexity(content)
        assert score.directives == 2

    def test_template_variables(self):
        """Template variables ({{ ... }}) are counted."""
        content = "Hello {{ name }}, you have {{ count }} messages."
        score = estimate_complexity(content)
        assert score.variables == 2

    def test_realistic_api_doc(self):
        """Realistic API documentation should score high."""
        content = """\
# API Reference

## `get_user(id)`

Returns user by ID.

```python
from api import get_user

user = get_user(123)
print(user.name)
```

:::{note}
This endpoint requires authentication.
:::

```json
{
    "id": 123,
    "name": "John Doe"
}
```

## Parameters

| Name | Type | Description |
|------|------|-------------|
| id | int | User ID |
"""
        score = estimate_complexity(content)

        # Should have 2 code blocks, 1 directive
        assert score.code_blocks == 2
        assert score.directives == 1
        assert score.score > 20  # Definitely a "heavy" page

    def test_realistic_blog_post(self):
        """Simple blog post should score low."""
        content = """\
# My Blog Post

This is a short blog post about my weekend adventures.

I went hiking and saw some beautiful views.

The end.
"""
        score = estimate_complexity(content)

        assert score.code_blocks == 0
        assert score.directives == 0
        assert score.score < 5  # "Light" page


class TestSortByComplexity:
    """Tests for sort_by_complexity function."""

    def _make_page(self, content: str, name: str = "page") -> Mock:
        """Create a mock page with content."""
        page = Mock()
        page.content = content
        page.name = name
        # Ensure it's not a PageProxy
        del page._full_page
        return page

    def test_heavy_pages_first(self):
        """Heavy pages should sort first (descending)."""
        light = self._make_page("short", "light")
        heavy = self._make_page("```python\n```\n" * 10, "heavy")  # 10 code blocks

        sorted_pages = sort_by_complexity([light, heavy])

        assert sorted_pages[0] is heavy
        assert sorted_pages[1] is light

    def test_preserves_order_for_equal_complexity(self):
        """Stable sort: equal complexity pages maintain original order."""
        pages = [self._make_page("same", f"page_{i}") for i in range(5)]

        sorted_pages = sort_by_complexity(pages)

        # Python's Timsort is stable
        for i, page in enumerate(pages):
            assert sorted_pages[i] is page

    def test_does_not_modify_input(self):
        """Original list should remain unchanged."""
        pages = [self._make_page("a", "a"), self._make_page("b" * 1000, "b")]
        original_order = list(pages)

        sorted_pages = sort_by_complexity(pages)

        assert pages == original_order
        assert sorted_pages is not pages

    def test_page_proxy_without_content(self):
        """PageProxy with unloaded content is treated as light."""
        # Simulate PageProxy with _full_page = None (not loaded)
        proxy = Mock()
        proxy._full_page = None
        proxy.content = "this should not be accessed"

        regular = self._make_page("```\n```\n" * 5, "regular")  # 5 code blocks

        sorted_pages = sort_by_complexity([proxy, regular])

        # Regular page (with content) should sort first
        assert sorted_pages[0] is regular

    def test_ascending_order(self):
        """Can sort in ascending order (light first) if needed."""
        light = self._make_page("short", "light")
        heavy = self._make_page("```\n```\n" * 10, "heavy")

        sorted_pages = sort_by_complexity([heavy, light], descending=False)

        assert sorted_pages[0] is light
        assert sorted_pages[1] is heavy

    def test_large_list_performance(self):
        """Sorting 1000 pages should complete quickly."""
        import time

        pages = [self._make_page("x" * (i * 10), f"page_{i}") for i in range(1000)]

        start = time.perf_counter()
        sorted_pages = sort_by_complexity(pages)
        elapsed = time.perf_counter() - start

        # Should complete in < 500ms (conservative for CI with parallel test overhead)
        assert elapsed < 0.5
        assert len(sorted_pages) == 1000


class TestCachedScore:
    """Tests for score caching behavior."""

    def _make_page(self, content: str) -> Mock:
        """Create a mock page with content."""
        page = Mock()
        page.content = content
        del page._full_page
        return page

    def test_score_cached_on_page(self):
        """Score is cached on page object after first computation."""
        page = self._make_page("```\n```\n" * 3)

        score1 = get_cached_score(page)
        score2 = get_cached_score(page)

        assert score1 == score2
        assert hasattr(page, "_complexity_score")
        assert page._complexity_score == score1

    def test_uses_cached_score(self):
        """Second call uses cached score without recomputation."""
        page = self._make_page("```\n```\n" * 3)

        # First call computes
        score1 = get_cached_score(page)

        # Modify content (but cache should be used)
        page.content = "completely different"

        # Second call should return cached value
        score2 = get_cached_score(page)

        assert score1 == score2


class TestComplexityStats:
    """Tests for get_complexity_stats function."""

    def _make_page(self, content: str) -> Mock:
        """Create a mock page with content."""
        page = Mock()
        page.content = content
        del page._full_page
        return page

    def test_empty_pages(self):
        """Empty page list returns zero stats."""
        stats = get_complexity_stats([])
        assert stats["count"] == 0
        assert stats["variance_ratio"] == 1.0

    def test_stats_include_samples(self):
        """Stats include top and bottom score samples."""
        pages = [self._make_page("x" * (i * 500)) for i in range(10)]

        stats = get_complexity_stats(pages)

        assert "top_5_scores" in stats
        assert "bottom_5_scores" in stats
        assert len(stats["top_5_scores"]) == 5
        assert len(stats["bottom_5_scores"]) == 5

    def test_variance_ratio_high_for_mixed_content(self):
        """Variance ratio is high when pages have different complexities."""
        # Light pages
        light_pages = [self._make_page("short") for _ in range(90)]
        # Heavy pages
        heavy_pages = [self._make_page("```\n```\n" * 30) for _ in range(10)]

        all_pages = light_pages + heavy_pages
        stats = get_complexity_stats(all_pages)

        # Heavy pages have ~300 score (30 code blocks * 10)
        # Light pages have ~0 score
        assert stats["variance_ratio"] > 50
        assert stats["max"] > 200  # Heavy pages
        assert stats["min"] < 5  # Light pages

    def test_variance_ratio_low_for_uniform_content(self):
        """Variance ratio is low when pages have similar complexities."""
        pages = [self._make_page("x" * 500) for _ in range(100)]  # All ~1 point

        stats = get_complexity_stats(pages)

        # All pages have same complexity
        assert stats["variance_ratio"] == 1.0
        assert stats["min"] == stats["max"]

    def test_mean_and_median(self):
        """Mean and median are calculated correctly."""
        # Pages with scores: 0, 1, 2, 3, 4
        pages = [self._make_page("x" * (i * 500)) for i in range(5)]

        stats = get_complexity_stats(pages)

        assert stats["count"] == 5
        assert stats["min"] == 0
        assert stats["max"] == 4
        # Mean of 0,1,2,3,4 = 2.0
        assert stats["mean"] == 2.0
        # Median of sorted descending [4,3,2,1,0] at index 2 = 2
        assert stats["median"] == 2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unclosed_code_block(self):
        """Handles unclosed code blocks gracefully."""
        # 5 fence markers = 2 complete blocks (rounds down)
        content = "```\na\n```\n```\nb\n```\n```"
        score = estimate_complexity(content)
        assert score.code_blocks == 2  # 5 // 2 = 2

    def test_none_content(self):
        """Handles None-ish content from getattr."""
        page = Mock()
        page.content = None
        del page._full_page

        score = get_cached_score(page)
        assert score == 0

    def test_page_without_content_attribute(self):
        """Handles pages missing content attribute."""
        page = Mock(spec=[])  # Empty spec = no attributes
        del page._full_page

        score = get_cached_score(page)
        assert score == 0

    def test_very_large_content(self):
        """Handles very large content efficiently."""
        import time

        # 1MB of content
        content = "x" * (1024 * 1024)

        start = time.perf_counter()
        score = estimate_complexity(content)
        elapsed = time.perf_counter() - start

        # Should complete in < 100ms even for 1MB (conservative for CI)
        assert elapsed < 0.1
        assert score.content_bytes == 1024 * 1024
