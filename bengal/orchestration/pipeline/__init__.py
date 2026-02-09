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
        parallel: Run independent tasks within batches concurrently.
        max_workers: Thread cap per batch (``None`` = batch size).
        on_task_start: Optional ``(task_name) -> None`` callback.
        on_task_complete: Optional ``(task_name, duration_ms, status) -> None``
            callback.

    Returns:
        :class:`PipelineResult` with per-task outcomes and timing.
    """
    scheduler = TaskScheduler(tasks, initial_keys=initial_keys)
    executor = BatchExecutor(
        parallel=parallel,
        max_workers=max_workers,
        on_task_start=on_task_start,  # type: ignore[arg-type]
        on_task_complete=on_task_complete,  # type: ignore[arg-type]
    )
    return executor.execute(scheduler.batches, ctx)  # type: ignore[arg-type]
