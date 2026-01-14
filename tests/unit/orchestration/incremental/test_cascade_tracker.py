"""
Tests for CascadeTracker component of the incremental package.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.orchestration.build.results import ChangeSummary
from bengal.orchestration.incremental.cascade_tracker import CascadeTracker
from bengal.utils.primitives.hashing import hash_str


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site with sections."""
    site = Mock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.pages = []
    site.sections = []
    # page_by_source_path is a dict property built from site.pages
    # The real implementation is a cached property on PageCachesMixin
    site.page_by_source_path = {}
    return site


@pytest.fixture
def mock_cache():
    """Create a mock BuildCache for testing."""
    cache = Mock()
    cache.parsed_content = {}
    return cache


@pytest.fixture
def tracker(mock_site):
    """Create a CascadeTracker instance without cache."""
    return CascadeTracker(mock_site)


@pytest.fixture
def tracker_with_cache(mock_site, mock_cache):
    """Create a CascadeTracker instance with cache."""
    return CascadeTracker(mock_site, mock_cache)


class TestCascadeRebuilds:
    """Test cascade-driven rebuild logic."""

    def test_cascade_change_marks_descendants(self, tracker, mock_site):
        """When section index with cascade changes, mark descendants."""
        # Create index page with cascade
        index_page = Page(
            source_path=Path("/site/content/docs/_index.md"),
            _raw_content="Index",
            metadata={"title": "Docs", "cascade": {"type": "doc"}},
        )

        # Create child pages
        child1 = Page(
            source_path=Path("/site/content/docs/page1.md"),
            _raw_content="Page 1",
            metadata={"title": "Page 1"},
        )
        child2 = Page(
            source_path=Path("/site/content/docs/page2.md"),
            _raw_content="Page 2",
            metadata={"title": "Page 2"},
        )

        # Create a mock section
        section = Mock()
        section.name = "docs"
        section.path = Path("/site/content/docs")
        section.index_page = index_page
        section.pages = [index_page, child1, child2]
        section.regular_pages_recursive = [child1, child2]

        mock_site.pages = [index_page, child1, child2]
        mock_site.sections = [section]
        # Update page_by_source_path cache (mirrors PageCachesMixin behavior)
        mock_site.page_by_source_path = {p.source_path: p for p in mock_site.pages}

        # Prepare inputs
        pages_to_rebuild = {index_page.source_path}
        change_summary = ChangeSummary()

        # Apply cascade
        affected_count = tracker.apply_cascade_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=True,
            change_summary=change_summary,
        )

        # Should add both children
        assert affected_count == 2
        assert child1.source_path in pages_to_rebuild
        assert child2.source_path in pages_to_rebuild
        assert "Cascade changes" in change_summary.extra_changes

    def test_no_cascade_no_extra_rebuilds(self, tracker, mock_site):
        """Index without cascade should not trigger extra rebuilds."""
        # Index without cascade
        index_page = Page(
            source_path=Path("/site/content/blog/_index.md"),
            _raw_content="Blog",
            metadata={"title": "Blog"},  # No cascade
        )

        child = Page(
            source_path=Path("/site/content/blog/post.md"),
            _raw_content="Post",
            metadata={"title": "Post"},
        )

        # Create a mock section
        section = Mock()
        section.name = "blog"
        section.path = Path("/site/content/blog")
        section.index_page = index_page
        section.pages = [index_page, child]
        section.regular_pages_recursive = [child]

        mock_site.pages = [index_page, child]
        mock_site.sections = [section]
        # Update page_by_source_path cache (mirrors PageCachesMixin behavior)
        mock_site.page_by_source_path = {p.source_path: p for p in mock_site.pages}

        pages_to_rebuild = {index_page.source_path}
        change_summary = ChangeSummary()

        affected_count = tracker.apply_cascade_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=True,
            change_summary=change_summary,
        )

        # Should not add child
        assert affected_count == 0
        assert child.source_path not in pages_to_rebuild


