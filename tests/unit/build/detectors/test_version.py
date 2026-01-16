"""
Unit tests for bengal.build.detectors.version.

Tests VersionChangeDetector for cross-version dependency detection.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReasonCode
from bengal.build.detectors.version import VersionChangeDetector


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create mock BuildCache."""
    return MagicMock()


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create mock Site with temp directory."""
    site = MagicMock()
    site.root_path = tmp_path
    site.versioning_enabled = False
    site.page_by_source_path = {}
    site.version_config = None
    return site


@pytest.fixture
def mock_tracker() -> MagicMock:
    """Create mock DependencyTracker."""
    tracker = MagicMock()
    tracker.get_cross_version_dependents.return_value = set()
    return tracker


@pytest.fixture
def detector() -> VersionChangeDetector:
    """Create VersionChangeDetector instance."""
    return VersionChangeDetector()


# =============================================================================
# Basic Detection Tests
# =============================================================================


class TestVersionChangeDetectorBasics:
    """Basic tests for VersionChangeDetector."""

    def test_versioning_disabled_returns_empty(
        self, detector: VersionChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Versioning disabled returns empty result."""
        mock_site.versioning_enabled = False
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_no_tracker_returns_empty(
        self, detector: VersionChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Missing tracker returns empty result."""
        mock_site.versioning_enabled = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site, tracker=None)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_tracker_without_method_returns_empty(
        self, detector: VersionChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Tracker without get_cross_version_dependents returns empty result."""
        mock_site.versioning_enabled = True
        tracker = MagicMock(spec=[])  # No methods
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site, tracker=tracker)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()


# =============================================================================
# Cross-Version Dependency Tests
# =============================================================================


class TestCrossVersionDependencies:
    """Tests for cross-version dependency detection."""

    def test_cross_version_dependent_rebuilt(
        self,
        detector: VersionChangeDetector,
        mock_cache: MagicMock,
        mock_site: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """Cross-version dependent page is rebuilt."""
        mock_site.versioning_enabled = True
        
        # Changed page in v2
        changed_page = MagicMock()
        changed_page.source_path = mock_site.root_path / "content" / "docs" / "v2" / "guide.md"
        changed_page.version = "v2"
        changed_page.metadata = {}
        
        # Dependent page in v3
        dependent_path = mock_site.root_path / "content" / "docs" / "v3" / "migration.md"
        
        mock_site.page_by_source_path = {
            changed_page.source_path: changed_page,
        }
        
        mock_tracker.get_cross_version_dependents.return_value = {dependent_path}
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/v2/guide.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        assert CacheKey("content/docs/v3/migration.md") in result.pages_to_rebuild

    def test_page_without_version_skipped(
        self,
        detector: VersionChangeDetector,
        mock_cache: MagicMock,
        mock_site: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """Page without version is skipped."""
        mock_site.versioning_enabled = True
        
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "about.md"
        page.version = None
        page.metadata = {}
        
        mock_site.page_by_source_path = {page.source_path: page}
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/about.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        # Tracker should not be called for non-versioned page
        mock_tracker.get_cross_version_dependents.assert_not_called()

    def test_no_dependents_returns_empty(
        self,
        detector: VersionChangeDetector,
        mock_cache: MagicMock,
        mock_site: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """No dependents returns empty result."""
        mock_site.versioning_enabled = True
        
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "docs" / "v2" / "guide.md"
        page.version = "v2"
        page.metadata = {}
        
        mock_site.page_by_source_path = {page.source_path: page}
        mock_tracker.get_cross_version_dependents.return_value = set()
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/v2/guide.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()


# =============================================================================
# Rebuild Reason Tests
# =============================================================================


class TestRebuildReasons:
    """Tests for rebuild reason assignment."""

    def test_rebuild_reason_is_cross_version_dependency(
        self,
        detector: VersionChangeDetector,
        mock_cache: MagicMock,
        mock_site: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """Rebuild reason code is CROSS_VERSION_DEPENDENCY."""
        mock_site.versioning_enabled = True
        
        changed_page = MagicMock()
        changed_page.source_path = mock_site.root_path / "content" / "docs" / "v2" / "guide.md"
        changed_page.version = "v2"
        changed_page.metadata = {}
        
        dependent_path = mock_site.root_path / "content" / "docs" / "v3" / "migration.md"
        
        mock_site.page_by_source_path = {changed_page.source_path: changed_page}
        mock_tracker.get_cross_version_dependents.return_value = {dependent_path}
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/v2/guide.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            previous=previous,
        )
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/docs/v3/migration.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.CROSS_VERSION_DEPENDENCY


# =============================================================================
# Version Config Tests
# =============================================================================


class TestVersionConfig:
    """Tests for version configuration handling."""

    def test_version_from_page_attribute(
        self,
        detector: VersionChangeDetector,
        mock_cache: MagicMock,
        mock_site: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """Version is read from page.version attribute."""
        mock_site.versioning_enabled = True
        
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "docs" / "v2" / "guide.md"
        page.version = "v2"
        page.metadata = {}
        
        mock_site.page_by_source_path = {page.source_path: page}
        mock_tracker.get_cross_version_dependents.return_value = set()
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/v2/guide.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            previous=previous,
        )
        detector.detect(ctx)
        
        # Verify tracker was called with correct version
        mock_tracker.get_cross_version_dependents.assert_called_once()
        call_args = mock_tracker.get_cross_version_dependents.call_args
        assert call_args.kwargs["changed_version"] == "v2"

    def test_version_from_metadata_fallback(
        self,
        detector: VersionChangeDetector,
        mock_cache: MagicMock,
        mock_site: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """Version falls back to page.metadata['version']."""
        mock_site.versioning_enabled = True
        
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "docs" / "v2" / "guide.md"
        page.version = None  # No version attribute
        page.metadata = {"version": "v2"}
        
        mock_site.page_by_source_path = {page.source_path: page}
        mock_tracker.get_cross_version_dependents.return_value = set()
        
        previous = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("content/docs/v2/guide.md")])
        )
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            previous=previous,
        )
        detector.detect(ctx)
        
        # Verify tracker was called with correct version
        mock_tracker.get_cross_version_dependents.assert_called_once()
        call_args = mock_tracker.get_cross_version_dependents.call_args
        assert call_args.kwargs["changed_version"] == "v2"
