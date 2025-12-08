"""
Tests for BuildOrchestrator.
"""

from unittest.mock import ANY, MagicMock, Mock, patch

import pytest

from bengal.orchestration.build import BuildOrchestrator
from bengal.utils.build_stats import BuildStats


class TestBuildOrchestrator:
    @pytest.fixture
    def mock_site(self, tmp_path):
        site = MagicMock()
        site.root_path = tmp_path  # Use real path to prevent MagicMock file leaks
        site.config = {"strict_mode": False, "fonts": {}}
        site.pages = []
        site.regular_pages = []
        site.generated_pages = []
        site.assets = []
        site.sections = []
        site.taxonomies = {}
        site.menu = []

        # Configure indexes
        site.indexes.stats.return_value = {"total_indexes": 0}
        site.indexes.update_incremental.return_value = {}
        site.indexes.build_all.return_value = None

        site.theme = None
        return site

    @pytest.fixture
    def mock_orchestrators(self):
        with (
            patch("bengal.orchestration.build.ContentOrchestrator") as MockContent,
            patch("bengal.orchestration.build.SectionOrchestrator") as MockSection,
            patch("bengal.orchestration.build.TaxonomyOrchestrator") as MockTaxonomy,
            patch("bengal.orchestration.build.MenuOrchestrator") as MockMenu,
            patch("bengal.orchestration.build.RenderOrchestrator") as MockRender,
            patch("bengal.orchestration.build.AssetOrchestrator") as MockAsset,
            patch("bengal.orchestration.build.PostprocessOrchestrator") as MockPostprocess,
            patch("bengal.orchestration.build.IncrementalOrchestrator") as MockIncremental,
            patch("bengal.orchestration.build.get_logger") as MockLogger,
            patch("bengal.utils.cli_output.init_cli_output") as MockCli,
        ):
            # Configure logger level to avoid TypeError in comparisons
            MockLogger.return_value.level.value = 20  # INFO level

            yield {
                "content": MockContent,
                "section": MockSection,
                "taxonomy": MockTaxonomy,
                "menu": MockMenu,
                "render": MockRender,
                "asset": MockAsset,
                "postprocess": MockPostprocess,
                "incremental": MockIncremental,
                "logger": MockLogger,
                "cli": MockCli,
            }

    def test_full_build_sequence(self, mock_site, mock_orchestrators):
        """Test that a full build calls all orchestrators in correct order."""
        orchestrator = BuildOrchestrator(mock_site)

        # Setup mocks for successful flow
        mock_orchestrators["incremental"].return_value.initialize.return_value = (Mock(), Mock())
        mock_orchestrators["incremental"].return_value.check_config_changed.return_value = False
        mock_orchestrators["section"].return_value.validate_sections.return_value = []

        # Run build
        stats = orchestrator.build(incremental=False, parallel=False)

        # Verify sequence
        # 1. Initialization
        mock_orchestrators["incremental"].return_value.initialize.assert_called_once()

        # 2. Content Discovery
        mock_orchestrators["content"].return_value.discover.assert_called_once_with(
            incremental=False, cache=None, build_context=ANY
        )

        # 3. Section Finalization
        mock_orchestrators["section"].return_value.finalize_sections.assert_called_once()
        mock_orchestrators["section"].return_value.validate_sections.assert_called_once()

        # 4. Taxonomies
        mock_orchestrators["taxonomy"].return_value.collect_and_generate.assert_called_once()

        # 5. Menus
        mock_orchestrators["menu"].return_value.build.assert_called_once()

        # 6. Assets
        mock_orchestrators["asset"].return_value.process.assert_called_once()

        # 7. Rendering
        mock_orchestrators["render"].return_value.process.assert_called_once()

        # 8. Post-processing
        mock_orchestrators["postprocess"].return_value.run.assert_called_once()

        # 9. Cache Save
        mock_orchestrators["incremental"].return_value.save_cache.assert_called_once()

        assert isinstance(stats, BuildStats)

    def test_incremental_build_sequence(self, mock_site, mock_orchestrators):
        """Test incremental build flow."""
        orchestrator = BuildOrchestrator(mock_site)

        # Setup mocks for incremental flow
        from bengal.orchestration.build.results import ChangeSummary

        mock_inc = mock_orchestrators["incremental"].return_value
        mock_inc.initialize.return_value = (Mock(), Mock())
        mock_inc.check_config_changed.return_value = False
        # Simulate finding work
        mock_inc.find_work_early.return_value = ([Mock()], [], ChangeSummary())

        # Run incremental build
        orchestrator.build(incremental=True, parallel=True)

        # Verify incremental-specific calls
        mock_inc.find_work_early.assert_called_once()

        # Should use incremental discovery
        mock_orchestrators["content"].return_value.discover.assert_called_with(
            incremental=True, cache=ANY, build_context=ANY
        )

        # Should use incremental taxonomy generation
        mock_orchestrators[
            "taxonomy"
        ].return_value.collect_and_generate_incremental.assert_called_once()
        mock_orchestrators["taxonomy"].return_value.collect_and_generate.assert_not_called()

    def test_section_validation_error_strict(self, mock_site, mock_orchestrators):
        """Test that section validation errors raise exception in strict mode."""
        # Enable strict mode in config
        mock_site.config["strict_mode"] = True
        orchestrator = BuildOrchestrator(mock_site)

        # Setup mocks to return validation errors
        mock_orchestrators["section"].return_value.validate_sections.return_value = ["Error 1"]
        mock_orchestrators["incremental"].return_value.initialize.return_value = (Mock(), Mock())

        # Expect exception
        with pytest.raises(Exception, match="Build failed: 1 section validation error"):
            orchestrator.build(incremental=False, strict=True)

    def test_flag_propagation(self, mock_site, mock_orchestrators):
        """Test that flags are propagated to sub-orchestrators."""
        orchestrator = BuildOrchestrator(mock_site)
        mock_orchestrators["incremental"].return_value.initialize.return_value = (Mock(), Mock())

        # Run with specific flags
        orchestrator.build(parallel=True, incremental=False)

        # Check propagation
        mock_orchestrators["taxonomy"].return_value.collect_and_generate.assert_called_with(
            parallel=True
        )
        mock_orchestrators["asset"].return_value.process.assert_called_with(
            mock_site.assets, parallel=True, progress_manager=None
        )
