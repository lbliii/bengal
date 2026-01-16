"""
Tests for internal link checker.

Tests health/linkcheck/internal_checker.py:
- InternalLinkChecker: Validates internal links within a built site

This test file includes operator precedence tests that would have caught Bug #5.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.health.linkcheck.internal_checker import InternalLinkChecker
from bengal.health.linkcheck.models import LinkStatus


@pytest.fixture
def mock_site(tmp_path):
    """Create mock site with output directory."""
    site = MagicMock()
    site.output_dir = tmp_path
    site.baseurl = ""
    site.config = {}

    # Create some HTML files
    (tmp_path / "index.html").write_text("<html><body>Home</body></html>")
    (tmp_path / "about").mkdir()
    (tmp_path / "about" / "index.html").write_text("<html><body>About</body></html>")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.html").write_text("<html><body>Guide</body></html>")

    return site


class TestInternalLinkCheckerBasics:
    """Tests for InternalLinkChecker initialization."""

    def test_builds_output_path_index(self, mock_site):
        """Checker builds index of output paths on init."""
        checker = InternalLinkChecker(mock_site)

        assert "/" in checker._output_paths
        assert "/about/" in checker._output_paths
        assert "/docs/guide" in checker._output_paths

    def test_handles_empty_output_dir(self, tmp_path):
        """Handles site with empty output directory."""
        site = MagicMock()
        site.output_dir = tmp_path
        site.baseurl = ""
        site.config = {}

        checker = InternalLinkChecker(site)
        assert len(checker._output_paths) == 0

    def test_handles_missing_output_dir(self, tmp_path):
        """Handles site with non-existent output directory."""
        site = MagicMock()
        site.output_dir = tmp_path / "nonexistent"
        site.baseurl = ""
        site.config = {}

        checker = InternalLinkChecker(site)
        assert len(checker._output_paths) == 0


class TestInternalLinkCheckerSourceFileFiltering:
    """
    Tests for source file reference filtering.

    These tests verify the operator precedence fix in Bug #5:
    The condition `"/bengal/" in url and ".py" in url` should be
    properly grouped with parentheses.
    """

    def test_filters_python_file_with_line_anchor(self, mock_site):
        """Filters .py#L123 references (autodoc source links)."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("bengal/core/page.py#L42", ["test.html"])

        assert result.status == LinkStatus.IGNORED
        assert "source" in result.ignore_reason.lower()

    def test_filters_python_file_with_anchor(self, mock_site):
        """Filters .py# references."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("module.py#section", ["test.html"])

        assert result.status == LinkStatus.IGNORED

    def test_filters_python_file_without_anchor(self, mock_site):
        """Filters plain .py file references."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("module.py", ["test.html"])

        assert result.status == LinkStatus.IGNORED

    def test_filters_bengal_path_with_py(self, mock_site):
        """
        Filters URLs containing /bengal/ AND .py.

        This is the key test for the operator precedence fix.
        The condition should be: ("/bengal/" in url AND ".py" in url)
        Not: "/bengal/" in url OR (".py" in url AND something_else)
        """
        checker = InternalLinkChecker(mock_site)

        # Should be filtered: has both /bengal/ and .py
        result = checker._check_internal_link("/bengal/core/page.py", ["test.html"])
        assert result.status == LinkStatus.IGNORED

        # Should be filtered: relative path with bengal and .py
        result = checker._check_internal_link("../bengal/utils.py#L10", ["test.html"])
        assert result.status == LinkStatus.IGNORED

    def test_does_not_filter_bengal_path_without_py(self, mock_site):
        """
        Does NOT filter /bengal/ paths that don't have .py.

        This verifies the AND operator precedence is correct.
        """
        checker = InternalLinkChecker(mock_site)

        # Create the page so it's found
        (mock_site.output_dir / "bengal").mkdir(exist_ok=True)
        (mock_site.output_dir / "bengal" / "index.html").write_text("<html></html>")

        # Rebuild index with new page
        checker = InternalLinkChecker(mock_site)

        # Should NOT be filtered - it's a real page, not a source file
        result = checker._check_internal_link("/bengal/", ["test.html"])
        # Could be OK or BROKEN depending on index, but NOT IGNORED
        assert result.status != LinkStatus.IGNORED or "source" not in (
            result.ignore_reason or ""
        ).lower()

    def test_filters_relative_py_paths(self, mock_site):
        """Filters relative paths to .py files (../ prefix)."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("../module.py", ["test.html"])
        assert result.status == LinkStatus.IGNORED

        result = checker._check_internal_link("../../package/module.py#L1", ["test.html"])
        assert result.status == LinkStatus.IGNORED


class TestInternalLinkCheckerValidLinks:
    """Tests for valid internal link detection."""

    def test_valid_absolute_link(self, mock_site):
        """Validates absolute internal links."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("/about/", ["test.html"])

        assert result.status == LinkStatus.OK

    def test_valid_link_without_trailing_slash(self, mock_site):
        """Validates links without trailing slash."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("/about", ["test.html"])

        assert result.status == LinkStatus.OK

    def test_root_link(self, mock_site):
        """Validates root link."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("/", ["test.html"])

        assert result.status == LinkStatus.OK


