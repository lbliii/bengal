"""Regression tests for DAG task contracts and executor safety."""

from __future__ import annotations

import time
from dataclasses import dataclass

from bengal.orchestration.pipeline.executor import BatchExecutor
from bengal.orchestration.pipeline import execute_pipeline
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


def test_scheduler_plan_for_outputs_builds_minimal_subgraph() -> None:
    """Reverse planning includes only tasks needed for target outputs."""

    def _noop(_ctx: _DummyContext) -> None:
        return

    tasks = [
        BuildTask(
            name="discover",
            requires=frozenset({"site"}),
            produces=frozenset({"pages"}),
            execute=_noop,
        ),
        BuildTask(
            name="parse",
            requires=frozenset({"pages"}),
            produces=frozenset({"parsed"}),
            execute=_noop,
        ),
        BuildTask(
            name="render",
            requires=frozenset({"parsed"}),
            produces=frozenset({"html"}),
            execute=_noop,
        ),
        BuildTask(
            name="assets",
            requires=frozenset({"site"}),
            produces=frozenset({"asset_manifest"}),
            execute=_noop,
        ),
        BuildTask(
            name="health",
            requires=frozenset({"html", "asset_manifest"}),
            produces=frozenset({"report"}),
            execute=_noop,
        ),
    ]
    scheduler = TaskScheduler(tasks, initial_keys=frozenset({"site"}))
    planned = scheduler.plan_for_outputs(frozenset({"asset_manifest"}))
    planned_names = [task.name for batch in planned for task in batch]

    assert planned_names == ["assets"]


def test_scheduler_plan_for_outputs_preserves_dependency_order() -> None:
    """Planned batches still satisfy topological dependencies."""

    def _noop(_ctx: _DummyContext) -> None:
        return

    tasks = [
        BuildTask(
            name="discover",
            requires=frozenset({"site"}),
            produces=frozenset({"pages"}),
            execute=_noop,
        ),
        BuildTask(
            name="parse",
            requires=frozenset({"pages"}),
            produces=frozenset({"parsed"}),
            execute=_noop,
        ),
        BuildTask(
            name="render",
            requires=frozenset({"parsed"}),
            produces=frozenset({"html"}),
            execute=_noop,
        ),
        BuildTask(
            name="assets",
            requires=frozenset({"site"}),
            produces=frozenset({"asset_manifest"}),
            execute=_noop,
        ),
        BuildTask(
            name="health",
            requires=frozenset({"html", "asset_manifest"}),
            produces=frozenset({"report"}),
            execute=_noop,
        ),
    ]
    scheduler = TaskScheduler(tasks, initial_keys=frozenset({"site"}))
    planned = scheduler.plan_for_outputs(frozenset({"report"}))
    task_to_batch: dict[str, int] = {}
    for batch_idx, batch in enumerate(planned):
        for task in batch:
            task_to_batch[task.name] = batch_idx

    assert task_to_batch["discover"] < task_to_batch["parse"] < task_to_batch["render"]
    assert task_to_batch["assets"] < task_to_batch["health"]
    assert task_to_batch["render"] < task_to_batch["health"]


def test_execute_pipeline_respects_target_outputs() -> None:
    """execute_pipeline should run only tasks needed for target outputs."""

    @dataclass
    class _Ctx:
        executed: list[str]

    def _make_exec(name: str):
        def _exec(ctx: _Ctx) -> None:
            ctx.executed.append(name)

        return _exec

    tasks = [
        BuildTask(
            name="discover",
            requires=frozenset({"site"}),
            produces=frozenset({"pages"}),
            execute=_make_exec("discover"),
        ),
        BuildTask(
            name="parse",
            requires=frozenset({"pages"}),
            produces=frozenset({"parsed"}),
            execute=_make_exec("parse"),
        ),
        BuildTask(
            name="render",
            requires=frozenset({"parsed"}),
            produces=frozenset({"rendered_pages"}),
            execute=_make_exec("render"),
        ),
        BuildTask(
            name="assets",
            requires=frozenset({"site"}),
            produces=frozenset({"asset_manifest"}),
            execute=_make_exec("assets"),
        ),
    ]

    ctx = _Ctx(executed=[])
    result = execute_pipeline(
        tasks=tasks,
        ctx=ctx,
        initial_keys=frozenset({"site"}),
        target_outputs=frozenset({"asset_manifest"}),
        parallel=False,
    )

    assert result.success
    assert ctx.executed == ["assets"]


def test_scheduler_plan_for_rendered_pages_fast_uses_lean_chain() -> None:
    """Fast render target should prune related/index tasks."""
    scheduler = TaskScheduler(
        all_tasks(target_outputs=frozenset({"rendered_pages_fast"})),
        initial_keys=INITIAL_KEYS,
    )

    batches = scheduler.plan_for_outputs(frozenset({"rendered_pages_fast"}))
    task_names = {task.name for batch in batches for task in batch}

    assert "render_pages_targeted" in task_names
    assert "render_pages" not in task_names
    assert "build_related" not in task_names
    assert "build_indexes" not in task_names


def test_scheduler_prioritizes_critical_path_with_timing_hints() -> None:
    """Timing hints should prioritize longer downstream critical paths."""

    def _noop(_ctx: _DummyContext) -> None:
        return

    tasks = [
        BuildTask(
            name="root",
            requires=frozenset({"site"}),
            produces=frozenset({"root_out"}),
            execute=_noop,
        ),
        BuildTask(
            name="branch_heavy",
            requires=frozenset({"root_out"}),
            produces=frozenset({"heavy_out"}),
            execute=_noop,
        ),
        BuildTask(
            name="branch_light",
            requires=frozenset({"root_out"}),
            produces=frozenset({"light_out"}),
            execute=_noop,
        ),
        BuildTask(
            name="heavy_leaf",
            requires=frozenset({"heavy_out"}),
            produces=frozenset({"done_heavy"}),
            execute=_noop,
        ),
        BuildTask(
            name="light_leaf",
            requires=frozenset({"light_out"}),
            produces=frozenset({"done_light"}),
            execute=_noop,
        ),
    ]

    scheduler = TaskScheduler(
        tasks,
        initial_keys=frozenset({"site"}),
        task_durations_ms={
            "root": 1.0,
            "branch_heavy": 50.0,
            "branch_light": 5.0,
            "heavy_leaf": 100.0,
            "light_leaf": 1.0,
        },
    )

    # Batch 1 should contain both branch tasks with heavy branch first.
    branch_batch = scheduler.batches[1]
    assert [task.name for task in branch_batch] == ["branch_heavy", "branch_light"]
