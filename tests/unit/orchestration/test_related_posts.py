"""
Tests for related posts orchestration.
"""

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.related_posts import RelatedPostsOrchestrator
from tests._testing.mocks import make_mock_page as _page


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
    page1 = _page(
        source_path=Path("page1.md"),
        metadata={"title": "Post 1", "tags": ["python", "django"]},
    )
    page2 = _page(
        source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["python", "flask"]}
    )
    page3 = _page(
        source_path=Path("page3.md"), metadata={"title": "Post 3", "tags": ["javascript"]}
    )

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
    page1 = _page(
        source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["a", "b", "c"]}
    )
    page2 = _page(
        source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["a", "b", "c"]}
    )  # 3 shared
    page3 = _page(
        source_path=Path("page3.md"), metadata={"title": "Post 3", "tags": ["a", "b"]}
    )  # 2 shared
    page4 = _page(
        source_path=Path("page4.md"), metadata={"title": "Post 4", "tags": ["a"]}
    )  # 1 shared

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
        page = _page(
            source_path=Path(f"page{i}.md"),
            metadata={"title": f"Post {i}", "tags": ["python"]},
        )
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
    page1 = _page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    page2 = _page(
        source_path=Path("page2.md"),
        metadata={"title": "Post 2", "tags": ["python"], "_generated": True},
    )

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
    page1 = _page(source_path=Path("page1.md"), metadata={"title": "Post 1"})  # No tags
    page2 = _page(source_path=Path("page2.md"), metadata={"title": "Post 2", "tags": ["python"]})

    mock_site.pages = [page1, page2]
    mock_site.taxonomies = {
        "tags": {"python": {"name": "Python", "slug": "python", "pages": [page2]}}
    }

    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5)

    # page1 has no tags, should have no related posts
    assert len(page1.related_posts) == 0, "Pages without tags should have no related posts"


def test_related_posts_equal_score_tie_break_is_stable(mock_site):
    """Equal-score candidates must order by the stable source_path key.

    Regression guard (#350 S9): the candidate-index refactor moved the tie-break
    into a precomputed sort_keys map. When several candidates share the same
    number of tags (equal score), their order must be deterministic
    (source_path-sorted), not dependent on insertion/scheduling order — otherwise
    related-posts, and every page rendering them, diverge run-to-run.
    """
    target = _page(source_path=Path("aaa_target.md"), metadata={"title": "T", "tags": ["x"]})
    # Each candidate shares exactly one tag ("x") with target -> all score == 1.
    # Insertion order is deliberately NOT alphabetical.
    cand_c = _page(source_path=Path("ccc.md"), metadata={"title": "C", "tags": ["x"]})
    cand_a = _page(source_path=Path("aab.md"), metadata={"title": "A", "tags": ["x"]})
    cand_b = _page(source_path=Path("bbb.md"), metadata={"title": "B", "tags": ["x"]})

    mock_site.pages = [target, cand_c, cand_a, cand_b]
    mock_site.taxonomies = {
        "tags": {"x": {"name": "X", "slug": "x", "pages": [target, cand_c, cand_a, cand_b]}}
    }

    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5, parallel=False)

    related_paths = [str(p.source_path) for p in target.related_posts]
    assert related_paths == ["aab.md", "bbb.md", "ccc.md"], (
        f"equal-score candidates must be source_path-sorted, got {related_paths}"
    )
    # Explicitly: the order is the stable sort, independent of insertion order.
    assert related_paths == sorted(related_paths)


def test_related_posts_no_taxonomies(mock_site):
    """Should handle sites without taxonomies gracefully."""
    page1 = _page(source_path=Path("page1.md"), metadata={"title": "Post 1", "tags": ["python"]})
    mock_site.pages = [page1]
    # No taxonomies built

    orchestrator = RelatedPostsOrchestrator(mock_site)
    orchestrator.build_index(limit=5)

    # Should not crash, just return empty lists
    assert len(page1.related_posts) == 0, "Should handle missing taxonomies gracefully"
