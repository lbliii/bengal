"""Listing cached properties return immutable tuples.

Template-facing ``page.authors`` and Section listing helpers must not return
mutable lists: a raced ``@cached_property`` write during parallel render can
drop one thread's list. Tuples keep iteration/len/index working while making
in-place mutation fail.
"""

from __future__ import annotations

from operator import setitem
from typing import TYPE_CHECKING, Any

import pytest

from bengal.core.section import Section
from tests._testing.mocks import make_mock_page as _page
from tests._testing.page_records import make_test_page

if TYPE_CHECKING:
    from pathlib import Path


def _assert_immutable_tuple(value: object) -> None:
    assert isinstance(value, tuple)
    with pytest.raises(AttributeError):
        value.append(None)
    with pytest.raises(TypeError):
        setitem(value, 0, None)


def test_page_authors_is_immutable_tuple() -> None:
    page = make_test_page(
        metadata={"author": "Ada Lovelace", "authors": [{"name": "Grace Hopper"}]},
    )
    authors = page.authors

    _assert_immutable_tuple(authors)
    assert len(authors) == 2
    assert authors[0].name == "Ada Lovelace"
    assert authors[1].name == "Grace Hopper"
    assert [author.name for author in authors] == ["Ada Lovelace", "Grace Hopper"]


def test_page_authors_empty_is_tuple() -> None:
    page = make_test_page(metadata={"title": "No authors"})
    authors = page.authors

    _assert_immutable_tuple(authors)
    assert authors == ()
    assert len(authors) == 0


def test_section_listing_properties_are_immutable_tuples(tmp_path: Path) -> None:
    root = Section(name="docs", path=tmp_path / "docs")
    child = Section(
        name="guides",
        path=tmp_path / "docs/guides",
        metadata={"title": "Guides", "weight": 1},
    )
    root.add_subsection(child)

    first = _page(
        source_path=tmp_path / "docs/first.md",
        _raw_content="First",
        _raw_metadata={"title": "First", "weight": 2},
    )
    second = _page(
        source_path=tmp_path / "docs/second.md",
        _raw_content="Second",
        _raw_metadata={"title": "Second", "weight": 1},
    )
    nested = _page(
        source_path=tmp_path / "docs/guides/nested.md",
        _raw_content="Nested",
        _raw_metadata={"title": "Nested"},
    )
    root.add_page(first)
    root.add_page(second)
    child.add_page(nested)

    listings: dict[str, Any] = {
        "sorted_pages": root.sorted_pages,
        "regular_pages": root.regular_pages,
        "regular_pages_recursive": root.regular_pages_recursive,
        "sorted_subsections": root.sorted_subsections,
        "content_pages": root.content_pages,
    }
    for name, value in listings.items():
        _assert_immutable_tuple(value)
        assert len(value) >= 1, name
        assert value[0] is not None
        assert list(value) == [*value]

    assert root.sorted_pages[0] is second
    assert root.sorted_pages[1] is first
    assert root.regular_pages == root.sorted_pages
    assert root.content_pages == root.sorted_pages
    assert nested in root.regular_pages_recursive
    assert root.sorted_subsections[0] is child
