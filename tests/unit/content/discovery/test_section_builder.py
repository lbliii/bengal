"""
Unit tests for SectionBuilder.

Tests: nested section hierarchy, section ordering, root section creation,
sections with _index.md, add_versioned_sections_recursive, get_top_level_counts.
"""

from __future__ import annotations

from pathlib import Path

from bengal.content.discovery.section_builder import SectionBuilder
from bengal.core.page import Page


class TestSectionBuilderCreateSection:
    """Test create_section."""

    def test_create_section_uses_dir_name(self, tmp_path: Path) -> None:
        """create_section uses directory name by default."""
        builder = SectionBuilder()
        section = builder.create_section(tmp_path / "blog")
        assert section.name == "blog"
        assert section.path == tmp_path / "blog"

    def test_create_section_with_name_override(self, tmp_path: Path) -> None:
        """create_section accepts name override."""
        builder = SectionBuilder()
        section = builder.create_section(tmp_path / "blog", name="articles")
        assert section.name == "articles"


class TestSectionBuilderAddSection:
    """Test add_section behavior."""

    def test_add_section_with_pages(self, tmp_path: Path) -> None:
        """Section with pages is added."""
        builder = SectionBuilder()
        section = builder.create_section(tmp_path / "blog")
        page = Page(source_path=tmp_path / "post.md", _raw_content="", _raw_metadata={})
        section.add_page(page)
        builder.add_section(section)
        assert section in builder.sections

    def test_add_section_with_subsections(self, tmp_path: Path) -> None:
        """Section with subsections is added."""
        builder = SectionBuilder()
        parent = builder.create_section(tmp_path / "docs")
        child = builder.create_section(tmp_path / "docs" / "api")
        parent.add_subsection(child)
        builder.add_section(parent)
        assert parent in builder.sections

    def test_add_section_empty_not_added(self, tmp_path: Path) -> None:
        """Empty section (no pages, no subsections) is not added."""
        builder = SectionBuilder()
        section = builder.create_section(tmp_path / "empty")
        builder.add_section(section)
        assert section not in builder.sections


class TestSectionBuilderSortAllSections:
    """Test sort_all_sections."""

    def test_sort_by_weight(self, tmp_path: Path) -> None:
        """Sections are sorted by weight then title."""
        builder = SectionBuilder()
        s1 = builder.create_section(tmp_path / "z")
        s1.metadata["weight"] = 10
        s2 = builder.create_section(tmp_path / "a")
        s2.metadata["weight"] = 5
        s3 = builder.create_section(tmp_path / "m")
        s3.metadata["weight"] = 5
        builder.sections = [s1, s2, s3]
        builder.sort_all_sections()
        names = [s.name for s in builder.sections]
        assert names == ["a", "m", "z"]

    def test_sort_default_weight_zero(self, tmp_path: Path) -> None:
        """Sections without weight default to 0."""
        builder = SectionBuilder()
        s = builder.create_section(tmp_path / "x")
        builder.sections = [s]
        builder.sort_all_sections()
        assert builder.sections[0].name == "x"


class TestSectionBuilderGetTopLevelCounts:
    """Test get_top_level_counts."""

    def test_top_level_sections_count(self, tmp_path: Path) -> None:
        """Counts top-level sections."""
        builder = SectionBuilder()
        s1 = builder.create_section(tmp_path / "a")
        s1.add_page(Page(source_path=tmp_path / "p1.md", _raw_content="", _raw_metadata={}))
        s2 = builder.create_section(tmp_path / "b")
        builder.sections = [s1, s2]
        builder.pages = list(s1.pages)
        top_sections, top_pages = builder.get_top_level_counts()
        assert top_sections == 2
        assert top_pages == 0

    def test_top_level_pages_count(self, tmp_path: Path) -> None:
        """Counts pages not in any section."""
        builder = SectionBuilder()
        p = Page(source_path=tmp_path / "root.md", _raw_content="", _raw_metadata={})
        builder.pages = [p]
        builder.sections = []
        top_sections, top_pages = builder.get_top_level_counts()
        assert top_sections == 0
        assert top_pages == 1


class TestSectionBuilderAddVersionedSectionsRecursive:
    """Test add_versioned_sections_recursive."""

    def test_extracts_content_sections_from_versions(self, tmp_path: Path) -> None:
        """Content sections under _versions/v1/ are added to sections."""
        builder = SectionBuilder()
        version_container = builder.create_section(tmp_path / "_versions")
        v1 = builder.create_section(tmp_path / "_versions" / "v1")
        docs = builder.create_section(tmp_path / "_versions" / "v1" / "docs")
        docs.add_page(
            Page(
                source_path=tmp_path / "v1" / "docs" / "readme.md",
                _raw_content="",
                _raw_metadata={},
            )
        )
        v1.add_subsection(docs)
        version_container.add_subsection(v1)
        builder.add_versioned_sections_recursive(version_container)
        assert docs in builder.sections
