"""WaveScheduler template_first grouping consumes BuildPlan (RFC handoff step 2)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from bengal.orchestration.build_context import BuildContext
from bengal.snapshots import create_site_snapshot
from bengal.snapshots.build_plan import BuildPlan, PagePlan, assemble_build_plan
from bengal.snapshots.scheduler import WaveScheduler


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
def test_template_first_stores_frozen_build_plan_with_page_html(site) -> None:
    scheduler = _scheduler(site)
    render_stats = scheduler.render_all(list(site.pages))

    plan = scheduler.build_plan
    assert isinstance(plan, BuildPlan)
    assert isinstance(plan.pages, tuple)
    assert any(page_plan.template_name == "page.html" for page_plan in plan.pages)
    with pytest.raises(FrozenInstanceError):
        plan.config_hash = "mutated"

    plan_by_source = {page_plan.source_path: page_plan for page_plan in plan.pages}
    page_html_count = 0
    for page in site.pages:
        page_plan = plan_by_source.get(str(page.source_path))
        if page_plan is not None and page_plan.template_name == "page.html":
            page_html_count += 1

    assert page_html_count > 0
    assert render_stats.template_batches["page.html"] == page_html_count


@pytest.mark.bengal(testroot="test-basic")
def test_plan_grouping_skips_live_resolver_when_page_is_in_plan(site, monkeypatch) -> None:
    def fail_resolve(page, default: str = "page.html") -> str:
        raise AssertionError("build_plan_missing_page leftover must not run for planned pages")

    monkeypatch.setattr("bengal.snapshots.scheduler.resolve_template_name", fail_resolve)

    scheduler = _scheduler(site)
    render_stats = scheduler.render_all(list(site.pages))

    assert render_stats.pages_rendered == len(site.pages)
    plan_by_source = {page_plan.source_path: page_plan for page_plan in scheduler.build_plan.pages}
    for page in site.pages:
        page_plan = plan_by_source[str(page.source_path)]
        if page_plan.template_name == "page.html":
            assert "page.html" in render_stats.template_batches


@pytest.mark.bengal(testroot="test-basic")
def test_render_template_first_calls_assemble_build_plan(site, monkeypatch) -> None:
    calls: list[tuple[object, str, str]] = []
    real = assemble_build_plan

    def wrapper(snapshot, *, config_hash: str, content_snapshot_id: str) -> BuildPlan:
        calls.append((snapshot, config_hash, content_snapshot_id))
        return real(
            snapshot,
            config_hash=config_hash,
            content_snapshot_id=content_snapshot_id,
        )

    monkeypatch.setattr("bengal.snapshots.build_plan.assemble_build_plan", wrapper)

    scheduler = _scheduler(site)
    scheduler.render_all(list(site.pages))

    assert len(calls) == 1
    snapshot, config_hash, content_snapshot_id = calls[0]
    assert snapshot is scheduler.snapshot
    assert config_hash == "unhashed"
    assert content_snapshot_id == str(scheduler.snapshot.snapshot_time)
    assert isinstance(scheduler.build_plan, BuildPlan)
    assert isinstance(scheduler.build_plan.pages[0], PagePlan)


@pytest.mark.bengal(testroot="test-basic")
def test_missing_plan_page_falls_back_to_resolve_template_name(site, monkeypatch) -> None:
    from bengal.snapshots.utils import resolve_template_name as real_resolve

    real = assemble_build_plan
    resolved: list[str] = []

    def empty_pages(snapshot, *, config_hash: str, content_snapshot_id: str) -> BuildPlan:
        plan = real(
            snapshot,
            config_hash=config_hash,
            content_snapshot_id=content_snapshot_id,
        )
        return BuildPlan(
            config_hash=plan.config_hash,
            content_snapshot_id=plan.content_snapshot_id,
            pages=(),
            sections=plan.sections,
            template_dependencies=plan.template_dependencies,
            generated_outputs=plan.generated_outputs,
        )

    def spy_resolve(page, default: str = "page.html") -> str:
        resolved.append(str(page.source_path))
        return real_resolve(page, default=default)

    monkeypatch.setattr("bengal.snapshots.build_plan.assemble_build_plan", empty_pages)
    monkeypatch.setattr("bengal.snapshots.scheduler.resolve_template_name", spy_resolve)

    scheduler = _scheduler(site)
    render_stats = scheduler.render_all(list(site.pages))

    assert render_stats.pages_rendered == len(site.pages)
    assert {str(page.source_path) for page in site.pages} == set(resolved)
    assert scheduler.build_plan.pages == ()
