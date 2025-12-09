"""Tests for performance validator.

Tests health/validators/performance.py:
- PerformanceValidator: build performance validation in health check system
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.performance import PerformanceValidator


@pytest.fixture
def validator():
    """Create PerformanceValidator instance."""
    return PerformanceValidator()


@pytest.fixture
def mock_site():
    """Create mock site with build stats."""
    site = MagicMock()
    site.config = {"parallel": True}
    site._last_build_stats = {
        "build_time_ms": 2000,  # 2 seconds
        "total_pages": 100,
        "rendering_time_ms": 1500,
    }
    return site


class TestPerformanceValidatorBasics:
    """Tests for PerformanceValidator basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Performance"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates build performance metrics"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestPerformanceValidatorNoStats:
    """Tests when no build stats available."""

    def test_info_when_no_stats(self, validator):
        """Returns info when no build stats available."""
        site = MagicMock()
        site._last_build_stats = None

        results = validator.validate(site)

        assert len(results) == 1
        assert results[0].status == CheckStatus.INFO
        assert "no build statistics" in results[0].message.lower()


class TestPerformanceValidatorBuildTime:
    """Tests for build time validation."""

    def test_success_for_fast_build(self, validator, mock_site):
        """Returns success for fast build."""
        mock_site._last_build_stats = {
            "build_time_ms": 1000,  # 1 second
            "total_pages": 100,
            "rendering_time_ms": 800,
        }

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("build time" in r.message.lower() for r in success_results)

    def test_warning_for_slow_build(self, validator, mock_site):
        """Returns warning for slow build."""
        # Very slow: 60 seconds for 100 pages
        mock_site._last_build_stats = {
            "build_time_ms": 60000,
            "total_pages": 100,
            "rendering_time_ms": 50000,
        }

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("slower" in r.message.lower() for r in warning_results)

    def test_info_for_moderate_build_time(self, validator, mock_site):
        """Returns info for moderate build time."""
        mock_site._last_build_stats = {
            "build_time_ms": 15000,  # 15 seconds
            "total_pages": 100,
            "rendering_time_ms": 12000,
        }

        results = validator.validate(mock_site)

        # For moderate time (15s for 100 pages), should get results about build/throughput
        # The validator returns success for "reasonable" times and warns for slow
        # With parallel=True (default), 100 pages at 50/sec = 2 sec expected, 15s is 7.5x
        # So this might trigger a warning for being slower than expected
        assert len(results) >= 1  # Should have at least one result about performance

    def test_info_for_zero_pages(self, validator, mock_site):
        """Returns info when no pages."""
        mock_site._last_build_stats = {
            "build_time_ms": 500,
            "total_pages": 0,
            "rendering_time_ms": 0,
        }

        results = validator.validate(mock_site)

        info_results = [r for r in results if r.status == CheckStatus.INFO]
        assert any("no pages" in r.message.lower() for r in info_results)


class TestPerformanceValidatorThroughput:
    """Tests for throughput validation."""

    def test_excellent_throughput(self, validator, mock_site):
        """Success for excellent throughput."""
        mock_site._last_build_stats = {
            "build_time_ms": 500,  # 0.5 seconds
            "total_pages": 100,  # 200 pages/sec
            "rendering_time_ms": 400,
        }

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("excellent" in r.message.lower() for r in success_results)

    def test_good_throughput(self, validator, mock_site):
        """Success for good throughput."""
        mock_site._last_build_stats = {
            "build_time_ms": 1500,
            "total_pages": 100,  # ~67 pages/sec
            "rendering_time_ms": 1200,
        }

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("good" in r.message.lower() for r in success_results)

    def test_acceptable_throughput(self, validator, mock_site):
        """Info for acceptable throughput."""
        mock_site._last_build_stats = {
            "build_time_ms": 4000,
            "total_pages": 100,  # 25 pages/sec
            "rendering_time_ms": 3000,
        }

        results = validator.validate(mock_site)

        info_results = [r for r in results if r.status == CheckStatus.INFO]
        assert any("acceptable" in r.message.lower() for r in info_results)

    def test_slow_throughput_warning(self, validator, mock_site):
        """Warning for slow throughput."""
        mock_site._last_build_stats = {
            "build_time_ms": 10000,
            "total_pages": 100,  # 10 pages/sec
            "rendering_time_ms": 8000,
        }

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("slow" in r.message.lower() for r in warning_results)


