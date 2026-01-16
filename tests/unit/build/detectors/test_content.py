"""
Unit tests for bengal.build.detectors.content.

Tests ContentChangeDetector for content and asset change detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReasonCode
from bengal.build.detectors.content import ContentChangeDetector


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create mock BuildCache."""
    cache = MagicMock()
    cache.should_bypass.return_value = False
    cache.is_changed.return_value = False
    return cache


@pytest.fixture
def mock_site() -> MagicMock:
    """Create mock Site with default empty pages/assets."""
    site = MagicMock()
    site.root_path = Path("/site")
    site.pages = []
    site.assets = []
    return site


@pytest.fixture
def mock_page(mock_site: MagicMock) -> MagicMock:
    """Create a mock page."""
    page = MagicMock()
    page.source_path = Path("/site/content/about.md")
    page.metadata = {}
    page.tags = None
    return page


@pytest.fixture
def detector() -> ContentChangeDetector:
    """Create ContentChangeDetector instance."""
    return ContentChangeDetector()


# =============================================================================
# Basic Detection Tests
# =============================================================================


class TestContentChangeDetectorBasics:
    """Basic tests for ContentChangeDetector."""

    def test_empty_site_returns_empty_result(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Empty site returns empty result."""
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        assert result.pages_to_rebuild == frozenset()
        assert result.assets_to_process == frozenset()

    def test_skips_generated_pages(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Generated pages are skipped."""
        page = MagicMock()
        page.source_path = Path("/site/content/generated.md")
        page.metadata = {"_generated": True}
        page.tags = None
        mock_site.pages = [page]
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert CacheKey("content/generated.md") not in result.pages_to_rebuild


# =============================================================================
# Forced Change Detection Tests
# =============================================================================


class TestForcedChanges:
    """Tests for forced change detection."""

    def test_forced_changed_triggers_rebuild(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Page in forced_changed set is marked for rebuild."""
        page = MagicMock()
        page.source_path = Path("/site/content/about.md")
        page.metadata = {}
        page.tags = None
        mock_site.pages = [page]

        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            forced_changed=frozenset([CacheKey("content/about.md")]),
        )
        result = detector.detect(ctx)

        assert CacheKey("content/about.md") in result.pages_to_rebuild
        reason = result.rebuild_reasons.get(CacheKey("content/about.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.FORCED


# =============================================================================
# Nav Change Detection Tests
# =============================================================================


class TestNavChanges:
    """Tests for navigation change detection."""

    def test_nav_changed_triggers_rebuild(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Page in nav_changed set is marked for rebuild."""
        page = MagicMock()
        page.source_path = Path("/site/content/about.md")
        page.metadata = {}
        page.tags = None
        mock_site.pages = [page]

        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            nav_changed=frozenset([CacheKey("content/about.md")]),
        )
        result = detector.detect(ctx)

        assert CacheKey("content/about.md") in result.pages_to_rebuild
        reason = result.rebuild_reasons.get(CacheKey("content/about.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.ADJACENT_NAV_CHANGED


# =============================================================================
# Cache Bypass Detection Tests
# =============================================================================


class TestCacheBypass:
    """Tests for cache bypass detection."""

    def test_should_bypass_triggers_rebuild(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Page with cache.should_bypass=True is marked for rebuild."""
        page = MagicMock()
        page.source_path = Path("/site/content/about.md")
        page.metadata = {}
        page.tags = None
        mock_site.pages = [page]
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert CacheKey("content/about.md") in result.pages_to_rebuild
        reason = result.rebuild_reasons.get(CacheKey("content/about.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.CONTENT_CHANGED


# =============================================================================
# Tag Tracking Tests
# =============================================================================


class TestTagTracking:
    """Tests for tag tracking."""

    def test_changed_page_tags_are_tracked(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Changed page's tags are added to affected_tags."""
        page = MagicMock()
        page.source_path = Path("/site/content/post.md")
        page.metadata = {}
        page.tags = ["Python", "Web Dev"]
        mock_site.pages = [page]
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert "python" in result.affected_tags
        assert "web-dev" in result.affected_tags

    def test_none_tags_are_skipped(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """None values in tags list are skipped."""
        page = MagicMock()
        page.source_path = Path("/site/content/post.md")
        page.metadata = {}
        page.tags = ["Python", None, "Rust"]
        mock_site.pages = [page]
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert "python" in result.affected_tags
        assert "rust" in result.affected_tags
        # No assertion about None since it would be skipped

    def test_tags_are_normalized(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Tags are lowercased and spaces replaced with hyphens."""
        page = MagicMock()
        page.source_path = Path("/site/content/post.md")
        page.metadata = {}
        page.tags = ["Machine Learning", "AI"]
        mock_site.pages = [page]
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert "machine-learning" in result.affected_tags
        assert "ai" in result.affected_tags


# =============================================================================
# Asset Detection Tests
# =============================================================================


class TestAssetDetection:
    """Tests for asset change detection."""

    def test_forced_asset_is_processed(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Asset in forced_changed is marked for processing."""
        asset = MagicMock()
        asset.source_path = Path("/site/static/style.css")
        mock_site.assets = [asset]

        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            forced_changed=frozenset([CacheKey("static/style.css")]),
        )
        result = detector.detect(ctx)

        assert CacheKey("static/style.css") in result.assets_to_process

    def test_bypassed_asset_is_processed(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Asset with cache.should_bypass=True is marked for processing."""
        asset = MagicMock()
        asset.source_path = Path("/site/static/style.css")
        mock_site.assets = [asset]
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert CacheKey("static/style.css") in result.assets_to_process


# =============================================================================
# Content Files Changed Tests
# =============================================================================


class TestContentFilesChanged:
    """Tests for content_files_changed tracking."""

    def test_changed_pages_in_content_files_changed(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Changed pages are added to content_files_changed."""
        page = MagicMock()
        page.source_path = Path("/site/content/about.md")
        page.metadata = {}
        page.tags = None
        mock_site.pages = [page]
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert CacheKey("content/about.md") in result.content_files_changed


# =============================================================================
# Multiple Pages Tests
# =============================================================================


class TestMultiplePages:
    """Tests for multiple page detection."""

    def test_multiple_changed_pages(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Multiple changed pages are all detected."""
        pages = []
        for name in ["about.md", "contact.md", "services.md"]:
            page = MagicMock()
            page.source_path = Path(f"/site/content/{name}")
            page.metadata = {}
            page.tags = None
            pages.append(page)
        
        mock_site.pages = pages
        mock_cache.should_bypass.return_value = True

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert len(result.pages_to_rebuild) == 3
        for name in ["about.md", "contact.md", "services.md"]:
            assert CacheKey(f"content/{name}") in result.pages_to_rebuild

    def test_mixed_changed_and_unchanged(
        self, detector: ContentChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Only changed pages are detected."""
        page1 = MagicMock()
        page1.source_path = Path("/site/content/changed.md")
        page1.metadata = {}
        page1.tags = None

        page2 = MagicMock()
        page2.source_path = Path("/site/content/unchanged.md")
        page2.metadata = {}
        page2.tags = None

        mock_site.pages = [page1, page2]

        def should_bypass_side_effect(path: Path) -> bool:
            # Only changed.md should return True
            return path.name == "changed.md"

        mock_cache.should_bypass.side_effect = should_bypass_side_effect

        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)

        assert CacheKey("content/changed.md") in result.pages_to_rebuild
        assert CacheKey("content/unchanged.md") not in result.pages_to_rebuild
