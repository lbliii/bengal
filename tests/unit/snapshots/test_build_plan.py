"""Construction and immutability tests for frozen BuildPlan records."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from bengal.snapshots.build_plan import (
    BuildPlan,
    GeneratedOutputPlan,
    IncrementalPlan,
    PagePlan,
    SectionPlan,
)


def _sample_plan() -> BuildPlan:
    return BuildPlan(
        config_hash="cfg-abc",
        content_snapshot_id="snap-123",
        pages=(
            PagePlan(
                source_path="content/index.md",
                href="/",
                template_name="page.html",
            ),
            PagePlan(
                source_path="content/blog/hello.md",
                href="/blog/hello/",
                template_name="blog.html",
                section_path="blog",
            ),
        ),
        sections=(
            SectionPlan(
                path="blog",
                title="Blog",
                page_hrefs=("/blog/hello/",),
            ),
        ),
        template_dependencies={
            "page.html": ("base.html",),
            "blog.html": ("base.html", "macros.html"),
        },
        generated_outputs=(GeneratedOutputPlan(kind="sitemap", path="sitemap.xml"),),
    )


def test_build_plan_constructs_pages_sections_and_dependencies() -> None:
    plan = _sample_plan()

    assert plan.config_hash == "cfg-abc"
    assert plan.content_snapshot_id == "snap-123"
    assert len(plan.pages) == 2
    assert plan.pages[0].source_path == "content/index.md"
    assert plan.pages[1].section_path == "blog"
    assert plan.sections[0].title == "Blog"
    assert plan.sections[0].page_hrefs == ("/blog/hello/",)
    assert plan.template_dependencies["page.html"] == ("base.html",)
    assert plan.generated_outputs[0].kind == "sitemap"


def test_build_plan_is_frozen() -> None:
    plan = _sample_plan()

    with pytest.raises(FrozenInstanceError):
        plan.config_hash = "mutated"
    with pytest.raises(FrozenInstanceError):
        plan.pages[0].href = "/changed/"
    with pytest.raises(FrozenInstanceError):
        plan.sections[0].title = "Changed"
    with pytest.raises(TypeError):
        plan.template_dependencies["page.html"] = ("other.html",)


def test_build_plan_collections_are_immutable() -> None:
    plan = _sample_plan()

    assert isinstance(plan.pages, tuple)
    assert isinstance(plan.sections, tuple)
    assert isinstance(plan.generated_outputs, tuple)
    assert isinstance(plan.sections[0].page_hrefs, tuple)
    assert isinstance(plan.template_dependencies, MappingProxyType)
    assert isinstance(plan.template_dependencies["blog.html"], tuple)


def test_incremental_plan_wraps_build_plan() -> None:
    plan = _sample_plan()
    incremental = IncrementalPlan(
        build_plan=plan,
        changed_inputs=("content/blog/hello.md",),
        affected_pages=("/blog/hello/",),
        affected_outputs=("sitemap.xml",),
        fallback_reasons=(),
    )

    assert incremental.build_plan is plan
    assert incremental.changed_inputs == ("content/blog/hello.md",)
    assert incremental.affected_pages == ("/blog/hello/",)
    assert incremental.affected_outputs == ("sitemap.xml",)
    assert incremental.fallback_reasons == ()
    with pytest.raises(FrozenInstanceError):
        incremental.affected_pages = ("/other/",)


@pytest.mark.parallel_unsafe
def test_build_plan_parallel_reads_are_stable() -> None:
    plan = _sample_plan()

    def read_plan(_index: int) -> tuple[str, int, tuple[str, ...], str]:
        return (
            plan.config_hash,
            len(plan.pages),
            plan.template_dependencies["blog.html"],
            plan.pages[1].href,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(executor.map(read_plan, range(200)))

    assert len(set(results)) == 1
    assert results[0] == ("cfg-abc", 2, ("base.html", "macros.html"), "/blog/hello/")
