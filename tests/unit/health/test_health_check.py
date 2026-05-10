"""
Tests for health check orchestrator.

Tests parallel execution, error isolation, threshold behavior, and observability.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bengal.health.base import BaseValidator
from bengal.health.health_check import HealthCheck, HealthCheckStats
from bengal.health.report import CheckResult, CheckStatus
from bengal.health.scope import get_validation_scope


class MockValidator(BaseValidator):
    """Mock validator for testing."""

    last_file_results: dict[Path, list[CheckResult]] | None = None

    def __init__(
        self,
        name: str,
        results: list[CheckResult] | None = None,
        sleep_time: float = 0,
        raise_exception: Exception | None = None,
    ):
        self.name = name
        self._results = results if results is not None else [CheckResult.success(f"{name} passed")]
        self._sleep_time = sleep_time
        self._raise_exception = raise_exception
        self.was_called = False
        self.call_count = 0
        self.received_context = None
        self.last_file_results = None

    def validate(self, site: Any, build_context: Any = None) -> list[CheckResult]:
        """Run validation."""
        self.was_called = True
        self.call_count += 1
        self.received_context = build_context

        if self._sleep_time > 0:
            time.sleep(self._sleep_time)

        if self._raise_exception:
            raise self._raise_exception

        return self._results

    def is_enabled(self, config: dict) -> bool:
        """Always enabled for tests."""
        return True


class TestHealthCheckParallelExecution:
    """Test parallel validator execution."""

    @pytest.fixture
    def mock_site(self):
        """Create a mock site."""
        site = MagicMock()
        site.config = {}
        site.pages = []
        return site

    def test_parallel_execution_runs_all_validators(self, mock_site):
        """Test that parallel execution runs all validators."""
        # Create 4 validators (above PARALLEL_THRESHOLD of 3)
        validators = [MockValidator(f"Validator{i}", sleep_time=0.01) for i in range(4)]

        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        report = health_check.run()

        # All validators should have been called
        for v in validators:
            assert v.was_called, f"{v.name} was not called"
            assert v.call_count == 1, f"{v.name} was called {v.call_count} times"

        # Report should have all validator reports
        assert len(report.validator_reports) == 4

    def test_parallel_execution_faster_than_sequential(self, mock_site):
        """Test that parallel execution is faster than sequential for slow validators."""
        # Create 4 validators that each take 50ms
        validators = [MockValidator(f"SlowValidator{i}", sleep_time=0.05) for i in range(4)]

        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        start = time.time()
        report = health_check.run()
        duration = time.time() - start

        # Sequential would take ~200ms (4 * 50ms)
        # Parallel with 4 workers should take ~50-100ms
        # Allow some overhead, but should be less than 150ms
        assert duration < 0.15, f"Parallel execution took {duration:.3f}s, expected < 0.15s"
        assert len(report.validator_reports) == 4

    def test_error_isolation_one_validator_crashes(self, mock_site):
        """Test that one validator crashing doesn't affect others."""
        validators = [
            MockValidator("Good1"),
            MockValidator("Bad", raise_exception=RuntimeError("Test error")),
            MockValidator("Good2"),
            MockValidator("Good3"),
        ]

        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        report = health_check.run()

        # All validators should have reports
        assert len(report.validator_reports) == 4

        # Find the bad validator's report
        bad_report = next(r for r in report.validator_reports if r.validator_name == "Bad")
        assert bad_report.error_count == 1
        assert "crashed" in bad_report.results[0].message.lower()

        # Good validators should have succeeded
        good_reports = [r for r in report.validator_reports if r.validator_name.startswith("Good")]
        for gr in good_reports:
            assert gr.error_count == 0

    def test_threshold_below_runs_sequential(self, mock_site):
        """Test that fewer than PARALLEL_THRESHOLD validators run sequentially."""
        # Create only 2 validators (below threshold of 3)
        validators = [MockValidator(f"Validator{i}") for i in range(2)]

        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        # Patch to verify sequential method is called
        with (
            patch.object(health_check, "_run_validators_sequential") as mock_sequential,
            patch.object(health_check, "_run_validators_parallel") as mock_parallel,
        ):
            mock_sequential.return_value = None
            health_check.run()

            mock_sequential.assert_called_once()
            mock_parallel.assert_not_called()

    def test_threshold_at_runs_parallel(self, mock_site):
        """Test that exactly PARALLEL_THRESHOLD validators run in parallel."""
        # Create exactly 3 validators (at threshold)
        validators = [MockValidator(f"Validator{i}") for i in range(3)]

        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        # Patch to verify parallel method is called
        with (
            patch.object(health_check, "_run_validators_sequential") as mock_sequential,
            patch.object(health_check, "_run_validators_parallel") as mock_parallel,
        ):
            mock_parallel.return_value = None
            health_check.run()

            mock_parallel.assert_called_once()
            mock_sequential.assert_not_called()

    def test_results_same_as_sequential(self, mock_site):
        """Test that parallel and sequential produce equivalent results."""
        # Create validators with specific results
        results_data = [
            [CheckResult.success("Check 1")],
            [CheckResult.warning("Warning 1", recommendation="Fix it")],
            [CheckResult.error("Error 1")],
            [CheckResult.info("Info 1")],
        ]

        # Run with parallel (4 validators)
        validators_parallel = [MockValidator(f"V{i}", results=results_data[i]) for i in range(4)]
        health_check_parallel = HealthCheck(mock_site, auto_register=False)
        for v in validators_parallel:
            health_check_parallel.register(v)
        report_parallel = health_check_parallel.run()

        # Run with sequential (2 validators, below threshold)
        validators_sequential = [MockValidator(f"V{i}", results=results_data[i]) for i in range(2)]
        health_check_sequential = HealthCheck(mock_site, auto_register=False)
        for v in validators_sequential:
            health_check_sequential.register(v)
        report_sequential = health_check_sequential.run()

        # Compare first 2 validators (present in both)
        # Note: Order may differ in parallel, so compare by validator name
        for i in range(2):
            seq_report = next(
                r for r in report_sequential.validator_reports if r.validator_name == f"V{i}"
            )
            par_report = next(
                r for r in report_parallel.validator_reports if r.validator_name == f"V{i}"
            )

            assert len(seq_report.results) == len(par_report.results)
            assert seq_report.results[0].status == par_report.results[0].status
            assert seq_report.results[0].message == par_report.results[0].message

    def test_verbose_run_returns_report_without_direct_stdout(self, mock_site, capsys):
        """HealthCheck leaves terminal rendering to the CLI output boundary."""
        validators = [MockValidator(f"Validator{i}") for i in range(4)]

        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        report = health_check.run(verbose=True)

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
        for i in range(4):
            assert any(r.validator_name == f"Validator{i}" for r in report.validator_reports)


