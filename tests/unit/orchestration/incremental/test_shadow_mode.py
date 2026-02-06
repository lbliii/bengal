"""
Tests for IncrementalOrchestrator change detection.

Tests that the orchestrator correctly delegates to EffectBasedDetector
for change detection.

RFC: Aggressive Cleanup - EffectBasedDetector replaces old pipeline.
"""

from unittest.mock import Mock, patch

import pytest

from bengal.cache.paths import BengalPaths
from bengal.core.page import Page
from bengal.errors import BengalError
from bengal.orchestration.incremental import IncrementalOrchestrator


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site with pages."""
    site = Mock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.paths = BengalPaths(tmp_path)
    site.config = Mock()
    site.config.path = tmp_path / "bengal.toml"
    site.theme = None
    site.sections = []

    site.pages = [
        Page(
            source_path=tmp_path / "content/page1.md",
            _raw_content="Content 1",
            _raw_metadata={"title": "Page 1"},
        ),
        Page(
            source_path=tmp_path / "content/page2.md",
            _raw_content="Content 2",
            _raw_metadata={"title": "Page 2"},
        ),
    ]
    site.assets = []
    site.regular_pages = site.pages
    site.generated_pages = []
    # page_by_source_path is a dict property built from site.pages
    # The real implementation is a cached property on Site
    site.page_by_source_path = {p.source_path: p for p in site.pages}

    return site


@pytest.fixture
def orchestrator(mock_site):
    """Create an IncrementalOrchestrator instance."""
    orch = IncrementalOrchestrator(mock_site)
    orch.initialize(enabled=False)
    return orch


class TestOrchestratorInitialization:
    """Test IncrementalOrchestrator initialization."""

    def test_initialization(self, mock_site):
        """Orchestrator should initialize with site reference."""
        orch = IncrementalOrchestrator(mock_site)

        assert orch.site is mock_site
        assert orch.cache is None
        assert orch.tracker is None
        assert orch._detector is None

    def test_initialize_creates_cache_and_tracker(self, mock_site):
        """initialize() should create cache and tracker."""
        orch = IncrementalOrchestrator(mock_site)
        cache, tracker = orch.initialize(enabled=False)

        assert cache is not None
        assert tracker is not None
        assert orch.cache is cache
        assert orch.tracker is tracker


class TestFindWorkEarly:
    """Test early phase change detection."""

    def test_find_work_early_detects_changed_pages(self, orchestrator, mock_site):
        """find_work_early should detect changed pages."""
        orchestrator.cache.should_bypass = Mock(return_value=True)
        orchestrator.cache.is_changed = Mock(return_value=False)

        with patch.object(
            orchestrator._cache_manager, "_get_theme_templates_dir", return_value=None
        ):
            pages, assets, summary = orchestrator.find_work_early(verbose=True)

        assert len(pages) == 2

    def test_find_work_early_with_forced_changes(self, orchestrator, mock_site):
        """find_work_early should handle forced changes from watcher."""
        forced_path = mock_site.pages[0].source_path
        orchestrator.cache.should_bypass = Mock(return_value=True)
        orchestrator.cache.is_changed = Mock(return_value=False)

        with patch.object(
            orchestrator._cache_manager, "_get_theme_templates_dir", return_value=None
        ):
            pages, assets, summary = orchestrator.find_work_early(
                verbose=True,
                forced_changed_sources={forced_path},
            )

        assert len(pages) >= 1

    def test_find_work_early_without_cache_raises(self, mock_site):
        """find_work_early should raise if cache not initialized."""
        orch = IncrementalOrchestrator(mock_site)

        with pytest.raises(BengalError, match="Cache not initialized"):
            orch.find_work_early()


class TestFindWork:
    """Test full phase change detection."""

    def test_find_work_detects_all_changes(self, orchestrator, mock_site):
        """find_work should detect all changed pages."""
        orchestrator.cache.is_changed = Mock(return_value=True)
        orchestrator.cache.should_bypass = Mock(return_value=True)
        orchestrator.cache.get_previous_tags = Mock(return_value=set())

        with patch.object(
            orchestrator._cache_manager, "_get_theme_templates_dir", return_value=None
        ):
            pages, assets, summary = orchestrator.find_work(verbose=True)

        assert len(pages) == 2

    def test_find_work_returns_summary_dict(self, orchestrator, mock_site):
        """find_work should return ChangeSummary."""
        orchestrator.cache.is_changed = Mock(return_value=True)
        orchestrator.cache.should_bypass = Mock(return_value=True)
        orchestrator.cache.get_previous_tags = Mock(return_value=set())

        with patch.object(
            orchestrator._cache_manager, "_get_theme_templates_dir", return_value=None
        ):
            pages, assets, summary = orchestrator.find_work(verbose=True)

        from bengal.orchestration.build.results import ChangeSummary

        assert isinstance(summary, ChangeSummary)

    def test_find_work_without_cache_raises(self, mock_site):
        """find_work should raise if cache not initialized."""
        orch = IncrementalOrchestrator(mock_site)

        with pytest.raises(BengalError, match="Cache not initialized"):
            orch.find_work()


class TestChangeDetectorDelegation:
    """Test that orchestrator properly delegates to EffectBasedDetector."""

    def test_change_detector_lazily_initialized(self, orchestrator, mock_site):
        """EffectBasedDetector should be initialized during initialize()."""
        # Detector is created during initialize(), not lazily
        assert orchestrator._detector is not None

    def test_change_detector_reused(self, orchestrator, mock_site):
        """Detector should be reused across calls."""
        orchestrator.cache.should_bypass = Mock(return_value=False)
        orchestrator.cache.is_changed = Mock(return_value=False)
        orchestrator.cache.get_previous_tags = Mock(return_value=set())

        with patch.object(
            orchestrator._cache_manager, "_get_theme_templates_dir", return_value=None
        ):
            orchestrator.find_work_early()
            first_detector = orchestrator._detector

            orchestrator.find_work()
            second_detector = orchestrator._detector

        assert first_detector is second_detector


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
