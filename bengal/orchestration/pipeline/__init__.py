"""
Data-driven build pipeline for Bengal.

Replaces the 26-phase sequential build with a DAG-scheduled pipeline
where tasks declare inputs/outputs, the scheduler computes execution
order, and independent tasks run in parallel batches.

Quick start::

    from bengal.orchestration.pipeline import execute_pipeline
    from bengal.orchestration.tasks import all_tasks

    result = execute_pipeline(
        tasks=all_tasks(),
        ctx=build_context,
        initial_keys=frozenset({"site", "options", "cache", "stats"}),
    )
"""

from pathlib import Path

from bengal.orchestration.pipeline.executor import (
    BatchExecutor,
    PipelineResult,
    TaskResult,
)
from bengal.orchestration.pipeline.scheduler import (
    CyclicDependencyError,
    DuplicateProducerError,
    MissingDependencyError,
    TaskScheduler,
)
from bengal.orchestration.pipeline.task import BuildTask
from bengal.orchestration.pipeline.timings import load_task_timings, update_task_timings

__all__ = [
    "BatchExecutor",
    "BuildTask",
    "CyclicDependencyError",
    "DuplicateProducerError",
    "MissingDependencyError",
    "PipelineResult",
    "TaskResult",
    "TaskScheduler",
    "execute_pipeline",
]


def execute_pipeline(
    tasks: list[BuildTask],
    ctx: object,
    initial_keys: frozenset[str] | None = None,
    target_outputs: frozenset[str] | None = None,
    parallel: bool = False,
    max_workers: int | None = None,
    on_task_start: object | None = None,
    on_task_complete: object | None = None,
) -> PipelineResult:
    """
    Schedule and execute a build pipeline.

    Convenience function that creates a :class:`TaskScheduler` and
    :class:`BatchExecutor`, then runs all batches against *ctx*.

    Args:
        tasks: :class:`BuildTask` declarations.
        ctx: :class:`~bengal.orchestration.build_context.BuildContext`
            with initial state.
        initial_keys: Keys already present on *ctx* before any task runs.
        target_outputs: Optional set of logical output keys to build. When
            provided, the scheduler computes a minimal required subgraph and
            executes only those tasks.
        parallel: Run independent tasks within batches concurrently.
        max_workers: Thread cap per batch (``None`` = batch size).
        on_task_start: Optional ``(task_name) -> None`` callback.
        on_task_complete: Optional ``(task_name, duration_ms, status) -> None``
            callback.

    Returns:
        :class:`PipelineResult` with per-task outcomes and timing.
    """
    root_path = _try_get_root_path(ctx)
    task_timings = load_task_timings(root_path) if root_path is not None else None

    scheduler = TaskScheduler(
        tasks,
        initial_keys=initial_keys,
        task_durations_ms=task_timings,
    )
    planned_batches = (
        scheduler.plan_for_outputs(target_outputs)
        if target_outputs
        else scheduler.batches
    )
    executor = BatchExecutor(
        parallel=parallel,
        max_workers=max_workers,
        on_task_start=on_task_start,  # type: ignore[arg-type]
        on_task_complete=on_task_complete,  # type: ignore[arg-type]
    )
    result = executor.execute(planned_batches, ctx)  # type: ignore[arg-type]
    _try_persist_timings(root_path, result)
    return result


def _try_get_root_path(ctx: object) -> Path | None:
    """Best-effort extraction of site root path from build context."""
    site = getattr(ctx, "site", None)
    if site is None:
        return None
    root_path = getattr(site, "root_path", None)
    return root_path if isinstance(root_path, Path) else None


def _try_persist_timings(root_path: Path | None, result: PipelineResult) -> None:
    """Persist completed task timings for future scheduling hints."""
    if root_path is None:
        return

    observed: dict[str, float] = {
        item.name: item.duration_ms
        for item in result.completed
        if item.duration_ms > 0
    }
    if not observed:
        return

    try:
        update_task_timings(root_path, observed)
    except Exception:
        # Timing hints are best-effort only.
        return
