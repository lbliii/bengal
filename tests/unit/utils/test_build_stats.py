"""
Tests for bengal/utils/build_stats.py.

Covers:
- BuildWarning dataclass
- BuildStats dataclass and properties
- Directive tracking
- Warning grouping
- Stats formatting (format_time)
- Stats display functions
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestBuildWarning:
    """Test BuildWarning dataclass."""

    def test_init_with_all_fields(self) -> None:
        """Test BuildWarning initialization with all fields."""
        from bengal.utils.build_stats import BuildWarning

        warning = BuildWarning(
            file_path="/path/to/file.md",
            message="Test message",
            warning_type="jinja2",
        )

        assert warning.file_path == "/path/to/file.md"
        assert warning.message == "Test message"
        assert warning.warning_type == "jinja2"

    def test_short_path_relative_to_cwd(self, tmp_path: Path, monkeypatch: MagicMock) -> None:
        """Test short_path returns path relative to cwd."""
        from bengal.utils.build_stats import BuildWarning

        # Change cwd to tmp_path
        monkeypatch.chdir(tmp_path)

        file_path = tmp_path / "content" / "post.md"
        warning = BuildWarning(
            file_path=str(file_path),
            message="Test",
            warning_type="other",
        )

        assert warning.short_path == "content/post.md"

    def test_short_path_fallback(self) -> None:
        """Test short_path fallback when not relative to cwd."""
        from bengal.utils.build_stats import BuildWarning

        warning = BuildWarning(
            file_path="/some/absolute/path/file.md",
            message="Test",
            warning_type="other",
        )

        # Should return parent/name or just name
        short = warning.short_path
        assert "file.md" in short


class TestBuildStats:
    """Test BuildStats dataclass."""

    def test_init_with_defaults(self) -> None:
        """Test BuildStats initialization with defaults."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.total_pages == 0
        assert stats.regular_pages == 0
        assert stats.generated_pages == 0
        assert stats.total_assets == 0
        assert stats.total_sections == 0
        assert stats.build_time_ms == 0
        assert stats.parallel is True
        assert stats.incremental is False

    def test_init_with_custom_values(self) -> None:
        """Test BuildStats initialization with custom values."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats(
            total_pages=100,
            regular_pages=80,
            generated_pages=20,
            build_time_ms=1500.0,
        )

        assert stats.total_pages == 100
        assert stats.regular_pages == 80
        assert stats.generated_pages == 20
        assert stats.build_time_ms == 1500.0

    def test_post_init_creates_warnings_list(self) -> None:
        """Test that __post_init__ creates warnings list."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.warnings == []
        assert isinstance(stats.warnings, list)

    def test_post_init_creates_template_errors_list(self) -> None:
        """Test that __post_init__ creates template_errors list."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.template_errors == []
        assert isinstance(stats.template_errors, list)

    def test_post_init_creates_directives_dict(self) -> None:
        """Test that __post_init__ creates directives_by_type dict."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.directives_by_type == {}
        assert isinstance(stats.directives_by_type, dict)


class TestBuildStatsAddWarning:
    """Test BuildStats.add_warning method."""

    def test_add_warning_appends_to_list(self) -> None:
        """Test that add_warning appends to warnings list."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()
        stats.add_warning("/path/to/file.md", "Test message", "jinja2")

        assert len(stats.warnings) == 1
        assert stats.warnings[0].file_path == "/path/to/file.md"
        assert stats.warnings[0].message == "Test message"
        assert stats.warnings[0].warning_type == "jinja2"

    def test_add_warning_default_type(self) -> None:
        """Test add_warning with default warning type."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()
        stats.add_warning("/path/to/file.md", "Test message")

        assert stats.warnings[0].warning_type == "other"

    def test_add_multiple_warnings(self) -> None:
        """Test adding multiple warnings."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()
        stats.add_warning("/file1.md", "Message 1", "jinja2")
        stats.add_warning("/file2.md", "Message 2", "link")
        stats.add_warning("/file3.md", "Message 3", "preprocessing")

        assert len(stats.warnings) == 3


class TestBuildStatsAddDirective:
    """Test BuildStats.add_directive method."""

    def test_add_directive_increments_total(self) -> None:
        """Test that add_directive increments total_directives."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()
        stats.add_directive("note")

        assert stats.total_directives == 1

    def test_add_directive_tracks_by_type(self) -> None:
        """Test that add_directive tracks by type."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()
        stats.add_directive("note")
        stats.add_directive("warning")
        stats.add_directive("note")

        assert stats.directives_by_type["note"] == 2
        assert stats.directives_by_type["warning"] == 1
        assert stats.total_directives == 3


class TestBuildStatsHasErrors:
    """Test BuildStats.has_errors property."""

    def test_has_errors_false_when_no_errors(self) -> None:
        """Test has_errors is False when no template errors."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.has_errors is False

    def test_has_errors_true_when_template_errors(self) -> None:
        """Test has_errors is True when template errors exist."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()
        stats.add_template_error(MagicMock())

        assert stats.has_errors is True


class TestBuildStatsWarningsByType:
    """Test BuildStats.warnings_by_type property."""

    def test_groups_warnings_by_type(self) -> None:
        """Test that warnings_by_type groups correctly."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()
        stats.add_warning("/file1.md", "Jinja error", "jinja2")
        stats.add_warning("/file2.md", "Another jinja error", "jinja2")
        stats.add_warning("/file3.md", "Link broken", "link")

        grouped = stats.warnings_by_type

        assert len(grouped["jinja2"]) == 2
        assert len(grouped["link"]) == 1

    def test_returns_empty_dict_when_no_warnings(self) -> None:
        """Test warnings_by_type returns empty dict when no warnings."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.warnings_by_type == {}


class TestBuildStatsToDict:
    """Test BuildStats.to_dict method."""

    def test_to_dict_includes_all_fields(self) -> None:
        """Test that to_dict includes all expected fields."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats(
            total_pages=50,
            regular_pages=40,
            generated_pages=10,
            build_time_ms=1000.0,
        )

        result = stats.to_dict()

        assert result["total_pages"] == 50
        assert result["regular_pages"] == 40
        assert result["generated_pages"] == 10
        assert result["build_time_ms"] == 1000.0
        assert "parallel" in result
        assert "incremental" in result


