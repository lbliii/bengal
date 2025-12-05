"""
Tests for build finalization phases.

Covers:
- phase_postprocess(): Post-processing phase
- phase_cache_save(): Cache saving phase
- phase_collect_stats(): Statistics collection
- run_health_check(): Health check execution
- phase_finalize(): Final cleanup phase
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from bengal.orchestration.build.finalization import (
    phase_cache_save,
    phase_collect_stats,
    phase_finalize,
    phase_postprocess,
    run_health_check,
)


class MockPhaseContext:
    """Helper to create mock context for phase functions."""

    @staticmethod
    def create_orchestrator(tmp_path, config=None):
        """Create a mock orchestrator."""
        orchestrator = MagicMock()
        orchestrator.site = MagicMock()
        orchestrator.site.root_path = tmp_path
        orchestrator.site.output_dir = tmp_path / "public"
        orchestrator.site.config = config or {}
        orchestrator.site.pages = []
        orchestrator.site.regular_pages = []
        orchestrator.site.generated_pages = []
        orchestrator.site.sections = []
        orchestrator.site.assets = []
        orchestrator.site.taxonomies = {}

        orchestrator.stats = MagicMock()
        orchestrator.stats.postprocess_time_ms = 0
        orchestrator.stats.build_time_ms = 0
        orchestrator.stats.health_check_time_ms = 0
        orchestrator.stats.rendering_time_ms = 100
        orchestrator.stats.memory_rss_mb = 0
        orchestrator.stats.memory_heap_mb = 0
        orchestrator.stats.total_pages = 0
        orchestrator.stats.total_assets = 0

        orchestrator.logger = MagicMock()
        orchestrator.logger.phase = MagicMock(
            return_value=MagicMock(__enter__=Mock(), __exit__=Mock())
        )

        orchestrator.postprocess = MagicMock()
        orchestrator.incremental = MagicMock()

        return orchestrator

    @staticmethod
    def create_cli():
        """Create a mock CLI."""
        return MagicMock()


class TestPhasePostprocess:
    """Tests for phase_postprocess function."""

    def test_runs_postprocess(self, tmp_path):
        """Runs post-processing through postprocess orchestrator."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        ctx = MagicMock()

        phase_postprocess(orchestrator, cli, parallel=True, ctx=ctx, incremental=False)

        orchestrator.postprocess.run.assert_called_once_with(
            parallel=True,
            progress_manager=None,
            build_context=ctx,
            incremental=False,
        )

    def test_updates_postprocess_time_stats(self, tmp_path):
        """Updates post-process time statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        ctx = MagicMock()

        phase_postprocess(orchestrator, cli, parallel=False, ctx=ctx, incremental=False)

        assert orchestrator.stats.postprocess_time_ms >= 0

    def test_shows_phase_completion(self, tmp_path):
        """Shows phase completion message."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        ctx = MagicMock()

        phase_postprocess(orchestrator, cli, parallel=False, ctx=ctx, incremental=False)

        cli.phase.assert_called_once()


class TestPhaseCacheSave:
    """Tests for phase_cache_save function."""

    def test_saves_cache(self, tmp_path):
        """Saves build cache."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        pages_to_build = [MagicMock()]
        assets_to_process = [MagicMock()]

        phase_cache_save(orchestrator, pages_to_build, assets_to_process)

        orchestrator.incremental.save_cache.assert_called_once_with(
            pages_to_build, assets_to_process
        )

    def test_logs_cache_saved(self, tmp_path):
        """Logs cache saved message."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        phase_cache_save(orchestrator, [], [])

        orchestrator.logger.info.assert_called_with("cache_saved")


