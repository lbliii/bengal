"""Tests for WorkScope structured concurrency primitive."""

from __future__ import annotations

import contextvars
import threading
import time

import pytest

from bengal.utils.concurrency.work_scope import WorkResult, WorkScope
from bengal.utils.concurrency.workers import WorkloadType


class TestWorkResult:
    def test_success_result(self):
        r = WorkResult(value=42, error=None, elapsed_ms=1.0)
        assert r.ok
        assert r.value == 42
        assert r.error is None

    def test_error_result(self):
        err = ValueError("boom")
        r = WorkResult(value=None, error=err, elapsed_ms=1.0)
        assert not r.ok
        assert r.error is err

    def test_frozen(self):
        r = WorkResult(value=1, error=None, elapsed_ms=0.0)
        with pytest.raises(AttributeError):
            r.value = 2  # type: ignore[misc]


class TestWorkScopeSequential:
    """Tests that hit the sequential fast path."""

    def test_empty_items(self):
        with WorkScope("test") as scope:
            results = scope.map(lambda x: x * 2, [])
        assert results == []

    def test_single_item(self):
        with WorkScope("test") as scope:
            results = scope.map(lambda x: x * 2, [5])
        assert len(results) == 1
        assert results[0].value == 10
        assert results[0].ok

    def test_small_list_runs_sequentially(self):
        """Below parallel threshold, items run in the calling thread."""
        thread_ids: list[int] = []

        def capture_thread(x: int) -> int:
            thread_ids.append(threading.current_thread().ident)
            return x

        with WorkScope("test") as scope:
            scope.map(capture_thread, [1, 2])

        main = threading.current_thread().ident
        assert all(tid == main for tid in thread_ids)

    def test_error_captured_not_raised(self):
        def fail(x: int) -> int:
            if x == 2:
                raise ValueError("bad")
            return x

        with WorkScope("test") as scope:
            results = scope.map(fail, [1, 2, 3])

        values = [r.value for r in results if r.ok]
        errors = [r for r in results if not r.ok]
        assert 1 in values
        assert 3 in values
        assert len(errors) == 1
        assert "bad" in str(errors[0].error)

    def test_elapsed_ms_populated(self):
        def slow(x: int) -> int:
            time.sleep(0.01)
            return x

        with WorkScope("test") as scope:
            results = scope.map(slow, [1])

        assert results[0].elapsed_ms >= 5  # at least 5ms


class TestWorkScopeParallel:
    """Tests that exercise the parallel path."""

    def test_parallel_execution(self):
        """Force parallel with explicit max_workers."""
        thread_ids: list[int] = []

        def work(x: int) -> int:
            thread_ids.append(threading.current_thread().ident)
            time.sleep(0.01)  # Small sleep so threads overlap
            return x

        with WorkScope("test", max_workers=4) as scope:
            results = scope.map(work, [1, 2, 3, 4, 5, 6, 7, 8])

        assert all(r.ok for r in results)
        # At least 2 distinct threads used
        assert len(set(thread_ids)) >= 2

    def test_context_propagation(self):
        """ContextVars from the submitting thread are visible in workers."""
        test_var: contextvars.ContextVar[str] = contextvars.ContextVar("test_var")
        test_var.set("hello")

        def read_var(x: int) -> str:
            return test_var.get("missing")

        with WorkScope("test", max_workers=2) as scope:
            results = scope.map(read_var, [1, 2, 3])

        assert all(r.ok for r in results)
        assert all(r.value == "hello" for r in results)

    def test_scope_timeout_cancels_slow_items(self):
        """Scope deadline causes remaining slow items to be cancelled."""
        stop = threading.Event()

        def slow(x: int) -> int:
            if x > 2:
                stop.wait(timeout=5)  # Interruptible wait
            return x

        with WorkScope("test", max_workers=2, timeout=0.5) as scope:
            results = scope.map(slow, [1, 2, 3, 4, 5])

        stop.set()  # Release any waiting threads

        errors = [r for r in results if not r.ok]
        assert len(errors) >= 1

    def test_scope_deadline_parallel(self):
        """Scope-level timeout cancels remaining work in parallel mode."""

        def slow(x: int) -> int:
            time.sleep(0.3)
            return x

        with WorkScope("test", max_workers=2, timeout=0.5) as scope:
            results = scope.map(slow, list(range(20)))

        # Some should complete, some should timeout
        assert len(results) > 0
        errors = [r for r in results if not r.ok]
        assert len(errors) >= 1

    def test_mixed_success_and_failure(self):
        def work(x: int) -> int:
            if x % 2 == 0:
                raise ValueError(f"even: {x}")
            return x * 10

        with WorkScope("test", max_workers=4) as scope:
            results = scope.map(work, [1, 2, 3, 4, 5])

        successes = [r for r in results if r.ok]
        failures = [r for r in results if not r.ok]
        assert len(successes) == 3
        assert len(failures) == 2

    def test_multiple_map_calls_reuse_executor(self):
        """Multiple .map() calls within one scope reuse the same executor."""
        with WorkScope("test", max_workers=2) as scope:
            r1 = scope.map(lambda x: x + 1, [1, 2, 3])
            r2 = scope.map(lambda x: x * 2, [4, 5, 6])

        assert len(r1) == 3
        assert len(r2) == 3
        assert all(r.ok for r in r1 + r2)

    def test_on_progress_callback(self):
        calls: list[tuple[int, int]] = []

        def on_progress(completed: int, total: int) -> None:
            calls.append((completed, total))

        with WorkScope("test", max_workers=2, on_progress=on_progress) as scope:
            scope.map(lambda x: x, [1, 2, 3, 4])

        assert len(calls) == 4
        totals = [t for _, t in calls]
        assert all(t == 4 for t in totals)
        completed_counts = sorted(c for c, _ in calls)
        assert completed_counts == [1, 2, 3, 4]


class TestWorkScopeEdgeCases:
    def test_no_timeout(self):
        """timeout=0 means no scope deadline."""
        with WorkScope("test", timeout=0, max_workers=2) as scope:
            results = scope.map(lambda x: x, [1, 2])
        assert all(r.ok for r in results)

    def test_exception_in_fn_does_not_crash_scope(self):
        def crash(x: int) -> int:
            raise RuntimeError("crash")

        with WorkScope("test", max_workers=2) as scope:
            results = scope.map(crash, [1, 2, 3])

        assert len(results) == 3
        assert all(not r.ok for r in results)

    def test_workload_type_auto_tune(self):
        """WorkloadType is used for auto-tuning when max_workers is None."""
        with WorkScope("test", workload_type=WorkloadType.IO_BOUND) as scope:
            results = scope.map(lambda x: x, list(range(100)))
        assert len(results) == 100
