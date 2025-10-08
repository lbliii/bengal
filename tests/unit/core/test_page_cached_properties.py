"""
Tests for Page cached properties (meta_description, reading_time, excerpt).

Tests automatic caching behavior and performance optimization.
"""

import pytest
from pathlib import Path
from bengal.core.page import Page


class TestPageMetaDescription:
    """Test Page.meta_description cached property."""
    
    def test_meta_description_from_metadata(self, tmp_path):
        """Explicit description in metadata is used."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="Some long content here that would be truncated",
            metadata={'description': 'Custom description'}
        )
        
        assert page.meta_description == 'Custom description'
    
    def test_meta_description_from_content(self, tmp_path):
        """Description generated from content when not in metadata."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="This is the content of the page with some text.",
            metadata={}
        )
        
        desc = page.meta_description
        assert desc == "This is the content of the page with some text."
        assert len(desc) <= 160
    
    def test_meta_description_strips_html(self, tmp_path):
        """HTML tags are stripped from content."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="<p>This is <strong>bold</strong> text.</p>",
            metadata={}
        )
        
        assert page.meta_description == "This is bold text."
    
    def test_meta_description_truncates_long_content(self, tmp_path):
        """Long content is truncated to 160 chars."""
        long_content = "This is a very long piece of content. " * 20
        page = Page(
            source_path=tmp_path / "test.md",
            content=long_content,
            metadata={}
        )
        
        desc = page.meta_description
        assert len(desc) <= 160
        # Should end with sentence boundary (.) or word boundary (…)
        assert desc.endswith('.') or desc.endswith('…')
    
    def test_meta_description_sentence_boundary(self, tmp_path):
        """Tries to end at sentence boundary."""
        content = "First sentence. Second sentence. Third sentence. " * 10
        page = Page(
            source_path=tmp_path / "test.md",
            content=content,
            metadata={}
        )
        
        desc = page.meta_description
        # Should end at a sentence boundary (period)
        assert desc.endswith('.') or desc.endswith('…')
    
    def test_meta_description_caching(self, tmp_path):
        """Result is cached after first access."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="Original content",
            metadata={}
        )
        
        # First access computes
        desc1 = page.meta_description
        
        # Modify content (shouldn't affect cached result)
        page.content = "Modified content"
        
        # Second access returns cached value
        desc2 = page.meta_description
        
        assert desc1 == desc2 == "Original content"
        assert desc1 is desc2  # Same object in memory
    
    def test_meta_description_empty_content(self, tmp_path):
        """Empty content returns empty string."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="",
            metadata={}
        )
        
        assert page.meta_description == ''
    
    def test_meta_description_whitespace_normalization(self, tmp_path):
        """Multiple spaces are normalized."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="This  has    multiple   spaces",
            metadata={}
        )
        
        assert page.meta_description == "This has multiple spaces"


