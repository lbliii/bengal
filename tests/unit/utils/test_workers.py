"""
Tests for bengal.utils.workers module.

Tests the unified worker auto-tune utility including:
- Environment detection
- Worker count calculation
- Parallelization decisions
- Page weight estimation
- Complexity ordering
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from bengal.utils.concurrency.workers import (
    Environment,
    WorkloadProfile,
    WorkloadType,
    detect_environment,
    estimate_page_weight,
    get_optimal_workers,
    get_profile,
    order_by_complexity,
    should_parallelize,
)


def _make_page_mock(raw_content: str, metadata: dict | None = None) -> MagicMock:
    """
    Create a properly configured page mock for estimate_page_weight tests.
    
    MagicMock auto-creates attributes, so hasattr(mock, "_source") is always True.
    The estimate_page_weight function checks _source first, then _raw_content.
    We set _source to the content so it works correctly.
    """
    page = MagicMock()
    # Set _source to the content (estimate_page_weight checks _source first)
    page._source = raw_content
    page._raw_content = raw_content
    page.metadata = metadata if metadata is not None else {}
    return page


class TestDetectEnvironment:
    """Test environment auto-detection."""

    def test_explicit_override_production(self) -> None:
        """BENGAL_ENV=production takes precedence."""
        with patch.dict(os.environ, {"BENGAL_ENV": "production"}, clear=True):
            assert detect_environment() == Environment.PRODUCTION

    def test_explicit_override_ci(self) -> None:
        """BENGAL_ENV=ci takes precedence over CI env vars."""
        with patch.dict(os.environ, {"BENGAL_ENV": "ci", "CI": "false"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_explicit_override_local(self) -> None:
        """BENGAL_ENV=local takes precedence."""
        with patch.dict(os.environ, {"BENGAL_ENV": "local", "CI": "true"}, clear=True):
            assert detect_environment() == Environment.LOCAL

    def test_github_actions_detection(self) -> None:
        """Detects GitHub Actions environment."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_gitlab_ci_detection(self) -> None:
        """Detects GitLab CI environment."""
        with patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_generic_ci_detection(self) -> None:
        """Detects generic CI environment variable."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_circleci_detection(self) -> None:
        """Detects CircleCI environment."""
        with patch.dict(os.environ, {"CIRCLECI": "true"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_travis_detection(self) -> None:
        """Detects Travis CI environment."""
        with patch.dict(os.environ, {"TRAVIS": "true"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_jenkins_detection(self) -> None:
        """Detects Jenkins environment."""
        with patch.dict(os.environ, {"JENKINS_URL": "http://jenkins.example.com"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_buildkite_detection(self) -> None:
        """Detects Buildkite environment."""
        with patch.dict(os.environ, {"BUILDKITE": "true"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_aws_codebuild_detection(self) -> None:
        """Detects AWS CodeBuild environment."""
        with patch.dict(os.environ, {"CODEBUILD_BUILD_ID": "abc123"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_azure_pipelines_detection(self) -> None:
        """Detects Azure Pipelines environment."""
        with patch.dict(os.environ, {"TF_BUILD": "True"}, clear=True):
            assert detect_environment() == Environment.CI

    def test_default_to_local(self) -> None:
        """Defaults to LOCAL when no CI indicators present."""
        with patch.dict(os.environ, {}, clear=True):
            assert detect_environment() == Environment.LOCAL

    def test_case_insensitive_bengal_env(self) -> None:
        """BENGAL_ENV is case-insensitive."""
        with patch.dict(os.environ, {"BENGAL_ENV": "PRODUCTION"}, clear=True):
            assert detect_environment() == Environment.PRODUCTION

        with patch.dict(os.environ, {"BENGAL_ENV": "CI"}, clear=True):
            assert detect_environment() == Environment.CI


class TestGetOptimalWorkers:
    """Test worker count calculation."""

    def test_user_override_respected(self) -> None:
        """User config_override bypasses auto-tune."""
        result = get_optimal_workers(100, config_override=16)
        assert result == 16

    def test_user_override_zero_ignored(self) -> None:
        """config_override=0 is treated as no override."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_optimal_workers(
                100,
                config_override=0,
                workload_type=WorkloadType.CPU_BOUND,
                environment=Environment.LOCAL,
            )
            # Should auto-tune, not return 0
            assert result >= 1

    def test_user_override_negative_ignored(self) -> None:
        """Negative config_override is ignored."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_optimal_workers(
                100,
                config_override=-1,
                workload_type=WorkloadType.CPU_BOUND,
                environment=Environment.LOCAL,
            )
            assert result >= 1

    def test_ci_caps_cpu_bound(self) -> None:
        """CI mode caps CPU-bound workers at 2."""
        result = get_optimal_workers(
            100,
            workload_type=WorkloadType.CPU_BOUND,
            environment=Environment.CI,
        )
        assert result <= 2

    def test_ci_caps_mixed(self) -> None:
        """CI mode caps mixed workers at 2."""
        result = get_optimal_workers(
            100,
            workload_type=WorkloadType.MIXED,
            environment=Environment.CI,
        )
        assert result <= 2

    def test_ci_io_bound_more_workers(self) -> None:
        """CI mode allows more workers for I/O-bound work."""
        result = get_optimal_workers(
            100,
            workload_type=WorkloadType.IO_BOUND,
            environment=Environment.CI,
        )
        assert result <= 4  # I/O-bound can use up to 4 in CI

    def test_never_more_workers_than_tasks(self) -> None:
        """Worker count never exceeds task count."""
        result = get_optimal_workers(
            3,
            workload_type=WorkloadType.IO_BOUND,
            environment=Environment.PRODUCTION,  # Would normally allow 10
        )
        assert result <= 3

    def test_minimum_one_worker(self) -> None:
        """Always returns at least 1 worker."""
        result = get_optimal_workers(0)
        assert result >= 1

    def test_task_weight_increases_effective_tasks(self) -> None:
        """task_weight > 1 allows more workers for heavy tasks."""
        # With weight=1, 3 tasks caps at 3 workers
        result_normal = get_optimal_workers(
            3,
            workload_type=WorkloadType.IO_BOUND,
            environment=Environment.PRODUCTION,
            task_weight=1.0,
        )
        # With weight=3, 3 tasks -> 9 effective tasks
        result_weighted = get_optimal_workers(
            3,
            workload_type=WorkloadType.IO_BOUND,
            environment=Environment.PRODUCTION,
            task_weight=3.0,
        )
        assert result_weighted >= result_normal

    def test_local_cpu_bound_moderate_workers(self) -> None:
        """Local CPU-bound uses moderate workers."""
        with patch("os.cpu_count", return_value=12):
            result = get_optimal_workers(
                100,
                workload_type=WorkloadType.CPU_BOUND,
                environment=Environment.LOCAL,
            )
            # 50% of 12 cores = 6, but capped at max_workers=4
            assert result <= 4
            assert result >= 2

    def test_production_allows_more_workers(self) -> None:
        """Production environment allows more workers."""
        with patch("os.cpu_count", return_value=16):
            result = get_optimal_workers(
                200,
                workload_type=WorkloadType.IO_BOUND,
                environment=Environment.PRODUCTION,
            )
            # 75% of 16 = 12, capped at max_workers=10
            assert result <= 10
            assert result >= 2

    def test_auto_detects_environment(self) -> None:
        """Auto-detects environment when not specified."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            result = get_optimal_workers(100, workload_type=WorkloadType.CPU_BOUND)
            assert result <= 2  # CI caps at 2


