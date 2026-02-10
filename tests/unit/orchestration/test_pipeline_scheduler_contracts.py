"""Regression tests for DAG task contracts and executor safety."""

from __future__ import annotations

import time
from dataclasses import dataclass

from bengal.orchestration.pipeline.executor import BatchExecutor
from bengal.orchestration.pipeline.scheduler import TaskScheduler
from bengal.orchestration.pipeline.task import BuildTask
from bengal.orchestration.tasks import INITIAL_KEYS, all_tasks


def _batch_index_by_task_name(scheduler: TaskScheduler) -> dict[str, int]:
    task_to_batch: dict[str, int] = {}
    for index, batch in enumerate(scheduler.batches):
        for task in batch:
            task_to_batch[task.name] = index
    return task_to_batch


def test_scheduler_orders_filter_before_dependents() -> None:
    """filter_pages must run before sections/assets/related work."""
    scheduler = TaskScheduler(all_tasks(), INITIAL_KEYS)
    task_batch = _batch_index_by_task_name(scheduler)

    filter_batch = task_batch["filter_pages"]
    assert filter_batch < task_batch["finalize_sections"]
    assert filter_batch < task_batch["build_related"]
    assert filter_batch < task_batch["process_assets"]


def test_scheduler_orders_taxonomy_before_parse_and_indexes() -> None:
    """Taxonomy mutation of pages_to_build must precede parsing/render prerequisites."""
    scheduler = TaskScheduler(all_tasks(), INITIAL_KEYS)
    task_batch = _batch_index_by_task_name(scheduler)

    taxonomy_batch = task_batch["build_taxonomies"]
    assert taxonomy_batch < task_batch["parse_content"]
    assert taxonomy_batch < task_batch["build_menus"]
    assert taxonomy_batch < task_batch["build_indexes"]
    assert task_batch["parse_content"] < task_batch["render_pages"]


@dataclass
class _DummyContext:
    executed: list[str]


def test_executor_cancels_downstream_when_upstream_fails() -> None:
    """Downstream tasks are cancelled when required upstream task fails."""

    def execute_fail(_ctx: _DummyContext) -> None:
        raise RuntimeError("boom")

    def execute_downstream(ctx: _DummyContext) -> None:
        ctx.executed.append("downstream")

    tasks = [
        BuildTask(
            name="upstream",
            requires=frozenset(),
            produces=frozenset({"a"}),
            execute=execute_fail,
        ),
        BuildTask(
            name="downstream",
            requires=frozenset({"a"}),
            produces=frozenset({"b"}),
            execute=execute_downstream,
        ),
    ]
    scheduler = TaskScheduler(tasks, initial_keys=frozenset())
    result = BatchExecutor(parallel=False).execute(scheduler.batches, _DummyContext(executed=[]))

    statuses = {task_result.name: task_result.status for task_result in result.task_results}
    assert statuses["upstream"] == "failed"
    assert statuses["downstream"] == "cancelled"


def test_executor_parallel_results_are_deterministic_in_task_order() -> None:
    """Parallel batch result order should match task declaration order."""

    def execute_fast(_ctx: _DummyContext) -> None:
        return

    def execute_slow(_ctx: _DummyContext) -> None:
        time.sleep(0.03)

    tasks = [
        BuildTask(
            name="first",
            requires=frozenset(),
            produces=frozenset({"a"}),
            execute=execute_slow,
        ),
        BuildTask(
            name="second",
            requires=frozenset(),
            produces=frozenset({"b"}),
            execute=execute_fast,
        ),
        BuildTask(
            name="third",
            requires=frozenset(),
            produces=frozenset({"c"}),
            execute=execute_fast,
        ),
    ]
    scheduler = TaskScheduler(tasks, initial_keys=frozenset())
    result = BatchExecutor(parallel=True).execute(scheduler.batches, _DummyContext(executed=[]))

    assert [task_result.name for task_result in result.task_results] == ["first", "second", "third"]


def test_executor_treats_skip_predicate_errors_as_failures() -> None:
    """skip_if exceptions should fail the task instead of running it."""

    def skip_raises(_ctx: _DummyContext) -> bool:
        raise ValueError("bad skip predicate")

    def execute_should_not_run(ctx: _DummyContext) -> None:
        ctx.executed.append("ran")

    task = BuildTask(
        name="skip_broken",
        requires=frozenset(),
        produces=frozenset({"x"}),
        execute=execute_should_not_run,
        skip_if=skip_raises,
    )
    scheduler = TaskScheduler([task], initial_keys=frozenset())
    ctx = _DummyContext(executed=[])
    result = BatchExecutor(parallel=False).execute(scheduler.batches, ctx)

    assert result.task_results[0].status == "failed"
    assert result.task_results[0].error is not None
    assert ctx.executed == []
