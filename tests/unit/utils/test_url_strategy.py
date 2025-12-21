"""
Comprehensive tests for URLStrategy utility.

Tests URL and path computation for all page types:
- Regular content pages
- Index pages
- Archive pages
- Tag pages
- Virtual paths
- Edge cases and error handling
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.section import Section
from bengal.core.site import Site
from bengal.errors import BengalContentError
from bengal.utils.url_strategy import URLStrategy


class TestURLStrategy:
    """Test URLStrategy path computation."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create mock site with realistic structure."""
        site = Mock(spec=Site)
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.config = {"site": {"base_url": "https://example.com"}, "pretty_urls": True}
        # Mock paths object to return correct Path for generated_dir
        site.paths.generated_dir = tmp_path / ".bengal" / "generated"
        return site

    @pytest.fixture
    def url_strategy(self):
        """Create URLStrategy instance."""
        return URLStrategy()

    # =========================================================================
    # Virtual Path Generation Tests
    # =========================================================================

    def test_make_virtual_path_simple(self, url_strategy, mock_site):
        """Test virtual path generation with single segment."""
        result = url_strategy.make_virtual_path(mock_site, "tags")

        expected = mock_site.root_path / ".bengal" / "generated" / "tags" / "index.md"
        assert result == expected
        assert result.name == "index.md"

    def test_make_virtual_path_nested(self, url_strategy, mock_site):
        """Test virtual path with multiple segments."""
        result = url_strategy.make_virtual_path(mock_site, "archives", "blog", "page_2")

        expected = (
            mock_site.root_path
            / ".bengal"
            / "generated"
            / "archives"
            / "blog"
            / "page_2"
            / "index.md"
        )
        assert result == expected

    def test_make_virtual_path_deep_nesting(self, url_strategy, mock_site):
        """Test virtual path with deep nesting."""
        result = url_strategy.make_virtual_path(mock_site, "a", "b", "c", "d", "e")

        expected = (
            mock_site.root_path / ".bengal" / "generated" / "a" / "b" / "c" / "d" / "e" / "index.md"
        )
        assert result == expected

    def test_make_virtual_path_no_segments(self, url_strategy, mock_site):
        """Test virtual path with no segments (edge case)."""
        result = url_strategy.make_virtual_path(mock_site)

        expected = mock_site.root_path / ".bengal" / "generated" / "index.md"
        assert result == expected

    # =========================================================================
    # Archive Output Path Tests
    # =========================================================================

    def test_compute_archive_output_path_top_level(self, url_strategy, mock_site, tmp_path):
        """Test archive path for top-level section."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        result = url_strategy.compute_archive_output_path(
            section=section, page_num=1, site=mock_site
        )

        expected = mock_site.output_dir / "blog" / "index.html"
        assert result == expected

    def test_compute_archive_output_path_nested_section(self, url_strategy, mock_site, tmp_path):
        """Test archive path for nested section."""
        parent = Section(name="docs", path=tmp_path / "content" / "docs")
        child = Section(name="guides", path=tmp_path / "content" / "docs" / "guides")
        parent.add_subsection(child)

        result = url_strategy.compute_archive_output_path(section=child, page_num=1, site=mock_site)

        # Should include full hierarchy: docs/guides/
        expected = mock_site.output_dir / "docs" / "guides" / "index.html"
        assert result == expected

    def test_compute_archive_output_path_deeply_nested(self, url_strategy, mock_site, tmp_path):
        """Test archive path for deeply nested section."""
        top = Section(name="api", path=tmp_path / "content" / "api")
        middle = Section(name="v2", path=tmp_path / "content" / "api" / "v2")
        bottom = Section(name="users", path=tmp_path / "content" / "api" / "v2" / "users")

        top.add_subsection(middle)
        middle.add_subsection(bottom)

        result = url_strategy.compute_archive_output_path(
            section=bottom, page_num=1, site=mock_site
        )

        # Should be: api/v2/users/
        expected = mock_site.output_dir / "api" / "v2" / "users" / "index.html"
        assert result == expected

    def test_compute_archive_output_path_with_pagination_page2(
        self, url_strategy, mock_site, tmp_path
    ):
        """Test archive path with pagination (page 2)."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        result = url_strategy.compute_archive_output_path(
            section=section, page_num=2, site=mock_site
        )

        # Should be: blog/page/2/index.html
        expected = mock_site.output_dir / "blog" / "page" / "2" / "index.html"
        assert result == expected

    def test_compute_archive_output_path_with_pagination_page10(
        self, url_strategy, mock_site, tmp_path
    ):
        """Test archive path with high page number."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        result = url_strategy.compute_archive_output_path(
            section=section, page_num=10, site=mock_site
        )

        expected = mock_site.output_dir / "blog" / "page" / "10" / "index.html"
        assert result == expected

    def test_compute_archive_output_path_nested_with_pagination(
        self, url_strategy, mock_site, tmp_path
    ):
        """Test nested section archive with pagination."""
        parent = Section(name="docs", path=tmp_path / "content" / "docs")
        child = Section(name="tutorials", path=tmp_path / "content" / "docs" / "tutorials")
        parent.add_subsection(child)

        result = url_strategy.compute_archive_output_path(section=child, page_num=3, site=mock_site)

        # Should be: docs/tutorials/page/3/index.html
        expected = mock_site.output_dir / "docs" / "tutorials" / "page" / "3" / "index.html"
        assert result == expected

    def test_compute_archive_output_path_skips_root(self, url_strategy, mock_site, tmp_path):
        """Test that 'root' is excluded from hierarchy."""
        # Section with root in hierarchy (should be filtered out)
        section = Section(name="blog", path=tmp_path / "content" / "blog")
        # Manually set hierarchy to include 'root'
        root_section = Section(name="root", path=tmp_path / "content")
        root_section.add_subsection(section)

        result = url_strategy.compute_archive_output_path(
            section=section, page_num=1, site=mock_site
        )

        # Should be just: blog/index.html (root filtered out)
        expected = mock_site.output_dir / "blog" / "index.html"
        assert result == expected

    # =========================================================================
    # Tag Output Path Tests
    # =========================================================================

    def test_compute_tag_index_output_path(self, url_strategy, mock_site):
        """Test tag index page path computation."""
        result = url_strategy.compute_tag_index_output_path(mock_site)

        expected = mock_site.output_dir / "tags" / "index.html"
        assert result == expected

    def test_compute_tag_output_path_page_one(self, url_strategy, mock_site):
        """Test tag page path for first page."""
        result = url_strategy.compute_tag_output_path(tag_slug="python", page_num=1, site=mock_site)

        expected = mock_site.output_dir / "tags" / "python" / "index.html"
        assert result == expected

    def test_compute_tag_output_path_with_pagination(self, url_strategy, mock_site):
        """Test tag page path with pagination."""
        result = url_strategy.compute_tag_output_path(tag_slug="python", page_num=2, site=mock_site)

        # Should be: tags/python/page/2/index.html
        expected = mock_site.output_dir / "tags" / "python" / "page" / "2" / "index.html"
        assert result == expected

    def test_compute_tag_output_path_multi_word_slug(self, url_strategy, mock_site):
        """Test tag path with multi-word slug."""
        result = url_strategy.compute_tag_output_path(
            tag_slug="static-site-generators", page_num=1, site=mock_site
        )

        expected = mock_site.output_dir / "tags" / "static-site-generators" / "index.html"
        assert result == expected

    def test_compute_tag_output_path_special_chars_in_slug(self, url_strategy, mock_site):
        """Test tag path with special characters (should be pre-slugified)."""
        # Assumes tag_slug is already slugified by caller
        result = url_strategy.compute_tag_output_path(
            tag_slug="c-plus-plus", page_num=1, site=mock_site
        )

        expected = mock_site.output_dir / "tags" / "c-plus-plus" / "index.html"
        assert result == expected

    # =========================================================================
    # URL from Output Path Tests
    # =========================================================================

    def test_url_from_output_path_root_index(self, url_strategy, mock_site, tmp_path):
        """Test URL generation for root index page."""
        output_path = mock_site.output_dir / "index.html"

        result = url_strategy.url_from_output_path(output_path, mock_site)

        assert result == "/"

    def test_url_from_output_path_top_level_page(self, url_strategy, mock_site, tmp_path):
        """Test URL for top-level page."""
        output_path = mock_site.output_dir / "about" / "index.html"

        result = url_strategy.url_from_output_path(output_path, mock_site)

        assert result == "/about/"

    def test_url_from_output_path_nested_page(self, url_strategy, mock_site, tmp_path):
        """Test URL for nested page."""
        output_path = mock_site.output_dir / "docs" / "guide" / "index.html"

        result = url_strategy.url_from_output_path(output_path, mock_site)

        assert result == "/docs/guide/"

    def test_url_from_output_path_deeply_nested(self, url_strategy, mock_site, tmp_path):
        """Test URL for deeply nested page."""
        output_path = mock_site.output_dir / "api" / "v2" / "users" / "create" / "index.html"

        result = url_strategy.url_from_output_path(output_path, mock_site)

        assert result == "/api/v2/users/create/"

    def test_url_from_output_path_non_index_html(self, url_strategy, mock_site, tmp_path):
        """Test URL for non-index HTML files."""
        output_path = mock_site.output_dir / "about.html"

        result = url_strategy.url_from_output_path(output_path, mock_site)

        # Should strip .html and add trailing slash
        assert result == "/about/"

    def test_url_from_output_path_nested_non_index(self, url_strategy, mock_site, tmp_path):
        """Test URL for nested non-index file."""
        output_path = mock_site.output_dir / "blog" / "post-1.html"

        result = url_strategy.url_from_output_path(output_path, mock_site)

        assert result == "/blog/post-1/"

    def test_url_from_output_path_with_pagination(self, url_strategy, mock_site, tmp_path):
        """Test URL for paginated content."""
        output_path = mock_site.output_dir / "blog" / "page" / "2" / "index.html"

        result = url_strategy.url_from_output_path(output_path, mock_site)

        assert result == "/blog/page/2/"

    def test_url_from_output_path_invalid_not_under_output_dir(
        self, url_strategy, mock_site, tmp_path
    ):
        """Test error when path is not under output directory."""
        output_path = tmp_path / "other" / "page.html"

        with pytest.raises(BengalContentError, match="not under output directory"):
            url_strategy.url_from_output_path(output_path, mock_site)

    def test_url_from_output_path_outside_root(self, url_strategy, mock_site, tmp_path):
        """Test error when path is completely outside project."""
        output_path = Path("/tmp/external/page.html")

        with pytest.raises(BengalContentError, match="not under output directory"):
            url_strategy.url_from_output_path(output_path, mock_site)

    # =========================================================================
    # Edge Cases and Integration Tests
    # =========================================================================

    def test_archive_path_and_url_consistency(self, url_strategy, mock_site, tmp_path):
        """Test that archive path and URL generation are consistent."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        # Compute output path
        output_path = url_strategy.compute_archive_output_path(
            section=section, page_num=1, site=mock_site
        )

        # Generate URL from that path
        url = url_strategy.url_from_output_path(output_path, mock_site)

        # Should be: /blog/
        assert url == "/blog/"
        assert output_path == mock_site.output_dir / "blog" / "index.html"

    def test_tag_path_and_url_consistency(self, url_strategy, mock_site, tmp_path):
        """Test that tag path and URL generation are consistent."""
        # Compute output path
        output_path = url_strategy.compute_tag_output_path(
            tag_slug="python", page_num=1, site=mock_site
        )

        # Generate URL from that path
        url = url_strategy.url_from_output_path(output_path, mock_site)

        # Should be: /tags/python/
        assert url == "/tags/python/"
        assert output_path == mock_site.output_dir / "tags" / "python" / "index.html"

    @pytest.mark.parametrize(
        "page_num,expected_url",
        [
            (1, "/blog/"),
            (2, "/blog/page/2/"),
            (5, "/blog/page/5/"),
            (10, "/blog/page/10/"),
        ],
        ids=["page_1", "page_2", "page_5", "page_10"],
    )
    def test_paginated_paths_have_correct_urls(
        self, url_strategy, mock_site, tmp_path, page_num, expected_url
    ):
        """
        Test URL generation for paginated archive pages.

        Page 1 should be at section root (/blog/), while subsequent pages
        should include /page/N/ in the path. This ensures consistent URL
        structure for pagination across all sections.
        """
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        output_path = url_strategy.compute_archive_output_path(
            section=section, page_num=page_num, site=mock_site
        )
        url = url_strategy.url_from_output_path(output_path, mock_site)

        assert url == expected_url, f"Page {page_num} should have URL '{expected_url}', got '{url}'"

    def test_virtual_path_structure_is_consistent(self, url_strategy, mock_site, tmp_path):
        """Test that virtual paths have consistent structure."""
        paths = [
            url_strategy.make_virtual_path(mock_site, "archives", "blog"),
            url_strategy.make_virtual_path(mock_site, "tags", "python"),
            url_strategy.make_virtual_path(mock_site, "search", "results"),
        ]

        for path in paths:
            # All should be under .bengal/generated/
            assert ".bengal" in path.parts
            assert "generated" in path.parts
            # All should end with index.md
            assert path.name == "index.md"
            # All should be absolute
            assert path.is_absolute()

    def test_hierarchy_filtering_removes_only_root(self, url_strategy, mock_site, tmp_path):
        """Test that only 'root' is filtered from hierarchy, not other segments."""
        # Create section with 'root' and 'roots' in hierarchy
        root = Section(name="root", path=tmp_path / "content")
        roots = Section(name="roots", path=tmp_path / "content" / "roots")
        blog = Section(name="blog", path=tmp_path / "content" / "roots" / "blog")

        root.add_subsection(roots)
        roots.add_subsection(blog)

        result = url_strategy.compute_archive_output_path(section=blog, page_num=1, site=mock_site)

        # Should filter 'root' but keep 'roots': roots/blog/index.html
        expected = mock_site.output_dir / "roots" / "blog" / "index.html"
        assert result == expected

    def test_empty_hierarchy_section(self, url_strategy, mock_site, tmp_path):
        """Test section with empty hierarchy (edge case)."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")
        # Manually clear hierarchy (shouldn't happen in practice)
        section.parent = None

        result = url_strategy.compute_archive_output_path(
            section=section, page_num=1, site=mock_site
        )

        # Should still work: blog/index.html
        expected = mock_site.output_dir / "blog" / "index.html"
        assert result == expected

    # =========================================================================
    # Static Method Tests (can be called without instance)
    # =========================================================================

    def test_static_method_make_virtual_path(self, mock_site):
        """Test make_virtual_path as static method."""
        result = URLStrategy.make_virtual_path(mock_site, "test")

        expected = mock_site.root_path / ".bengal" / "generated" / "test" / "index.md"
        assert result == expected

    def test_static_method_compute_archive_path(self, mock_site, tmp_path):
        """Test compute_archive_output_path as static method."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        result = URLStrategy.compute_archive_output_path(section, 1, mock_site)

        expected = mock_site.output_dir / "blog" / "index.html"
        assert result == expected

    def test_static_method_url_from_path(self, mock_site):
        """Test url_from_output_path as static method."""
        output_path = mock_site.output_dir / "about" / "index.html"

        result = URLStrategy.url_from_output_path(output_path, mock_site)

        assert result == "/about/"

    # =========================================================================
    # Docstring and Interface Tests
    # =========================================================================

    def test_all_methods_are_static(self, url_strategy):
        """Verify that all methods are static (class design choice)."""
        import inspect

        for name, _method in inspect.getmembers(URLStrategy, predicate=inspect.isfunction):
            if not name.startswith("_"):
                # All public methods should be static
                assert isinstance(inspect.getattr_static(URLStrategy, name), staticmethod), (
                    f"Method {name} should be static"
                )

    def test_class_has_docstring(self):
        """Verify URLStrategy has comprehensive docstring."""
        assert URLStrategy.__doc__ is not None
        assert len(URLStrategy.__doc__) > 50
        assert (
            "centraliz" in URLStrategy.__doc__.lower()
        )  # Matches both "centralize" and "centralized"
