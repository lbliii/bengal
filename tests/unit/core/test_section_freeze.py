"""
Tests for Section.freeze() phase separation.

Verifies that frozen sections:
- Reject mutations (add_page, add_subsection, sort_children_by_weight)
- Have pre-computed cached properties (no lazy computation during render)
- Are idempotent (calling freeze() twice is safe)
- Propagate freeze to child sections recursively
"""

from pathlib import Path

import pytest

from bengal.core.page import Page
from bengal.core.section import Section


def _make_section(tmp_path: Path, name: str = "blog") -> Section:
    """Create a section with a few pages for testing."""
    section = Section(name=name, path=tmp_path / name)
    for i in range(3):
        page = Page(
            source_path=tmp_path / name / f"post-{i}.md",
            _raw_content=f"Content {i}",
            _raw_metadata={"title": f"Post {i}", "weight": i, "tags": ["python"]},
        )
        section.add_page(page)
    return section


class TestFreezeGuards:
    """Frozen sections reject all mutations."""

    def test_add_page_raises_after_freeze(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        new_page = Page(
            source_path=tmp_path / "blog/new.md",
            _raw_content="New",
            _raw_metadata={"title": "New"},
        )
        with pytest.raises(RuntimeError, match="frozen Section"):
            section.add_page(new_page)

    def test_add_subsection_raises_after_freeze(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        child = Section(name="child", path=tmp_path / "child")
        with pytest.raises(RuntimeError, match="frozen Section"):
            section.add_subsection(child)

    def test_sort_children_by_weight_raises_after_freeze(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        with pytest.raises(RuntimeError, match="frozen Section"):
            section.sort_children_by_weight()

    def test_mutations_allowed_before_freeze(self, tmp_path):
        """Sanity check: mutations work normally before freeze."""
        section = _make_section(tmp_path)

        page = Page(
            source_path=tmp_path / "blog/extra.md",
            _raw_content="Extra",
            _raw_metadata={"title": "Extra"},
        )
        section.add_page(page)
        assert len(section.pages) == 4

        child = Section(name="child", path=tmp_path / "child")
        section.add_subsection(child)
        assert len(section.subsections) == 1

        section.sort_children_by_weight()


class TestFreezePreComputation:
    """Freeze eagerly computes all cached properties."""

    def test_sorted_pages_precomputed(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        assert "sorted_pages" in section.__dict__
        assert len(section.sorted_pages) == 3

    def test_regular_pages_precomputed(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        assert "regular_pages" in section.__dict__

    def test_content_pages_precomputed(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        assert "content_pages" in section.__dict__

    def test_tag_index_precomputed(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        assert "_tag_index" in section.__dict__
        assert len(section.pages_with_tag("python")) == 3

    def test_dated_pages_precomputed(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        assert "_dated_pages_sorted" in section.__dict__

    def test_featured_pages_precomputed(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        assert "_featured_pages_sorted" in section.__dict__

    def test_post_count_precomputed(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        assert "post_count" in section.__dict__
        assert section.post_count == 3

    def test_pages_converted_to_tuple(self, tmp_path):
        section = _make_section(tmp_path)
        assert isinstance(section.pages, list)

        section.freeze()
        assert isinstance(section.pages, tuple)

    def test_subsections_converted_to_tuple(self, tmp_path):
        parent = Section(name="parent", path=tmp_path / "parent")
        child = Section(name="child", path=tmp_path / "child")
        parent.add_subsection(child)
        assert isinstance(parent.subsections, list)

        parent.freeze()
        assert isinstance(parent.subsections, tuple)


class TestFreezeIdempotency:
    """Calling freeze() multiple times is safe."""

    def test_double_freeze_is_noop(self, tmp_path):
        section = _make_section(tmp_path)
        section.freeze()

        sorted_first = section.sorted_pages
        section.freeze()
        sorted_second = section.sorted_pages

        assert sorted_first is sorted_second

    def test_frozen_flag_set(self, tmp_path):
        section = _make_section(tmp_path)
        assert not section._frozen

        section.freeze()
        assert section._frozen


class TestFreezeRecursion:
    """Freeze propagates to all child sections."""

    def test_child_sections_frozen(self, tmp_path):
        parent = Section(name="parent", path=tmp_path / "parent")
        child = Section(name="child", path=tmp_path / "child")
        grandchild = Section(name="grandchild", path=tmp_path / "grandchild")

        child.add_subsection(grandchild)
        parent.add_subsection(child)

        for page_name in ("a", "b"):
            parent.add_page(
                Page(
                    source_path=tmp_path / f"parent/{page_name}.md",
                    _raw_content=page_name,
                    _raw_metadata={"title": page_name},
                )
            )
            child.add_page(
                Page(
                    source_path=tmp_path / f"child/{page_name}.md",
                    _raw_content=page_name,
                    _raw_metadata={"title": page_name},
                )
            )

        parent.freeze()

        assert parent._frozen
        assert child._frozen
        assert grandchild._frozen

    def test_child_caches_precomputed(self, tmp_path):
        parent = Section(name="parent", path=tmp_path / "parent")
        child = Section(name="child", path=tmp_path / "child")
        parent.add_subsection(child)

        child.add_page(
            Page(
                source_path=tmp_path / "child/post.md",
                _raw_content="Post",
                _raw_metadata={"title": "Post", "tags": ["test"]},
            )
        )

        parent.freeze()

        assert "sorted_pages" in child.__dict__
        assert "_tag_index" in child.__dict__
        assert len(child.pages_with_tag("test")) == 1

    def test_child_mutation_blocked_after_parent_freeze(self, tmp_path):
        parent = Section(name="parent", path=tmp_path / "parent")
        child = Section(name="child", path=tmp_path / "child")
        parent.add_subsection(child)

        parent.freeze()

        page = Page(
            source_path=tmp_path / "child/new.md",
            _raw_content="New",
            _raw_metadata={"title": "New"},
        )
        with pytest.raises(RuntimeError, match="frozen Section"):
            child.add_page(page)