class TestFormatTime:
    """Test format_time function."""

    def test_formats_sub_millisecond(self) -> None:
        """Test formatting sub-millisecond times."""
        from bengal.utils.build_stats import format_time

        result = format_time(0.5)
        assert result == "0.50 ms"

    def test_formats_milliseconds(self) -> None:
        """Test formatting millisecond times."""
        from bengal.utils.build_stats import format_time

        result = format_time(500)
        assert result == "500 ms"

    def test_formats_seconds(self) -> None:
        """Test formatting second-scale times."""
        from bengal.utils.build_stats import format_time

        result = format_time(2500)
        assert result == "2.50 s"

    def test_formats_exact_one_second(self) -> None:
        """Test formatting exactly 1 second."""
        from bengal.utils.build_stats import format_time

        result = format_time(1000)
        assert result == "1.00 s"


class TestDisplayFunctions:
    """Test display functions."""

    @patch("bengal.utils.build_stats.CLIOutput")
    def test_display_warnings_skips_when_no_warnings(self, mock_cli_class: MagicMock) -> None:
        """Test display_warnings does nothing when no warnings."""
        from bengal.utils.build_stats import BuildStats, display_warnings

        stats = BuildStats()

        display_warnings(stats)

        # Should not create CLI output when no warnings
        mock_cli_class.return_value.error_header.assert_not_called()

    @patch("bengal.utils.build_stats.CLIOutput")
    def test_display_simple_build_stats_handles_skipped(
        self, mock_cli_class: MagicMock
    ) -> None:
        """Test display_simple_build_stats handles skipped builds."""
        from bengal.utils.build_stats import BuildStats, display_simple_build_stats

        stats = BuildStats(skipped=True)
        mock_cli = MagicMock()
        mock_cli_class.return_value = mock_cli

        display_simple_build_stats(stats)

        # Should indicate build was skipped
        mock_cli.info.assert_called()

    @patch("bengal.utils.build_stats.CLIOutput")
    def test_display_build_stats_handles_skipped(self, mock_cli_class: MagicMock) -> None:
        """Test display_build_stats handles skipped builds."""
        from bengal.utils.build_stats import BuildStats, display_build_stats

        stats = BuildStats(skipped=True)
        mock_cli = MagicMock()
        mock_cli_class.return_value = mock_cli

        display_build_stats(stats)

        mock_cli.info.assert_called()

    def test_show_building_indicator_does_nothing(self) -> None:
        """Test show_building_indicator does nothing (header shown elsewhere)."""
        from bengal.utils.build_stats import show_building_indicator

        # Should not raise
        show_building_indicator("Building")

    @patch("bengal.utils.build_stats.CLIOutput")
    def test_show_error_displays_error(self, mock_cli_class: MagicMock) -> None:
        """Test show_error displays error message."""
        from bengal.utils.build_stats import show_error

        mock_cli = MagicMock()
        mock_cli_class.return_value = mock_cli

        show_error("Test error message")

        mock_cli.error_header.assert_called()


class TestBuildStatsPhaseTimings:
    """Test phase timing fields."""

    def test_phase_timing_defaults(self) -> None:
        """Test phase timing fields default to 0."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.discovery_time_ms == 0
        assert stats.taxonomy_time_ms == 0
        assert stats.rendering_time_ms == 0
        assert stats.assets_time_ms == 0
        assert stats.postprocess_time_ms == 0
        assert stats.health_check_time_ms == 0

    def test_phase_timing_custom_values(self) -> None:
        """Test phase timing with custom values."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats(
            discovery_time_ms=100.0,
            taxonomy_time_ms=50.0,
            rendering_time_ms=500.0,
            assets_time_ms=200.0,
            postprocess_time_ms=100.0,
        )

        assert stats.discovery_time_ms == 100.0
        assert stats.taxonomy_time_ms == 50.0
        assert stats.rendering_time_ms == 500.0
        assert stats.assets_time_ms == 200.0
        assert stats.postprocess_time_ms == 100.0


class TestBuildStatsMemoryMetrics:
    """Test memory metric fields."""

    def test_memory_metrics_defaults(self) -> None:
        """Test memory metric fields default to 0."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.memory_rss_mb == 0
        assert stats.memory_heap_mb == 0
        assert stats.memory_peak_mb == 0


class TestBuildStatsCacheStatistics:
    """Test cache statistic fields."""

    def test_cache_statistics_defaults(self) -> None:
        """Test cache statistic fields default to 0."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats()

        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.time_saved_ms == 0

    def test_cache_statistics_custom_values(self) -> None:
        """Test cache statistics with custom values."""
        from bengal.utils.build_stats import BuildStats

        stats = BuildStats(
            cache_hits=100,
            cache_misses=20,
            time_saved_ms=5000.0,
        )

        assert stats.cache_hits == 100
        assert stats.cache_misses == 20
        assert stats.time_saved_ms == 5000.0



