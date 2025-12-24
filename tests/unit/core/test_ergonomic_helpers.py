"""
Tests for ergonomic helper methods on Site and Section.

These methods simplify common template patterns by providing
intuitive method calls instead of verbose filter chains.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site.core import Site


class TestSiteGetSectionByName:
    """Tests for Site.get_section_by_name()."""

    def test_returns_section_when_found(self, tmp_path: Path) -> None:
        """Returns the section when name matches."""
        site = Site(root_path=tmp_path, config={})
        blog_section = Section(name="blog", path=tmp_path / "content/blog")
        docs_section = Section(name="docs", path=tmp_path / "content/docs")
        site.sections = [blog_section, docs_section]

        result = site.get_section_by_name("blog")

        assert result is blog_section

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Returns None when no section matches the name."""
        site = Site(root_path=tmp_path, config={})
        docs_section = Section(name="docs", path=tmp_path / "content/docs")
        site.sections = [docs_section]

        result = site.get_section_by_name("blog")

        assert result is None

    def test_returns_none_for_empty_sections(self, tmp_path: Path) -> None:
        """Returns None when site has no sections."""
        site = Site(root_path=tmp_path, config={})
        site.sections = []

        result = site.get_section_by_name("any")

        assert result is None

    def test_returns_first_match_when_duplicates_exist(self, tmp_path: Path) -> None:
        """Returns first matching section if duplicates exist (edge case)."""
        site = Site(root_path=tmp_path, config={})
        section1 = Section(name="blog", path=tmp_path / "content/blog1")
        section2 = Section(name="blog", path=tmp_path / "content/blog2")
        site.sections = [section1, section2]

        result = site.get_section_by_name("blog")

        assert result is section1


class TestSitePagesBySection:
    """Tests for Site.pages_by_section()."""

    def test_returns_pages_in_section(self, tmp_path: Path) -> None:
        """Returns only pages belonging to the specified section."""
        # Create a mock site with registry (needed for _section property lookup)
        mock_site = Mock(spec=Site)
        mock_site._mock_sections = {}
        mock_site.registry = Mock()
        mock_site.registry.epoch = 0
        mock_site.registry.register_section = Mock(
            side_effect=lambda s: mock_site._mock_sections.update({s.path: s})
        )

        blog_section = Section(name="blog", path=tmp_path / "blog")
        docs_section = Section(name="docs", path=tmp_path / "docs")

        # Register sections with mock lookup
        mock_site.registry.register_section(blog_section)
        mock_site.registry.register_section(docs_section)
        mock_site.get_section_by_path = Mock(
            side_effect=lambda path: mock_site._mock_sections.get(path)
        )

        blog_page = Page(
            source_path=tmp_path / "blog/post.md",
            content="Blog post",
            metadata={"title": "Blog Post"},
        )
        # Pages need site reference for _section lookup
        blog_page._site = mock_site
        blog_page._section = blog_section

        docs_page = Page(
            source_path=tmp_path / "docs/guide.md",
            content="Guide",
            metadata={"title": "Guide"},
        )
        docs_page._site = mock_site
        docs_page._section = docs_section

        # Now create the real Site for testing pages_by_section()
        site = Site(root_path=tmp_path, config={})
        site.pages = [blog_page, docs_page]

        result = site.pages_by_section("blog")

        assert len(result) == 1
        assert result[0] is blog_page

    def test_returns_empty_for_nonexistent_section(self, tmp_path: Path) -> None:
        """Returns empty list when section doesn't exist."""
        site = Site(root_path=tmp_path, config={})
        site.pages = []

        result = site.pages_by_section("nonexistent")

        assert result == []

    def test_handles_pages_without_section(self, tmp_path: Path) -> None:
        """Skips pages that don't have a _section attribute."""
        site = Site(root_path=tmp_path, config={})
        page_without_section = Page(
            source_path=tmp_path / "content/orphan.md",
            content="Orphan",
            metadata={"title": "Orphan"},
        )
        # Page without _section set (no site, no section path)

        site.pages = [page_without_section]

        result = site.pages_by_section("blog")

        assert result == []


class TestSectionRecentPages:
    """Tests for Section.recent_pages()."""

    def test_returns_pages_sorted_by_date_desc(self, tmp_path: Path) -> None:
        """Returns pages sorted by date, newest first."""
        section = Section(name="blog", path=tmp_path / "blog")

        old_page = Page(
            source_path=tmp_path / "blog/old.md",
            content="Old",
            metadata={"title": "Old Post", "date": datetime(2025, 1, 1)},
        )
        new_page = Page(
            source_path=tmp_path / "blog/new.md",
            content="New",
            metadata={"title": "New Post", "date": datetime(2025, 12, 1)},
        )
        mid_page = Page(
            source_path=tmp_path / "blog/mid.md",
            content="Mid",
            metadata={"title": "Mid Post", "date": datetime(2025, 6, 1)},
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
            content="Dated",
            metadata={"title": "Dated Post", "date": datetime(2025, 1, 1)},
        )
        undated_page = Page(
            source_path=tmp_path / "blog/undated.md",
            content="Undated",
            metadata={"title": "Undated Post"},
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
                content=f"Post {i}",
                metadata={"title": f"Post {i}", "date": datetime(2025, 1, i + 1)},
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
            content="Undated",
            metadata={"title": "Undated"},
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
                content=f"Post {i}",
                metadata={"title": f"Post {i}", "date": datetime(2025, 1, i + 1)},
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
            content="Page 1",
            metadata={"title": "Page 1", "weight": 10},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Page 2",
            metadata={"title": "Page 2", "weight": 1},
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
            content="Page",
            metadata={"title": "Page"},
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
            content="Python post",
            metadata={"title": "Python Post", "tags": ["python", "tutorial"]},
        )
        javascript_page = Page(
            source_path=tmp_path / "blog/js.md",
            content="JS post",
            metadata={"title": "JS Post", "tags": ["javascript"]},
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
            content="Post",
            metadata={"title": "Post", "tags": ["Python"]},  # Capital P
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
            content="Post",
            metadata={"title": "Post", "tags": ["python"]},
        )
        section.pages = [page]

        result = section.pages_with_tag("javascript")

        assert result == []

    def test_handles_pages_without_tags(self, tmp_path: Path) -> None:
        """Handles pages that don't have a tags field."""
        section = Section(name="blog", path=tmp_path / "blog")

        page_with_tags = Page(
            source_path=tmp_path / "blog/tagged.md",
            content="Tagged",
            metadata={"title": "Tagged", "tags": ["python"]},
        )
        page_without_tags = Page(
            source_path=tmp_path / "blog/untagged.md",
            content="Untagged",
            metadata={"title": "Untagged"},  # No tags
        )
        section.pages = [page_with_tags, page_without_tags]

        result = section.pages_with_tag("python")

        assert len(result) == 1
        assert result[0] is page_with_tags