class TestShouldParallelize:
    """Test parallelization decision logic."""

    def test_below_threshold_returns_false_cpu_bound(self) -> None:
        """Below CPU-bound threshold (5) returns False."""
        assert not should_parallelize(
            4,
            workload_type=WorkloadType.CPU_BOUND,
            environment=Environment.LOCAL,
        )

    def test_at_threshold_returns_true_cpu_bound(self) -> None:
        """At CPU-bound threshold (5) returns True."""
        assert should_parallelize(
            5,
            workload_type=WorkloadType.CPU_BOUND,
            environment=Environment.LOCAL,
        )

    def test_above_threshold_returns_true(self) -> None:
        """Above threshold returns True."""
        assert should_parallelize(
            20,
            workload_type=WorkloadType.CPU_BOUND,
            environment=Environment.LOCAL,
        )

    def test_io_bound_higher_threshold(self) -> None:
        """I/O-bound has higher threshold (20)."""
        assert not should_parallelize(
            19,
            workload_type=WorkloadType.IO_BOUND,
            environment=Environment.LOCAL,
        )
        assert should_parallelize(
            20,
            workload_type=WorkloadType.IO_BOUND,
            environment=Environment.LOCAL,
        )

    def test_small_work_estimate_returns_false(self) -> None:
        """Small total_work_estimate (<5KB) returns False."""
        assert not should_parallelize(
            100,
            workload_type=WorkloadType.CPU_BOUND,
            total_work_estimate=1000,  # < 5000 bytes
        )

    def test_large_work_estimate_returns_true(self) -> None:
        """Large total_work_estimate (>=5KB) allows parallelization."""
        assert should_parallelize(
            100,
            workload_type=WorkloadType.CPU_BOUND,
            total_work_estimate=10000,  # >= 5000 bytes
        )

    def test_none_work_estimate_ignored(self) -> None:
        """None total_work_estimate doesn't affect decision."""
        assert should_parallelize(
            100,
            workload_type=WorkloadType.CPU_BOUND,
            total_work_estimate=None,
        )


