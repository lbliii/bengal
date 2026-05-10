"""Tests for finalization task policy contracts."""

from __future__ import annotations

from bengal.orchestration.build.finalization_tasks import (
    FinalizationFailurePolicy,
    FinalizationTaskTier,
    blocking_finalization_task_names,
    default_finalization_task_specs,
)
from bengal.orchestration.build.options import BuildCompletionPolicy


def test_complete_policy_blocks_all_default_tasks() -> None:
    specs = default_finalization_task_specs()

    assert blocking_finalization_task_names(BuildCompletionPolicy.COMPLETE) == tuple(
        spec.name for spec in specs
    )


def test_serve_ready_blocks_only_browse_critical_tasks() -> None:
    assert blocking_finalization_task_names(BuildCompletionPolicy.SERVE_READY) == (
        "special_pages",
        "stats",
    )


def test_background_serve_tasks_are_nonfatal_warnings() -> None:
    background_specs = [
        spec
        for spec in default_finalization_task_specs()
        if not spec.blocks(BuildCompletionPolicy.SERVE_READY)
    ]

    assert background_specs
    assert {spec.tier for spec in background_specs} >= {
        FinalizationTaskTier.ARTIFACTS,
        FinalizationTaskTier.QUALITY,
        FinalizationTaskTier.PERSISTENCE,
    }
    assert all(spec.failure_policy is FinalizationFailurePolicy.WARN for spec in background_specs)
