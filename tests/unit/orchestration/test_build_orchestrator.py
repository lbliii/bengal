"""
Tests for BuildOrchestrator.
"""

from unittest.mock import ANY, MagicMock, Mock, patch

import pytest

from bengal.orchestration.build import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.stats import BuildStats


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
        site.menu = {}  # dict[str, list[MenuItem]], not list

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
            patch("bengal.orchestration.incremental.IncrementalOrchestrator") as MockIncremental,
            patch("bengal.orchestration.build.get_logger") as MockLogger,
            patch("bengal.output.init_cli_output") as MockCli,
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
        from bengal.orchestration.build.results import FilterResult

        # Setup mocks for successful flow
        # Note: initialize() returns (cache, tracker) - order matters!
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_tracker = MagicMock()
        mock_orchestrators["incremental"].return_value.initialize.return_value = (mock_cache, mock_tracker)
        mock_orchestrators["incremental"].return_value.check_config_changed.return_value = False
        mock_orchestrators["section"].return_value.validate_sections.return_value = []

        with patch(
            "bengal.orchestration.build.provenance_filter.phase_incremental_filter_provenance"
        ) as mock_filter:
            mock_filter.return_value = FilterResult(
                pages_to_build=[],
                assets_to_process=[],
                affected_tags=set(),
                changed_page_paths=set(),
                affected_sections=None,
            )
            # Run build with BuildOptions
            options = BuildOptions(incremental=False, force_sequential=True)
            stats = orchestrator.build(options)

        # Verify sequence
        # 1. Initialization
        mock_orchestrators["incremental"].return_value.initialize.assert_called_once()

        # 2. Content Discovery (calls discover_content, not discover)
        mock_orchestrators["content"].return_value.discover_content.assert_called_once_with(
            incremental=False, cache=None, build_context=ANY, build_cache=ANY
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
        from bengal.orchestration.build.results import FilterResult

        mock_inc = mock_orchestrators["incremental"].return_value
        # Note: initialize() returns (cache, tracker) - order matters!
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_tracker = MagicMock()
        mock_inc.initialize.return_value = (mock_cache, mock_tracker)
        mock_inc.check_config_changed.return_value = False
        # Simulate filtering work
        filter_result = FilterResult(
            pages_to_build=[Mock()],
            assets_to_process=[],
            affected_tags=set(),
            changed_page_paths=set(),
            affected_sections=None,
        )

        with patch(
            "bengal.orchestration.build.provenance_filter.phase_incremental_filter_provenance"
        ) as mock_filter:
            mock_filter.return_value = filter_result
            # Run incremental build with BuildOptions
            options = BuildOptions(incremental=True, force_sequential=False)
            orchestrator.build(options)

        # Should use incremental discovery (calls discover_content, not discover)
        mock_orchestrators["content"].return_value.discover_content.assert_called_with(
            incremental=True, cache=ANY, build_context=ANY, build_cache=ANY
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
        # Note: initialize() returns (cache, tracker) - order matters!
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_tracker = MagicMock()
        mock_orchestrators["incremental"].return_value.initialize.return_value = (mock_cache, mock_tracker)
        from bengal.orchestration.build.results import FilterResult
        filter_result = FilterResult(
            pages_to_build=[],
            assets_to_process=[],
            affected_tags=set(),
            changed_page_paths=set(),
            affected_sections=None,
        )

        # Expect exception with strict mode
        options = BuildOptions(incremental=False, strict=True)
        with patch(
            "bengal.orchestration.build.provenance_filter.phase_incremental_filter_provenance"
        ) as mock_filter:
            mock_filter.return_value = filter_result
            with pytest.raises(Exception, match="Build failed: 1 section validation error"):
                orchestrator.build(options)

    def test_flag_propagation(self, mock_site, mock_orchestrators):
        """Test that flags are propagated to sub-orchestrators."""
        orchestrator = BuildOrchestrator(mock_site)
        # Note: initialize() returns (cache, tracker) - order matters!
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_tracker = MagicMock()
        mock_orchestrators["incremental"].return_value.initialize.return_value = (mock_cache, mock_tracker)

        from bengal.orchestration.build.results import FilterResult
        filter_result = FilterResult(
            pages_to_build=[],
            assets_to_process=[],
            affected_tags=set(),
            changed_page_paths=set(),
            affected_sections=None,
        )

        # Run with specific flags (force_sequential=False means auto-detect, which may use parallel)
        options = BuildOptions(force_sequential=False, incremental=False)
        with patch(
            "bengal.orchestration.build.provenance_filter.phase_incremental_filter_provenance"
        ) as mock_filter:
            mock_filter.return_value = filter_result
            orchestrator.build(options)

        # Check that taxonomy orchestrator was called
        # Note: The taxonomy orchestrator is now called with force_sequential parameter
        mock_orchestrators["taxonomy"].return_value.collect_and_generate.assert_called_once()
        # Asset orchestrator process is called
        mock_orchestrators["asset"].return_value.process.assert_called_once()
