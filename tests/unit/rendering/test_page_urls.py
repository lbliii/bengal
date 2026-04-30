"""Tests for rendering-side Page URL helpers."""

from __future__ import annotations

from pathlib import Path

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.rendering.page_urls import (
    get_absolute_href,
    get_href,
    get_path,
    path_from_output_relative_path,
)


def _page(output_path: Path | None = None) -> Page:
    return Page(
        source_path=Path("/site/content/docs/page.md"),
        _raw_metadata={"title": "Page"},
        output_path=output_path,
    )


def test_path_from_output_relative_path_strips_index_html() -> None:
    assert path_from_output_relative_path(Path("docs/page/index.html")) == "/docs/page/"


def test_path_from_output_relative_path_strips_html_suffix() -> None:
    assert path_from_output_relative_path(Path("docs/page.html")) == "/docs/page/"


def test_page_url_helpers_apply_baseurl() -> None:
    site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
    site.output_dir = Path("/site/public")
    page = _page(Path("/site/public/docs/page/index.html"))
    page._site = site

    assert get_path(page) == "/docs/page/"
    assert get_href(page) == "/bengal/docs/page/"
    assert page._path == "/docs/page/"
    assert page.href == "/bengal/docs/page/"


def test_page_url_helpers_use_absolute_origin() -> None:
    site = Site(root_path=Path("/site"), config={"baseurl": "https://example.com"})
    site.output_dir = Path("/site/public")
    page = _page(Path("/site/public/docs/page/index.html"))
    page._site = site

    assert get_absolute_href(page) == "https://example.com/docs/page/"
    assert page.absolute_href == "https://example.com/docs/page/"


def test_page_url_helpers_preserve_manual_overrides() -> None:
    page = _page()
    page.__dict__["href"] = "/manual/"
    page.__dict__["_path"] = "/manual-path/"

    assert get_href(page) == "/manual/"
    assert get_path(page) == "/manual-path/"


def test_page_url_helpers_fall_back_without_site_or_output_path() -> None:
    page = _page()

    assert get_path(page) == "/page/"
    assert get_href(page) == "/page/"
