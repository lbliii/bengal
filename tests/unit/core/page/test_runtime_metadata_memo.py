"""Regression tests for RuntimePage.metadata section-path memoization (#307).

``metadata`` is read hundreds of times per page during rendering. The relative
section path it feeds to the cascade is memoized per site so the ``relative_to``
resolution is not redone on every access. These tests pin that the memo is
correct (cache hit returns the same cascade-merged value) and is invalidated when
the page's section changes.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bengal.core.cascade import CascadeSnapshot
from tests._testing import make_test_page

pytestmark = pytest.mark.parallel_unsafe


def _site_with_cascade(root: Path) -> SimpleNamespace:
    content = root / "content"
    snapshot = CascadeSnapshot(
        _data={
            "docs": {"layout": "doc-layout"},
            "blog": {"layout": "blog-layout"},
        },
        _content_dir=str(content),
    )
    return SimpleNamespace(cascade=snapshot, root_path=root)


def _section(root: Path, name: str) -> SimpleNamespace:
    return SimpleNamespace(path=root / "content" / name, name=name, _path=f"/{name}/")


def test_metadata_resolves_cascade_for_section() -> None:
    root = Path("/site")
    site = _site_with_cascade(root)
    page = make_test_page(site=site, section=_section(root, "docs"), metadata={"title": "T"})

    # Cascade value for the "docs" section is surfaced through metadata.
    assert page.metadata.get("layout") == "doc-layout"


def test_section_path_is_memoized_after_first_access() -> None:
    root = Path("/site")
    site = _site_with_cascade(root)
    page = make_test_page(site=site, section=_section(root, "docs"), metadata={"title": "T"})

    assert page._section_path_rel_cache is None
    # First access computes and memoizes the relative section path.
    assert page.metadata.get("layout") == "doc-layout"
    assert page._section_path_rel_cache == "docs"
    assert page._section_path_rel_site == id(site)

    # Repeated access is a cache hit and returns the same resolved value.
    for _ in range(5):
        assert page.metadata.get("layout") == "doc-layout"
    assert page._section_path_rel_cache == "docs"


def test_section_change_invalidates_memo_and_reresolves() -> None:
    root = Path("/site")
    site = _site_with_cascade(root)
    page = make_test_page(site=site, section=_section(root, "docs"), metadata={"title": "T"})

    assert page.metadata.get("layout") == "doc-layout"
    assert page._section_path_rel_cache == "docs"

    # Reassigning the section must clear the memo so the cascade re-resolves.
    page._section = _section(root, "blog")
    assert page._section_path_rel_cache is None
    assert page.metadata.get("layout") == "blog-layout"
    assert page._section_path_rel_cache == "blog"


def test_no_section_returns_empty_relative_path() -> None:
    root = Path("/site")
    site = _site_with_cascade(root)
    page = make_test_page(site=site, metadata={"title": "T"})

    # With no section path, the helper returns "" and never calls relative_to.
    assert page._relative_section_path() == ""
