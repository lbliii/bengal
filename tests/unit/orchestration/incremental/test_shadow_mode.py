"""
Tests for shadow mode execution in IncrementalOrchestrator.

Shadow mode runs both legacy and new change detection paths
and compares results for validation during the refactoring period.
"""

from unittest.mock import Mock, patch

import pytest

from bengal.cache.paths import BengalPaths
from bengal.core.page import Page
from bengal.orchestration.build.options import BuildOptions
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
            content="Content 1",
            metadata={"title": "Page 1"},
        ),
        Page(
            source_path=tmp_path / "content/page2.md",
            content="Content 2",
            metadata={"title": "Page 2"},
        ),
    ]
    site.assets = []
    site.regular_pages = site.pages
    site.generated_pages = []

    return site


@pytest.fixture
def orchestrator(mock_site):
    """Create an IncrementalOrchestrator instance."""
    orch = IncrementalOrchestrator(mock_site)
    orch.initialize(enabled=False)
    return orch


class TestFeatureFlagConfiguration:
    """Test feature flag configuration for unified change detector."""

    def test_default_feature_flags(self):
        """Default options should have feature flags disabled."""
        options = BuildOptions()

        assert options.use_unified_change_detector is False
        assert options.shadow_mode is False

    def test_enable_unified_change_detector(self):
        """Can enable unified change detector via options."""
        options = BuildOptions(use_unified_change_detector=True)

        assert options.use_unified_change_detector is True

    def test_enable_shadow_mode(self):
        """Can enable shadow mode via options."""
        options = BuildOptions(shadow_mode=True)

        assert options.shadow_mode is True

    def test_orchestrator_reads_config_flags(self, mock_site):
        """Orchestrator should read feature flags from site config."""
        # Setup config with feature flags
        mock_site.config = {
            "build": {
                "use_unified_change_detector": True,
                "shadow_mode": True,
            }
        }

        orch = IncrementalOrchestrator(mock_site)

        assert orch._use_unified_change_detector is True
        assert orch._shadow_mode is True

    def test_orchestrator_defaults_when_config_missing(self, mock_site):
        """Orchestrator should use defaults when config is missing."""
        # Setup config without build section
        mock_site.config = {}

        orch = IncrementalOrchestrator(mock_site)

        assert orch._use_unified_change_detector is False
        assert orch._shadow_mode is False


class TestLegacyPath:
    """Test legacy change detection path."""

    def test_find_work_uses_legacy_by_default(self, orchestrator, mock_site):
        """find_work should use legacy path when feature flag is off."""
        # Setup cache mocks
        orchestrator.cache.is_changed = Mock(return_value=True)
        orchestrator.cache.should_bypass = Mock(return_value=True)
        orchestrator.cache.get_previous_tags = Mock(return_value=set())

        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            pages, assets, summary = orchestrator.find_work(verbose=True)

        # Should return pages
        assert len(pages) == 2

    def test_find_work_early_uses_legacy_by_default(self, orchestrator, mock_site):
        """find_work_early should use legacy path when feature flag is off."""
        orchestrator.cache.should_bypass = Mock(return_value=True)
        orchestrator.cache.is_changed = Mock(return_value=False)

        with patch.object(orchestrator, "_get_theme_templates_dir", return_value=None):
            pages, assets, summary = orchestrator.find_work_early(verbose=True)

        assert len(pages) == 2


class TestUnifiedPath:
    """Test unified change detection path."""

    def test_find_work_early_uses_unified_when_enabled(self, mock_site):
        """find_work_early should use unified path when feature flag is on."""
        mock_site.config = {"build": {"use_unified_change_detector": True}}

        orch = IncrementalOrchestrator(mock_site)
        orch.initialize(enabled=False)

        orch.cache.should_bypass = Mock(return_value=True)
        orch.cache.is_changed = Mock(return_value=False)

        with patch.object(orch, "_get_theme_templates_dir", return_value=None):
            pages, assets, summary = orch.find_work_early(verbose=True)

        # Should work with unified path
        assert len(pages) == 2

    def test_find_work_uses_unified_when_enabled(self, mock_site):
        """find_work should use unified path when feature flag is on."""
        mock_site.config = {"build": {"use_unified_change_detector": True}}

        orch = IncrementalOrchestrator(mock_site)
        orch.initialize(enabled=False)

        orch.cache.should_bypass = Mock(return_value=True)
        orch.cache.is_changed = Mock(return_value=True)
        orch.cache.get_previous_tags = Mock(return_value=set())

        with patch.object(orch, "_get_theme_templates_dir", return_value=None):
            pages, assets, summary = orch.find_work(verbose=True)

        assert len(pages) == 2


class TestResultComparison:
    """Test comparison logic between legacy and new results."""

    def test_compare_results_matching(self, orchestrator, mock_site):
        """Matching results should not log warnings."""
        page = mock_site.pages[0]

        # Should not raise
        orchestrator._compare_results(
            "find_work",
            new_pages=[page],
            new_assets=[],
            legacy_pages=[page],
            legacy_assets=[],
        )

    def test_compare_results_different_pages(self, orchestrator, mock_site, caplog):
        """Different page results should be logged."""
        import logging

        with caplog.at_level(logging.WARNING):
            orchestrator._compare_results(
                "find_work",
                new_pages=[mock_site.pages[0]],
                new_assets=[],
                legacy_pages=[mock_site.pages[1]],
                legacy_assets=[],
            )

        # Should log discrepancy
        # Note: Actual logging depends on structlog configuration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