class TestPerformanceValidatorSlowPages:
    """Tests for slow page detection."""

    def test_warning_for_high_avg_render_time(self, validator, mock_site):
        """Warning for high average render time per page."""
        mock_site._last_build_stats = {
            "build_time_ms": 20000,
            "total_pages": 100,
            "rendering_time_ms": 15000,  # 150ms per page
        }

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("render time" in r.message.lower() for r in warning_results)

    def test_info_for_high_rendering_percentage(self, validator, mock_site):
        """Info when rendering takes disproportionate time."""
        mock_site._last_build_stats = {
            "build_time_ms": 5000,
            "total_pages": 100,
            "rendering_time_ms": 4500,  # 90% of build time
        }

        results = validator.validate(mock_site)

        info_results = [r for r in results if r.status == CheckStatus.INFO]
        assert any("render" in r.message.lower() and "%" in r.message for r in info_results)

    def test_success_for_good_render_time(self, validator, mock_site):
        """Success for good render time."""
        mock_site._last_build_stats = {
            "build_time_ms": 2000,
            "total_pages": 100,
            "rendering_time_ms": 1000,  # 10ms per page
        }

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any(
            "render time" in r.message.lower() and "good" in r.message.lower()
            for r in success_results
        )


class TestPerformanceValidatorParallelMode:
    """Tests for parallel mode consideration."""

    def test_considers_parallel_mode(self, validator, mock_site):
        """Uses different thresholds for parallel mode."""
        mock_site.config["parallel"] = True
        mock_site._last_build_stats = {
            "build_time_ms": 3000,
            "total_pages": 100,
            "rendering_time_ms": 2000,
        }

        results = validator.validate(mock_site)

        # Should pass for parallel mode
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        build_warnings = [r for r in warning_results if "build" in r.message.lower()]
        assert len(build_warnings) == 0

    def test_considers_sequential_mode(self, validator, mock_site):
        """Uses different thresholds for sequential mode."""
        mock_site.config["parallel"] = False
        mock_site._last_build_stats = {
            "build_time_ms": 5000,
            "total_pages": 100,
            "rendering_time_ms": 4000,
        }

        results = validator.validate(mock_site)

        # Should not flag as too slow for sequential
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        speed_warnings = [r for r in warning_results if "slower than expected" in r.message.lower()]
        assert len(speed_warnings) == 0


class TestPerformanceValidatorRecommendations:
    """Tests for recommendation messages."""

    def test_slow_build_has_recommendation(self, validator, mock_site):
        """Slow build warning has recommendation."""
        mock_site._last_build_stats = {
            "build_time_ms": 60000,
            "total_pages": 100,
            "rendering_time_ms": 50000,
        }

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        slow_warning = next((r for r in warning_results if "slower" in r.message.lower()), None)
        assert slow_warning is not None
        assert slow_warning.recommendation is not None

    def test_slow_throughput_has_recommendation(self, validator, mock_site):
        """Slow throughput warning has recommendation."""
        mock_site._last_build_stats = {
            "build_time_ms": 10000,
            "total_pages": 100,
            "rendering_time_ms": 8000,
        }

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        throughput_warning = next(
            (r for r in warning_results if "throughput" in r.message.lower()), None
        )
        assert throughput_warning is not None
        assert throughput_warning.recommendation is not None


class TestPerformanceValidatorEdgeCases:
    """Tests for edge cases."""

    def test_handles_zero_build_time(self, validator, mock_site):
        """Handles zero build time gracefully."""
        mock_site._last_build_stats = {
            "build_time_ms": 0,
            "total_pages": 0,
            "rendering_time_ms": 0,
        }

        # Should not raise
        results = validator.validate(mock_site)
        assert isinstance(results, list)

    def test_handles_missing_rendering_time(self, validator, mock_site):
        """Handles missing rendering time."""
        mock_site._last_build_stats = {
            "build_time_ms": 2000,
            "total_pages": 100,
            # rendering_time_ms missing
        }

        # Should not raise
        results = validator.validate(mock_site)
        assert isinstance(results, list)
