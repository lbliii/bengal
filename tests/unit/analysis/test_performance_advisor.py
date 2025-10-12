"""
Tests for performance advisor and intelligent suggestions.
"""

import pytest

from bengal.analysis.performance_advisor import (
    PerformanceAdvisor,
    PerformanceGrade,
    SuggestionPriority,
    SuggestionType,
    analyze_build,
)
from bengal.utils.build_stats import BuildStats


@pytest.fixture
def fast_build_stats():
    """Create stats for a fast build."""
    stats = BuildStats()
    stats.total_pages = 50
    stats.regular_pages = 40
    stats.generated_pages = 10
    stats.total_assets = 20
    stats.build_time_ms = 500  # 0.5s
    stats.discovery_time_ms = 50
    stats.taxonomy_time_ms = 50
    stats.rendering_time_ms = 200
    stats.assets_time_ms = 100
    stats.postprocess_time_ms = 100
    stats.parallel = True
    stats.incremental = False
    return stats


@pytest.fixture
def slow_build_stats():
    """Create stats for a slow build."""
    stats = BuildStats()
    stats.total_pages = 200
    stats.regular_pages = 150
    stats.generated_pages = 50
    stats.total_assets = 100
    stats.build_time_ms = 10000  # 10s
    stats.discovery_time_ms = 500
    stats.taxonomy_time_ms = 500
    stats.rendering_time_ms = 7000  # Major bottleneck
    stats.assets_time_ms = 1000
    stats.postprocess_time_ms = 1000
    stats.parallel = False  # Not using parallel!
    stats.incremental = False
    return stats


@pytest.fixture
def balanced_build_stats():
    """Create stats for a well-balanced build."""
    stats = BuildStats()
    stats.total_pages = 100
    stats.regular_pages = 80
    stats.generated_pages = 20
    stats.total_assets = 50
    stats.build_time_ms = 1000
    stats.discovery_time_ms = 200
    stats.taxonomy_time_ms = 200
    stats.rendering_time_ms = 200
    stats.assets_time_ms = 200
    stats.postprocess_time_ms = 200
    stats.parallel = True
    stats.incremental = True
    return stats


class TestPerformanceGrade:
    """Test performance grade calculation."""

    def test_excellent_grade(self, fast_build_stats):
        """Test calculation of excellent grade."""
        grade = PerformanceGrade.calculate(fast_build_stats)

        assert grade.grade == "A"
        assert grade.score >= 90
        assert grade.category == "Excellent"
        assert "excellent" in grade.summary.lower()

    def test_poor_grade(self, slow_build_stats):
        """Test calculation of poor grade."""
        grade = PerformanceGrade.calculate(slow_build_stats)

        assert grade.grade in ["D", "F"]
        assert grade.score < 60
        assert grade.category in ["Poor", "Critical"]

    def test_good_grade(self, balanced_build_stats):
        """Test calculation of good grade."""
        grade = PerformanceGrade.calculate(balanced_build_stats)

        # Should be good because it's well-balanced and fast
        assert grade.score >= 75
        assert grade.category in ["Good", "Excellent"]

    def test_bottleneck_penalty(self):
        """Test that bottlenecks reduce score."""
        stats = BuildStats()
        stats.total_pages = 100
        stats.build_time_ms = 1000
        stats.discovery_time_ms = 100
        stats.taxonomy_time_ms = 100
        stats.rendering_time_ms = 700  # 70% - clear bottleneck
        stats.assets_time_ms = 50
        stats.postprocess_time_ms = 50
        stats.parallel = True

        grade = PerformanceGrade.calculate(stats)

        # Score should be penalized for bottleneck
        assert grade.score < 90