class TestInternalLinkCheckerBrokenLinks:
    """Tests for broken link detection."""

    def test_broken_link_not_found(self, mock_site):
        """Detects links to non-existent pages."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("/nonexistent/", ["test.html"])

        assert result.status == LinkStatus.BROKEN
        assert "not found" in result.reason.lower()

    def test_broken_link_reports_first_ref(self, mock_site):
        """Broken link result includes first reference."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("/missing/", ["page1.html", "page2.html"])

        assert result.first_ref == "page1.html"


class TestInternalLinkCheckerRelativeLinks:
    """Tests for relative link handling."""

    def test_relative_link_skipped(self, mock_site):
        """Relative links (not starting with /) are currently skipped."""
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("sibling-page", ["test.html"])

        # Relative links return OK with a note (not fully validated)
        assert result.status == LinkStatus.OK
        assert result.metadata is not None
        assert "relative" in result.metadata.get("note", "").lower()


class TestInternalLinkCheckerBaseURL:
    """Tests for baseurl handling."""

    def test_strips_baseurl_from_links(self, mock_site):
        """Strips baseurl prefix from links before checking."""
        mock_site.baseurl = "https://example.com/docs"

        checker = InternalLinkChecker(mock_site)

        # Link with baseurl prefix should work
        result = checker._check_internal_link("/docs/about/", ["test.html"])

        assert result.status == LinkStatus.OK

    def test_handles_baseurl_with_path(self, mock_site):
        """Handles baseurl that includes path component."""
        mock_site.baseurl = "/myproject"

        checker = InternalLinkChecker(mock_site)

        # Should strip /myproject prefix
        result = checker._check_internal_link("/myproject/about/", ["test.html"])

        assert result.status == LinkStatus.OK


class TestInternalLinkCheckerBatchChecking:
    """Tests for batch link checking."""

    def test_check_links_deduplicates(self, mock_site):
        """check_links deduplicates URLs."""
        checker = InternalLinkChecker(mock_site)

        links = [
            ("/about/", "page1.html"),
            ("/about/", "page2.html"),
            ("/about/", "page3.html"),
        ]

        results = checker.check_links(links)

        # Should have only one result for /about/
        assert len(results) == 1
        assert "/about/" in results

    def test_check_links_tracks_ref_count(self, mock_site):
        """check_links tracks reference count for each URL."""
        checker = InternalLinkChecker(mock_site)

        links = [
            ("/about/", "page1.html"),
            ("/about/", "page2.html"),
            ("/", "page3.html"),
        ]

        results = checker.check_links(links)

        assert results["/about/"].ref_count == 2
        assert results["/"].ref_count == 1
