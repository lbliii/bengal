"""
Property-based tests for pagination using Hypothesis.

These tests verify that pagination maintains critical invariants
across ALL possible inputs, not just the cases we thought to test.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bengal.utils.pagination import Paginator


class TestPaginatorProperties:
    """
    Property-based tests for Paginator class.

    Each test runs 100+ times with randomly generated inputs
    to discover edge cases automatically.
    """

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=0, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_all_items_included(self, items, per_page):
        """
        Property: Concatenating all pages gives back all original items.

        This is the most critical property - no items should be lost
        or duplicated during pagination.
        """
        paginator = Paginator(items, per_page=per_page)

        # Collect all items from all pages
        all_paginated_items = []
        for page_num in range(1, paginator.num_pages + 1):
            all_paginated_items.extend(paginator.page(page_num))

        assert all_paginated_items == items, (
            f"Pagination lost/reordered items: expected {len(items)}, "
            f"got {len(all_paginated_items)}"
        )

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=0, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_page_count_calculation(self, items, per_page):
        """
        Property: Page count calculation is correct.

        Mathematical invariant:
        (num_pages - 1) * per_page < len(items) <= num_pages * per_page

        Except for empty lists, which have exactly 1 page.
        """
        paginator = Paginator(items, per_page=per_page)

        if not items:
            # Empty list has 1 page
            assert paginator.num_pages == 1, "Empty list should have 1 page"
        else:
            # Non-empty: verify page count bounds
            assert (paginator.num_pages - 1) * per_page < len(items), (
                f"Too many pages: {paginator.num_pages} pages × {per_page} per_page "
                f"can't hold only {len(items)} items"
            )
            assert len(items) <= paginator.num_pages * per_page, (
                f"Too few pages: {paginator.num_pages} pages × {per_page} per_page "
                f"is not enough for {len(items)} items"
            )

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=1, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_all_pages_within_size_limit(self, items, per_page):
        """
        Property: Each page has at most per_page items.

        No page should exceed the specified page size.
        """
        paginator = Paginator(items, per_page=per_page)

        for page_num in range(1, paginator.num_pages + 1):
            page_items = paginator.page(page_num)
            assert len(page_items) <= per_page, (
                f"Page {page_num} has {len(page_items)} items, " f"exceeds limit of {per_page}"
            )

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=1, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_last_page_can_be_partial(self, items, per_page):
        """
        Property: Last page can have fewer items than per_page.

        If len(items) is not evenly divisible by per_page,
        the last page will have the remainder.
        """
        paginator = Paginator(items, per_page=per_page)
        last_page_items = paginator.page(paginator.num_pages)

        expected_last_page_size = len(items) % per_page
        if expected_last_page_size == 0:
            expected_last_page_size = per_page

        assert len(last_page_items) == expected_last_page_size, (
            f"Last page should have {expected_last_page_size} items, " f"got {len(last_page_items)}"
        )

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=1, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_first_page_always_full(self, items, per_page):
        """
        Property: First page is always full (or has all items if < per_page).

        The first page should have exactly per_page items,
        unless there are fewer items total.
        """
        paginator = Paginator(items, per_page=per_page)
        first_page = paginator.page(1)

        expected_size = min(len(items), per_page)
        assert (
            len(first_page) == expected_size
        ), f"First page should have {expected_size} items, got {len(first_page)}"

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(min_value=0, max_value=100), min_size=10, max_size=100),
        per_page=st.integers(min_value=1, max_value=20),
    )
    def test_no_item_duplication(self, items, per_page):
        """
        Property: No item appears on multiple pages.

        Each item should appear exactly once across all pages.
        """
        # Use unique items to detect duplication
        unique_items = list(range(len(items)))
        paginator = Paginator(unique_items, per_page=per_page)

        seen_items = set()
        for page_num in range(1, paginator.num_pages + 1):
            page_items = paginator.page(page_num)
            for item in page_items:
                assert item not in seen_items, f"Item {item} appears on multiple pages!"
                seen_items.add(item)

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=0, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_invalid_page_numbers_raise_error(self, items, per_page):
        """
        Property: Requesting invalid page numbers raises ValueError.

        Page numbers must be 1-indexed and within valid range.
        """
        paginator = Paginator(items, per_page=per_page)

        # Test page 0 (invalid)
        with pytest.raises(ValueError, match="out of range"):
            paginator.page(0)

        # Test negative page (invalid)
        with pytest.raises(ValueError, match="out of range"):
            paginator.page(-1)

        # Test beyond last page (invalid)
        if paginator.num_pages < 1000:  # Avoid huge numbers
            with pytest.raises(ValueError, match="out of range"):
                paginator.page(paginator.num_pages + 1)

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=0, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_page_context_consistency(self, items, per_page):
        """
        Property: page_context data is internally consistent.

        Verifies that has_previous/has_next align with previous_page/next_page.
        """
        paginator = Paginator(items, per_page=per_page)

        for page_num in range(1, paginator.num_pages + 1):
            context = paginator.page_context(page_num, "/test/")

            # Check has_previous consistency
            if context["has_previous"]:
                assert (
                    context["previous_page"] is not None
                ), f"Page {page_num}: has_previous=True but previous_page is None"
                assert context["previous_page"] == page_num - 1, (
                    f"Page {page_num}: previous_page should be {page_num - 1}, "
                    f"got {context['previous_page']}"
                )
            else:
                assert (
                    context["previous_page"] is None
                ), f"Page {page_num}: has_previous=False but previous_page is not None"

            # Check has_next consistency
            if context["has_next"]:
                assert (
                    context["next_page"] is not None
                ), f"Page {page_num}: has_next=True but next_page is None"
                assert context["next_page"] == page_num + 1, (
                    f"Page {page_num}: next_page should be {page_num + 1}, "
                    f"got {context['next_page']}"
                )
            else:
                assert (
                    context["next_page"] is None
                ), f"Page {page_num}: has_next=False but next_page is not None"

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=0, max_size=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_total_items_matches(self, items, per_page):
        """
        Property: total_items in context matches actual item count.

        The context should accurately report the total number of items.
        """
        paginator = Paginator(items, per_page=per_page)

        for page_num in range(1, paginator.num_pages + 1):
            context = paginator.page_context(page_num, "/test/")
            assert context["total_items"] == len(
                items
            ), f"total_items={context['total_items']} but actual count={len(items)}"

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=1, max_size=100),
        per_page=st.integers(min_value=1, max_value=20),
    )
    def test_first_page_has_no_previous(self, items, per_page):
        """
        Property: First page has no previous page.

        Page 1 should always have has_previous=False.
        """
        paginator = Paginator(items, per_page=per_page)
        context = paginator.page_context(1, "/test/")

        assert context["has_previous"] is False, "Page 1 should not have previous"
        assert context["previous_page"] is None, "Page 1 should have previous_page=None"

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=1, max_size=100),
        per_page=st.integers(min_value=1, max_value=20),
    )
    def test_last_page_has_no_next(self, items, per_page):
        """
        Property: Last page has no next page.

        The last page should always have has_next=False.
        """
        paginator = Paginator(items, per_page=per_page)
        last_page = paginator.num_pages
        context = paginator.page_context(last_page, "/test/")

        assert context["has_next"] is False, f"Page {last_page} should not have next"
        assert context["next_page"] is None, f"Page {last_page} should have next_page=None"


class TestPaginatorEdgeCases:
    """
    Targeted property tests for specific edge cases.
    """

    @pytest.mark.hypothesis
    def test_empty_list_has_one_page(self):
        """
        Property: Empty list always has exactly 1 page.

        This prevents division by zero and provides consistent behavior.
        """
        paginator = Paginator([], per_page=10)
        assert paginator.num_pages == 1, "Empty list should have 1 page"

        page_1 = paginator.page(1)
        assert page_1 == [], "Page 1 of empty list should be empty"

    @pytest.mark.hypothesis
    @given(per_page=st.integers(min_value=-100, max_value=0))
    def test_invalid_per_page_handled_gracefully(self, per_page):
        """
        Property: Invalid per_page values are handled (clamped to 1).

        Negative or zero per_page should be converted to 1.
        """
        items = [1, 2, 3, 4, 5]
        paginator = Paginator(items, per_page=per_page)

        assert paginator.per_page >= 1, f"per_page should be >= 1, got {paginator.per_page}"

    @pytest.mark.hypothesis
    @given(
        n=st.integers(min_value=1, max_value=100), per_page=st.integers(min_value=1, max_value=20)
    )
    def test_single_item_per_page(self, n, per_page):
        """
        Property: With various per_page values, pagination is correct.

        Tests different per_page values to ensure calculation works.
        """
        items = list(range(n))
        paginator = Paginator(items, per_page=per_page)

        # Expected number of pages
        expected_pages = (n + per_page - 1) // per_page  # Ceiling division

        assert paginator.num_pages == expected_pages, (
            f"For {n} items with {per_page} per page, expected {expected_pages} pages, "
            f"got {paginator.num_pages}"
        )

    @pytest.mark.hypothesis
    @given(
        items=st.lists(st.integers(), min_size=10, max_size=100),
        page_size=st.integers(min_value=1, max_value=10),
    )
    def test_page_range_within_bounds(self, items, page_size):
        """
        Property: Page range never exceeds valid page numbers.

        The page_range should only contain valid page numbers (1 to num_pages).
        """
        paginator = Paginator(items, per_page=page_size)

        for page_num in range(1, paginator.num_pages + 1):
            context = paginator.page_context(page_num, "/test/")
            page_range = context["page_range"]

            # All page numbers in range should be valid
            for pg in page_range:
                assert 1 <= pg <= paginator.num_pages, (
                    f"Page range contains invalid page {pg} "
                    f"(valid range: 1-{paginator.num_pages})"
                )

    @pytest.mark.hypothesis
    @given(base_url=st.text(alphabet="abcdefghijklmnopqrstuvwxyz/-", min_size=1, max_size=50))
    def test_base_url_normalization(self, base_url):
        """
        Property: base_url in context always ends with /.

        Ensures consistent URL formatting regardless of input.
        """
        paginator = Paginator([1, 2, 3], per_page=2)
        context = paginator.page_context(1, base_url)

        result_url = context["base_url"]
        assert result_url.endswith("/"), f"base_url should end with '/', got '{result_url}'"


# Example output documentation
"""
EXAMPLE HYPOTHESIS OUTPUT
-------------------------

When running these tests, Hypothesis will generate examples like:

1. Empty lists: []
2. Single item: [42]
3. Exact multiples: [1,2,3,4,5,6,7,8,9,10] with per_page=5
4. Partial last page: [1,2,3,4,5,6,7] with per_page=3
5. Large lists: 1000 items with per_page=7
6. Edge case per_page: per_page=1 or per_page=999

Each test runs 100+ times with different combinations,
automatically discovering edge cases like:
- Empty list handling
- Single-page scenarios
- Large page counts
- Boundary conditions

To see statistics:
    pytest tests/unit/utils/test_pagination_properties.py --hypothesis-show-statistics
"""