class TestPhaseCollectStats:
    """Tests for phase_collect_stats function."""

    def test_collects_page_stats(self, tmp_path):
        """Collects page statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.pages = [MagicMock(), MagicMock()]
        orchestrator.site.regular_pages = [MagicMock()]
        orchestrator.site.generated_pages = [MagicMock()]

        phase_collect_stats(orchestrator, build_start=time.time() - 1)

        assert orchestrator.stats.total_pages == 2
        assert orchestrator.stats.regular_pages == 1
        assert orchestrator.stats.generated_pages == 1

    def test_collects_asset_stats(self, tmp_path):
        """Collects asset statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.assets = [MagicMock() for _ in range(5)]

        phase_collect_stats(orchestrator, build_start=time.time())

        assert orchestrator.stats.total_assets == 5

    def test_collects_section_stats(self, tmp_path):
        """Collects section statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.sections = [MagicMock() for _ in range(3)]

        phase_collect_stats(orchestrator, build_start=time.time())

        assert orchestrator.stats.total_sections == 3

    def test_collects_taxonomy_stats(self, tmp_path):
        """Collects taxonomy statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {
            "tags": {"python": {}, "rust": {}},
            "categories": {"programming": {}},
        }

        phase_collect_stats(orchestrator, build_start=time.time())

        # 2 tags + 1 category = 3 terms
        assert orchestrator.stats.taxonomies_count == 3

    def test_calculates_build_time(self, tmp_path):
        """Calculates total build time."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {}

        build_start = time.time() - 1.5  # 1.5 seconds ago

        phase_collect_stats(orchestrator, build_start=build_start)

        # Build time should be roughly 1500ms
        assert orchestrator.stats.build_time_ms >= 1400  # Allow some variance

    def test_stores_stats_for_health_check(self, tmp_path):
        """Stores stats on site for health check validators."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {}

        phase_collect_stats(orchestrator, build_start=time.time())

        # Should store _last_build_stats
        assert hasattr(orchestrator.site, "_last_build_stats")


