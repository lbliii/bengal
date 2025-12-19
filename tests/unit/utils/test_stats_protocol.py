"""
Tests for stats protocol compliance.

Verifies that BuildStats and MinimalStats both correctly implement
the DisplayableStats protocol, ensuring type safety and compatibility
with display_build_stats().

Related:
    - bengal/utils/stats_protocol.py: Protocol definitions
    - bengal/utils/stats_minimal.py: MinimalStats implementation
    - bengal/utils/build_stats.py: BuildStats implementation
"""

from __future__ import annotations

from bengal.server.build_executor import BuildResult
from bengal.utils.build_stats import BuildStats
from bengal.utils.stats_minimal import MinimalStats
from bengal.utils.stats_protocol import CoreStats, DisplayableStats


class TestCoreStatsProtocol:
    """Tests for CoreStats protocol compliance."""

    def test_build_stats_implements_core_stats(self) -> None:
        """BuildStats must implement CoreStats protocol."""
        stats = BuildStats()
        assert isinstance(stats, CoreStats)

    def test_minimal_stats_implements_core_stats(self) -> None:
        """MinimalStats must implement CoreStats protocol."""
        stats = MinimalStats(total_pages=10, build_time_ms=100.0, incremental=True)
        assert isinstance(stats, CoreStats)

    def test_core_stats_attributes_accessible(self) -> None:
        """CoreStats attributes must be accessible on implementations."""
        stats = MinimalStats(total_pages=42, build_time_ms=123.5, incremental=False)

        assert stats.total_pages == 42
        assert stats.build_time_ms == 123.5
        assert stats.incremental is False


class TestDisplayableStatsProtocol:
    """Tests for DisplayableStats protocol compliance."""

    def test_build_stats_implements_displayable_stats(self) -> None:
        """BuildStats must implement DisplayableStats protocol."""
        stats = BuildStats()
        assert isinstance(stats, DisplayableStats)

    def test_minimal_stats_implements_displayable_stats(self) -> None:
        """MinimalStats must implement DisplayableStats protocol."""
        stats = MinimalStats(total_pages=10, build_time_ms=100.0, incremental=True)
        assert isinstance(stats, DisplayableStats)

    def test_displayable_stats_all_attributes_accessible(self) -> None:
        """All DisplayableStats attributes must be accessible."""
        stats = MinimalStats(total_pages=50, build_time_ms=500.0, incremental=True)

        # Core counts
        assert hasattr(stats, "total_pages")
        assert hasattr(stats, "regular_pages")
        assert hasattr(stats, "generated_pages")
        assert hasattr(stats, "total_assets")
        assert hasattr(stats, "total_sections")
        assert hasattr(stats, "taxonomies_count")
        assert hasattr(stats, "total_directives")
        assert hasattr(stats, "directives_by_type")

        # Flags
        assert hasattr(stats, "build_time_ms")
        assert hasattr(stats, "incremental")
        assert hasattr(stats, "parallel")
        assert hasattr(stats, "skipped")

        # Warnings
        assert hasattr(stats, "warnings")

        # Phase timings
        assert hasattr(stats, "discovery_time_ms")
        assert hasattr(stats, "taxonomy_time_ms")
        assert hasattr(stats, "rendering_time_ms")
        assert hasattr(stats, "assets_time_ms")
        assert hasattr(stats, "postprocess_time_ms")
        assert hasattr(stats, "health_check_time_ms")


class TestMinimalStatsFactory:
    """Tests for MinimalStats.from_build_result factory."""

    def test_from_build_result_extracts_pages(self) -> None:
        """Factory should extract pages_built from BuildResult."""
        result = BuildResult(success=True, pages_built=100, build_time_ms=250.0)
        stats = MinimalStats.from_build_result(result)

        assert stats.total_pages == 100
        assert stats.regular_pages == 100

    def test_from_build_result_extracts_build_time(self) -> None:
        """Factory should extract build_time_ms from BuildResult."""
        result = BuildResult(success=True, pages_built=50, build_time_ms=123.456)
        stats = MinimalStats.from_build_result(result)

        assert stats.build_time_ms == 123.456

    def test_from_build_result_sets_incremental_flag(self) -> None:
        """Factory should set incremental flag from parameter."""
        result = BuildResult(success=True, pages_built=10, build_time_ms=100.0)

        stats_inc = MinimalStats.from_build_result(result, incremental=True)
        assert stats_inc.incremental is True

        stats_full = MinimalStats.from_build_result(result, incremental=False)
        assert stats_full.incremental is False

    def test_from_build_result_has_sensible_defaults(self) -> None:
        """Factory should provide sensible defaults for missing data."""
        result = BuildResult(success=True, pages_built=10, build_time_ms=100.0)
        stats = MinimalStats.from_build_result(result)

        # Defaults
        assert stats.generated_pages == 0
        assert stats.total_assets == 0
        assert stats.total_sections == 0
        assert stats.taxonomies_count == 0
        assert stats.total_directives == 0
        assert stats.directives_by_type == {}
        assert stats.parallel is True
        assert stats.skipped is False
        assert stats.warnings == []

        # Timings default to 0
        assert stats.discovery_time_ms == 0.0
        assert stats.taxonomy_time_ms == 0.0
        assert stats.rendering_time_ms == 0.0
        assert stats.assets_time_ms == 0.0
        assert stats.postprocess_time_ms == 0.0
        assert stats.health_check_time_ms == 0.0

    def test_from_build_result_returns_displayable_stats(self) -> None:
        """Factory should return an object implementing DisplayableStats."""
        result = BuildResult(success=True, pages_built=10, build_time_ms=100.0)
        stats = MinimalStats.from_build_result(result)

        assert isinstance(stats, DisplayableStats)


class TestBuildStatsDisplayableCompliance:
    """Verify BuildStats has all DisplayableStats attributes."""

    def test_build_stats_has_all_required_attributes(self) -> None:
        """BuildStats must have all attributes required by DisplayableStats."""
        stats = BuildStats(
            total_pages=100,
            regular_pages=90,
            generated_pages=10,
            build_time_ms=500.0,
            incremental=True,
        )

        # These should all be accessible without AttributeError
        _ = stats.total_pages
        _ = stats.regular_pages
        _ = stats.generated_pages
        _ = stats.total_assets
        _ = stats.total_sections
        _ = stats.taxonomies_count
        _ = stats.total_directives
        _ = stats.directives_by_type
        _ = stats.build_time_ms
        _ = stats.incremental
        _ = stats.parallel
        _ = stats.skipped
        _ = stats.warnings
        _ = stats.discovery_time_ms
        _ = stats.taxonomy_time_ms
        _ = stats.rendering_time_ms
        _ = stats.assets_time_ms
        _ = stats.postprocess_time_ms
        _ = stats.health_check_time_ms
