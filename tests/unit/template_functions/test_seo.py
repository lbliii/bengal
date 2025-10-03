"""Tests for SEO helper template functions."""

import pytest
from bengal.rendering.template_functions.seo import (
    meta_description,
    meta_keywords,
    canonical_url,
    og_image,
)


class TestMetaDescription:
    """Tests for meta_description filter."""
    
    def test_short_text(self):
        text = "This is a short description."
        result = meta_description(text, length=160)
        assert result == text
    
    def test_long_text(self):
        text = "This is a very long piece of text that needs to be truncated. " * 5
        result = meta_description(text, length=160)
        assert len(result) <= 161  # 160 + ellipsis
    
    def test_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence."
        result = meta_description(text, length=30)
        # Should end at sentence boundary or with ellipsis
        assert result.endswith('.') or result.endswith('…')
    
    def test_html_stripping(self):
        html = "<p>This is <strong>HTML</strong> content.</p>"
        result = meta_description(html)
        assert '<' not in result
        assert '>' not in result
    
    def test_empty_text(self):
        assert meta_description('') == ''


class TestMetaKeywords:
    """Tests for meta_keywords filter."""
    
    def test_basic_keywords(self):
        tags = ['python', 'web', 'development']
        result = meta_keywords(tags)
        assert result == 'python, web, development'
    
    def test_limit_keywords(self):
        tags = ['tag1', 'tag2', 'tag3', 'tag4', 'tag5']
        result = meta_keywords(tags, max_count=3)
        assert result == 'tag1, tag2, tag3'
    
    def test_empty_tags(self):
        assert meta_keywords([]) == ''


class TestCanonicalUrl:
    """Tests for canonical_url function."""
    
    def test_relative_path(self):
        result = canonical_url('/posts/my-post/', 'https://example.com')
        assert result == 'https://example.com/posts/my-post/'
    
    def test_already_absolute(self):
        url = 'https://other.com/page/'
        result = canonical_url(url, 'https://example.com')
        assert result == url
    
    def test_no_base_url(self):
        result = canonical_url('/posts/', '')
        assert result == '/posts/'
    
    def test_empty_path(self):
        result = canonical_url('', 'https://example.com')
        assert result == 'https://example.com'


class TestOgImage:
    """Tests for og_image function."""
    
    def test_relative_path(self):
        result = og_image('hero.jpg', 'https://example.com')
        assert result == 'https://example.com/assets/hero.jpg'
    
    def test_absolute_path(self):
        result = og_image('/images/hero.jpg', 'https://example.com')
        assert result == 'https://example.com/images/hero.jpg'
    
    def test_already_absolute(self):
        url = 'https://cdn.example.com/image.jpg'
        result = og_image(url, 'https://example.com')
        assert result == url
    
    def test_empty_path(self):
        result = og_image('', 'https://example.com')
        assert result == ''

