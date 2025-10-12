"""
Tests for related posts orchestration.
"""

from pathlib import Path

import pytest

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.orchestration.related_posts import RelatedPostsOrchestrator


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site for testing."""
    site = Site(root_path=tmp_path, config={})
    site.pages = []
    site.taxonomies = {}
    return site


def test_related_posts_with_shared_tags(mock_site):
    """Pages with shared tags should be related."""
    # Create pages with tags
    page1 = Page(
        source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python", "django"]}
    )
    page2 = Page(
        source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["python", "flask"]}
    )
    page3 = Page(source_path=Path("page3.md"), metadata={"title": "Post 3", "tags": ["javascript"]})

    page1.__post_init__()
    page2.__post_init__()
    page3.__post_init__()

    mock_site.pages = [page1, page2, page3]

    # Build taxonomy structure
    mock_site.taxonomies = {
        "tags": {
            "python": {"name": "Python", "slug": "python", "pages": [page1, page2]},
            "django": {"name": "Django", "slug": "django", "pages": [page1]},
            "flask": {"name": "Flask", "slug": "flask", "pages": [page2]},
            "javascript": {"name": "JavaScript", "slug": "javascript", "pages": [page3]},
        }
    }

    # Build related posts index
    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5)

    # Verify results
    # page1 and page2 share "python" tag
    assert page2 in page1.related_posts, "page2 should be related to page1 (shared tag: python)"
    assert page1 in page2.related_posts, "page1 should be related to page2 (shared tag: python)"

    # page3 has no shared tags with page1 or page2
    assert page3 not in page1.related_posts, "page3 should not be related to page1 (no shared tags)"
    assert page1 not in page3.related_posts, "page1 should not be related to page3 (no shared tags)"
    assert len(page3.related_posts) == 0, "page3 should have no related posts"


def test_related_posts_sorted_by_relevance(mock_site):
    """Related posts should be sorted by number of shared tags."""
    # Create pages with varying tag overlap
    page1 = Page(
        source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["a", "b", "c"]}
    )
    page2 = Page(
        source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["a", "b", "c"]}
    )  # 3 shared
    page3 = Page(
        source_path=Path("page3.md"), metadata={"title": "Post 3", "tags": ["a", "b"]}
    )  # 2 shared
    page4 = Page(
        source_path=Path("page4.md"), metadata={"title": "Post 4", "tags": ["a"]}
    )  # 1 shared

    for page in [page1, page2, page3, page4]:
        page.__post_init__()

    mock_site.pages = [page1, page2, page3, page4]

    # Build taxonomy structure
    mock_site.taxonomies = {
        "tags": {
            "a": {"name": "A", "slug": "a", "pages": [page1, page2, page3, page4]},
            "b": {"name": "B", "slug": "b", "pages": [page1, page2, page3]},
            "c": {"name": "C", "slug": "c", "pages": [page1, page2]},
        }
    }

    # Build related posts index
    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5)

    # Verify sorting by relevance
    # page1 should be related to: page2 (3 tags), page3 (2 tags), page4 (1 tag)
    assert len(page1.related_posts) == 3, "page1 should have 3 related posts"
    assert page1.related_posts[0] == page2, "page2 should be first (3 shared tags)"
    assert page1.related_posts[1] == page3, "page3 should be second (2 shared tags)"
    assert page1.related_posts[2] == page4, "page4 should be third (1 shared tag)"


def test_related_posts_respects_limit(mock_site):
    """Should respect the limit parameter."""
    # Create many pages with same tag
    pages = []
    for i in range(10):
        page = Page(
            source_path=Path(f"page{i}.md"), metadata={"title": f"Post {i}", "tags": ["python"]}
        )
        page.__post_init__()
        pages.append(page)

    mock_site.pages = pages
    mock_site.taxonomies = {
        "tags": {"python": {"name": "Python", "slug": "python", "pages": pages}}
    }

    # Build with limit of 3
    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=3)

    # Each page should have exactly 3 related posts (not all 9 others)
    for page in pages:
        assert len(page.related_posts) == 3, (
            f"Page should have exactly 3 related posts, got {len(page.related_posts)}"
        )


def test_related_posts_skips_generated_pages(mock_site):
    """Should skip generated pages (tag indexes, archives, etc.)."""
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page2 = Page(
        source_path=Path("page2.md"),
        metadata={"title": "Post 2", "tags": ["python"], "_generated": True},
    )

    page1.__post_init__()
    page2.__post_init__()

    mock_site.pages = [page1, page2]
    mock_site.taxonomies = {
        "tags": {"python": {"name": "Python", "slug": "python", "pages": [page1, page2]}}
    }

    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5)

    # page1 should not have page2 as related (it's generated)
    assert page2 not in page1.related_posts, "Generated pages should be excluded from related posts"

    # Generated page should have empty related_posts
    assert page2.related_posts == [], "Generated pages should have empty related_posts"


def test_related_posts_no_tags(mock_site):
    """Pages without tags should have no related posts."""
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1"})  # No tags
    page2 = Page(source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["python"]})

    page1.__post_init__()
    page2.__post_init__()

    mock_site.pages = [page1, page2]
    mock_site.taxonomies = {
        "tags": {"python": {"name": "Python", "slug": "python", "pages": [page2]}}
    }

    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5)

    # page1 has no tags, should have no related posts
    assert len(page1.related_posts) == 0, "Pages without tags should have no related posts"


def test_related_posts_no_taxonomies(mock_site):
    """Should handle sites without taxonomies gracefully."""
    page1 = Page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page1.__post_init__()

    mock_site.pages = [page1]
    # No taxonomies built

    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5)

    # Should not crash, just return empty lists
    assert len(page1.related_posts) == 0, "Should handle missing taxonomies gracefully"
