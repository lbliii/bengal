"""
Task registry for the data-driven build pipeline.

Each module in this package defines one :class:`~bengal.orchestration.pipeline.task.BuildTask`.
Call :func:`all_tasks` to get the full ordered list for
:class:`~bengal.orchestration.pipeline.scheduler.TaskScheduler`.

The ``INITIAL_KEYS`` constant lists keys that are available on
:class:`~bengal.orchestration.build_context.BuildContext` *before*
any task runs (populated by the build setup code).
"""

from __future__ import annotations

from bengal.orchestration.pipeline.task import BuildTask

# Keys available on BuildContext before the pipeline starts.
# The scheduler uses these to validate that every task's ``requires``
# can be satisfied.
INITIAL_KEYS: frozenset[str] = frozenset({
    "site",
    "options",
    "cache",
    "stats",
    "cli",
    "orchestrator",
    "build_start",
    "output_collector",
})


def all_tasks(target_outputs: frozenset[str] | None = None) -> list[BuildTask]:
    """
    Return every registered build task.

    Order does not matter -- the scheduler computes execution order from
    ``requires`` / ``produces`` declarations.
    """
    from bengal.orchestration.tasks.assets import TASK as assets_task
    from bengal.orchestration.tasks.cache import TASK as cache_task
    from bengal.orchestration.tasks.config import TASK as config_task
    from bengal.orchestration.tasks.discovery import TASK as discovery_task
    from bengal.orchestration.tasks.filtering import TASK as filtering_task
    from bengal.orchestration.tasks.fonts import TASK as fonts_task
    from bengal.orchestration.tasks.health import TASK as health_task
    from bengal.orchestration.tasks.indexes import TASK as indexes_task
    from bengal.orchestration.tasks.menus import TASK as menus_task
    from bengal.orchestration.tasks.parsing import TASK as parsing_task
    from bengal.orchestration.tasks.postprocess import TASK as postprocess_task
    from bengal.orchestration.tasks.related import TASK as related_task
    from bengal.orchestration.tasks.rendering import TASK as rendering_task
    from bengal.orchestration.tasks.rendering_targeted import TASK as rendering_targeted_task
    from bengal.orchestration.tasks.sections import TASK as sections_task
    from bengal.orchestration.tasks.taxonomy import TASK as taxonomy_task
    from bengal.orchestration.tasks.validation import TASK as validation_task

    use_targeted_render = bool(
        target_outputs
        and target_outputs.issubset(frozenset({"rendered_pages_fast"}))
    )

    common_tasks = [
        config_task,
        fonts_task,
        discovery_task,
        filtering_task,
        sections_task,
        taxonomy_task,
        menus_task,
        related_task,
        indexes_task,
        parsing_task,
        assets_task,
        validation_task,
    ]

    if use_targeted_render:
        return [*common_tasks, rendering_targeted_task]

    return [*common_tasks, rendering_task, postprocess_task, health_task, cache_task]
