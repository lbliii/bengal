"""
Tests for ergonomic helper methods on Section.

These methods simplify common template patterns by providing
intuitive method calls instead of verbose filter chains.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bengal.core.page import Page
from bengal.core.section import Section


class TestSectionRecentPages:
    """Tests for Section.recent_pages()."""

    def test_returns_pages_sorted_by_date_desc(self, tmp_path: Path) -> None:
        """Returns pages sorted by date, newest first."""
        section = Section(name="blog", path=tmp_path / "blog")

        old_page = Page(
            source_path=tmp_path / "blog/old.md",
            _raw_content="Old",
            _raw_metadata={"title": "Old Post", "date": datetime(2025, 1, 1)},
        )
        new_page = Page(
            source_path=tmp_path / "blog/new.md",
            _raw_content="New",
            _raw_metadata={"title": "New Post", "date": datetime(2025, 12, 1)},
        )
        mid_page = Page(
            source_path=tmp_path / "blog/mid.md",
            _raw_content="Mid",
            _raw_metadata={"title": "Mid Post", "date": datetime(2025, 6, 1)},
        )

        section.pages = [old_page, new_page, mid_page]

        result = section.recent_pages(10)

        assert len(result) == 3
        assert result[0] is new_page
        assert result[1] is mid_page
        assert result[2] is old_page

    def test_excludes_pages_without_date(self, tmp_path: Path) -> None:
        """Excludes pages that don't have a date."""
        section = Section(name="blog", path=tmp_path / "blog")

        dated_page = Page(
            source_path=tmp_path / "blog/dated.md",
            _raw_content="Dated",
            _raw_metadata={"title": "Dated Post", "date": datetime(2025, 1, 1)},
        )
        undated_page = Page(
            source_path=tmp_path / "blog/undated.md",
            _raw_content="Undated",
            _raw_metadata={"title": "Undated Post"},
        )

        section.pages = [dated_page, undated_page]

        result = section.recent_pages(10)

        assert len(result) == 1
        assert result[0] is dated_page

    def test_respects_limit(self, tmp_path: Path) -> None:
        """Respects the limit parameter."""
        section = Section(name="blog", path=tmp_path / "blog")

        pages = [
            Page(
                source_path=tmp_path / f"blog/post{i}.md",
                _raw_content=f"Post {i}",
                _raw_metadata={"title": f"Post {i}", "date": datetime(2025, 1, i + 1)},
            )
            for i in range(5)
        ]
        section.pages = pages

        result = section.recent_pages(3)

        assert len(result) == 3

    def test_returns_empty_for_no_dated_pages(self, tmp_path: Path) -> None:
        """Returns empty list when no pages have dates."""
        section = Section(name="blog", path=tmp_path / "blog")

        undated_page = Page(
            source_path=tmp_path / "blog/undated.md",
            _raw_content="Undated",
            _raw_metadata={"title": "Undated"},
        )
        section.pages = [undated_page]

        result = section.recent_pages(10)

        assert result == []

    def test_default_limit_is_ten(self, tmp_path: Path) -> None:
        """Default limit is 10 pages."""
        section = Section(name="blog", path=tmp_path / "blog")

        pages = [
            Page(
                source_path=tmp_path / f"blog/post{i}.md",
                _raw_content=f"Post {i}",
                _raw_metadata={"title": f"Post {i}", "date": datetime(2025, 1, i + 1)},
            )
            for i in range(15)
        ]
        section.pages = pages

        result = section.recent_pages()  # No limit specified

        assert len(result) == 10


class TestSectionContentPages:
    """Tests for Section.content_pages property."""

    def test_returns_sorted_pages(self, tmp_path: Path) -> None:
        """Returns sorted pages (same as sorted_pages)."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            _raw_content="Page 1",
            _raw_metadata={"title": "Page 1", "weight": 10},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            _raw_content="Page 2",
            _raw_metadata={"title": "Page 2", "weight": 1},
        )
        section.pages = [page1, page2]

        result = section.content_pages

        # Should be sorted by weight
        assert result[0] is page2  # weight=1
        assert result[1] is page1  # weight=10

    def test_is_cached_property(self, tmp_path: Path) -> None:
        """content_pages is a cached property (same object on repeated access)."""
        section = Section(name="docs", path=tmp_path / "docs")

        page = Page(
            source_path=tmp_path / "docs/page.md",
            _raw_content="Page",
            _raw_metadata={"title": "Page"},
        )
        section.pages = [page]

        result1 = section.content_pages
        result2 = section.content_pages

        # Same list object (cached)
        assert result1 is result2


class TestSectionPagesWithTag:
    """Tests for Section.pages_with_tag()."""

    def test_returns_pages_with_matching_tag(self, tmp_path: Path) -> None:
        """Returns only pages that have the specified tag."""
        section = Section(name="blog", path=tmp_path / "blog")

        python_page = Page(
            source_path=tmp_path / "blog/python.md",
            _raw_content="Python post",
            _raw_metadata={"title": "Python Post", "tags": ["python", "tutorial"]},
        )
        javascript_page = Page(
            source_path=tmp_path / "blog/js.md",
            _raw_content="JS post",
            _raw_metadata={"title": "JS Post", "tags": ["javascript"]},
        )
        section.pages = [python_page, javascript_page]

        result = section.pages_with_tag("python")

        assert len(result) == 1
        assert result[0] is python_page

    def test_case_insensitive_matching(self, tmp_path: Path) -> None:
        """Tag matching is case-insensitive."""
        section = Section(name="blog", path=tmp_path / "blog")

        page = Page(
            source_path=tmp_path / "blog/post.md",
            _raw_content="Post",
            _raw_metadata={"title": "Post", "tags": ["Python"]},  # Capital P
        )
        section.pages = [page]

        # Search with lowercase
        result = section.pages_with_tag("python")

        assert len(result) == 1
        assert result[0] is page

    def test_returns_empty_for_no_matches(self, tmp_path: Path) -> None:
        """Returns empty list when no pages have the tag."""
        section = Section(name="blog", path=tmp_path / "blog")

        page = Page(
            source_path=tmp_path / "blog/post.md",
            _raw_content="Post",
            _raw_metadata={"title": "Post", "tags": ["python"]},
        )
        section.pages = [page]

        result = section.pages_with_tag("javascript")

        assert result == []

    def test_handles_pages_without_tags(self, tmp_path: Path) -> None:
        """Handles pages that don't have a tags field."""
        section = Section(name="blog", path=tmp_path / "blog")

        page_with_tags = Page(
            source_path=tmp_path / "blog/tagged.md",
            _raw_content="Tagged",
            _raw_metadata={"title": "Tagged", "tags": ["python"]},
        )
        page_without_tags = Page(
            source_path=tmp_path / "blog/untagged.md",
            _raw_content="Untagged",
            _raw_metadata={"title": "Untagged"},  # No tags
        )
        section.pages = [page_with_tags, page_without_tags]

        result = section.pages_with_tag("python")

        assert len(result) == 1
        assert result[0] is page_with_tags
