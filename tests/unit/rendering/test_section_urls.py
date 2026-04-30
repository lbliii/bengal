"""Tests for rendering-side Section URL helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.rendering.section_urls import (
    apply_version_path_transform,
    get_absolute_href,
    get_href,
    get_path,
    subsection_index_urls,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_section_url_helpers_apply_baseurl(tmp_path: Path) -> None:
    site = Site(root_path=tmp_path, config={"baseurl": "/bengal"})
    section = Section(name="docs", path=tmp_path / "content" / "docs")
    section._site = site

    assert get_path(section) == "/docs/"
    assert get_href(section) == "/bengal/docs/"
    assert section._path == "/docs/"
    assert section.href == "/bengal/docs/"


def test_section_url_helpers_use_absolute_origin(tmp_path: Path) -> None:
    site = Site(root_path=tmp_path, config={"baseurl": "https://example.com"})
    section = Section(name="docs", path=tmp_path / "content" / "docs")
    section._site = site

    assert get_absolute_href(section) == "https://example.com/docs/"
    assert section.absolute_href == "https://example.com/docs/"


def test_section_url_helpers_handle_virtual_section(tmp_path: Path) -> None:
    section = Section.create_virtual("api", "/api/python/")
    section._site = Site(root_path=tmp_path, config={"baseurl": "/docs"})

    assert get_path(section) == "/api/python/"
    assert get_href(section) == "/docs/api/python/"


def test_subsection_index_urls_uses_page_paths(tmp_path: Path) -> None:
    parent = Section(name="docs", path=tmp_path / "content" / "docs")
    child = Section(name="api", path=tmp_path / "content" / "docs" / "api")
    parent.add_subsection(child)
    child.index_page = Page(
        source_path=tmp_path / "content" / "docs" / "api" / "_index.md",
        _raw_metadata={"title": "API"},
    )
    child.index_page.__dict__["_path"] = "/docs/api/"

    assert subsection_index_urls(parent) == {"/docs/api/"}
    assert parent.subsection_index_urls == {"/docs/api/"}


def test_version_path_transform_moves_non_latest_version(tmp_path: Path) -> None:
    section = Section(name="about", path=tmp_path / "content" / "_versions" / "v1" / "docs")
    section._site = SimpleNamespace(
        versioning_enabled=True,
        version_config=SimpleNamespace(
            get_version=lambda version_id: (
                SimpleNamespace(latest=False) if version_id == "v1" else None
            )
        ),
    )

    assert apply_version_path_transform(section, "/_versions/v1/docs/about/") == "/docs/v1/about/"
    assert section._apply_version_path_transform("/_versions/v1/docs/about/") == "/docs/v1/about/"


def test_version_path_transform_removes_latest_version(tmp_path: Path) -> None:
    section = Section(name="about", path=tmp_path / "content" / "_versions" / "v3" / "docs")
    section._site = SimpleNamespace(
        versioning_enabled=True,
        version_config=SimpleNamespace(
            get_version=lambda version_id: (
                SimpleNamespace(latest=True) if version_id == "v3" else None
            )
        ),
    )

    assert apply_version_path_transform(section, "/_versions/v3/docs/about/") == "/docs/about/"
