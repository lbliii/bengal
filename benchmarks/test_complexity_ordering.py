"""Benchmarks for complexity-based page ordering optimization.

Tests both the overhead of complexity estimation and validates
that the optimization works correctly with realistic content.

Run with: pytest benchmarks/test_complexity_ordering.py -v --benchmark-only
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bengal.orchestration.complexity import (
    estimate_complexity,
    get_complexity_stats,
    sort_by_complexity,
)


def _make_page(content: str, name: str = "page") -> Mock:
    """Create a mock page with content for benchmarking."""
    page = Mock()
    page.content = content
    page.name = name
    page.__dict__ = {"content": content, "name": name}  # For vars() check
    return page


class TestEstimationOverhead:
    """Measure estimation overhead to ensure < 0.1ms per page."""

    @pytest.mark.benchmark(group="estimation")
    @pytest.mark.parametrize(
        ("size", "label"),
        [
            (100, "100B"),
            (1000, "1KB"),
            (10000, "10KB"),
            (100000, "100KB"),
        ],
    )
    def test_estimation_by_size(self, benchmark, size: int, label: str) -> None:
        """Estimation should be fast regardless of content size."""
        content = "x" * size

        result = benchmark(estimate_complexity, content)

        # Basic sanity check
        assert result.content_bytes == size

    @pytest.mark.benchmark(group="estimation")
    def test_estimation_with_code_blocks(self, benchmark) -> None:
        """Estimation with realistic content (code blocks + prose)."""
        content = "# Title\n\nSome prose.\n\n" + "```python\ncode\n```\n\n" * 20

        result = benchmark(estimate_complexity, content)

        assert result.code_blocks == 20

    @pytest.mark.benchmark(group="estimation")
    def test_estimation_api_doc(self, benchmark) -> None:
        """Estimation of realistic API documentation page."""
        content = (
            """
# API Reference

## `create_user(name, email)`

Creates a new user in the system.

```python
from myapi import create_user

user = create_user(name="John", email="john@example.com")
print(user.id)
```

:::{note}
This endpoint requires authentication.
:::

### Parameters

| Name | Type | Description |
|------|------|-------------|
| name | str | User's full name |
| email | str | User's email address |

### Returns

```json
{
    "id": 123,
    "name": "John",
    "email": "john@example.com"
}
```

## `get_user(user_id)`

Retrieves a user by ID.

```python
user = get_user(123)
```
"""
            * 5
        )  # Multiply to simulate larger API doc

        result = benchmark(estimate_complexity, content)

        # Should detect multiple code blocks and directives
        assert result.code_blocks > 10
        assert result.directives >= 5


class TestSortingOverhead:
    """Measure sorting overhead for various page counts."""

    @pytest.mark.benchmark(group="sorting")
    @pytest.mark.parametrize(
        "page_count",
        [10, 50, 100, 500, 1000],
    )
    def test_sorting_by_count(self, benchmark, page_count: int) -> None:
        """Sorting should scale well with page count."""
        # Create pages with varying complexity
        pages = []
        for i in range(page_count):
            # Mix of heavy and light pages
            if i % 10 == 0:
                content = "```python\ncode\n```\n\n" * 30  # Heavy
            else:
                content = f"# Page {i}\n\nShort content."  # Light
            pages.append(_make_page(content, f"page_{i}"))

        result = benchmark(sort_by_complexity, pages)

        assert len(result) == page_count

    @pytest.mark.benchmark(group="sorting")
    def test_sorting_high_variance(self, benchmark) -> None:
        """Sorting pages with high complexity variance."""
        pages = []

        # 10 heavy pages (API docs with many code blocks)
        for i in range(10):
            content = "```python\ncode\n```\n\n" * 30
            pages.append(_make_page(content, f"api_{i}"))

        # 90 light pages (blog posts)
        for i in range(90):
            content = f"# Blog Post {i}\n\nShort content here."
            pages.append(_make_page(content, f"blog_{i}"))

        result = benchmark(sort_by_complexity, pages)

        # Heavy pages should be first
        assert "api_" in result[0].name
        assert "blog_" in result[-1].name


class TestStatsOverhead:
    """Measure stats calculation overhead."""

    @pytest.mark.benchmark(group="stats")
    def test_stats_100_pages(self, benchmark) -> None:
        """Stats calculation for 100 pages."""
        pages = [_make_page("x" * (i * 100), f"page_{i}") for i in range(100)]

        result = benchmark(get_complexity_stats, pages)

        assert result["count"] == 100

    @pytest.mark.benchmark(group="stats")
    def test_stats_1000_pages(self, benchmark) -> None:
        """Stats calculation for 1000 pages."""
        pages = [_make_page("x" * (i * 10), f"page_{i}") for i in range(1000)]

        result = benchmark(get_complexity_stats, pages)

        assert result["count"] == 1000


class TestRealWorldScenarios:
    """Test realistic scenarios to validate ordering benefits."""

    def test_high_variance_ordering_correct(self) -> None:
        """Verify heavy pages are correctly sorted first."""
        # Create a realistic mix
        pages = []

        # Heavy API docs (30 code blocks each = ~300 points)
        for i in range(5):
            content = "```python\ncode\n```\n\n" * 30
            pages.append(_make_page(content, f"api_{i}"))

        # Medium tutorials (10 code blocks each = ~100 points)
        for i in range(10):
            content = "```python\ncode\n```\n\n" * 10
            pages.append(_make_page(content, f"tutorial_{i}"))

        # Light blog posts (~1 point each)
        for i in range(85):
            content = f"# Blog {i}\n\nShort."
            pages.append(_make_page(content, f"blog_{i}"))

        # Shuffle to simulate random input
        import random

        random.shuffle(pages)

        # Sort
        sorted_pages = sort_by_complexity(pages)

        # Verify ordering: API docs first, then tutorials, then blogs
        # Check first 5 are API docs
        for i in range(5):
            assert "api_" in sorted_pages[i].name, (
                f"Expected api at {i}, got {sorted_pages[i].name}"
            )

        # Check last 85 are blog posts
        for i in range(85):
            assert "blog_" in sorted_pages[-(i + 1)].name, (
                f"Expected blog at {-(i + 1)}, got {sorted_pages[-(i + 1)].name}"
            )

    def test_variance_ratio_interpretation(self) -> None:
        """Validate variance ratio interpretation from RFC."""
        # High variance scenario
        high_var_pages = []
        for i in range(10):
            high_var_pages.append(_make_page("```\n```\n" * 30, f"heavy_{i}"))
        for i in range(90):
            high_var_pages.append(_make_page("short", f"light_{i}"))

        stats = get_complexity_stats(high_var_pages)

        # Should have very high variance ratio (> 100)
        assert stats["variance_ratio"] > 50, (
            f"Expected high variance, got {stats['variance_ratio']}"
        )

        # Low variance scenario - use content that has score > 0 for meaningful ratio
        low_var_pages = [
            _make_page("x" * 500, f"page_{i}") for i in range(100)
        ]  # Each page = 1 point
        stats = get_complexity_stats(low_var_pages)

        # Should have variance ratio of 1.0 (all same complexity)
        assert stats["variance_ratio"] == 1.0, f"Expected 1.0, got {stats['variance_ratio']}"
