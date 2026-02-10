"""
Tests for BuildOrchestrator.

With the data-driven pipeline (Bengal 0.2), build() delegates to
execute_pipeline(). These tests verify:
  1. Pipeline is invoked with correct context and options
  2. BuildContext is populated with required fields
  3. BuildStats is returned correctly
  4. Strict-mode section validation still raises
"""

from unittest.mock import MagicMock, patch

import pytest

from bengal.orchestration.build import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.pipeline.executor import PipelineResult, TaskResult
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
        """Test that a full build sets up context and calls execute_pipeline."""
        orchestrator = BuildOrchestrator(mock_site)

        # Setup mocks for successful flow
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_cache.file_fingerprints = {}
        mock_orchestrators["incremental"].return_value.initialize.return_value = mock_cache
        mock_orchestrators["incremental"].return_value.check_config_changed.return_value = False
        mock_orchestrators["section"].return_value.validate_sections.return_value = []

        with patch(
            "bengal.orchestration.pipeline.execute_pipeline"
        ) as mock_pipeline:
            mock_pipeline.return_value = PipelineResult()

            options = BuildOptions(incremental=False, force_sequential=True)
            stats = orchestrator.build(options)

        # 1. Pipeline was called
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]

        # 2. Context has required pipeline fields
        ctx = call_kwargs["ctx"]
        assert ctx.site is mock_site
        assert ctx._orchestrator is orchestrator
        assert ctx._build_options is options
        assert ctx.cache is mock_cache
        assert ctx.stats is not None
        assert ctx.output_collector is not None
        assert ctx.incremental is False
        assert ctx.verbose is False
        assert ctx.strict is False

        # 3. INITIAL_KEYS were passed
        assert call_kwargs["initial_keys"] is not None

        # 4. Parallel flag matches force_sequential=True → parallel=False
        assert call_kwargs["parallel"] is False

        # 5. Returns BuildStats
        assert isinstance(stats, BuildStats)

        # 6. Cache was initialized
        mock_orchestrators["incremental"].return_value.initialize.assert_called_once()

    def test_incremental_build_sequence(self, mock_site, mock_orchestrators):
        """Test incremental build sets up context with incremental=True."""
        orchestrator = BuildOrchestrator(mock_site)

        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_cache.file_fingerprints = {"some_file": "hash123"}
        mock_inc = mock_orchestrators["incremental"].return_value
        mock_inc.initialize.return_value = mock_cache
        mock_inc.check_config_changed.return_value = False

        with patch(
            "bengal.orchestration.pipeline.execute_pipeline"
        ) as mock_pipeline:
            mock_pipeline.return_value = PipelineResult()

            options = BuildOptions(incremental=True, force_sequential=False)
            stats = orchestrator.build(options)

        # Verify incremental mode propagated to context
        ctx = mock_pipeline.call_args[1]["ctx"]
        assert ctx.incremental is True

        # Parallel enabled when force_sequential=False
        assert mock_pipeline.call_args[1]["parallel"] is True

        assert isinstance(stats, BuildStats)

    def test_section_validation_error_strict(self, mock_site, mock_orchestrators):
        """Test that section validation errors raise exception in strict mode."""
        # Enable strict mode in config
        mock_site.config["strict_mode"] = True
        orchestrator = BuildOrchestrator(mock_site)

        # Setup mocks to return validation errors
        mock_orchestrators["section"].return_value.validate_sections.return_value = ["Error 1"]
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_cache.file_fingerprints = {}
        mock_orchestrators["incremental"].return_value.initialize.return_value = mock_cache

        # The section validation now happens inside the sections task (via pipeline).
        # When strict mode is on and validation fails, the task raises an exception
        # which propagates through the pipeline as a failed task.
        # We simulate this by making execute_pipeline raise the error.
        with patch(
            "bengal.orchestration.pipeline.execute_pipeline"
        ) as mock_pipeline:
            mock_pipeline.side_effect = RuntimeError(
                "Build failed: 1 section validation error"
            )
            options = BuildOptions(incremental=False, strict=True)
            with pytest.raises(RuntimeError, match="Build failed: 1 section validation error"):
                orchestrator.build(options)

    def test_flag_propagation(self, mock_site, mock_orchestrators):
        """Test that build flags are propagated to BuildContext."""
        orchestrator = BuildOrchestrator(mock_site)
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_cache.file_fingerprints = {}
        mock_orchestrators["incremental"].return_value.initialize.return_value = mock_cache

        with patch(
            "bengal.orchestration.pipeline.execute_pipeline"
        ) as mock_pipeline:
            mock_pipeline.return_value = PipelineResult()

            options = BuildOptions(
                force_sequential=False,
                incremental=False,
                verbose=True,
                quiet=False,
                strict=True,
                memory_optimized=True,
            )
            orchestrator.build(options)

        ctx = mock_pipeline.call_args[1]["ctx"]
        assert ctx.verbose is True
        assert ctx.quiet is False
        assert ctx.strict is True
        assert ctx.memory_optimized is True
        assert ctx._build_options is options

    def test_pipeline_failure_raises_runtime_error(self, mock_site, mock_orchestrators):
        """Build should fail loudly when pipeline reports failed tasks."""
        orchestrator = BuildOrchestrator(mock_site)
        mock_cache = MagicMock()
        mock_cache.parsed_content = {}
        mock_cache.file_fingerprints = {}
        mock_orchestrators["incremental"].return_value.initialize.return_value = mock_cache

        failed_result = PipelineResult(
            task_results=[
                TaskResult(
                    name="parse_content",
                    status="failed",
                    duration_ms=12.5,
                    error=RuntimeError("parse blew up"),
                )
            ]
        )

        with patch("bengal.orchestration.pipeline.execute_pipeline") as mock_pipeline:
            mock_pipeline.return_value = failed_result
            with pytest.raises(RuntimeError, match="Build failed in task 'parse_content'"):
                orchestrator.build(BuildOptions(incremental=False))
