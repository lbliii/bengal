"""
Build task definition for the data-driven pipeline.

A BuildTask is a declarative unit of work: it names the data it reads
(``requires``) and the data it produces (``produces``).  The scheduler
uses these declarations to compute a dependency DAG and parallel
execution batches -- tasks never need to know their execution order.

See Also:
    bengal.orchestration.pipeline.scheduler: DAG scheduling
    bengal.orchestration.pipeline.executor: Batch execution
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


@dataclass(frozen=True, slots=True)
class BuildTask:
    """
    A declarative build task for the data-driven pipeline.

    Each task declares what data it requires and produces.  The
    :class:`~bengal.orchestration.pipeline.scheduler.TaskScheduler`
    uses these declarations to compute the dependency DAG and execution
    order.  Tasks whose outputs another task requires are guaranteed to
    run first.

    Attributes:
        name: Human-readable task name (used in logs and CLI output).
        requires: Logical data keys this task reads from the build context.
        produces: Logical data keys this task writes to the build context.
        execute: Callable that performs the task's work, receiving the
            shared :class:`~bengal.orchestration.build_context.BuildContext`.
        skip_if: Optional predicate.  When it returns ``True`` the task
            is skipped entirely and its ``produces`` keys are **not**
            guaranteed to be populated.

    Example::

        check_config_task = BuildTask(
            name="check_config",
            requires=frozenset({"config", "cache"}),
            produces=frozenset({"config_check_result"}),
            execute=_run_check_config,
            skip_if=None,  # always runs (fast)
        )
    """

    name: str
    requires: frozenset[str]
    produces: frozenset[str]
    execute: Callable[[BuildContext], None]
    skip_if: Callable[[BuildContext], bool] | None = None

    def __repr__(self) -> str:
        skip = "yes" if self.skip_if is not None else "no"
        return (
            f"BuildTask(name={self.name!r}, "
            f"requires={len(self.requires)}, "
            f"produces={len(self.produces)}, "
            f"skip={skip})"
        )
