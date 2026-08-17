"""Incremental cache records the same template key as live process_page (#802)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bengal.cache.build_cache import BuildCache
from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.rendering.pipeline.output import determine_template
from bengal.snapshots.build_plan import BuildPlan, PagePlan

_BLOG_PAGE = "content/blog/hello.md"
_PLAN_TEMPLATE = "page.html"  # #750 WaveScheduler consumer
_LEFTOVER_TYPE = "post"  # leftover determine_template → single.html


def _page(source_path: str = _BLOG_PAGE) -> SimpleNamespace:
    return SimpleNamespace(source_path=Path(source_path), metadata={"type": _LEFTOVER_TYPE})


def _plan(*pages: PagePlan) -> BuildPlan:
    return BuildPlan(
        config_hash="cfg",
        content_snapshot_id="snap",
        pages=pages,
        sections=(),
        template_dependencies={},
    )


def _manager(tmp_path: Path) -> CacheManager:
    site = SimpleNamespace(root_path=tmp_path)
    manager = CacheManager(site)
    manager.cache = BuildCache(site_root=tmp_path)
    return manager


def test_records_page_plan_template_name_when_plan_present(tmp_path: Path) -> None:
    """Matching PagePlan supplies page.html; leftover type would pick single.html."""
    page = _page()
    leftover = determine_template(page)
    plan = _plan(
        PagePlan(source_path=_BLOG_PAGE, href="/blog/hello/", template_name=_PLAN_TEMPLATE)
    )
    manager = _manager(tmp_path)

    with patch(
        "bengal.rendering.pipeline.output.determine_template",
        wraps=determine_template,
    ) as spy:
        manager._record_page_template_deps([page], SimpleNamespace(build_plan=plan))

    recorded = manager.cache.template_dependencies[str(page.source_path)]
    assert leftover == "single.html"
    assert leftover != _PLAN_TEMPLATE
    assert _PLAN_TEMPLATE in recorded
    assert leftover not in recorded
    spy.assert_called_once()
    assert spy.call_args.kwargs["build_plan"] is plan


def test_leftover_when_build_context_is_none(tmp_path: Path) -> None:
    """No build_context: leftover determine_template(page) still runs."""
    page = _page()
    leftover = determine_template(page)
    manager = _manager(tmp_path)

    with patch(
        "bengal.rendering.pipeline.output.determine_template",
        wraps=determine_template,
    ) as spy:
        manager._record_page_template_deps([page], None)

    recorded = manager.cache.template_dependencies[str(page.source_path)]
    assert leftover == "single.html"
    assert leftover in recorded
    spy.assert_called_once()
    assert spy.call_args.kwargs["build_plan"] is None


def test_leftover_when_plan_pages_empty(tmp_path: Path) -> None:
    """Empty BuildPlan.pages: leftover type still selects the cache key."""
    page = _page()
    leftover = determine_template(page)
    manager = _manager(tmp_path)
    empty_plan = _plan()

    with patch(
        "bengal.rendering.pipeline.output.determine_template",
        wraps=determine_template,
    ) as spy:
        manager._record_page_template_deps([page], SimpleNamespace(build_plan=empty_plan))

    recorded = manager.cache.template_dependencies[str(page.source_path)]
    assert leftover == "single.html"
    assert leftover != _PLAN_TEMPLATE
    assert leftover in recorded
    spy.assert_called_once()
    assert spy.call_args.kwargs["build_plan"] is empty_plan
    assert leftover == determine_template(page, build_plan=None)
