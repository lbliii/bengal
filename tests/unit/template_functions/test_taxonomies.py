"""Tests for taxonomy helper template functions."""

import pytest
from bengal.rendering.template_functions.taxonomies import (
    related_posts,
    popular_tags,
    tag_url,
    has_tag,
)


class MockPage:
    """Mock page object for testing."""
    def __init__(self, title: str, tags: list = None):
        self.title = title
        self.tags = tags or []


class TestRelatedPosts:
    """Tests for related_posts function."""
    
    def test_find_related(self):
        current = MockPage('Current', ['python', 'web'])
        all_pages = [
            MockPage('Post 1', ['python', 'django']),
            MockPage('Post 2', ['javascript']),
            MockPage('Post 3', ['python', 'web', 'flask']),
        ]
        
        result = related_posts(current, all_pages, limit=5)
        assert len(result) == 2
        # Post 3 should be first (shares 2 tags)
        assert result[0].title == 'Post 3'
    
    def test_no_tags(self):
        current = MockPage('Current', [])
        all_pages = [MockPage('Post 1', ['python'])]
        
        result = related_posts(current, all_pages)
        assert result == []
    
    def test_limit_results(self):
        current = MockPage('Current', ['python'])
        all_pages = [
            MockPage(f'Post {i}', ['python']) for i in range(10)
        ]
        
        result = related_posts(current, all_pages, limit=3)
        assert len(result) == 3


class TestPopularTags:
    """Tests for popular_tags function."""
    
    def test_count_tags(self):
        tags_dict = {
            'python': [1, 2, 3],
            'web': [1, 2],
            'javascript': [1],
        }
        
        result = popular_tags(tags_dict, limit=10)
        assert len(result) == 3
        assert result[0] == ('python', 3)  # Most popular
        assert result[1] == ('web', 2)
    
    def test_limit_tags(self):
        tags_dict = {
            'tag1': [1, 2, 3],
            'tag2': [1, 2],
            'tag3': [1],
        }
        
        result = popular_tags(tags_dict, limit=2)
        assert len(result) == 2
    
    def test_empty_dict(self):
        result = popular_tags({})
        assert result == []


class TestTagUrl:
    """Tests for tag_url function."""
    
    def test_basic_tag(self):
        result = tag_url('python')
        assert result == '/tags/python/'
    
    def test_tag_with_spaces(self):
        result = tag_url('web development')
        assert result == '/tags/web-development/'
    
    def test_tag_with_special_chars(self):
        result = tag_url('C++')
        assert result == '/tags/c/'
    
    def test_empty_tag(self):
        result = tag_url('')
        assert result == '/tags/'


class TestHasTag:
    """Tests for has_tag filter."""
    
    def test_has_tag(self):
        page = MockPage('Test', ['python', 'web'])
        assert has_tag(page, 'python') is True
    
    def test_no_tag(self):
        page = MockPage('Test', ['python'])
        assert has_tag(page, 'javascript') is False
    
    def test_case_insensitive(self):
        page = MockPage('Test', ['Python'])
        assert has_tag(page, 'python') is True
    
    def test_no_tags(self):
        page = MockPage('Test', [])
        assert has_tag(page, 'python') is False

