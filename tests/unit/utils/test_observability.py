"""
Tests for bengal.utils.observability module.

Verifies:
- ComponentStats formatting and calculations
- HasStats protocol compliance
- Logging context generation
"""

from __future__ import annotations

from bengal.utils.observability import ComponentStats, HasStats, format_phase_stats


class TestComponentStats:
    """Tests for ComponentStats dataclass."""

    def test_default_values(self) -> None:
        """Test default initialization."""
        stats = ComponentStats()

        assert stats.items_total == 0
        assert stats.items_processed == 0
        assert stats.items_skipped == {}
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.sub_timings == {}
        assert stats.metrics == {}

    def test_cache_hit_rate_empty(self) -> None:
        """Test cache hit rate with no cache operations."""
        stats = ComponentStats()
        assert stats.cache_hit_rate == 0.0

    def test_cache_hit_rate_all_hits(self) -> None:
        """Test cache hit rate with 100% hits."""
        stats = ComponentStats(cache_hits=100, cache_misses=0)
        assert stats.cache_hit_rate == 100.0

    def test_cache_hit_rate_all_misses(self) -> None:
        """Test cache hit rate with 0% hits."""
        stats = ComponentStats(cache_hits=0, cache_misses=100)
        assert stats.cache_hit_rate == 0.0

    def test_cache_hit_rate_mixed(self) -> None:
        """Test cache hit rate with mixed results."""
        stats = ComponentStats(cache_hits=75, cache_misses=25)
        assert stats.cache_hit_rate == 75.0

    def test_skip_rate_empty(self) -> None:
        """Test skip rate with no items."""
        stats = ComponentStats()
        assert stats.skip_rate == 0.0

    def test_skip_rate_none_skipped(self) -> None:
        """Test skip rate with nothing skipped."""
        stats = ComponentStats(items_total=100, items_processed=100)
        assert stats.skip_rate == 0.0

    def test_skip_rate_all_skipped(self) -> None:
        """Test skip rate with everything skipped."""
        stats = ComponentStats(items_total=100, items_processed=0)
        stats.items_skipped["filtered"] = 100
        assert stats.skip_rate == 100.0

    def test_skip_rate_partial(self) -> None:
        """Test skip rate with some items skipped."""
        stats = ComponentStats(items_total=100, items_processed=70)
        stats.items_skipped["autodoc"] = 20
        stats.items_skipped["draft"] = 10
        assert stats.skip_rate == 30.0

    def test_total_skipped(self) -> None:
        """Test total_skipped property."""
        stats = ComponentStats()
        stats.items_skipped["autodoc"] = 20
        stats.items_skipped["draft"] = 10
        stats.items_skipped["filtered"] = 5
        assert stats.total_skipped == 35

    def test_format_summary_empty(self) -> None:
        """Test format_summary with no data."""
        stats = ComponentStats()
        assert stats.format_summary() == "(no data)"
        assert stats.format_summary("Test") == "Test: (no data)"

    def test_format_summary_processing_only(self) -> None:
        """Test format_summary with only processing stats."""
        stats = ComponentStats(items_total=100, items_processed=80)
        result = stats.format_summary()
        assert result == "processed=80/100"

    def test_format_summary_with_name(self) -> None:
        """Test format_summary with component name."""
        stats = ComponentStats(items_total=100, items_processed=80)
        result = stats.format_summary("Directives")
        assert result == "Directives: processed=80/100"

    def test_format_summary_with_skipped(self) -> None:
        """Test format_summary with skip breakdown."""
        stats = ComponentStats(items_total=100, items_processed=70)
        stats.items_skipped["autodoc"] = 20
        stats.items_skipped["draft"] = 10
        result = stats.format_summary()
        assert "processed=70/100" in result
        assert "skipped=[" in result
        assert "autodoc=20" in result
        assert "draft=10" in result

    def test_format_summary_with_cache(self) -> None:
        """Test format_summary with cache stats."""
        stats = ComponentStats(items_total=100, items_processed=100, cache_hits=80, cache_misses=20)
        result = stats.format_summary()
        assert "processed=100/100" in result
        assert "cache=80/100 (80%)" in result

    def test_format_summary_with_timings(self) -> None:
        """Test format_summary with sub-timings."""
        stats = ComponentStats(items_total=100, items_processed=100)
        stats.sub_timings["analyze"] = 150.5
        stats.sub_timings["render"] = 800.3
        result = stats.format_summary()
        assert "timings=[" in result
        assert "analyze=150ms" in result  # Rounded
        assert "render=800ms" in result

    def test_format_summary_with_metrics(self) -> None:
        """Test format_summary with custom metrics."""
        stats = ComponentStats(items_total=100, items_processed=100)
        stats.metrics["pages_per_sec"] = 375
        stats.metrics["total_links"] = 2500
        result = stats.format_summary()
        assert "metrics=[" in result
        assert "pages_per_sec=375" in result
        assert "total_links=2500" in result

    def test_format_summary_full(self) -> None:
        """Test format_summary with all data types."""
        stats = ComponentStats(
            items_total=776,
            items_processed=115,
            cache_hits=115,
            cache_misses=0,
        )
        stats.items_skipped["no_path"] = 228
        stats.items_skipped["autodoc"] = 433
        stats.sub_timings["analyze"] = 64
        stats.sub_timings["rendering"] = 800
        stats.metrics["directives"] = 450

        result = stats.format_summary("Directives")
        expected_parts = [
            "Directives:",
            "processed=115/776",
            "skipped=[",
            "no_path=228",
            "autodoc=433",
            "cache=115/115 (100%)",
            "timings=[",
            "analyze=64ms",
            "rendering=800ms",
            "metrics=[",
            "directives=450",
        ]
        for part in expected_parts:
            assert part in result, f"Expected '{part}' in '{result}'"

    def test_to_log_context_basic(self) -> None:
        """Test to_log_context returns flat dict."""
        stats = ComponentStats(
            items_total=100,
            items_processed=80,
            cache_hits=75,
            cache_misses=25,
        )

        ctx = stats.to_log_context()

        assert ctx["items_total"] == 100
        assert ctx["items_processed"] == 80
        assert ctx["cache_hits"] == 75
        assert ctx["cache_misses"] == 25
        assert ctx["cache_hit_rate"] == 75.0
        assert ctx["skip_rate"] == 0.0

    def test_to_log_context_with_skipped(self) -> None:
        """Test to_log_context flattens skipped reasons."""
        stats = ComponentStats(items_total=100)
        stats.items_skipped["autodoc"] = 50
        stats.items_skipped["draft"] = 10

        ctx = stats.to_log_context()

        assert ctx["skipped_autodoc"] == 50
        assert ctx["skipped_draft"] == 10

    def test_to_log_context_with_timings(self) -> None:
        """Test to_log_context flattens sub-timings."""
        stats = ComponentStats(items_total=100)
        stats.sub_timings["analyze"] = 150.5
        stats.sub_timings["render"] = 800.3

        ctx = stats.to_log_context()

        assert ctx["timing_analyze_ms"] == 150.5
        assert ctx["timing_render_ms"] == 800.3

    def test_to_log_context_with_metrics(self) -> None:
        """Test to_log_context flattens custom metrics."""
        stats = ComponentStats(items_total=100)
        stats.metrics["pages_per_sec"] = 375
        stats.metrics["status"] = "success"

        ctx = stats.to_log_context()

        assert ctx["metric_pages_per_sec"] == 375
        assert ctx["metric_status"] == "success"