class TestHealthCheckHelperMethods:
    """Test helper methods of HealthCheck."""

    @pytest.fixture
    def mock_site(self):
        """Create a mock site."""
        site = MagicMock()
        site.config = {}
        site.pages = []
        return site

    def test_is_validator_enabled_no_profile(self, mock_site):
        """Test _is_validator_enabled with no profile."""
        validator = MockValidator("Test")
        health_check = HealthCheck(mock_site, auto_register=False)

        # With no profile and enabled by default
        assert health_check._is_validator_enabled(validator, None) is True

    def test_get_files_to_validate_with_context(self, mock_site):
        """Test _get_files_to_validate with explicit context."""
        health_check = HealthCheck(mock_site, auto_register=False)

        context = [Path("file1.md"), Path("file2.md")]
        files = health_check._get_files_to_validate(context, False, None)

        assert files == {Path("file1.md"), Path("file2.md")}

    def test_get_files_to_validate_no_context(self, mock_site):
        """Test _get_files_to_validate with no context."""
        health_check = HealthCheck(mock_site, auto_register=False)

        files = health_check._get_files_to_validate(None, False, None)

        assert files is None

    def test_run_single_validator_success(self, mock_site):
        """Test _run_single_validator with successful validator."""
        validator = MockValidator("Test", results=[CheckResult.success("OK")])
        health_check = HealthCheck(mock_site, auto_register=False)

        report = health_check._run_single_validator(validator, None, None, None)

        assert report.validator_name == "Test"
        assert len(report.results) == 1
        assert report.results[0].status == CheckStatus.SUCCESS
        assert report.duration_ms >= 0

    def test_run_single_validator_crash(self, mock_site):
        """Test _run_single_validator with crashing validator."""
        validator = MockValidator("Bad", raise_exception=ValueError("Test error"))
        health_check = HealthCheck(mock_site, auto_register=False)

        report = health_check._run_single_validator(validator, None, None, None)

        assert report.validator_name == "Bad"
        assert len(report.results) == 1
        assert report.results[0].status == CheckStatus.ERROR
        assert "crashed" in report.results[0].message.lower()

    def test_run_single_validator_passes_validation_scope(self, mock_site):
        """File-specific validators receive scoped validation context."""
        page = MagicMock()
        page.source_path = Path("content/changed.md")
        mock_site.pages = [page]
        validator = MockValidator("Links", results=[])
        health_check = HealthCheck(mock_site, auto_register=False)

        report = health_check._run_single_validator(
            validator, build_context=None, cache=None, files_to_validate={page.source_path}
        )

        scope = get_validation_scope(validator.received_context)
        assert report.results == []
        assert scope is not None
        assert scope.files_to_validate == frozenset({page.source_path})
        assert scope.pages_to_validate(mock_site) == [page]

    def test_run_single_validator_merges_cached_results_for_plain_validator(self, mock_site):
        """Cached unchanged-file results are merged for validators that do not consume them."""
        changed = MagicMock()
        changed.source_path = Path("content/changed.md")
        unchanged = MagicMock()
        unchanged.source_path = Path("content/unchanged.md")
        mock_site.pages = [changed, unchanged]

        cached = CheckResult.error("cached broken", code="H101", validator="Links")
        cache = MagicMock()
        cache.get_cached_validation_results.return_value = [cached.to_cache_dict()]

        fresh = CheckResult.warning("fresh broken", code="H102")
        validator = MockValidator("Links", results=[fresh])
        health_check = HealthCheck(mock_site, auto_register=False)

        report = health_check._run_single_validator(
            validator,
            build_context=None,
            cache=cache,
            files_to_validate={changed.source_path},
        )

        assert [result.message for result in report.results] == ["cached broken", "fresh broken"]
        cache.get_cached_validation_results.assert_called_once_with(unchanged.source_path, "Links")

    def test_missing_unchanged_validation_cache_disables_incremental_scope(self, mock_site):
        """Missing cached unchanged-file findings fall back to full validation."""
        changed = MagicMock()
        changed.source_path = Path("content/changed.md")
        unchanged = MagicMock()
        unchanged.source_path = Path("content/unchanged.md")
        mock_site.pages = [changed, unchanged]

        cache = MagicMock()
        cache.get_cached_validation_results.return_value = None
        validator = MockValidator("Links", results=[])
        health_check = HealthCheck(mock_site, auto_register=False)

        scope = health_check._build_validation_scope(
            validator,
            cache,
            files_to_validate={changed.source_path},
        )

        assert scope is None

    def test_run_single_validator_caches_file_results(self, mock_site):
        """Validator-provided per-file results are persisted for changed files."""
        page = MagicMock()
        page.source_path = Path("content/changed.md")
        mock_site.pages = [page]
        file_result = CheckResult.error("fresh broken", code="H101")
        validator = MockValidator("Links", results=[file_result])
        validator.last_file_results = {page.source_path: [file_result]}
        cache = MagicMock()
        health_check = HealthCheck(mock_site, auto_register=False)

        health_check._run_single_validator(
            validator,
            build_context=None,
            cache=cache,
            files_to_validate={page.source_path},
        )

        cache.cache_validation_results.assert_called_once_with(
            page.source_path, "Links", [file_result]
        )

    def test_run_single_validator_caches_full_run_file_results(self, mock_site):
        """Full validation seeds per-file result cache for future incremental runs."""
        page1 = MagicMock()
        page1.source_path = Path("content/one.md")
        page2 = MagicMock()
        page2.source_path = Path("content/two.md")
        mock_site.pages = [page1, page2]

        result1 = CheckResult.error("first broken", code="H101")
        result2 = CheckResult.warning("second warning", code="H102")
        validator = MockValidator("Links", results=[result1, result2])
        validator.last_file_results = {
            page1.source_path: [result1],
            page2.source_path: [result2],
        }
        cache = MagicMock()
        health_check = HealthCheck(mock_site, auto_register=False)

        health_check._run_single_validator(
            validator,
            build_context=None,
            cache=cache,
            files_to_validate=None,
        )

        assert cache.cache_validation_results.call_count == 2
        cache.cache_validation_results.assert_any_call(page1.source_path, "Links", [result1])
        cache.cache_validation_results.assert_any_call(page2.source_path, "Links", [result2])

    def test_link_validation_cache_uses_registry_fingerprint_context(self, mock_site):
        """Links cache keys include rendered URL and anchor truth when available."""
        changed = MagicMock()
        changed.source_path = Path("content/changed.md")
        unchanged = MagicMock()
        unchanged.source_path = Path("content/unchanged.md")
        mock_site.pages = [changed, unchanged]
        mock_site.link_registry = MagicMock(fingerprint="registry-fingerprint")
        cache = MagicMock()
        cache.get_cached_validation_results.return_value = []
        validator = MockValidator("Links", results=[])
        validator.last_file_results = {changed.source_path: []}
        health_check = HealthCheck(mock_site, auto_register=False)

        health_check._run_single_validator(
            validator,
            build_context=None,
            cache=cache,
            files_to_validate={changed.source_path},
        )

        cache.get_cached_validation_results.assert_called_once_with(
            unchanged.source_path,
            "Links",
            cache_context={"link_registry_fingerprint": "registry-fingerprint"},
        )
        cache.cache_validation_results.assert_called_once_with(
            changed.source_path,
            "Links",
            [],
            cache_context={"link_registry_fingerprint": "registry-fingerprint"},
        )


