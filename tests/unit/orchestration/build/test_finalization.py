"""
Tests for build finalization phases.

Covers:
- phase_postprocess(): Post-processing phase
- phase_cache_save(): Cache saving phase
- phase_collect_stats(): Statistics collection
- run_health_check(): Health check execution
- phase_finalize(): Final cleanup phase
- Build badge artifact generation
"""

import json
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from bengal.orchestration.build.finalization import (
    _normalize_build_badge_config,
    _write_if_changed_atomic,
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

    def test_build_badge_disabled_by_default(self, tmp_path):
        """Does not write build badge artifacts unless explicitly enabled."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path, config={})
        orchestrator.site.taxonomies = {}

        phase_collect_stats(orchestrator, build_start=time.time())

        out_dir = orchestrator.site.output_dir
        assert not (out_dir / "bengal" / "build.svg").exists()
        assert not (out_dir / "bengal" / "build.json").exists()

    def test_build_badge_writes_svg_and_json_when_enabled(self, tmp_path):
        """Writes build badge artifacts when build_badge is enabled."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": {"enabled": True}},
        )
        orchestrator.site.taxonomies = {}

        phase_collect_stats(orchestrator, build_start=time.time() - 1.2)

        out_dir = orchestrator.site.output_dir
        svg_path = out_dir / "bengal" / "build.svg"
        json_path = out_dir / "bengal" / "build.json"

        assert svg_path.exists()
        assert json_path.exists()

        svg = svg_path.read_text(encoding="utf-8")
        data = json_path.read_text(encoding="utf-8")

        assert "built in" in svg
        assert '"build_time_ms"' in data


class TestBuildBadgeConfig:
    """Tests for build badge configuration normalization."""

    def test_none_config_disables_badge(self):
        """None config disables build badge."""
        result = _normalize_build_badge_config(None)
        assert result["enabled"] is False

    def test_false_config_disables_badge(self):
        """False config disables build badge."""
        result = _normalize_build_badge_config(False)
        assert result["enabled"] is False

    def test_true_config_enables_badge_with_defaults(self):
        """True config enables build badge with defaults."""
        result = _normalize_build_badge_config(True)

        assert result["enabled"] is True
        assert result["dir_name"] == "bengal"
        assert result["label"] == "built in"
        assert result["label_color"] == "#555"
        assert result["message_color"] == "#4c1d95"

    def test_dict_with_enabled_true(self):
        """Dict with enabled=True enables badge."""
        result = _normalize_build_badge_config({"enabled": True})
        assert result["enabled"] is True

    def test_dict_with_enabled_false(self):
        """Dict with enabled=False disables badge."""
        result = _normalize_build_badge_config({"enabled": False})
        assert result["enabled"] is False

    def test_dict_without_enabled_defaults_to_true(self):
        """Dict without 'enabled' key defaults to enabled."""
        result = _normalize_build_badge_config({"dir_name": "custom"})
        assert result["enabled"] is True

    def test_custom_dir_name(self):
        """Custom dir_name is respected."""
        result = _normalize_build_badge_config({"dir_name": "_meta"})
        assert result["dir_name"] == "_meta"

    def test_custom_label(self):
        """Custom label is respected."""
        result = _normalize_build_badge_config({"label": "generated in"})
        assert result["label"] == "generated in"

    def test_custom_colors(self):
        """Custom colors are respected."""
        result = _normalize_build_badge_config(
            {
                "label_color": "#333",
                "message_color": "#007bff",
            }
        )
        assert result["label_color"] == "#333"
        assert result["message_color"] == "#007bff"

    def test_unknown_type_disables_badge(self):
        """Unknown config type disables badge (fail-safe)."""
        result = _normalize_build_badge_config("invalid")
        assert result["enabled"] is False

        result = _normalize_build_badge_config(123)
        assert result["enabled"] is False

        result = _normalize_build_badge_config(["list"])
        assert result["enabled"] is False