class TestPageReadingTime:
    """Test Page.reading_time cached property."""
    
    def test_reading_time_calculation(self, tmp_path):
        """Reading time calculated at 200 WPM."""
        # 400 words = 2 minutes at 200 WPM
        words = ["word"] * 400
        content = " ".join(words)
        
        page = Page(
            source_path=tmp_path / "test.md",
            content=content,
            metadata={}
        )
        
        assert page.reading_time == 2
    
    def test_reading_time_minimum_one(self, tmp_path):
        """Minimum reading time is 1 minute."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="Just a few words",
            metadata={}
        )
        
        assert page.reading_time >= 1
    
    def test_reading_time_strips_html(self, tmp_path):
        """HTML tags are stripped before counting words."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="<p>This is <strong>bold</strong> text.</p>",
            metadata={}
        )
        
        # Should count 4 words (HTML tags stripped)
        assert page.reading_time == 1
    
    def test_reading_time_rounds_correctly(self, tmp_path):
        """Reading time is rounded to nearest minute."""
        # 250 words = 1.25 minutes -> rounds to 1
        words = ["word"] * 250
        content = " ".join(words)
        
        page = Page(
            source_path=tmp_path / "test.md",
            content=content,
            metadata={}
        )
        
        assert page.reading_time == 1
        
        # 350 words = 1.75 minutes -> rounds to 2
        words = ["word"] * 350
        content = " ".join(words)
        
        page2 = Page(
            source_path=tmp_path / "test2.md",
            content=content,
            metadata={}
        )
        
        assert page2.reading_time == 2
    
    def test_reading_time_caching(self, tmp_path):
        """Result is cached after first access."""
        page = Page(
            source_path=tmp_path / "test.md",
            content=" ".join(["word"] * 400),
            metadata={}
        )
        
        # First access computes
        time1 = page.reading_time
        
        # Modify content (shouldn't affect cached result)
        page.content = "short"
        
        # Second access returns cached value
        time2 = page.reading_time
        
        assert time1 == time2 == 2
    
    def test_reading_time_empty_content(self, tmp_path):
        """Empty content returns 1 minute."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="",
            metadata={}
        )
        
        assert page.reading_time == 1


class TestPageExcerpt:
    """Test Page.excerpt cached property."""
    
    def test_excerpt_short_content(self, tmp_path):
        """Short content is returned as-is."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="Short content here.",
            metadata={}
        )
        
        assert page.excerpt == "Short content here."
    
    def test_excerpt_long_content_truncated(self, tmp_path):
        """Long content is truncated to 200 chars."""
        long_content = "This is a long piece of content. " * 20
        page = Page(
            source_path=tmp_path / "test.md",
            content=long_content,
            metadata={}
        )
        
        excerpt = page.excerpt
        assert len(excerpt) <= 203  # 200 + "..."
        assert excerpt.endswith("...")
    
    def test_excerpt_strips_html(self, tmp_path):
        """HTML tags are stripped."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="<p>This is <strong>bold</strong> text.</p>",
            metadata={}
        )
        
        assert page.excerpt == "This is bold text."
    
    def test_excerpt_word_boundaries(self, tmp_path):
        """Respects word boundaries (doesn't cut words)."""
        # Create content that would normally be cut mid-word
        content = "A" * 195 + " word that would be cut"
        page = Page(
            source_path=tmp_path / "test.md",
            content=content,
            metadata={}
        )
        
        excerpt = page.excerpt
        # Should not cut the word "that"
        assert not excerpt.endswith("tha...")
        assert excerpt.endswith("...")
    
    def test_excerpt_caching(self, tmp_path):
        """Result is cached after first access."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="Original content here",
            metadata={}
        )
        
        # First access computes
        excerpt1 = page.excerpt
        
        # Modify content (shouldn't affect cached result)
        page.content = "Modified content"
        
        # Second access returns cached value
        excerpt2 = page.excerpt
        
        assert excerpt1 == excerpt2 == "Original content here"
        assert excerpt1 is excerpt2  # Same object in memory
    
    def test_excerpt_empty_content(self, tmp_path):
        """Empty content returns empty string."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="",
            metadata={}
        )
        
        assert page.excerpt == ''


class TestCachedPropertiesIntegration:
    """Test interaction between cached properties and Page lifecycle."""
    
    def test_multiple_pages_independent_caches(self, tmp_path):
        """Each page has its own independent cache."""
        page1 = Page(
            source_path=tmp_path / "page1.md",
            content="Content for page one",
            metadata={}
        )
        page2 = Page(
            source_path=tmp_path / "page2.md",
            content="Content for page two",
            metadata={}
        )
        
        desc1 = page1.meta_description
        desc2 = page2.meta_description
        
        assert desc1 == "Content for page one"
        assert desc2 == "Content for page two"
        assert desc1 != desc2
    
    def test_cached_properties_persist_across_accesses(self, tmp_path):
        """Cached properties can be accessed multiple times efficiently."""
        page = Page(
            source_path=tmp_path / "test.md",
            content="Test content",
            metadata={}
        )
        
        # Access each property multiple times
        for _ in range(5):
            desc = page.meta_description
            time = page.reading_time
            excerpt = page.excerpt
        
        # Should still have consistent values
        assert page.meta_description == "Test content"
        assert page.reading_time == 1
        assert page.excerpt == "Test content"
    
    def test_all_cached_properties_together(self, tmp_path):
        """All three cached properties work together."""
        content = "This is test content. " * 50
        page = Page(
            source_path=tmp_path / "test.md",
            content=content,
            metadata={}
        )
        
        # All should be computable
        desc = page.meta_description
        time = page.reading_time
        excerpt = page.excerpt
        
        assert len(desc) <= 160
        assert time >= 1
        assert len(excerpt) <= 203  # 200 + "..."
        
        # All should be cached
        assert page.meta_description is desc
        assert page.reading_time is time
        assert page.excerpt is excerpt