class TestCascadeHashComparison:
    """Test cascade metadata hash comparison for body-only change detection."""

    def test_cascade_unchanged_returns_true_when_hash_matches(
        self, tracker_with_cache, mock_site, mock_cache
    ):
        """When cascade metadata hash matches cached, return True (skip rebuild)."""
        path = Path("/site/content/_index.md")
        cascade_data = {"author": "lbliii"}
        
        # Create page with cascade
        page = Page(
            source_path=path,
            _raw_content="Hello world",
            metadata={"title": "Home", "cascade": cascade_data},
        )
        
        # Store matching hash in cache
        cascade_hash = hash_str(json.dumps(cascade_data, sort_keys=True, default=str))
        mock_cache.parsed_content[str(path)] = {
            "cascade_metadata_hash": cascade_hash,
        }
        
        # Should return True (cascade unchanged)
        assert tracker_with_cache._cascade_unchanged(page, path) is True

    def test_cascade_unchanged_returns_false_when_hash_differs(
        self, tracker_with_cache, mock_site, mock_cache
    ):
        """When cascade metadata hash differs from cached, return False (rebuild)."""
        path = Path("/site/content/_index.md")
        
        # Current cascade
        page = Page(
            source_path=path,
            _raw_content="Hello world",
            metadata={"title": "Home", "cascade": {"author": "newauthor"}},
        )
        
        # Cached with different cascade hash
        old_cascade = {"author": "oldauthor"}
        old_hash = hash_str(json.dumps(old_cascade, sort_keys=True, default=str))
        mock_cache.parsed_content[str(path)] = {
            "cascade_metadata_hash": old_hash,
        }
        
        # Should return False (cascade changed)
        assert tracker_with_cache._cascade_unchanged(page, path) is False

    def test_cascade_unchanged_returns_false_without_cache(self, tracker, mock_site):
        """Without cache, always return False (conservative rebuild)."""
        path = Path("/site/content/_index.md")
        page = Page(
            source_path=path,
            _raw_content="Hello world",
            metadata={"title": "Home", "cascade": {"author": "lbliii"}},
        )
        
        # No cache, should return False
        assert tracker._cascade_unchanged(page, path) is False

    def test_cascade_unchanged_returns_false_when_no_cached_entry(
        self, tracker_with_cache, mock_site, mock_cache
    ):
        """When no cached entry exists, return False (rebuild)."""
        path = Path("/site/content/_index.md")
        page = Page(
            source_path=path,
            _raw_content="Hello world",
            metadata={"title": "Home", "cascade": {"author": "lbliii"}},
        )
        
        # Empty cache
        mock_cache.parsed_content = {}
        
        # Should return False
        assert tracker_with_cache._cascade_unchanged(page, path) is False

    def test_cascade_body_only_change_skips_rebuild(
        self, tracker_with_cache, mock_site, mock_cache
    ):
        """Body-only changes to cascade pages don't trigger descendant rebuild."""
        # Create index page with cascade
        index_path = Path("/site/content/docs/_index.md")
        cascade_data = {"type": "doc"}
        
        index_page = Page(
            source_path=index_path,
            _raw_content="Updated body content",  # Body changed
            metadata={"title": "Docs", "cascade": cascade_data},  # Cascade same
        )

        # Create child page
        child = Page(
            source_path=Path("/site/content/docs/page1.md"),
            _raw_content="Page 1",
            metadata={"title": "Page 1"},
        )

        # Create mock section
        section = Mock()
        section.name = "docs"
        section.path = Path("/site/content/docs")
        section.index_page = index_page
        section.pages = [index_page, child]
        section.regular_pages_recursive = [child]

        mock_site.pages = [index_page, child]
        mock_site.sections = [section]
        mock_site.page_by_source_path = {p.source_path: p for p in mock_site.pages}

        # Store matching cascade hash in cache (simulating previous build)
        cascade_hash = hash_str(json.dumps(cascade_data, sort_keys=True, default=str))
        mock_cache.parsed_content[str(index_path)] = {
            "cascade_metadata_hash": cascade_hash,
        }

        # Only index page changed (body only)
        pages_to_rebuild = {index_path}
        change_summary = ChangeSummary()

        # Apply cascade rebuilds
        affected_count = tracker_with_cache.apply_cascade_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=True,
            change_summary=change_summary,
        )

        # Child should NOT be added (cascade unchanged, body-only change)
        assert affected_count == 0
        assert child.source_path not in pages_to_rebuild

    def test_cascade_metadata_change_triggers_rebuild(
        self, tracker_with_cache, mock_site, mock_cache
    ):
        """Changing cascade metadata values triggers descendant rebuild."""
        # Create index page with updated cascade
        index_path = Path("/site/content/docs/_index.md")
        new_cascade = {"type": "reference"}  # Changed from "doc"
        
        index_page = Page(
            source_path=index_path,
            _raw_content="Same body",
            metadata={"title": "Docs", "cascade": new_cascade},
        )

        # Create child page
        child = Page(
            source_path=Path("/site/content/docs/page1.md"),
            _raw_content="Page 1",
            metadata={"title": "Page 1"},
        )

        # Create mock section
        section = Mock()
        section.name = "docs"
        section.path = Path("/site/content/docs")
        section.index_page = index_page
        section.pages = [index_page, child]
        section.regular_pages_recursive = [child]

        mock_site.pages = [index_page, child]
        mock_site.sections = [section]
        mock_site.page_by_source_path = {p.source_path: p for p in mock_site.pages}

        # Store OLD cascade hash in cache
        old_cascade = {"type": "doc"}
        old_hash = hash_str(json.dumps(old_cascade, sort_keys=True, default=str))
        mock_cache.parsed_content[str(index_path)] = {
            "cascade_metadata_hash": old_hash,
        }

        pages_to_rebuild = {index_path}
        change_summary = ChangeSummary()

        # Apply cascade rebuilds
        affected_count = tracker_with_cache.apply_cascade_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=True,
            change_summary=change_summary,
        )

        # Child SHOULD be added (cascade changed)
        assert affected_count == 1
        assert child.source_path in pages_to_rebuild


