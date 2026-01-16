"""
Unit tests for bengal.build.detectors.autodoc.

Tests AutodocChangeDetector for autodoc source file change detection.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.contracts.results import RebuildReasonCode
from bengal.build.detectors.autodoc import AutodocChangeDetector


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create mock BuildCache."""
    cache = MagicMock()
    cache.autodoc_dependencies = {}
    cache.get_autodoc_source_files.return_value = []
    cache.get_affected_autodoc_pages.return_value = []
    cache.is_changed.return_value = False
    return cache


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create mock Site with temp directory."""
    site = MagicMock()
    site.root_path = tmp_path
    site.page_by_source_path = {}
    return site


@pytest.fixture
def detector() -> AutodocChangeDetector:
    """Create AutodocChangeDetector instance."""
    return AutodocChangeDetector()


# =============================================================================
# Basic Detection Tests
# =============================================================================


class TestAutodocChangeDetectorBasics:
    """Basic tests for AutodocChangeDetector."""

    def test_no_autodoc_dependencies_returns_empty(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Missing autodoc_dependencies returns empty result."""
        del mock_cache.autodoc_dependencies
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_no_source_files_returns_empty(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """No source files returns empty result."""
        mock_cache.get_autodoc_source_files.return_value = []
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()


# =============================================================================
# Source File Change Detection Tests
# =============================================================================


class TestSourceFileChangeDetection:
    """Tests for autodoc source file change detection."""

    def test_changed_source_triggers_rebuild(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Changed source file triggers rebuild of affected pages."""
        # Create a source file in project (not site-packages)
        source_file = mock_site.root_path / "src" / "mymodule.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()
        
        mock_cache.get_autodoc_source_files.return_value = [str(source_file)]
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_autodoc_pages.return_value = ["content/api/mymodule.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert CacheKey("content/api/mymodule.md") in result.pages_to_rebuild

    def test_unchanged_source_no_rebuild(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Unchanged source file doesn't trigger rebuild."""
        source_file = mock_site.root_path / "src" / "mymodule.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()
        
        mock_cache.get_autodoc_source_files.return_value = [str(source_file)]
        mock_cache.is_changed.return_value = False
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()


# =============================================================================
# External Source Exclusion Tests
# =============================================================================


class TestExternalSourceExclusion:
    """Tests for external source file exclusion."""

    def test_site_packages_excluded(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Files in site-packages are excluded."""
        mock_cache.get_autodoc_source_files.return_value = [
            "/usr/lib/python3.14/site-packages/requests/api.py"
        ]
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        # Should be excluded
        assert result.pages_to_rebuild == frozenset()

    def test_dist_packages_excluded(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Files in dist-packages are excluded."""
        mock_cache.get_autodoc_source_files.return_value = [
            "/usr/lib/python3.14/dist-packages/requests/api.py"
        ]
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_venv_excluded(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Files in .venv are excluded."""
        mock_cache.get_autodoc_source_files.return_value = [
            "/project/.venv/lib/python3.14/site-packages/module.py"
        ]
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()

    def test_tox_excluded(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Files in .tox are excluded."""
        mock_cache.get_autodoc_source_files.return_value = [
            "/project/.tox/py314/lib/python3.14/site-packages/module.py"
        ]
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()


# =============================================================================
# Rebuild Reason Tests
# =============================================================================


class TestRebuildReasons:
    """Tests for rebuild reason assignment."""

    def test_rebuild_reason_is_content_changed(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason code is CONTENT_CHANGED."""
        source_file = mock_site.root_path / "src" / "mymodule.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()
        
        mock_cache.get_autodoc_source_files.return_value = [str(source_file)]
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_autodoc_pages.return_value = ["content/api/mymodule.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/api/mymodule.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.CONTENT_CHANGED

    def test_rebuild_reason_trigger_is_autodoc(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason trigger indicates autodoc source."""
        source_file = mock_site.root_path / "src" / "mymodule.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()
        
        mock_cache.get_autodoc_source_files.return_value = [str(source_file)]
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_autodoc_pages.return_value = ["content/api/mymodule.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/api/mymodule.md"))
        assert reason is not None
        assert "autodoc" in reason.trigger.lower()


# =============================================================================
# Stale Source Detection Tests
# =============================================================================


class TestStaleSourceDetection:
    """Tests for stale autodoc source detection."""

    def test_stale_sources_trigger_rebuild(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Stale autodoc sources trigger rebuild."""
        mock_cache.get_autodoc_source_files.return_value = []
        mock_cache.get_stale_autodoc_sources.return_value = ["stale_source"]
        mock_cache.get_affected_autodoc_pages.return_value = ["content/api/module.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert CacheKey("content/api/module.md") in result.pages_to_rebuild


# =============================================================================
# Doc Content Hash Filtering Tests
# =============================================================================


class TestDocContentHashFiltering:
    """Tests for doc content hash filtering."""

    def test_unchanged_doc_content_skipped(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Pages with unchanged doc content are skipped."""
        source_file = mock_site.root_path / "src" / "mymodule.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()
        
        page = MagicMock()
        page.source_path = Path("content/api/mymodule.md")
        page.metadata = {"doc_content_hash": "abc123"}
        
        mock_site.page_by_source_path = {Path("content/api/mymodule.md"): page}
        mock_cache.get_autodoc_source_files.return_value = [str(source_file)]
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_autodoc_pages.return_value = ["content/api/mymodule.md"]
        mock_cache.autodoc_dependencies = {str(source_file): ["content/api/mymodule.md"]}
        mock_cache.is_doc_content_changed.return_value = False  # Content unchanged
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        # Page should be skipped because doc content is unchanged
        assert CacheKey("content/api/mymodule.md") not in result.pages_to_rebuild

    def test_changed_doc_content_included(
        self, detector: AutodocChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Pages with changed doc content are included."""
        source_file = mock_site.root_path / "src" / "mymodule.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()
        
        page = MagicMock()
        page.source_path = Path("content/api/mymodule.md")
        page.metadata = {"doc_content_hash": "abc123"}
        
        mock_site.page_by_source_path = {Path("content/api/mymodule.md"): page}
        mock_cache.get_autodoc_source_files.return_value = [str(source_file)]
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_autodoc_pages.return_value = ["content/api/mymodule.md"]
        mock_cache.autodoc_dependencies = {str(source_file): ["content/api/mymodule.md"]}
        mock_cache.is_doc_content_changed.return_value = True  # Content changed
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert CacheKey("content/api/mymodule.md") in result.pages_to_rebuild
