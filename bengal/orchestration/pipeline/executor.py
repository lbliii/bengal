"""
Batch executor for the data-driven build pipeline.

Runs task batches produced by
:class:`~bengal.orchestration.pipeline.scheduler.TaskScheduler`.
Each batch is executed sequentially by default; Phase 4 of the
pipeline plan enables parallel execution within batches via
:class:`concurrent.futures.ThreadPoolExecutor`.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.pipeline.task import BuildTask

logger = get_logger(__name__)

type _TaskStartCB = Callable[[str], None]
type _TaskCompleteCB = Callable[[str, float, str], None]


# ------------------------------------------------------------------
# Result types
# ------------------------------------------------------------------


@dataclass(slots=True)
class TaskResult:
    """Outcome of a single task execution."""

    name: str
    status: str  # "completed" | "skipped" | "failed" | "cancelled"
    duration_ms: float = 0.0
    error: Exception | None = None


@dataclass
class PipelineResult:
    """Aggregate result of the full pipeline run."""

    task_results: list[TaskResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def completed(self) -> list[TaskResult]:
        return [r for r in self.task_results if r.status == "completed"]

    @property
    def skipped(self) -> list[TaskResult]:
        return [r for r in self.task_results if r.status == "skipped"]

    @property
    def failed(self) -> list[TaskResult]:
        return [r for r in self.task_results if r.status == "failed"]

    @property
    def cancelled(self) -> list[TaskResult]:
        return [r for r in self.task_results if r.status == "cancelled"]

    @property
    def success(self) -> bool:
        """True when no task failed."""
        return len(self.failed) == 0


# ------------------------------------------------------------------
# Executor
# ------------------------------------------------------------------


class BatchExecutor:
    """
    Execute task batches against a shared :class:`BuildContext`.

    By default every batch is run sequentially.  Set *parallel=True* to
    run independent tasks within the same batch concurrently using
    :class:`concurrent.futures.ThreadPoolExecutor`.

    Args:
        parallel: Enable thread-parallel execution within batches.
        max_workers: Maximum threads per batch (``None`` = batch size).
        on_task_start: Optional callback ``(task_name) -> None``.
        on_task_complete: Optional callback
            ``(task_name, duration_ms, status) -> None``.
    """

    def __init__(
        self,
        parallel: bool = False,
        max_workers: int | None = None,
        on_task_start: _TaskStartCB | None = None,
        on_task_complete: _TaskCompleteCB | None = None,
    ) -> None:
        self._parallel = parallel
        self._max_workers = max_workers
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._task_dependencies: dict[str, frozenset[str]] = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def execute(
        self,
        batches: list[list[BuildTask]],
        ctx: BuildContext,
    ) -> PipelineResult:
        """Run all *batches* against *ctx* and return the aggregate result."""
        pipeline_start = time.perf_counter()
        result = PipelineResult()
        failed_tasks: set[str] = set()
        self._task_dependencies = self._build_task_dependencies(batches)

        for batch_idx, batch in enumerate(batches):
            batch_results = self._execute_batch(
                batch, ctx, batch_idx, failed_tasks
            )
            result.task_results.extend(batch_results)

            # Track failures/cancellations for dependency cancellation
            for r in batch_results:
                if r.status in {"failed", "cancelled"}:
                    failed_tasks.add(r.name)

        result.total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
        return result

    # ------------------------------------------------------------------
    # Batch strategies
    # ------------------------------------------------------------------

    def _execute_batch(
        self,
        batch: list[BuildTask],
        ctx: BuildContext,
        batch_idx: int,
        failed_upstream: set[str],
    ) -> list[TaskResult]:
        if self._parallel and len(batch) > 1:
            return self._execute_batch_parallel(
                batch, ctx, batch_idx, failed_upstream
            )
        return self._execute_batch_sequential(
            batch, ctx, batch_idx, failed_upstream
        )

    def _execute_batch_sequential(
        self,
        batch: list[BuildTask],
        ctx: BuildContext,
        batch_idx: int,
        failed_upstream: set[str],
    ) -> list[TaskResult]:
        results: list[TaskResult] = []
        for task in batch:
            result = self._execute_task(task, ctx, failed_upstream)
            results.append(result)
            if result.status == "failed":
                failed_upstream.add(task.name)
        return results

    def _execute_batch_parallel(
        self,
        batch: list[BuildTask],
        ctx: BuildContext,
        batch_idx: int,
        failed_upstream: set[str],
    ) -> list[TaskResult]:
        from concurrent.futures import ThreadPoolExecutor

        max_workers = self._max_workers or len(batch)

        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"Pipeline-B{batch_idx}",
        ) as pool:
            futures = [pool.submit(self._execute_task, task, ctx, failed_upstream) for task in batch]
            # Preserve task order for deterministic result processing.
            return [future.result() for future in futures]

    # ------------------------------------------------------------------
    # Single-task execution
    # ------------------------------------------------------------------

    def _execute_task(
        self,
        task: BuildTask,
        ctx: BuildContext,
        failed_upstream: set[str],
    ) -> TaskResult:
        """Run one task with skip / timing / error handling."""
        # 0. Cancel when any direct dependency task has failed/cancelled.
        # This blocks downstream work and prevents misleading follow-on failures.
        upstream_failed = self._task_dependencies.get(task.name, frozenset()) & failed_upstream
        if upstream_failed:
            logger.warning(
                "task_cancelled_upstream_failed",
                task=task.name,
                upstream_tasks=sorted(upstream_failed),
            )
            self._notify_complete(task.name, 0.0, "cancelled")
            return TaskResult(name=task.name, status="cancelled")

        # 1. Check skip predicate
        if task.skip_if is not None:
            try:
                if task.skip_if(ctx):
                    logger.info("task_skipped", task=task.name)
                    return TaskResult(name=task.name, status="skipped")
            except Exception as exc:
                logger.error(
                    "task_skip_check_failed",
                    task=task.name,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                self._notify_complete(task.name, 0.0, "failed")
                return TaskResult(
                    name=task.name,
                    status="failed",
                    duration_ms=0.0,
                    error=exc,
                )

        # 2. Notify start
        if self._on_task_start is not None:
            with contextlib.suppress(Exception):
                self._on_task_start(task.name)

        # 3. Execute
        start = time.perf_counter()
        try:
            task.execute(ctx)
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "task_completed",
                task=task.name,
                duration_ms=round(duration_ms, 1),
            )
            self._notify_complete(task.name, duration_ms, "completed")
            return TaskResult(
                name=task.name, status="completed", duration_ms=duration_ms
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "task_failed",
                task=task.name,
                duration_ms=round(duration_ms, 1),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            self._notify_complete(task.name, duration_ms, "failed")
            return TaskResult(
                name=task.name,
                status="failed",
                duration_ms=duration_ms,
                error=exc,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _notify_complete(
        self, name: str, duration_ms: float, status: str
    ) -> None:
        if self._on_task_complete is not None:
            with contextlib.suppress(Exception):
                self._on_task_complete(name, duration_ms, status)

    def _build_task_dependencies(
        self,
        batches: list[list[BuildTask]],
    ) -> dict[str, frozenset[str]]:
        """Map task -> direct upstream task names from requires/produces."""
        tasks = [task for batch in batches for task in batch]
        producers: dict[str, str] = {}
        for task in tasks:
            for key in task.produces:
                producers[key] = task.name

        dependencies: dict[str, frozenset[str]] = {}
        for task in tasks:
            upstream = {
                producers[key]
                for key in task.requires
                if key in producers and producers[key] != task.name
            }
            dependencies[task.name] = frozenset(upstream)
        return dependencies