class TestEstimatePageWeight:
    """Test page complexity estimation."""

    def test_simple_page_weight_near_one(self) -> None:
        """Simple page with minimal content has weight ~1.0."""
        page = _make_page_mock("# Simple Page\n\nJust some text.")

        weight = estimate_page_weight(page)
        assert 0.9 <= weight <= 1.1

    def test_large_content_increases_weight(self) -> None:
        """Large content (>10KB) increases weight."""
        page = _make_page_mock("x" * 30000)  # 30KB

        weight = estimate_page_weight(page)
        # (30000 - 10000) / 20000 = 1.0 additional weight
        assert weight >= 2.0

    def test_many_code_blocks_increase_weight(self) -> None:
        """Many code blocks (>5) increase weight."""
        code_blocks = "```python\ncode\n```\n" * 10  # 10 code blocks
        page = _make_page_mock(f"# Page\n\n{code_blocks}")

        weight = estimate_page_weight(page)
        # (10 - 5) * 0.1 = 0.5 additional weight
        assert weight >= 1.5

    def test_many_directives_increase_weight(self) -> None:
        """Many directives (>10) increase weight."""
        directives = ".. note::\n   Note\n\n" * 20  # 20 directives
        page = _make_page_mock(f"# Page\n\n{directives}")

        weight = estimate_page_weight(page)
        # (20 - 10) * 0.05 = 0.5 additional weight
        assert weight >= 1.4

    def test_autodoc_flag_adds_bonus(self) -> None:
        """is_autodoc metadata adds +1.0 weight bonus."""
        page = _make_page_mock("# API Reference", {"is_autodoc": True})

        weight = estimate_page_weight(page)
        assert weight >= 2.0

    def test_autodoc_key_adds_bonus(self) -> None:
        """autodoc metadata key also adds +1.0 weight bonus."""
        page = _make_page_mock("# API Reference", {"autodoc": {"module": "mymodule"}})

        weight = estimate_page_weight(page)
        assert weight >= 2.0

    def test_weight_capped_at_five(self) -> None:
        """Weight is capped at 5.0 to avoid outlier distortion."""
        # Huge content + many code blocks + many directives + autodoc
        page = _make_page_mock(
            "```\ncode\n```\n::\n" * 100 + "x" * 100000,
            {"is_autodoc": True},
        )

        weight = estimate_page_weight(page)
        assert weight == 5.0


class TestOrderByComplexity:
    """Test page ordering by complexity."""

    def test_orders_heavy_pages_first_by_default(self) -> None:
        """Heavy pages are ordered first by default (descending)."""
        light_page = _make_page_mock("# Light")
        heavy_page = _make_page_mock(
            "# Heavy\n" + "```\ncode\n```\n" * 20,
            {"is_autodoc": True},
        )
        medium_page = _make_page_mock("# Medium\n" + "x" * 15000)

        pages = [light_page, heavy_page, medium_page]
        ordered = order_by_complexity(pages)

        # Heavy should be first
        assert ordered[0] is heavy_page
        # Light should be last
        assert ordered[-1] is light_page

    def test_ascending_order_light_first(self) -> None:
        """descending=False puts light pages first."""
        light_page = _make_page_mock("# Light")
        heavy_page = _make_page_mock("x" * 50000, {"is_autodoc": True})

        pages = [heavy_page, light_page]
        ordered = order_by_complexity(pages, descending=False)

        assert ordered[0] is light_page
        assert ordered[1] is heavy_page

    def test_does_not_mutate_input(self) -> None:
        """Returns new list, does not mutate input."""
        page1 = _make_page_mock("# Page 1")
        page2 = _make_page_mock("# Page 2")

        pages = [page1, page2]
        original_order = list(pages)

        ordered = order_by_complexity(pages)

        # Original list unchanged
        assert pages == original_order
        # Returned list is different object
        assert ordered is not pages

    def test_empty_list_returns_empty(self) -> None:
        """Empty input returns empty list."""
        ordered = order_by_complexity([])
        assert ordered == []

    def test_single_page_returns_same(self) -> None:
        """Single page list returns list with that page."""
        page = _make_page_mock("# Single")

        ordered = order_by_complexity([page])
        assert len(ordered) == 1
        assert ordered[0] is page


