"""WaveScheduler page.html HTML parity: BuildPlan grouping vs leftover resolver.

Landing rule 2 for RFC snapshot BuildPlan handoff. Grouping source must not
change rendered HTML; render still uses mutable ``self.site``.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from bengal.orchestration.build_context import BuildContext
from bengal.snapshots import create_site_snapshot
from bengal.snapshots.build_plan import BuildPlan, assemble_build_plan
from bengal.snapshots.scheduler import WaveScheduler

_CONTENT_HASH_RE = re.compile(r'<meta name="bengal:content-hash" content="[0-9a-f]+">')


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
        max_workers=1,
    )


def _stripped_html(html: str) -> str:
    return _CONTENT_HASH_RE.sub("", html.strip())


def _page_html_source_paths(site, plan: BuildPlan) -> list[str]:
    plan_by_source = {page_plan.source_path: page_plan for page_plan in plan.pages}
    return [
        str(page.source_path)
        for page in site.pages
        if (page_plan := plan_by_source.get(str(page.source_path))) is not None
        and page_plan.template_name == "page.html"
    ]


def _capture_html(site, source_paths: list[str]) -> dict[str, str]:
    wanted = set(source_paths)
    captured: dict[str, str] = {}
    for page in site.pages:
        key = str(page.source_path)
        if key not in wanted:
            continue
        assert page.output_path is not None
        captured[key] = _stripped_html(page.output_path.read_text(encoding="utf-8"))
    return captured


@pytest.mark.bengal(testroot="test-basic")
def test_page_html_grouping_parity_build_plan_vs_leftover(site, monkeypatch) -> None:
    plan_scheduler = _scheduler(site)
    plan_scheduler.render_all(list(site.pages))

    plan = plan_scheduler.build_plan
    assert any(page_plan.template_name == "page.html" for page_plan in plan.pages)

    page_html_paths = _page_html_source_paths(site, plan)
    assert page_html_paths
    plan_html = _capture_html(site, page_html_paths)
    assert all(len(html) > 0 for html in plan_html.values())

    from bengal.snapshots.utils import resolve_template_name as real_resolve

    real = assemble_build_plan
    resolved: list[str] = []

    def empty_pages(snapshot, *, config_hash: str, content_snapshot_id: str) -> BuildPlan:
        assembled = real(
            snapshot,
            config_hash=config_hash,
            content_snapshot_id=content_snapshot_id,
        )
        return BuildPlan(
            config_hash=assembled.config_hash,
            content_snapshot_id=assembled.content_snapshot_id,
            pages=(),
            sections=assembled.sections,
            template_dependencies=assembled.template_dependencies,
            generated_outputs=assembled.generated_outputs,
        )

    def spy_resolve(page, default: str = "page.html") -> str:
        resolved.append(str(page.source_path))
        return real_resolve(page, default=default)

    monkeypatch.setattr("bengal.snapshots.build_plan.assemble_build_plan", empty_pages)
    monkeypatch.setattr("bengal.snapshots.scheduler.resolve_template_name", spy_resolve)

    leftover_scheduler = _scheduler(site)
    leftover_scheduler.render_all(list(site.pages))

    assert resolved
    leftover_html = _capture_html(site, page_html_paths)
    for source_path in page_html_paths:
        leftover = leftover_html[source_path]
        assert len(leftover) > 0
        assert plan_html[source_path] == leftover
