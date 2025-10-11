"""
Tests for Site property caching optimizations.

Verifies that expensive properties like regular_pages are cached
to prevent O(n²) performance issues.
"""

from bengal.core.site import Site
from bengal.core.page import Page


def test_regular_pages_caching(tmp_path):
    """Test that regular_pages is cached after first access."""
    site = Site(root_path=tmp_path)
    
    # Add some pages
    regular_page_1 = Page(source_path=tmp_path / "page1.md", metadata={'title': 'Page 1'})
    regular_page_2 = Page(source_path=tmp_path / "page2.md", metadata={'title': 'Page 2'})
    generated_page = Page(
        source_path=tmp_path / "tags" / "python.md", 
        metadata={'title': 'Python Tag', '_generated': True}
    )
    
    site.pages = [regular_page_1, regular_page_2, generated_page]
    
    # First access should compute and cache
    assert site._regular_pages_cache is None
    regular = site.regular_pages
    assert len(regular) == 2
    assert regular_page_1 in regular
    assert regular_page_2 in regular
    assert generated_page not in regular
    
    # Cache should now be populated
    assert site._regular_pages_cache is not None
    assert len(site._regular_pages_cache) == 2
    
    # Second access should use cache (same object reference)
    regular2 = site.regular_pages
    assert regular2 is site._regular_pages_cache


def test_regular_pages_cache_invalidation(tmp_path):
    """Test that regular_pages cache is invalidated when pages change."""
    site = Site(root_path=tmp_path)
    
    # Add initial pages
    regular_page = Page(source_path=tmp_path / "page1.md", metadata={'title': 'Page 1'})
    site.pages = [regular_page]
    
    # Access to populate cache
    regular = site.regular_pages
    assert len(regular) == 1
    assert site._regular_pages_cache is not None
    
    # Invalidate cache
    site.invalidate_regular_pages_cache()
    assert site._regular_pages_cache is None
    
    # Add a generated page
    generated_page = Page(
        source_path=tmp_path / "tags" / "python.md", 
        metadata={'title': 'Python Tag', '_generated': True}
    )
    site.pages.append(generated_page)
    
    # Access again should recompute
    regular2 = site.regular_pages
    assert len(regular2) == 1  # Still only 1 regular page
    assert generated_page not in regular2


def test_regular_pages_empty_site(tmp_path):
    """Test regular_pages with no pages."""
    site = Site(root_path=tmp_path)
    site.pages = []
    
    regular = site.regular_pages
    assert regular == []
    assert site._regular_pages_cache == []


def test_regular_pages_all_generated(tmp_path):
    """Test regular_pages when all pages are generated."""
    site = Site(root_path=tmp_path)
    
    generated1 = Page(
        source_path=tmp_path / "tags" / "python.md", 
        metadata={'title': 'Python Tag', '_generated': True}
    )
    generated2 = Page(
        source_path=tmp_path / "tags" / "django.md", 
        metadata={'title': 'Django Tag', '_generated': True}
    )
    
    site.pages = [generated1, generated2]
    
    regular = site.regular_pages
    assert regular == []
    assert site._regular_pages_cache == []


def test_regular_pages_cache_performance(tmp_path):
    """Test that caching provides O(1) subsequent access."""
    import time
    
    site = Site(root_path=tmp_path)
    
    # Add many pages
    for i in range(1000):
        is_generated = i % 10 == 0  # Every 10th page is generated
        page = Page(
            source_path=tmp_path / f"page{i}.md",
            metadata={
                'title': f'Page {i}',
                '_generated': is_generated
            }
        )
        site.pages.append(page)
    
    # First access (should filter all pages)
    start = time.time()
    regular1 = site.regular_pages
    first_time = time.time() - start
    assert len(regular1) == 900  # 900 regular, 100 generated
    
    # Second access (should use cache)
    start = time.time()
    regular2 = site.regular_pages
    second_time = time.time() - start
    
    # Cached access should be MUCH faster (at least 10x)
    assert second_time < first_time / 10
    assert regular2 is site._regular_pages_cache


def test_regular_pages_cache_across_multiple_accesses(tmp_path):
    """Test that cache remains valid across many accesses."""
    site = Site(root_path=tmp_path)
    
    # Add pages
    for i in range(100):
        page = Page(
            source_path=tmp_path / f"page{i}.md",
            metadata={'title': f'Page {i}'}
        )
        site.pages.append(page)
    
    # Access multiple times
    for _ in range(10):
        regular = site.regular_pages
        assert len(regular) == 100
        assert regular is site._regular_pages_cache

