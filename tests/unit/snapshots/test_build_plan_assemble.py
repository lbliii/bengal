"""Assemble BuildPlan from a frozen SiteSnapshot (construction-only)."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from bengal.snapshots.build_plan import assemble_build_plan
from bengal.snapshots.types import (
    NavigationPlan,
    PageSnapshot,
    RenderSchedule,
    SectionSnapshot,
    SiteSnapshot,
    TaxonomyPlan,
)


def _page_snapshot(
    *,
    source_path: str,
    href: str,
    template_name: str,
    section: SectionSnapshot | None = None,
) -> PageSnapshot:
    return PageSnapshot(
        title=Path(source_path).stem,
        href=href,
        source_path=Path(source_path),
        output_path=Path(f"public{href}index.html"),
        template_name=template_name,
        content="",
        parsed_html="",
        toc="",
        toc_items=(),
        excerpt="",
        meta_description="",
        metadata=MappingProxyType({}),
        tags=(),
        categories=(),
        reading_time=1,
        word_count=10,
        excerpt_words=150,
        content_hash=source_path,
        section=section,
    )


def _section_snapshot(
    *,
    path: Path | None,
    href: str,
    title: str,
    pages: tuple[PageSnapshot, ...] = (),
) -> SectionSnapshot:
    return SectionSnapshot(
        name=title.lower(),
        title=title,
        nav_title=title,
        href=href,
        path=path,
        pages=pages,
        sorted_pages=pages,
        regular_pages=pages,
        subsections=(),
        sorted_subsections=(),
    )


def _site_snapshot(
    *,
    pages: tuple[PageSnapshot, ...],
    sections: tuple[SectionSnapshot, ...],
    template_dependency_graph: MappingProxyType[str, frozenset[str]],
) -> SiteSnapshot:
    return SiteSnapshot(
        pages=pages,
        regular_pages=pages,
        sections=sections,
        root_section=_section_snapshot(path=None, href="/", title="Root"),
        config=MappingProxyType({}),
        params=MappingProxyType({}),
        data=MappingProxyType({}),
        navigation=NavigationPlan(menus=MappingProxyType({})),
        taxonomy=TaxonomyPlan(taxonomies=MappingProxyType({})),
        schedule=RenderSchedule(
            topological_order=(),
            template_groups=MappingProxyType({}),
            attention_order=pages,
            scout_hints=(),
            template_dependency_graph=template_dependency_graph,
        ),
        snapshot_time=0.0,
        page_count=len(pages),
        section_count=len(sections),
    )


def _minimal_snapshot() -> SiteSnapshot:
    blog_meta = _section_snapshot(path=Path("content/blog"), href="/blog/", title="Blog")
    tags_meta = _section_snapshot(path=None, href="/tags/", title="Tags")
    index = _page_snapshot(
        source_path="content/index.md",
        href="/",
        template_name="page.html",
    )
    hello = _page_snapshot(
        source_path="content/blog/hello.md",
        href="/blog/hello/",
        template_name="blog.html",
        section=blog_meta,
    )
    tagged = _page_snapshot(
        source_path="content/tags.md",
        href="/tags/",
        template_name="page.html",
        section=tags_meta,
    )
    blog = _section_snapshot(
        path=Path("content/blog"),
        href="/blog/",
        title="Blog",
        pages=(hello,),
    )
    return _site_snapshot(
        pages=(index, hello, tagged),
        sections=(blog,),
        template_dependency_graph=MappingProxyType(
            {
                "blog.html": frozenset({"macros.html", "base.html"}),
                "page.html": frozenset({"base.html"}),
            }
        ),
    )


def test_assemble_build_plan_maps_pages_sections_and_dependencies() -> None:
    snapshot = _minimal_snapshot()

    plan = assemble_build_plan(
        snapshot,
        config_hash="cfg-from-caller",
        content_snapshot_id="snap-from-caller",
    )

    assert plan.config_hash == "cfg-from-caller"
    assert plan.content_snapshot_id == "snap-from-caller"
    assert plan.generated_outputs == ()
    assert len(plan.pages) == 3
    assert len(plan.sections) == 1

    assert plan.pages[0].source_path == "content/index.md"
    assert plan.pages[0].href == "/"
    assert plan.pages[0].template_name == "page.html"
    assert plan.pages[0].section_path is None

    assert plan.pages[1].href == "/blog/hello/"
    assert plan.pages[1].template_name == "blog.html"
    assert plan.pages[1].section_path == "content/blog"

    assert plan.pages[2].section_path == "/tags/"

    assert plan.sections[0].path == "content/blog"
    assert plan.sections[0].title == "Blog"
    assert plan.sections[0].page_hrefs == ("/blog/hello/",)

    assert plan.template_dependencies["blog.html"] == ("base.html", "macros.html")
    assert plan.template_dependencies["page.html"] == ("base.html",)
    assert tuple(plan.template_dependencies) == ("blog.html", "page.html")


def test_assemble_build_plan_is_frozen() -> None:
    plan = assemble_build_plan(
        _minimal_snapshot(),
        config_hash="cfg",
        content_snapshot_id="snap",
    )

    with pytest.raises(FrozenInstanceError):
        plan.config_hash = "mutated"
    with pytest.raises(FrozenInstanceError):
        plan.pages[0].href = "/changed/"
    with pytest.raises(FrozenInstanceError):
        plan.sections[0].title = "Changed"
    with pytest.raises(TypeError):
        plan.template_dependencies["page.html"] = ("other.html",)
    with pytest.raises(TypeError):
        plan.sections[0].page_hrefs[0] = "/changed/"


def test_assemble_build_plan_collections_are_immutable() -> None:
    plan = assemble_build_plan(
        _minimal_snapshot(),
        config_hash="cfg",
        content_snapshot_id="snap",
    )

    assert isinstance(plan.pages, tuple)
    assert isinstance(plan.sections, tuple)
    assert isinstance(plan.generated_outputs, tuple)
    assert isinstance(plan.sections[0].page_hrefs, tuple)
    assert isinstance(plan.template_dependencies, MappingProxyType)
    assert isinstance(plan.template_dependencies["blog.html"], tuple)