class TestAdjacentNavigationRebuilds:
    """Test adjacent navigation (prev/next) rebuild logic."""

    def test_prev_page_added_to_rebuild(self, tracker, mock_site):
        """When page changes, its prev page should be rebuilt."""
        # Use Mock pages since prev/next are properties on real Page
        page1 = Mock()
        page1.source_path = Path("/site/content/page1.md")
        page1.metadata = {"title": "Page 1"}
        page1.prev = None
        page1.next = None

        page2 = Mock()
        page2.source_path = Path("/site/content/page2.md")
        page2.metadata = {"title": "Page 2"}
        page2.prev = page1
        page2.next = None

        # Set up navigation links
        page1.next = page2

        mock_site.pages = [page1, page2]
        # Update page_by_source_path cache (mirrors PageCachesMixin behavior)
        mock_site.page_by_source_path = {p.source_path: p for p in mock_site.pages}

        # page2 changed
        pages_to_rebuild = {page2.source_path}
        change_summary = ChangeSummary()

        affected_count = tracker.apply_adjacent_navigation_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=True,
            change_summary=change_summary,
        )

        # page1 should be added (has next link to page2)
        assert affected_count == 1
        assert page1.source_path in pages_to_rebuild

    def test_next_page_added_to_rebuild(self, tracker, mock_site):
        """When page changes, its next page should be rebuilt."""
        # Use Mock pages since prev/next are properties on real Page
        page1 = Mock()
        page1.source_path = Path("/site/content/page1.md")
        page1.metadata = {"title": "Page 1"}
        page1.prev = None
        page1.next = None

        page2 = Mock()
        page2.source_path = Path("/site/content/page2.md")
        page2.metadata = {"title": "Page 2"}
        page2.prev = None
        page2.next = None

        # Set up navigation links
        page1.next = page2
        page2.prev = page1

        mock_site.pages = [page1, page2]
        # Update page_by_source_path cache (mirrors PageCachesMixin behavior)
        mock_site.page_by_source_path = {p.source_path: p for p in mock_site.pages}

        # page1 changed
        pages_to_rebuild = {page1.source_path}
        change_summary = ChangeSummary()

        affected_count = tracker.apply_adjacent_navigation_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=True,
            change_summary=change_summary,
        )

        # page2 should be added (has prev link to page1)
        assert affected_count == 1
        assert page2.source_path in pages_to_rebuild

    def test_generated_pages_not_added_to_rebuild(self, tracker, mock_site):
        """Generated pages should not be added via navigation."""
        # Use Mock pages since next is a property on real Page
        page1 = Mock()
        page1.source_path = Path("/site/content/page1.md")
        page1.metadata = {"title": "Page 1"}
        page1.prev = None

        generated = Mock()
        generated.source_path = Path("/site/content/_generated/tag.md")
        generated.metadata = {"title": "Tag", "_generated": True}
        generated.prev = None
        generated.next = None

        page1.next = generated
        mock_site.pages = [page1, generated]
        # Update page_by_source_path cache (mirrors PageCachesMixin behavior)
        mock_site.page_by_source_path = {p.source_path: p for p in mock_site.pages}

        pages_to_rebuild = {page1.source_path}
        change_summary = ChangeSummary()

        affected_count = tracker.apply_adjacent_navigation_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=True,
            change_summary=change_summary,
        )

        # Generated page should not be added
        assert affected_count == 0
        assert generated.source_path not in pages_to_rebuild


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