class TestBuildBadgeArtifacts:
    """Tests for build badge artifact generation."""

    def test_json_contains_required_fields(self, tmp_path):
        """JSON artifact contains all required fields."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": True},
        )
        orchestrator.site.taxonomies = {}
        orchestrator.site.pages = [MagicMock() for _ in range(10)]
        orchestrator.site.assets = [MagicMock() for _ in range(5)]
        orchestrator.stats.rendering_time_ms = 150.5

        phase_collect_stats(orchestrator, build_start=time.time() - 2.5)

        json_path = orchestrator.site.output_dir / "bengal" / "build.json"
        data = json.loads(json_path.read_text())

        assert "build_time_ms" in data
        assert "build_time_human" in data
        assert "total_pages" in data
        assert "total_assets" in data
        assert "rendering_time_ms" in data
        assert "timestamp" in data

        assert data["total_pages"] == 10
        assert data["total_assets"] == 5
        assert data["rendering_time_ms"] == 150.5
        assert data["build_time_ms"] >= 2400  # ~2.5 seconds

    def test_custom_dir_name_used(self, tmp_path):
        """Custom dir_name creates artifacts in custom directory."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": {"dir_name": "_meta"}},
        )
        orchestrator.site.taxonomies = {}

        phase_collect_stats(orchestrator, build_start=time.time())

        assert (orchestrator.site.output_dir / "_meta" / "build.json").exists()
        assert (orchestrator.site.output_dir / "_meta" / "build.svg").exists()
        # Original dir should NOT exist
        assert not (orchestrator.site.output_dir / "bengal").exists()

    def test_custom_label_in_svg(self, tmp_path):
        """Custom label appears in SVG badge."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": {"label": "generated in"}},
        )
        orchestrator.site.taxonomies = {}

        phase_collect_stats(orchestrator, build_start=time.time())

        svg = (orchestrator.site.output_dir / "bengal" / "build.svg").read_text()
        assert "generated in" in svg

    def test_boolean_true_shorthand(self, tmp_path):
        """build_badge: true works as shorthand."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": True},
        )
        orchestrator.site.taxonomies = {}

        phase_collect_stats(orchestrator, build_start=time.time())

        assert (orchestrator.site.output_dir / "bengal" / "build.json").exists()

    def test_no_output_dir_gracefully_skips(self, tmp_path):
        """Gracefully skips when output_dir is None."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": True},
        )
        orchestrator.site.output_dir = None
        orchestrator.site.taxonomies = {}

        # Should not raise
        phase_collect_stats(orchestrator, build_start=time.time())


class TestBuildBadgeIncremental:
    """Tests for build badge behavior during incremental rebuilds."""

    def test_badge_updates_on_rebuild(self, tmp_path):
        """Badge artifacts update when build time changes."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": True},
        )
        orchestrator.site.taxonomies = {}

        # First build: 1 second
        phase_collect_stats(orchestrator, build_start=time.time() - 1.0)

        json_path = orchestrator.site.output_dir / "bengal" / "build.json"
        first_data = json.loads(json_path.read_text())
        first_mtime = json_path.stat().st_mtime

        # Second build: 3 seconds (different build time)
        time.sleep(0.1)  # Ensure mtime can differ
        phase_collect_stats(orchestrator, build_start=time.time() - 3.0)

        second_data = json.loads(json_path.read_text())
        second_mtime = json_path.stat().st_mtime

        # Build time should be different
        assert second_data["build_time_ms"] > first_data["build_time_ms"]
        # File should have been rewritten
        assert second_mtime > first_mtime

    def test_write_if_changed_skips_identical_content(self, tmp_path):
        """_write_if_changed_atomic skips write when content is identical."""
        from bengal.utils.atomic_write import AtomicFile

        test_file = tmp_path / "test.txt"
        content = "test content"

        # First write
        _write_if_changed_atomic(test_file, content, AtomicFile)
        first_mtime = test_file.stat().st_mtime

        # Small delay to ensure mtime could differ
        time.sleep(0.1)

        # Second write with identical content
        _write_if_changed_atomic(test_file, content, AtomicFile)
        second_mtime = test_file.stat().st_mtime

        # mtime should NOT change (file not rewritten)
        assert second_mtime == first_mtime

    def test_write_if_changed_updates_on_different_content(self, tmp_path):
        """_write_if_changed_atomic updates when content differs."""
        from bengal.utils.atomic_write import AtomicFile

        test_file = tmp_path / "test.txt"

        # First write
        _write_if_changed_atomic(test_file, "content v1", AtomicFile)
        first_mtime = test_file.stat().st_mtime

        # Small delay to ensure mtime could differ
        time.sleep(0.1)

        # Second write with different content
        _write_if_changed_atomic(test_file, "content v2", AtomicFile)
        second_mtime = test_file.stat().st_mtime

        # mtime should change (file rewritten)
        assert second_mtime > first_mtime
        assert test_file.read_text() == "content v2"

    def test_page_count_updates_on_incremental(self, tmp_path):
        """Page count in badge updates on incremental builds."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path,
            config={"build_badge": True},
        )
        orchestrator.site.taxonomies = {}

        # First build: 5 pages
        orchestrator.site.pages = [MagicMock() for _ in range(5)]
        phase_collect_stats(orchestrator, build_start=time.time())

        json_path = orchestrator.site.output_dir / "bengal" / "build.json"
        first_data = json.loads(json_path.read_text())
        assert first_data["total_pages"] == 5

        # Second build: 10 pages (new content added)
        orchestrator.site.pages = [MagicMock() for _ in range(10)]
        phase_collect_stats(orchestrator, build_start=time.time())

        second_data = json.loads(json_path.read_text())
        assert second_data["total_pages"] == 10


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
            patch("bengal.utils.cli_output.get_cli_output") as mock_get_cli,
        ):
            mock_config.return_value = {"enabled": True}
            mock_health = MagicMock()
            mock_health.last_stats = None
            mock_report = MagicMock()
            mock_report.has_errors.return_value = False
            mock_report.has_warnings.return_value = False
            mock_report.validator_reports = []
            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            run_health_check(orchestrator)

        # Should show phase line even when report is clean
        mock_get_cli.return_value.phase.assert_called()
        MockHealth.assert_called_once()
        mock_health.run.assert_called_once()

    def test_prints_validator_list_with_durations_when_parallel(self, tmp_path):
        """Prints exact validator list + per-validator durations when using parallel execution."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with (
            patch("bengal.config.defaults.get_feature_config") as mock_config,
            patch("bengal.health.HealthCheck") as MockHealth,
            patch("bengal.utils.cli_output.get_cli_output") as mock_get_cli,
        ):
            mock_config.return_value = {"enabled": True}

            mock_cli = MagicMock()
            mock_get_cli.return_value = mock_cli

            mock_health = MagicMock()
            mock_health.last_stats = MagicMock(
                execution_mode="parallel",
                validator_count=3,
                worker_count=3,
                speedup=1.2,
            )

            mock_report = MagicMock()
            mock_report.has_errors.return_value = False
            mock_report.has_warnings.return_value = False
            mock_report.validator_reports = [
                MagicMock(validator_name="Links", duration_ms=10.0),
                MagicMock(validator_name="Directives", duration_ms=700.0),
                MagicMock(validator_name="Output", duration_ms=50.0),
            ]

            mock_health.run.return_value = mock_report
            MockHealth.return_value = mock_health

            run_health_check(orchestrator)

            # First: parallel summary line
            mock_cli.info.assert_any_call("   ⚡ 3 validators, 3 workers, 1.2x speedup")
            # Then: exact validator list with durations (sorted by duration desc)
            mock_cli.info.assert_any_call(
                "   🔎 Validators: Directives: 700ms, Output: 50ms, Links: 10ms"
            )

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
