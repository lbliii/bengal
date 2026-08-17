"""WaveScheduler stashes frozen BuildPlan on live BuildContext (RFC handoff)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from bengal.orchestration.build_context import BuildContext
from bengal.snapshots import create_site_snapshot
from bengal.snapshots.build_plan import BuildPlan, PagePlan
from bengal.snapshots.scheduler import WaveScheduler
from bengal.utils.observability.logger import get_logger


def _scheduler(site) -> WaveScheduler:
    snapshot = create_site_snapshot(site)
    stats = MagicMock()
    build_context = BuildContext(
        site=site,
        pages=site.pages,
        stats=stats,
    )
    build_context.snapshot = snapshot
    return WaveScheduler(
        snapshot=snapshot,
        site=site,
        quiet=True,
        stats=stats,
        build_context=build_context,
        max_workers=2,
    )


@pytest.mark.bengal(testroot="test-basic")
def test_template_first_stashes_frozen_plan_on_build_context(site) -> None:
    scheduler = _scheduler(site)
    logger = get_logger("bengal.snapshots.scheduler")
    events_before = len(logger.get_events())

    scheduler.render_all(list(site.pages))

    plan = scheduler.build_plan
    assert isinstance(plan, BuildPlan)
    with pytest.raises(FrozenInstanceError):
        plan.config_hash = "mutated"
    assert scheduler.build_context.build_plan is scheduler.build_plan
    assert any(
        isinstance(page_plan, PagePlan) and page_plan.template_name == "page.html"
        for page_plan in plan.pages
    )

    leftover_events = [
        event
        for event in logger.get_events()[events_before:]
        if event.event_type == "render_uses_mutable_site"
    ]
    assert len(leftover_events) == 1


@pytest.mark.bengal(testroot="test-basic")
def test_template_first_renders_when_build_context_is_none(site) -> None:
    snapshot = create_site_snapshot(site)
    stats = MagicMock()
    scheduler = WaveScheduler(
        snapshot=snapshot,
        site=site,
        quiet=True,
        stats=stats,
        build_context=None,
        max_workers=2,
    )
    logger = get_logger("bengal.snapshots.scheduler")
    events_before = len(logger.get_events())

    render_stats = scheduler.render_all(list(site.pages))

    assert scheduler.build_context is None
    assert isinstance(scheduler.build_plan, BuildPlan)
    assert render_stats.pages_rendered == len(site.pages)
    leftover_events = [
        event
        for event in logger.get_events()[events_before:]
        if event.event_type == "render_uses_mutable_site"
    ]
    assert len(leftover_events) == 1
