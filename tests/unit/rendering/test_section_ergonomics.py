"""Tests for rendering-side Section ergonomic helpers."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.rendering.section_ergonomics import (
    aggregate_content,
    apply_section_template,
    recent_pages,
    word_count,
)

if TYPE_CHECKING:
    from pathlib import Path


def _page(
    tmp_path: Path,
    name: str,
    metadata: dict | None = None,
    content: str = "",
    html: str | None = None,
) -> Page:
    return Page(
        source_path=tmp_path / f"{name}.md",
        _raw_content=content,
        _raw_metadata={"title": name, **(metadata or {})},
        html_content=html,
    )


def test_recent_pages_direct_helper_sorts_dated_pages(tmp_path: Path) -> None:
    section = Section(name="blog", path=tmp_path / "blog")
    old = _page(tmp_path, "old", {"date": datetime(2025, 1, 1)})
    new = _page(tmp_path, "new", {"date": datetime(2025, 2, 1)})
    undated = _page(tmp_path, "undated")
    section.pages = [old, undated, new]

    assert recent_pages(section) == [new, old]


def test_section_recent_pages_shim_delegates_to_rendering_helper(tmp_path: Path) -> None:
    section = Section(name="blog", path=tmp_path / "blog")
    old = _page(tmp_path, "old", {"date": datetime(2025, 1, 1)})
    new = _page(tmp_path, "new", {"date": datetime(2025, 2, 1)})
    section.pages = [old, new]

    assert section.recent_pages(1) == [new]


def test_word_count_uses_template_content_surface(tmp_path: Path) -> None:
    section = Section(name="docs", path=tmp_path / "docs")
    page = _page(tmp_path, "page", html="<p>Hello <strong>rendered</strong> world</p>")
    section.pages = [page]

    assert word_count(section) == 3


def test_aggregate_content_collects_section_stats(tmp_path: Path) -> None:
    section = Section(name="docs", path=tmp_path / "docs")
    page = _page(tmp_path, "page", {"tags": ["python", "docs"]})
    section.pages = [page]

    assert aggregate_content(section) == {
        "page_count": 1,
        "total_page_count": 1,
        "subsection_count": 0,
        "tags": ["docs", "python"],
        "title": "Docs",
        "hierarchy": ["docs"],
    }


def test_apply_section_template_returns_index_page_rendered_html(tmp_path: Path) -> None:
    section = Section(name="docs", path=tmp_path / "docs")
    index_page = _page(tmp_path, "index")
    index_page.rendered_html = "<h1>Docs</h1>"
    section.index_page = index_page

    assert apply_section_template(section, template_engine=object()) == "<h1>Docs</h1>"
