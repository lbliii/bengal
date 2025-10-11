"""Tests for pagination helper template functions."""

from bengal.rendering.template_functions.pagination_helpers import (
    paginate_items,
    page_url,
    page_range,
)


class TestPaginateItems:
    """Tests for paginate_items filter."""
    
    def test_basic_pagination(self):
        items = list(range(25))
        result = paginate_items(items, per_page=10, current_page=1)
        
        assert len(result['items']) == 10
        assert result['total_pages'] == 3
        assert result['current_page'] == 1
        assert result['has_next'] is True
        assert result['has_prev'] is False
    
    def test_last_page(self):
        items = list(range(25))
        result = paginate_items(items, per_page=10, current_page=3)
        
        assert len(result['items']) == 5  # Last page has 5 items
        assert result['has_next'] is False
        assert result['has_prev'] is True
    
    def test_empty_list(self):
        result = paginate_items([], per_page=10)
        assert result['items'] == []
        assert result['total_pages'] == 0
    
    def test_single_page(self):
        items = list(range(5))
        result = paginate_items(items, per_page=10)
        
        assert len(result['items']) == 5
        assert result['total_pages'] == 1
        assert result['has_next'] is False
        assert result['has_prev'] is False


class TestPageUrl:
    """Tests for page_url function."""
    
    def test_first_page(self):
        result = page_url('/posts/', 1)
        assert result == '/posts/'
    
    def test_second_page(self):
        result = page_url('/posts/', 2)
        assert result == '/posts/page/2/'
    
    def test_page_zero(self):
        result = page_url('/posts/', 0)
        assert result == '/posts/'
    
    def test_trailing_slash(self):
        result = page_url('/posts', 2)
        assert result == '/posts/page/2/'


class TestPageRange:
    """Tests for page_range function."""
    
    def test_small_range(self):
        result = page_range(1, 5, window=2)
        assert result == [1, 2, 3, 4, 5]
    
    def test_with_ellipsis_before(self):
        result = page_range(10, 20, window=2)
        assert result[0] == 1
        assert result[1] is None  # Ellipsis
        assert 10 in result
    
    def test_with_ellipsis_after(self):
        result = page_range(5, 20, window=2)
        assert 20 in result
        assert None in result  # Ellipsis somewhere
    
    def test_both_ellipsis(self):
        result = page_range(10, 30, window=2)
        assert result[0] == 1
        assert result[-1] == 30
        assert result.count(None) == 2  # Two ellipses
    
    def test_single_page(self):
        result = page_range(1, 1)
        assert result == [1]

