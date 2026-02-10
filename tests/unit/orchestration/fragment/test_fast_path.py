"""Tests for fragment fast-path service."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bengal.orchestration.fragment.fast_path import FragmentFastPathService


def _make_service(site: object) -> FragmentFastPathService:
    return FragmentFastPathService(
        site,
        classify_markdown_change=lambda _path: (True, False, set(), False),
        is_content_only_change=lambda _path: True,
        get_template_dirs=lambda: [Path("/templates")],
        is_in_template_dir=lambda _path, _dirs: True,
    )


def test_content_fast_path_requires_modified_events() -> None:
    site = SimpleNamespace(page_by_source_path={}, config={})
    service = _make_service(site)
    assert service.try_content_update({Path("docs/a.md")}, {"created"}) is False


def test_content_fast_path_requires_markdown_files() -> None:
    site = SimpleNamespace(page_by_source_path={}, config={})
    service = _make_service(site)
    assert service.try_content_update({Path("assets/a.css")}, {"modified"}) is False


def test_content_fast_path_fails_without_warm_page() -> None:
    site = SimpleNamespace(page_by_source_path={}, config={})
    service = _make_service(site)
    assert service.try_content_update({Path("docs/a.md")}, {"modified"}) is False


def test_template_fast_path_requires_html_files() -> None:
    site = SimpleNamespace(page_by_source_path={}, config={})
    service = _make_service(site)
    assert service.try_template_update({Path("styles/site.css")}, {"modified"}) is False


def test_template_fast_path_requires_template_dir_membership() -> None:
    site = SimpleNamespace(page_by_source_path={}, config={})
    service = FragmentFastPathService(
        site,
        classify_markdown_change=lambda _path: (True, False, set(), False),
        is_content_only_change=lambda _path: True,
        get_template_dirs=lambda: [Path("/templates")],
        is_in_template_dir=lambda _path, _dirs: False,
    )
    assert service.try_template_update({Path("/tmp/base.html")}, {"modified"}) is False
