"""BuildPlan supplies the live pipeline cache template key (#800 / #750 Option 1)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bengal.rendering.pipeline.output import determine_template
from bengal.snapshots.build_plan import BuildPlan, PagePlan


def _page(
    source_path: str | Path,
    *,
    metadata: dict[str, object] | None = None,
    template: str | None = None,
) -> SimpleNamespace:
    page = SimpleNamespace(source_path=source_path, metadata=metadata or {})
    if template is not None:
        page.template = template
    return page


def _plan(*pages: PagePlan) -> BuildPlan:
    return BuildPlan(
        config_hash="cfg",
        content_snapshot_id="snap",
        pages=pages,
        sections=(),
        template_dependencies={},
    )


def test_plan_hit_wins_over_leftover_type() -> None:
    page = _page(Path("content/blog/hello.md"), metadata={"type": "post"})
    plan = _plan(
        PagePlan(
            source_path="content/blog/hello.md",
            href="/blog/hello/",
            template_name="page.html",
        )
    )

    leftover = determine_template(page)
    planned = determine_template(page, build_plan=plan)

    assert leftover == "single.html"
    assert planned == "page.html"
    assert planned != leftover


def test_plan_miss_uses_leftover_type() -> None:
    page = _page("content/index.md", metadata={"type": "post"})
    plan = _plan(
        PagePlan(
            source_path="content/other.md",
            href="/other/",
            template_name="page.html",
        )
    )

    assert determine_template(page, build_plan=plan) == "single.html"


def test_build_plan_none_uses_leftover() -> None:
    page = _page("content/index.md", metadata={"type": "page"})

    assert determine_template(page, build_plan=None) == "page.html"


def test_determine_template_without_kwargs_still_works() -> None:
    page = _page("content/index.md", metadata={"type": "page"})

    assert determine_template(page) == "page.html"


def test_leftover_explicit_metadata_template() -> None:
    page = _page("content/index.md", metadata={"template": "custom.html", "type": "page"})

    assert determine_template(page) == "custom.html"
    assert determine_template(page, build_plan=None) == "custom.html"


def test_leftover_section_type() -> None:
    page = _page("content/blog/_index.md", metadata={"type": "section"})

    assert determine_template(page) == "list.html"


def test_leftover_page_template_attribute() -> None:
    page = _page("content/index.md", metadata={"type": "page"}, template="from-attr.html")

    assert determine_template(page) == "from-attr.html"
