"""Unit tests for Paginator class."""

import pytest

from bengal.utils.exceptions import BengalError
from bengal.utils.pagination import Paginator


class TestPaginator:
    """Tests for Paginator utility."""

    def test_basic_pagination(self):
        """Test basic pagination with 25 items, 10 per page."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)

        assert paginator.num_pages == 3
        assert len(paginator.page(1)) == 10
        assert len(paginator.page(2)) == 10
        assert len(paginator.page(3)) == 5

    def test_single_page(self):
        """Test pagination with items that fit in one page."""
        items = list(range(5))
        paginator = Paginator(items, per_page=10)

        assert paginator.num_pages == 1
        assert len(paginator.page(1)) == 5

    def test_empty_list(self):
        """Test pagination with empty list."""
        paginator = Paginator([], per_page=10)

        assert paginator.num_pages == 1
        assert len(paginator.page(1)) == 0

    def test_page_out_of_range(self):
        """Test requesting page out of range raises error."""
        items = list(range(10))
        paginator = Paginator(items, per_page=10)

        with pytest.raises(BengalError, match="out of range"):
            paginator.page(2)

        with pytest.raises(BengalError, match="out of range"):
            paginator.page(0)

    def test_page_context(self):
        """Test page_context generates correct data."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)

        context = paginator.page_context(2, "/posts/")

        assert context["current_page"] == 2
        assert context["total_pages"] == 3
        assert context["has_previous"] is True
        assert context["has_next"] is True
        assert context["previous_page"] == 1
        assert context["next_page"] == 3
        assert context["base_url"] == "/posts/"

    def test_page_context_first_page(self):
        """Test page_context for first page."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)

        context = paginator.page_context(1, "/posts/")

        assert context["has_previous"] is False
        assert context["has_next"] is True
        assert context["previous_page"] is None

    def test_page_context_last_page(self):
        """Test page_context for last page."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)

        context = paginator.page_context(3, "/posts/")

        assert context["has_previous"] is True
        assert context["has_next"] is False
        assert context["next_page"] is None

    def test_per_page_minimum(self):
        """Test per_page is minimum 1."""
        items = list(range(10))
        paginator = Paginator(items, per_page=0)

        assert paginator.per_page == 1
        assert paginator.num_pages == 10

    def test_page_range(self):
        """Test page_range calculation."""
        items = list(range(100))
        paginator = Paginator(items, per_page=10)

        # Should show ±2 pages around current
        context = paginator.page_context(5, "/posts/")
        assert context["page_range"] == [3, 4, 5, 6, 7]

    def test_base_url_trailing_slash(self):
        """Test base_url gets trailing slash if missing."""
        items = list(range(10))
        paginator = Paginator(items, per_page=5)

        context = paginator.page_context(1, "/posts")
        assert context["base_url"] == "/posts/"
