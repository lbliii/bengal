"""
Tests for incremental taxonomy collection optimization.
"""

import pytest
from pathlib import Path
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.core.page import Page
from bengal.core.site import Site
from bengal.cache.build_cache import BuildCache


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site for testing."""
    site = Site(root_path=tmp_path, config={})
    site.pages = []
    site.taxonomies = {}
    return site


@pytest.fixture
def mock_cache():
    """Create a mock build cache."""
    return BuildCache()


def test_incremental_collection_tag_added(mock_site, mock_cache):
    """Test adding a tag to an existing page."""
    # Setup: Existing page with one tag
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page1.__post_init__()
    
    mock_site.pages = [page1]
    mock_site.taxonomies = {
        'tags': {
            'python': {'name': 'Python', 'slug': 'python', 'pages': [page1]}
        },
        'categories': {}
    }
    
    # Cache previous tags
    mock_cache.update_page_tags(page1.source_path, {"python"})
    
    # Modify page: Add a new tag
    page1_modified = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python", "django"]})
    page1_modified.__post_init__()
    
    # Update site.pages with modified page (simulates how the build system would work)
    mock_site.pages = [page1_modified]
    
    # Run incremental collection
    orchestrator = TaxonomyOrchestrator(mock_site)
    affected_tags = orchestrator.collect_and_generate_incremental([page1_modified], mock_cache)
    
    # Verify: django tag was added
    assert 'django' in affected_tags
    assert 'django' in mock_site.taxonomies['tags']
    assert page1_modified in mock_site.taxonomies['tags']['django']['pages']
    
    # python tag should still be there (and marked as affected for sort order)
    assert 'python' in affected_tags
    assert page1_modified in mock_site.taxonomies['tags']['python']['pages']


def test_incremental_collection_tag_removed(mock_site, mock_cache):
    """Test removing a tag from an existing page."""
    # Setup: Existing page with two tags
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python", "django"]})
    page1.__post_init__()
    
    mock_site.pages = [page1]
    mock_site.taxonomies = {
        'tags': {
            'python': {'name': 'Python', 'slug': 'python', 'pages': [page1]},
            'django': {'name': 'Django', 'slug': 'django', 'pages': [page1]}
        },
        'categories': {}
    }
    
    # Cache previous tags
    mock_cache.update_page_tags(page1.source_path, {"python", "django"})
    
    # Modify page: Remove django tag
    page1_modified = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page1_modified.__post_init__()
    
    # Update site.pages with modified page
    mock_site.pages = [page1_modified]
    
    # Run incremental collection
    orchestrator = TaxonomyOrchestrator(mock_site)
    affected_tags = orchestrator.collect_and_generate_incremental([page1_modified], mock_cache)
    
    # Verify: django tag was removed
    assert 'django' in affected_tags
    assert 'django' not in mock_site.taxonomies['tags'], "Empty tag should be removed"
    
    # python tag should still be there
    assert 'python' in affected_tags
    assert page1_modified in mock_site.taxonomies['tags']['python']['pages']


def test_incremental_collection_multiple_pages(mock_site, mock_cache):
    """Test incremental collection with multiple changed pages."""
    # Setup: Three pages with various tags
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page2 = Page(source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["python", "flask"]})
    page3 = Page(source_path=Path("page3.md"), metadata={"title": "Post 3", "tags": ["javascript"]})
    
    for page in [page1, page2, page3]:
        page.__post_init__()
    
    mock_site.pages = [page1, page2, page3]
    mock_site.taxonomies = {
        'tags': {
            'python': {'name': 'Python', 'slug': 'python', 'pages': [page1, page2]},
            'flask': {'name': 'Flask', 'slug': 'flask', 'pages': [page2]},
            'javascript': {'name': 'JavaScript', 'slug': 'javascript', 'pages': [page3]}
        },
        'categories': {}
    }
    
    # Cache previous tags
    mock_cache.update_page_tags(page1.source_path, {"python"})
    mock_cache.update_page_tags(page2.source_path, {"python", "flask"})
    
    # Modify page1: Add django
    page1_modified = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python", "django"]})
    page1_modified.__post_init__()
    
    # Modify page2: Remove flask
    page2_modified = Page(source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["python"]})
    page2_modified.__post_init__()
    
    # Update site.pages with modified pages
    mock_site.pages = [page1_modified, page2_modified, page3]
    
    # Run incremental collection  
    orchestrator = TaxonomyOrchestrator(mock_site)
    affected_tags = orchestrator.collect_and_generate_incremental([page1_modified, page2_modified], mock_cache)
    
    # Verify affected tags
    assert 'django' in affected_tags  # Added
    assert 'flask' in affected_tags   # Removed
    assert 'python' in affected_tags  # Updated (both pages)
    
    # Verify tag structure
    assert 'django' in mock_site.taxonomies['tags']
    assert 'flask' not in mock_site.taxonomies['tags'], "Empty flask tag should be removed"
    assert len(mock_site.taxonomies['tags']['python']['pages']) == 2


def test_incremental_collection_no_previous_taxonomy(mock_site, mock_cache):
    """Test that first build does full collection."""
    # Setup: No existing taxonomy
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page1.__post_init__()
    
    mock_site.pages = [page1]
    # No taxonomies set
    
    # Run incremental collection
    orchestrator = TaxonomyOrchestrator(mock_site)
    affected_tags = orchestrator.collect_and_generate_incremental([page1], mock_cache)
    
    # Should fall back to full collection
    assert 'python' in affected_tags
    assert 'python' in mock_site.taxonomies['tags']
    assert page1 in mock_site.taxonomies['tags']['python']['pages']


def test_incremental_collection_skips_generated_pages(mock_site, mock_cache):
    """Test that generated pages are skipped."""
    # Setup: Regular page and generated page
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page2 = Page(source_path=Path("tags/python.md"), metadata={
        "title": "Python Tag", 
        "tags": ["python"],
        "_generated": True
    })
    
    page1.__post_init__()
    page2.__post_init__()
    
    mock_site.pages = [page1, page2]
    mock_site.taxonomies = {
        'tags': {
            'python': {'name': 'Python', 'slug': 'python', 'pages': [page1]}
        },
        'categories': {}
    }
    
    mock_cache.update_page_tags(page1.source_path, {"python"})
    
    # Modify both pages (adding django tag)
    page1_modified = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python", "django"]})
    page2_modified = Page(source_path=Path("tags/python.md"), metadata={
        "title": "Python Tag",
        "tags": ["python", "django"],
        "_generated": True
    })
    
    page1_modified.__post_init__()
    page2_modified.__post_init__()
    
    # Update site.pages with modified pages
    mock_site.pages = [page1_modified, page2_modified]
    
    # Run incremental collection
    orchestrator = TaxonomyOrchestrator(mock_site)
    affected_tags = orchestrator.collect_and_generate_incremental([page1_modified, page2_modified], mock_cache)
    
    # Verify: Only page1 update was processed
    assert 'django' in affected_tags
    assert 'django' in mock_site.taxonomies['tags']
    # page2 (generated) should not be in django tag
    assert page2_modified not in mock_site.taxonomies['tags']['django']['pages']


def test_incremental_collection_sorting(mock_site, mock_cache):
    """Test that pages are sorted by date within tags."""
    from datetime import datetime
    
    # Setup: Two pages with same tag but different dates
    page1 = Page(
        source_path=Path("page1.md"),
        metadata={"title": "Old Post", "tags": ["python"], "date": datetime(2024, 1, 1)}
    )
    page2 = Page(
        source_path=Path("page2.md"),
        metadata={"title": "New Post", "tags": ["python"], "date": datetime(2024, 12, 1)}
    )
    
    page1.__post_init__()
    page2.__post_init__()
    
    mock_site.pages = [page1, page2]
    mock_site.taxonomies = {
        'tags': {
            'python': {'name': 'Python', 'slug': 'python', 'pages': [page1, page2]}
        },
        'categories': {}
    }
    
    mock_cache.update_page_tags(page1.source_path, {"python"})
    mock_cache.update_page_tags(page2.source_path, {"python"})
    
    # Modify page1 content (trigger resort)
    page1_modified = Page(
        source_path=Path("page1.md"),
        metadata={"title": "Old Post Updated", "tags": ["python"], "date": datetime(2024, 1, 1)}
    )
    page1_modified.__post_init__()
    
    # Update site.pages with modified pages
    mock_site.pages = [page1_modified, page2]
    
    # Run incremental collection
    orchestrator = TaxonomyOrchestrator(mock_site)
    orchestrator.collect_and_generate_incremental([page1_modified], mock_cache)
    
    # Verify: Pages are sorted by date (newest first)
    pages = mock_site.taxonomies['tags']['python']['pages']
    assert pages[0].date > pages[1].date, "Pages should be sorted newest first"


def test_collect_and_generate_incremental(mock_site, mock_cache):
    """Test the full incremental collect and generate flow."""
    # Setup: Existing page with tags
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page1.__post_init__()
    
    mock_site.pages = [page1]
    mock_site.taxonomies = {
        'tags': {
            'python': {'name': 'Python', 'slug': 'python', 'pages': [page1]}
        },
        'categories': {}
    }
    
    mock_cache.update_page_tags(page1.source_path, {"python"})
    
    # Modify page: Add django tag
    page1_modified = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python", "django"]})
    page1_modified.__post_init__()
    
    # Update site.pages with modified page
    mock_site.pages = [page1_modified]
    
    # Run full incremental flow
    orchestrator = TaxonomyOrchestrator(mock_site)
    affected_tags = orchestrator.collect_and_generate_incremental([page1_modified], mock_cache)
    
    # Verify affected tags returned
    assert 'django' in affected_tags
    assert 'python' in affected_tags
    
    # Note: generate_dynamic_pages_for_tags() creates actual Page objects
    # which would be tested in integration tests


