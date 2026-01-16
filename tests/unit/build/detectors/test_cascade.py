"""
Unit tests for bengal.build.detectors.cascade.

Tests SectionCascadeDetector and NavigationDependencyDetector.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReasonCode
from bengal.build.detectors.cascade import (
    NavigationDependencyDetector,
    SectionCascadeDetector,
)
from bengal.utils.primitives.hashing import hash_str


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create mock BuildCache."""
    cache = MagicMock()
    cache.parsed_content = {}
    return cache


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create mock Site with temp directory."""
    site = MagicMock()
    site.root_path = tmp_path
    site.pages = []
    site.sections = []
    site.page_by_source_path = {}
    return site


# =============================================================================
# SectionCascadeDetector Tests
# =============================================================================


class TestSectionCascadeDetector:
    """Tests for SectionCascadeDetector."""

    @pytest.fixture
    def detector(self) -> SectionCascadeDetector:
        """Create SectionCascadeDetector instance."""
        return SectionCascadeDetector()

    def test_no_previous_changes_returns_empty(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """No previous changes returns empty result."""
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=ChangeDetectionResult.empty(),
        )
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_non_index_pages_skipped(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Non-index pages don't trigger cascade."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "about.md"
        page.metadata = {"cascade": {"draft": False}}
        
        mock_site.page_by_source_path = {page.source_path: page}
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/about.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Only index pages trigger cascades
        assert result.pages_to_rebuild == frozenset()

    def test_index_page_without_cascade_skipped(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Index page without cascade metadata is skipped."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "_index.md"
        page.metadata = {}  # No cascade
        
        mock_site.page_by_source_path = {page.source_path: page}
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/_index.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_section_index_triggers_cascade(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Section index with cascade triggers rebuild of section pages."""
        index_page = MagicMock()
        index_page.source_path = mock_site.root_path / "content" / "docs" / "_index.md"
        index_page.metadata = {"cascade": {"draft": False}}
        
        child_page = MagicMock()
        child_page.source_path = mock_site.root_path / "content" / "docs" / "guide.md"
        child_page.metadata = {}
        
        section = MagicMock()
        section.index_page = index_page
        section.regular_pages_recursive = [child_page]
        
        mock_site.sections = [section]
        mock_site.pages = [index_page, child_page]
        mock_site.page_by_source_path = {
            index_page.source_path: index_page,
            child_page.source_path: child_page,
        }
        
        # No cached cascade hash (first build)
        mock_cache.parsed_content = {}
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/_index.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Child page should be in pages_to_rebuild
        assert CacheKey("content/docs/guide.md") in result.pages_to_rebuild

    def test_rebuild_reason_is_cascade(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason code is CASCADE."""
        index_page = MagicMock()
        index_page.source_path = mock_site.root_path / "content" / "docs" / "_index.md"
        index_page.metadata = {"cascade": {"draft": False}}
        
        child_page = MagicMock()
        child_page.source_path = mock_site.root_path / "content" / "docs" / "guide.md"
        child_page.metadata = {}
        
        section = MagicMock()
        section.index_page = index_page
        section.regular_pages_recursive = [child_page]
        
        mock_site.sections = [section]
        mock_site.pages = [index_page, child_page]
        mock_site.page_by_source_path = {
            index_page.source_path: index_page,
            child_page.source_path: child_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/_index.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/docs/guide.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.CASCADE


# =============================================================================
# Cascade Hash Comparison Tests
# =============================================================================


class TestCascadeHashComparison:
    """Test cascade metadata hash comparison for body-only change detection."""

    @pytest.fixture
    def detector(self) -> SectionCascadeDetector:
        """Create SectionCascadeDetector instance."""
        return SectionCascadeDetector()

    def test_cascade_unchanged_when_hash_matches(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """When cascade metadata hash matches cached, skip cascade rebuild."""
        cascade_data = {"author": "lbliii"}
        
        index_page = MagicMock()
        index_page.source_path = mock_site.root_path / "content" / "_index.md"
        index_page.metadata = {"title": "Home", "cascade": cascade_data}
        
        child_page = MagicMock()
        child_page.source_path = mock_site.root_path / "content" / "page1.md"
        child_page.metadata = {}
        
        # Store matching hash in cache
        cascade_hash = hash_str(json.dumps(cascade_data, sort_keys=True, default=str))
        mock_cache.parsed_content = {
            str(index_page.source_path): {"cascade_metadata_hash": cascade_hash}
        }
        
        mock_site.pages = [index_page, child_page]
        mock_site.page_by_source_path = {
            index_page.source_path: index_page,
            child_page.source_path: child_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/_index.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Child should NOT be rebuilt (cascade hash unchanged)
        assert CacheKey("content/page1.md") not in result.pages_to_rebuild

    def test_cascade_changed_when_hash_differs(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """When cascade metadata hash differs, trigger cascade rebuild."""
        new_cascade = {"author": "newauthor"}
        old_cascade = {"author": "oldauthor"}
        
        index_page = MagicMock()
        index_page.source_path = mock_site.root_path / "content" / "docs" / "_index.md"
        index_page.metadata = {"title": "Docs", "cascade": new_cascade}
        
        child_page = MagicMock()
        child_page.source_path = mock_site.root_path / "content" / "docs" / "guide.md"
        child_page.metadata = {}
        
        section = MagicMock()
        section.index_page = index_page
        section.regular_pages_recursive = [child_page]
        
        # Store OLD cascade hash in cache
        old_hash = hash_str(json.dumps(old_cascade, sort_keys=True, default=str))
        mock_cache.parsed_content = {
            str(index_page.source_path): {"cascade_metadata_hash": old_hash}
        }
        
        mock_site.sections = [section]
        mock_site.pages = [index_page, child_page]
        mock_site.page_by_source_path = {
            index_page.source_path: index_page,
            child_page.source_path: child_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/_index.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Child SHOULD be rebuilt (cascade changed)
        assert CacheKey("content/docs/guide.md") in result.pages_to_rebuild

    def test_cascade_triggers_rebuild_when_no_cached_entry(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """When no cached cascade hash exists, trigger rebuild (first build)."""
        cascade_data = {"type": "doc"}
        
        index_page = MagicMock()
        index_page.source_path = mock_site.root_path / "content" / "docs" / "_index.md"
        index_page.metadata = {"title": "Docs", "cascade": cascade_data}
        
        child_page = MagicMock()
        child_page.source_path = mock_site.root_path / "content" / "docs" / "guide.md"
        child_page.metadata = {}
        
        section = MagicMock()
        section.index_page = index_page
        section.regular_pages_recursive = [child_page]
        
        # Empty cache (first build)
        mock_cache.parsed_content = {}
        
        mock_site.sections = [section]
        mock_site.pages = [index_page, child_page]
        mock_site.page_by_source_path = {
            index_page.source_path: index_page,
            child_page.source_path: child_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/_index.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Child should be rebuilt (no cache = conservative rebuild)
        assert CacheKey("content/docs/guide.md") in result.pages_to_rebuild

    def test_body_only_change_skips_cascade_rebuild(
        self, detector: SectionCascadeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Body-only changes to index pages don't trigger descendant rebuild."""
        cascade_data = {"type": "doc"}
        
        index_page = MagicMock()
        index_page.source_path = mock_site.root_path / "content" / "docs" / "_index.md"
        # Same cascade, but body changed
        index_page.metadata = {"title": "Docs Updated", "cascade": cascade_data}
        
        child_page = MagicMock()
        child_page.source_path = mock_site.root_path / "content" / "docs" / "page1.md"
        child_page.metadata = {}
        
        section = MagicMock()
        section.index_page = index_page
        section.regular_pages_recursive = [child_page]
        
        # Store matching cascade hash (simulating previous build)
        cascade_hash = hash_str(json.dumps(cascade_data, sort_keys=True, default=str))
        mock_cache.parsed_content = {
            str(index_page.source_path): {"cascade_metadata_hash": cascade_hash}
        }
        
        mock_site.sections = [section]
        mock_site.pages = [index_page, child_page]
        mock_site.page_by_source_path = {
            index_page.source_path: index_page,
            child_page.source_path: child_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/_index.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Child should NOT be rebuilt (cascade unchanged, body-only change)
        assert CacheKey("content/docs/page1.md") not in result.pages_to_rebuild


# =============================================================================
# NavigationDependencyDetector Tests
# =============================================================================


class TestNavigationDependencyDetector:
    """Tests for NavigationDependencyDetector."""

    @pytest.fixture
    def detector(self) -> NavigationDependencyDetector:
        """Create NavigationDependencyDetector instance."""
        return NavigationDependencyDetector()

    def test_no_previous_changes_returns_empty(
        self, detector: NavigationDependencyDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """No previous changes returns empty result."""
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=ChangeDetectionResult.empty(),
        )
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_prev_page_rebuilt(
        self, detector: NavigationDependencyDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Previous page in navigation is rebuilt."""
        current_page = MagicMock()
        current_page.source_path = mock_site.root_path / "content" / "chapter2.md"
        current_page.metadata = {}
        
        prev_page = MagicMock()
        prev_page.source_path = mock_site.root_path / "content" / "chapter1.md"
        prev_page.metadata = {}
        
        current_page.prev = prev_page
        current_page.next = None
        
        mock_site.page_by_source_path = {
            current_page.source_path: current_page,
            prev_page.source_path: prev_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/chapter2.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        assert CacheKey("content/chapter1.md") in result.pages_to_rebuild

    def test_next_page_rebuilt(
        self, detector: NavigationDependencyDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Next page in navigation is rebuilt."""
        current_page = MagicMock()
        current_page.source_path = mock_site.root_path / "content" / "chapter1.md"
        current_page.metadata = {}
        
        next_page = MagicMock()
        next_page.source_path = mock_site.root_path / "content" / "chapter2.md"
        next_page.metadata = {}
        
        current_page.prev = None
        current_page.next = next_page
        
        mock_site.page_by_source_path = {
            current_page.source_path: current_page,
            next_page.source_path: next_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/chapter1.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        assert CacheKey("content/chapter2.md") in result.pages_to_rebuild

    def test_generated_neighbors_skipped(
        self, detector: NavigationDependencyDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Generated neighbor pages are skipped."""
        current_page = MagicMock()
        current_page.source_path = mock_site.root_path / "content" / "chapter1.md"
        current_page.metadata = {}
        
        next_page = MagicMock()
        next_page.source_path = mock_site.root_path / "content" / "generated.md"
        next_page.metadata = {"_generated": True}
        
        current_page.prev = None
        current_page.next = next_page
        
        mock_site.page_by_source_path = {
            current_page.source_path: current_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/chapter1.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Generated page should not be rebuilt
        assert CacheKey("content/generated.md") not in result.pages_to_rebuild

    def test_rebuild_reason_is_adjacent_nav_changed(
        self, detector: NavigationDependencyDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason code is ADJACENT_NAV_CHANGED."""
        current_page = MagicMock()
        current_page.source_path = mock_site.root_path / "content" / "chapter2.md"
        current_page.metadata = {}
        
        prev_page = MagicMock()
        prev_page.source_path = mock_site.root_path / "content" / "chapter1.md"
        prev_page.metadata = {}
        
        current_page.prev = prev_page
        current_page.next = None
        
        mock_site.page_by_source_path = {
            current_page.source_path: current_page,
            prev_page.source_path: prev_page,
        }
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/chapter2.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/chapter1.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.ADJACENT_NAV_CHANGED

    def test_neighbor_already_in_rebuild_skipped(
        self, detector: NavigationDependencyDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Neighbor already marked for rebuild is not added again."""
        current_page = MagicMock()
        current_page.source_path = mock_site.root_path / "content" / "chapter2.md"
        current_page.metadata = {}
        
        prev_page = MagicMock()
        prev_page.source_path = mock_site.root_path / "content" / "chapter1.md"
        prev_page.metadata = {}
        
        current_page.prev = prev_page
        current_page.next = None
        
        mock_site.page_by_source_path = {
            current_page.source_path: current_page,
            prev_page.source_path: prev_page,
        }
        
        # Both pages already marked for rebuild
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([
                CacheKey("content/chapter2.md"),
                CacheKey("content/chapter1.md"),
            ])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # No new pages should be added
        assert result.pages_to_rebuild == frozenset()