class TestGetProfile:
    """Test profile retrieval."""

    def test_returns_workload_profile(self) -> None:
        """Returns a WorkloadProfile instance."""
        profile = get_profile(WorkloadType.CPU_BOUND, Environment.LOCAL)
        assert isinstance(profile, WorkloadProfile)

    def test_cpu_bound_local_profile(self) -> None:
        """CPU_BOUND + LOCAL has expected values."""
        profile = get_profile(WorkloadType.CPU_BOUND, Environment.LOCAL)
        assert profile.parallel_threshold == 5
        assert profile.min_workers == 2
        assert profile.max_workers == 4
        assert profile.cpu_fraction == 0.5

    def test_io_bound_ci_profile(self) -> None:
        """IO_BOUND + CI has expected values."""
        profile = get_profile(WorkloadType.IO_BOUND, Environment.CI)
        assert profile.parallel_threshold == 20
        assert profile.min_workers == 2
        assert profile.max_workers == 4
        assert profile.cpu_fraction == 1.0

    def test_auto_detects_environment(self) -> None:
        """Auto-detects environment when not specified."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            profile = get_profile(WorkloadType.CPU_BOUND)
            # CI profile
            assert profile.max_workers == 2


class TestWorkloadTypeEnum:
    """Test WorkloadType enum."""

    def test_cpu_bound_value(self) -> None:
        assert WorkloadType.CPU_BOUND.value == "cpu_bound"

    def test_io_bound_value(self) -> None:
        assert WorkloadType.IO_BOUND.value == "io_bound"

    def test_mixed_value(self) -> None:
        assert WorkloadType.MIXED.value == "mixed"


class TestEnvironmentEnum:
    """Test Environment enum."""

    def test_ci_value(self) -> None:
        assert Environment.CI.value == "ci"

    def test_local_value(self) -> None:
        assert Environment.LOCAL.value == "local"

    def test_production_value(self) -> None:
        assert Environment.PRODUCTION.value == "production"


class TestWorkloadProfileDataclass:
    """Test WorkloadProfile dataclass."""

    def test_is_frozen(self) -> None:
        """WorkloadProfile is immutable (frozen)."""
        profile = WorkloadProfile(
            parallel_threshold=5,
            min_workers=2,
            max_workers=4,
            cpu_fraction=0.5,
        )
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            profile.parallel_threshold = 10  # type: ignore

    def test_has_all_attributes(self) -> None:
        """WorkloadProfile has all required attributes."""
        profile = WorkloadProfile(
            parallel_threshold=5,
            min_workers=2,
            max_workers=4,
            cpu_fraction=0.5,
        )
        assert profile.parallel_threshold == 5
        assert profile.min_workers == 2
        assert profile.max_workers == 4
        assert profile.cpu_fraction == 0.5


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow_ci(self) -> None:
        """Full workflow in CI environment."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            # Detect environment
            env = detect_environment()
            assert env == Environment.CI

            # Check if should parallelize
            should = should_parallelize(100, workload_type=WorkloadType.MIXED)
            assert should is True

            # Get optimal workers
            workers = get_optimal_workers(100, workload_type=WorkloadType.MIXED)
            assert workers == 2  # CI caps at 2

    def test_full_workflow_local(self) -> None:
        """Full workflow in local environment."""
        with patch.dict(os.environ, {}, clear=True), patch("os.cpu_count", return_value=8):
            # Detect environment
            env = detect_environment()
            assert env == Environment.LOCAL

            # Check if should parallelize
            should = should_parallelize(10, workload_type=WorkloadType.CPU_BOUND)
            assert should is True

            # Get optimal workers
            workers = get_optimal_workers(10, workload_type=WorkloadType.CPU_BOUND)
            assert 2 <= workers <= 4

    def test_user_override_bypasses_all(self) -> None:
        """User override bypasses environment and workload type."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            workers = get_optimal_workers(
                100,
                workload_type=WorkloadType.CPU_BOUND,
                config_override=12,
            )
            assert workers == 12  # Ignores CI cap