class TestPerformanceAdvisor:
    """Test performance advisor and suggestions."""

    def test_initialization(self, fast_build_stats):
        """Test advisor initialization."""
        advisor = PerformanceAdvisor(fast_build_stats)

        assert advisor.stats == fast_build_stats
        assert advisor.environment == {}
        assert advisor.suggestions == []

    def test_initialization_with_environment(self, fast_build_stats):
        """Test advisor initialization with environment info."""
        env = {"cpu_cores": 8, "is_ci": False}
        advisor = PerformanceAdvisor(fast_build_stats, environment=env)

        assert advisor.environment == env

    def test_parallel_suggestion_when_not_used(self, slow_build_stats):
        """Test that parallel build is suggested when not used."""
        advisor = PerformanceAdvisor(slow_build_stats)
        suggestions = advisor.analyze()

        # Should suggest enabling parallel
        parallel_suggestions = [s for s in suggestions if s.type == SuggestionType.PARALLEL]
        assert len(parallel_suggestions) > 0

        suggestion = parallel_suggestions[0]
        assert "parallel" in suggestion.title.lower()
        assert suggestion.priority in [SuggestionPriority.HIGH, SuggestionPriority.MEDIUM]

    def test_incremental_suggestion_when_not_used(self, slow_build_stats):
        """Test that incremental builds are suggested."""
        advisor = PerformanceAdvisor(slow_build_stats)
        suggestions = advisor.analyze()

        # Should suggest incremental builds
        incremental_suggestions = [s for s in suggestions if s.type == SuggestionType.CACHING]
        assert len(incremental_suggestions) > 0

        suggestion = incremental_suggestions[0]
        assert "incremental" in suggestion.title.lower()

    def test_rendering_bottleneck_detection(self):
        """Test detection of rendering bottleneck."""
        # Create a build with slow template rendering
        stats = BuildStats()
        stats.total_pages = 100
        stats.regular_pages = 100
        stats.build_time_ms = 8000
        stats.discovery_time_ms = 500
        stats.taxonomy_time_ms = 500
        stats.rendering_time_ms = 6000  # 60ms per page (slow!)
        stats.assets_time_ms = 500
        stats.postprocess_time_ms = 500
        stats.parallel = True  # Already using parallel

        advisor = PerformanceAdvisor(stats)
        suggestions = advisor.analyze()

        # Should detect rendering bottleneck (75% of time + >50ms per page)
        template_suggestions = [s for s in suggestions if s.type == SuggestionType.TEMPLATES]
        assert len(template_suggestions) > 0

        suggestion = template_suggestions[0]
        assert suggestion.priority == SuggestionPriority.HIGH
        assert (
            "template" in suggestion.title.lower()
            or "rendering" in suggestion.title.lower()
            or "optimize" in suggestion.title.lower()
        )

    def test_get_bottleneck(self, slow_build_stats):
        """Test bottleneck identification."""
        advisor = PerformanceAdvisor(slow_build_stats)
        bottleneck = advisor.get_bottleneck()

        assert bottleneck == "Rendering"  # 70% of time

    def test_no_bottleneck_when_balanced(self, balanced_build_stats):
        """Test that no bottleneck is reported for balanced builds."""
        advisor = PerformanceAdvisor(balanced_build_stats)
        bottleneck = advisor.get_bottleneck()

        assert bottleneck is None  # All phases are 20% each

    def test_get_top_suggestions(self, slow_build_stats):
        """Test getting top N suggestions."""
        advisor = PerformanceAdvisor(slow_build_stats)
        advisor.analyze()

        top_3 = advisor.get_top_suggestions(3)

        assert len(top_3) <= 3
        # Should be sorted by priority (high first)
        if len(top_3) >= 2:
            # Check priority ordering
            priority_values = {
                SuggestionPriority.HIGH: 0,
                SuggestionPriority.MEDIUM: 1,
                SuggestionPriority.LOW: 2,
            }
            for i in range(len(top_3) - 1):
                assert priority_values[top_3[i].priority] <= priority_values[top_3[i + 1].priority]

    def test_skipped_build_analysis(self):
        """Test that skipped builds return no suggestions."""
        stats = BuildStats()
        stats.skipped = True

        advisor = PerformanceAdvisor(stats)
        suggestions = advisor.analyze()

        assert suggestions == []

    def test_memory_usage_suggestion(self):
        """Test memory usage suggestions for high memory builds."""
        stats = BuildStats()
        stats.total_pages = 1000
        stats.build_time_ms = 5000
        stats.memory_peak_mb = 1500  # 1.5GB peak memory
        stats.rendering_time_ms = 2000
        stats.discovery_time_ms = 1000
        stats.taxonomy_time_ms = 1000
        stats.assets_time_ms = 500
        stats.postprocess_time_ms = 500
        stats.parallel = True

        advisor = PerformanceAdvisor(stats)
        suggestions = advisor.analyze()

        # Should suggest memory optimization
        memory_suggestions = [s for s in suggestions if s.type == SuggestionType.MEMORY]
        assert len(memory_suggestions) > 0

        suggestion = memory_suggestions[0]
        assert "memory" in suggestion.title.lower()

    def test_format_summary(self, slow_build_stats):
        """Test summary formatting."""
        advisor = PerformanceAdvisor(slow_build_stats)
        advisor.analyze()

        summary = advisor.format_summary()

        assert "Performance Grade:" in summary
        assert "Bottleneck:" in summary
        assert "Top Suggestions:" in summary


class TestConvenienceFunction:
    """Test convenience function."""

    def test_analyze_build(self, slow_build_stats):
        """Test quick analysis function."""
        advisor = analyze_build(slow_build_stats)

        assert isinstance(advisor, PerformanceAdvisor)
        assert len(advisor.suggestions) > 0  # Analysis was run (slow build should have suggestions)

    def test_analyze_build_with_environment(self, fast_build_stats):
        """Test analysis with environment info."""
        env = {"cpu_cores": 16}
        advisor = analyze_build(fast_build_stats, environment=env)

        assert advisor.environment == env


class TestSuggestionFormatting:
    """Test suggestion string formatting."""

    def test_suggestion_str_high_priority(self):
        """Test high priority suggestion formatting."""
        from bengal.analysis.performance_advisor import PerformanceSuggestion

        suggestion = PerformanceSuggestion(
            type=SuggestionType.PARALLEL,
            priority=SuggestionPriority.HIGH,
            title="Enable parallel rendering",
            description="Your pages are rendered sequentially",
            impact="Could save 5s",
            action="Run: bengal build --parallel",
        )

        str_repr = str(suggestion)
        assert "🔥" in str_repr
        assert "Enable parallel rendering" in str_repr

    def test_suggestion_str_medium_priority(self):
        """Test medium priority suggestion formatting."""
        from bengal.analysis.performance_advisor import PerformanceSuggestion

        suggestion = PerformanceSuggestion(
            type=SuggestionType.CACHING,
            priority=SuggestionPriority.MEDIUM,
            title="Try incremental builds",
            description="Rebuild only changed files",
            impact="Could save 2s",
            action="Run: bengal build --incremental",
        )

        str_repr = str(suggestion)
        assert "💡" in str_repr
        assert "Try incremental builds" in str_repr

    def test_suggestion_str_low_priority(self):
        """Test low priority suggestion formatting."""
        from bengal.analysis.performance_advisor import PerformanceSuggestion

        suggestion = PerformanceSuggestion(
            type=SuggestionType.OPTIMIZATION,
            priority=SuggestionPriority.LOW,
            title="Consider code splitting",
            description="Reduce bundle size",
            impact="Minor improvement",
            action="Review asset bundling config",
        )

        str_repr = str(suggestion)
        assert "ℹ️" in str_repr
        assert "Consider code splitting" in str_repr
