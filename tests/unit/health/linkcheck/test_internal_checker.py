"""
Tests for internal link checker.

Tests health/linkcheck/internal_checker.py:
- InternalLinkChecker: Validates internal links within a built site

This test file includes operator precedence tests that would have caught Bug #5.
"""

from __future__ import annotations

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
        assert (
            result.status != LinkStatus.IGNORED
            or "source" not in (result.ignore_reason or "").lower()
        )

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
    """Tests for relative link resolution (#489)."""

    def test_broken_relative_link_detected(self, mock_site):
        """A relative link to a non-existent page is reported as broken (#489).

        ``docs/guide.html`` is *served* at the pretty URL ``/docs/guide/``; a
        browser resolves ``../missing/`` against that served directory to
        ``/docs/missing/``, which does not exist in the output index.
        """
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("../missing/", ["docs/guide.html"])

        assert result.status == LinkStatus.BROKEN
        assert result.first_ref == "docs/guide.html"
        assert result.metadata.get("resolved") == "/docs/missing/"

    def test_valid_relative_link_resolves(self, mock_site):
        """A relative link that resolves to a real page is OK.

        ``docs/guide.html`` is served at ``/docs/guide/``; a browser resolves
        ``../../about/`` against that directory to ``/about/`` which exists.
        """
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("../../about/", ["docs/guide.html"])

        assert result.status == LinkStatus.OK

    def test_relative_md_link_resolves_to_clean_url(self, mock_site):
        """A relative ``.md`` link resolves against the build's clean URLs.

        From the home page (``/``), ``about/index.md`` should validate against
        the built ``/about/`` page rather than being skipped.
        """
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("about/index.md", ["index.html"])

        assert result.status == LinkStatus.OK

    def test_relative_link_broken_for_one_ref(self, mock_site):
        """A relative link is broken if it fails to resolve for any referrer.

        Both ``docs/x.html`` and the home page are served at pretty URLs
        (``/docs/x/`` and ``/``). ``../guide/`` resolves to ``/docs/guide/``
        from ``docs/x.html`` (valid) but to ``/guide/`` from the home page
        (invalid) — the link is reported broken against the home page.
        """
        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("../guide/", ["docs/x.html", "index.html"])

        assert result.status == LinkStatus.BROKEN
        assert result.first_ref == "index.html"

    def test_pretty_url_sibling_link_not_false_positive(self, mock_site, tmp_path):
        """Reviewer false-positive: ``../<sibling>.md`` from a flat non-index page.

        Bengal serves the non-index file ``section/other.html`` at the pretty
        URL ``/section/other/``. A browser resolves ``../other.md`` against that
        served directory to ``/section/other.md`` → ``/section/other/`` (a
        self-reference that exists). With the off-by-a-segment base (``/section/
        other``) it wrongly resolved to ``/other/`` and was reported BROKEN.
        This must now be OK.
        """
        section = tmp_path / "section"
        section.mkdir()
        # Flat-output non-index pages: served at /section/other/ and /section/sibling/
        (section / "other.html").write_text("<html><body>Other</body></html>")
        (section / "sibling.html").write_text("<html><body>Sibling</body></html>")

        checker = InternalLinkChecker(mock_site)

        # Self-referential sibling link authored on section/other.html.
        result = checker._check_internal_link("../other.md", ["section/other.html"])
        assert result.status == LinkStatus.OK, (
            f"expected OK, got {result.status} (resolved="
            f"{result.metadata.get('resolved') if result.metadata else None})"
        )

        # A real neighbouring page reached relative to the served directory.
        result = checker._check_internal_link("../sibling/", ["section/other.html"])
        assert result.status == LinkStatus.OK

    def test_pretty_url_relative_link_still_catches_broken(self, mock_site, tmp_path):
        """Discriminator: a genuinely-broken relative link from a flat page is BROKEN.

        From ``section/other.html`` (served ``/section/other/``), ``../ghost.md``
        resolves to ``/section/ghost.md`` → ``/section/ghost/`` which does not
        exist — must be reported BROKEN with the browser-accurate resolved path.
        """
        section = tmp_path / "section"
        section.mkdir()
        (section / "other.html").write_text("<html><body>Other</body></html>")

        checker = InternalLinkChecker(mock_site)

        result = checker._check_internal_link("../ghost.md", ["section/other.html"])
        assert result.status == LinkStatus.BROKEN
        assert result.first_ref == "section/other.html"
        # Browser-accurate base: resolves within the section, not at site root.
        assert result.metadata.get("resolved") == "/section/ghost.md"


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


class TestInternalLinkCheckerTxtFiles:
    """Tests for auxiliary .txt file indexing (LLM-friendly output)."""

    def test_indexes_txt_files(self, mock_site, tmp_path):
        """Checker indexes .txt files alongside .html files."""
        # Create a .txt companion file (like LLM-friendly output)
        (tmp_path / "about" / "index.txt").write_text("About page plain text")
        (tmp_path / "docs" / "guide.txt").write_text("Guide plain text")

        checker = InternalLinkChecker(mock_site)

        assert "/about/index.txt" in checker._output_paths
        assert "/docs/guide.txt" in checker._output_paths

    def test_txt_links_resolve_as_valid(self, mock_site, tmp_path):
        """Links to index.txt files are not reported as broken."""
        (tmp_path / "about" / "index.txt").write_text("About page plain text")

        checker = InternalLinkChecker(mock_site)
        result = checker._check_internal_link("/about/index.txt", ["page.html"])

        assert result.status == LinkStatus.OK

    def test_missing_txt_still_broken(self, mock_site):
        """Links to non-existent .txt files are still reported as broken."""
        checker = InternalLinkChecker(mock_site)
        result = checker._check_internal_link("/missing/index.txt", ["page.html"])

        assert result.status == LinkStatus.BROKEN


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