class TestHealthCheckStats:
    """Test HealthCheckStats observability."""

    def test_stats_speedup_calculation(self):
        """Test speedup calculation."""
        stats = HealthCheckStats(
            total_duration_ms=100,
            execution_mode="parallel",
            validator_count=4,
            worker_count=4,
            cpu_count=8,
            sum_validator_duration_ms=400,  # 4 validators * 100ms each
        )

        # Speedup = 400 / 100 = 4x
        assert stats.speedup == 4.0

    def test_stats_efficiency_calculation(self):
        """Test parallel efficiency calculation."""
        stats = HealthCheckStats(
            total_duration_ms=100,
            execution_mode="parallel",
            validator_count=4,
            worker_count=4,
            cpu_count=8,
            sum_validator_duration_ms=400,
        )

        # Efficiency = 4.0 / 4 = 1.0 (100%)
        assert stats.efficiency == 1.0

    def test_stats_format_summary_parallel(self):
        """Test format_summary for parallel mode."""
        stats = HealthCheckStats(
            total_duration_ms=100,
            execution_mode="parallel",
            validator_count=4,
            worker_count=4,
            cpu_count=8,
            sum_validator_duration_ms=400,
        )

        summary = stats.format_summary()
        # Uses icon set (ASCII by default: ✓ for success)
        assert "4 validators" in summary
        assert "4 workers" in summary
        assert "4.0x speedup" in summary

    def test_stats_format_summary_sequential(self):
        """Test format_summary for sequential mode."""
        stats = HealthCheckStats(
            total_duration_ms=100,
            execution_mode="sequential",
            validator_count=2,
            worker_count=1,
            cpu_count=8,
            sum_validator_duration_ms=100,
        )

        summary = stats.format_summary()
        # Uses icon set (ASCII by default: - for info)
        assert "2 validators" in summary
        assert "1 workers" in summary
        assert "1.0x speedup" in summary