class TestRunHealthCheck:
    """Tests for run_health_check function."""

    def test_skips_when_disabled(self, tmp_path):
        """Skips health check when disabled in config."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with patch("bengal.config.defaults.get_feature_config") as mock_config:
            mock_config.return_value = {"enabled": False}

            run_health_check(orchestrator)

        # Should return early without running health check

    def test_runs_health_check(self, tmp_path):
        """Runs health check when enabled."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with (
            patch("bengal.config.defaults.get_feature_config") as mock_config,
            patch("bengal.health.HealthCheck") as MockHealth,
            patch("bengal.utils.cli_output.get_cli_output"),
        ):
            mock_config.return_value = {"enabled": True}
            mock_health = MagicMock()
            mock_health.last_stats = None
            mock_report = MagicMock()
            mock_report.has_errors.return_value = False
            mock_report.has_warnings.return_value = False
            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            run_health_check(orchestrator)

        MockHealth.assert_called_once()
        mock_health.run.assert_called_once()

    def test_passes_profile_to_health_check(self, tmp_path):
        """Passes build profile to health check."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        mock_profile = MagicMock()

        with (
            patch("bengal.config.defaults.get_feature_config") as mock_config,
            patch("bengal.health.HealthCheck") as MockHealth,
            patch("bengal.utils.cli_output.get_cli_output"),
        ):
            mock_config.return_value = {"enabled": True}
            mock_health = MagicMock()
            mock_health.last_stats = None
            mock_report = MagicMock()
            mock_report.has_errors.return_value = False
            mock_report.has_warnings.return_value = False
            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            run_health_check(orchestrator, profile=mock_profile)

        mock_health.run.assert_called_once()
        call_args = mock_health.run.call_args
        assert call_args.kwargs["profile"] is mock_profile

    def test_passes_cache_for_incremental(self, tmp_path):
        """Passes cache for incremental validation."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        mock_cache = MagicMock()
        orchestrator.incremental.cache = mock_cache

        with (
            patch("bengal.config.defaults.get_feature_config") as mock_config,
            patch("bengal.health.HealthCheck") as MockHealth,
            patch("bengal.utils.cli_output.get_cli_output"),
        ):
            mock_config.return_value = {"enabled": True}
            mock_health = MagicMock()
            mock_health.last_stats = None
            mock_report = MagicMock()
            mock_report.has_errors.return_value = False
            mock_report.has_warnings.return_value = False
            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            run_health_check(orchestrator, incremental=True)

        call_args = mock_health.run.call_args
        assert call_args.kwargs["cache"] is mock_cache

    def test_raises_in_strict_mode_with_errors(self, tmp_path):
        """Raises exception in strict mode with health check errors."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with (
            patch("bengal.config.defaults.get_feature_config") as mock_config,
            patch("bengal.health.HealthCheck") as MockHealth,
            patch("bengal.utils.cli_output.get_cli_output"),
        ):
            mock_config.return_value = {"enabled": True, "strict_mode": True}
            mock_health = MagicMock()
            mock_health.last_stats = None
            mock_report = MagicMock()
            mock_report.has_errors.return_value = True
            mock_report.error_count = 3
            mock_report.has_warnings.return_value = False
            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            with pytest.raises(Exception, match="Build failed health checks"):
                run_health_check(orchestrator)

    def test_stores_report_in_stats(self, tmp_path):
        """Stores health report in stats."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with (
            patch("bengal.config.defaults.get_feature_config") as mock_config,
            patch("bengal.health.HealthCheck") as MockHealth,
            patch("bengal.utils.cli_output.get_cli_output"),
        ):
            mock_config.return_value = {"enabled": True}
            mock_health = MagicMock()
            mock_health.last_stats = None
            mock_report = MagicMock()
            mock_report.has_errors.return_value = False
            mock_report.has_warnings.return_value = False
            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            run_health_check(orchestrator)

        assert orchestrator.stats.health_report is mock_report

    def test_updates_health_check_time_stats(self, tmp_path):
        """Updates health check time statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with (
            patch("bengal.config.defaults.get_feature_config") as mock_config,
            patch("bengal.health.HealthCheck") as MockHealth,
            patch("bengal.utils.cli_output.get_cli_output"),
        ):
            mock_config.return_value = {"enabled": True}
            mock_health = MagicMock()
            mock_health.last_stats = None
            mock_report = MagicMock()
            mock_report.has_errors.return_value = False
            mock_report.has_warnings.return_value = False
            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            run_health_check(orchestrator)

        assert orchestrator.stats.health_check_time_ms >= 0


class TestPhaseFinalize:
    """Tests for phase_finalize function."""

    def test_ends_collector_and_saves(self, tmp_path):
        """Ends performance collector and saves data."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        collector = MagicMock()
        collector.end_build.return_value = orchestrator.stats

        phase_finalize(orchestrator, verbose=False, collector=collector)

        collector.end_build.assert_called_once_with(orchestrator.stats)
        collector.save.assert_called_once()

    def test_logs_build_completion(self, tmp_path):
        """Logs build completion message."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        phase_finalize(orchestrator, verbose=False, collector=None)

        orchestrator.logger.info.assert_called_with(
            "build_complete",
            duration_ms=orchestrator.stats.build_time_ms,
            total_pages=orchestrator.stats.total_pages,
            total_assets=orchestrator.stats.total_assets,
            success=True,
        )

    def test_includes_memory_stats_when_collected(self, tmp_path):
        """Includes memory stats in log when collected."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.stats.memory_rss_mb = 100.5
        orchestrator.stats.memory_heap_mb = 80.2

        phase_finalize(orchestrator, verbose=False, collector=None)

        # Check that memory stats are included in the log call
        call_args = orchestrator.logger.info.call_args
        assert "memory_rss_mb" in call_args.kwargs
        assert call_args.kwargs["memory_rss_mb"] == 100.5

    def test_restores_console_output(self, tmp_path):
        """Restores console output when not verbose."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with patch("bengal.utils.logger.set_console_quiet") as mock_set_quiet:
            phase_finalize(orchestrator, verbose=False, collector=None)

        mock_set_quiet.assert_called_once_with(False)

    def test_skips_console_restore_in_verbose(self, tmp_path):
        """Skips console restore in verbose mode."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with patch("bengal.utils.logger.set_console_quiet") as mock_set_quiet:
            phase_finalize(orchestrator, verbose=True, collector=None)

        mock_set_quiet.assert_not_called()

    def test_logs_pygments_cache_stats(self, tmp_path):
        """Logs Pygments cache statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with patch("bengal.rendering.pygments_cache.log_cache_stats") as mock_log_stats:
            phase_finalize(orchestrator, verbose=False, collector=None)

        mock_log_stats.assert_called_once()

    def test_handles_no_collector(self, tmp_path):
        """Handles None collector gracefully."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        # Should not raise
        phase_finalize(orchestrator, verbose=False, collector=None)

        # Build should still complete
        orchestrator.logger.info.assert_called()