class TestHasStatsProtocol:
    """Tests for HasStats protocol compliance."""

    def test_class_with_stats_is_has_stats(self) -> None:
        """Test that a class with last_stats attribute satisfies HasStats."""

        class ValidatorWithStats:
            last_stats: ComponentStats | None = None

        validator = ValidatorWithStats()
        validator.last_stats = ComponentStats(items_total=100)

        assert isinstance(validator, HasStats)

    def test_class_without_stats_is_not_has_stats(self) -> None:
        """Test that a class without last_stats doesn't satisfy HasStats."""

        class ValidatorWithoutStats:
            pass

        validator = ValidatorWithoutStats()
        assert not isinstance(validator, HasStats)


class TestFormatPhaseStats:
    """Tests for format_phase_stats helper function."""

    def test_fast_phase_returns_none(self) -> None:
        """Test that fast phases don't show stats."""

        class MockComponent:
            last_stats = ComponentStats(items_total=100, items_processed=100)

        result = format_phase_stats("Test", 500, MockComponent())
        assert result is None

    def test_slow_phase_with_stats_returns_formatted(self) -> None:
        """Test that slow phases with stats show formatted output."""

        class MockComponent:
            last_stats = ComponentStats(items_total=100, items_processed=80)

        result = format_phase_stats("Test", 1500, MockComponent())
        assert result is not None
        assert "processed=80/100" in result
        assert "Test:" in result

    def test_slow_phase_without_component_returns_none(self) -> None:
        """Test that slow phases without component return None."""
        result = format_phase_stats("Test", 1500, None)
        assert result is None

    def test_slow_phase_without_stats_returns_none(self) -> None:
        """Test that slow phases with None stats return None."""

        class MockComponent:
            last_stats = None

        result = format_phase_stats("Test", 1500, MockComponent())
        assert result is None

    def test_custom_threshold(self) -> None:
        """Test custom slow threshold."""

        class MockComponent:
            last_stats = ComponentStats(items_total=100, items_processed=100)

        # 500ms is slow with 200ms threshold
        result = format_phase_stats("Test", 500, MockComponent(), slow_threshold_ms=200)
        assert result is not None

        # 500ms is fast with 1000ms threshold
        result = format_phase_stats("Test", 500, MockComponent(), slow_threshold_ms=1000)
        assert result is None