class TestHealthCheckAutoScaling:
    """Test auto-scaling of worker count."""

    @pytest.fixture
    def mock_site(self):
        """Create a mock site."""
        site = MagicMock()
        site.config = {}
        site.pages = []
        return site

    def test_get_optimal_workers_scales_with_cpu(self, mock_site):
        """Test that worker count scales with CPU cores."""
        health_check = HealthCheck(mock_site, auto_register=False)

        with patch("os.cpu_count", return_value=8):
            # 8 cores -> 4 workers (50%)
            workers = health_check._get_optimal_workers(10)
            assert workers == 4

        with patch("os.cpu_count", return_value=16):
            # 16 cores -> 8 workers (50%, capped at 8)
            workers = health_check._get_optimal_workers(10)
            assert workers == 8

        with patch("os.cpu_count", return_value=2):
            # 2 cores -> 2 workers (minimum)
            workers = health_check._get_optimal_workers(10)
            assert workers == 2

    def test_get_optimal_workers_limited_by_validator_count(self, mock_site):
        """Test that workers don't exceed validator count."""
        health_check = HealthCheck(mock_site, auto_register=False)

        with patch("os.cpu_count", return_value=16):
            # 16 cores -> 8 workers, but only 3 validators
            workers = health_check._get_optimal_workers(3)
            assert workers == 3

    def test_last_stats_populated_after_run(self, mock_site):
        """Test that last_stats is populated after run()."""
        validators = [MockValidator(f"V{i}") for i in range(4)]
        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        assert health_check.last_stats is None

        health_check.run()

        assert health_check.last_stats is not None
        assert health_check.last_stats.validator_count == 4
        assert health_check.last_stats.execution_mode == "parallel"
        assert health_check.last_stats.total_duration_ms > 0

    def test_last_stats_sequential_mode(self, mock_site):
        """Test last_stats for sequential execution."""
        validators = [MockValidator(f"V{i}") for i in range(2)]
        health_check = HealthCheck(mock_site, auto_register=False)
        for v in validators:
            health_check.register(v)

        health_check.run()

        assert health_check.last_stats is not None
        assert health_check.last_stats.execution_mode == "sequential"
        assert health_check.last_stats.worker_count == 1


class TestHealthCheckIntegration:
    """Integration tests with real validators."""

    @pytest.fixture
    def mock_site(self):
        """Create a mock site with minimal config."""
        site = MagicMock()
        site.config = {"site": {"title": "Test Site"}}
        site.pages = []
        site.output_dir = Path("/tmp/output")
        site.root_path = Path("/tmp/site")
        return site

    def test_run_with_build_context(self, mock_site):
        """Test that build_context is passed to validators."""
        build_context = MagicMock()
        build_context.knowledge_graph = MagicMock()

        class ContextCheckingValidator(BaseValidator):
            name = "ContextChecker"
            received_context = None

            def validate(self, site: Any, build_context: Any = None) -> list[CheckResult]:
                ContextCheckingValidator.received_context = build_context
                return [CheckResult.success("OK")]

            def is_enabled(self, config: dict) -> bool:
                return True

        health_check = HealthCheck(mock_site, auto_register=False)
        health_check.register(ContextCheckingValidator())

        health_check.run(build_context=build_context)

        assert ContextCheckingValidator.received_context is build_context
