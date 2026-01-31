"""
Tests for bengal.health.utils module.

Tests the shared utilities extracted from validators:
- iter_pages_with_output
- sample_pages
- read_output_content
- relative_path
- get_section_pages
- get_health_config
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.health.utils import (
    get_health_config,
    get_section_pages,
    iter_pages_with_output,
    read_output_content,
    relative_path,
    sample_pages,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_page():
    """Create a mock page with output_path."""
    page = MagicMock()
    page.metadata = {}
    page.output_path = MagicMock()
    page.output_path.exists.return_value = True
    page.output_path.read_text.return_value = "<html><body>test</body></html>"
    return page


@pytest.fixture
def mock_page_no_output():
    """Create a mock page without output_path."""
    page = MagicMock()
    page.metadata = {}
    page.output_path = None
    return page


@pytest.fixture
def mock_generated_page():
    """Create a mock generated page."""
    page = MagicMock()
    page.metadata = {"_generated": True}
    page.output_path = MagicMock()
    page.output_path.exists.return_value = True
    return page


@pytest.fixture
def mock_site(mock_page, mock_page_no_output, mock_generated_page):
    """Create a mock site with various pages."""
    site = MagicMock()

    # Create 5 pages with output, 2 without, 2 generated
    pages_with_output = [MagicMock() for _ in range(5)]
    for i, p in enumerate(pages_with_output):
        p.metadata = {}
        p.output_path = MagicMock()
        p.output_path.exists.return_value = True
        p.output_path.name = f"page{i}.html"

    pages_without_output = [mock_page_no_output, MagicMock()]
    pages_without_output[1].metadata = {}
    pages_without_output[1].output_path = MagicMock()
    pages_without_output[1].output_path.exists.return_value = False

    generated_pages = [mock_generated_page, MagicMock()]
    generated_pages[1].metadata = {"_generated": True}
    generated_pages[1].output_path = MagicMock()
    generated_pages[1].output_path.exists.return_value = True

    site.pages = pages_with_output + pages_without_output + generated_pages
    site.config = {"health_check": {"orphan_threshold": 10, "verbose": True}}
    site.root_path = Path("/project")

    return site


# =============================================================================
# Tests: iter_pages_with_output
# =============================================================================


class TestIterPagesWithOutput:
    """Tests for iter_pages_with_output utility."""

    def test_yields_pages_with_existing_output(self, mock_site):
        """Should yield only pages with existing output_path."""
        pages = list(iter_pages_with_output(mock_site))
        # 5 regular + 2 generated = 7 pages with existing output
        assert len(pages) == 7

    def test_respects_limit(self, mock_site):
        """Should stop after limit pages."""
        pages = list(iter_pages_with_output(mock_site, limit=3))
        assert len(pages) == 3

    def test_excludes_generated_pages(self, mock_site):
        """Should exclude generated pages when flag is set."""
        pages = list(iter_pages_with_output(mock_site, exclude_generated=True))
        # Only 5 regular pages
        assert len(pages) == 5

    def test_handles_empty_site(self):
        """Should handle site with no pages."""
        site = MagicMock()
        site.pages = []
        pages = list(iter_pages_with_output(site))
        assert pages == []

    def test_handles_pages_without_output_path_attr(self):
        """Should skip pages that don't have output_path attribute."""
        site = MagicMock()
        page = MagicMock(spec=[])  # No attributes
        page.metadata = {}
        site.pages = [page]
        pages = list(iter_pages_with_output(site))
        assert pages == []


# =============================================================================
# Tests: sample_pages
# =============================================================================


class TestSamplePages:
    """Tests for sample_pages utility."""

    def test_returns_list_of_pages(self, mock_site):
        """Should return a list, not iterator."""
        pages = sample_pages(mock_site, count=3)
        assert isinstance(pages, list)
        assert len(pages) == 3

    def test_respects_count(self, mock_site):
        """Should return at most count pages."""
        pages = sample_pages(mock_site, count=2)
        assert len(pages) == 2

    def test_excludes_generated(self, mock_site):
        """Should exclude generated pages when flag is set."""
        pages = sample_pages(mock_site, count=10, exclude_generated=True)
        assert len(pages) == 5

    def test_without_require_output(self, mock_site):
        """Should include pages without output when require_output=False."""
        pages = sample_pages(mock_site, count=20, require_output=False)
        # All 9 pages (5 regular + 2 no output + 2 generated)
        assert len(pages) == 9


# =============================================================================
# Tests: read_output_content
# =============================================================================


class TestReadOutputContent:
    """Tests for read_output_content utility."""

    def test_reads_page_content(self, mock_page):
        """Should read and return page output content."""
        content = read_output_content(mock_page)
        assert content == "<html><body>test</body></html>"

    def test_returns_none_for_no_output_path(self, mock_page_no_output):
        """Should return None if page has no output_path."""
        content = read_output_content(mock_page_no_output)
        assert content is None

    def test_returns_none_on_read_error(self, mock_page):
        """Should return None if read fails."""
        mock_page.output_path.read_text.side_effect = OSError("Read failed")
        content = read_output_content(mock_page)
        assert content is None

    def test_uses_specified_encoding(self, mock_page):
        """Should use specified encoding."""
        read_output_content(mock_page, encoding="latin-1")
        mock_page.output_path.read_text.assert_called_with(encoding="latin-1")


# =============================================================================
# Tests: relative_path
# =============================================================================


class TestRelativePath:
    """Tests for relative_path utility."""

    def test_converts_absolute_to_relative(self):
        """Should convert absolute path to relative."""
        result = relative_path("/project/content/page.md", Path("/project"))
        assert result == "content/page.md"

    def test_handles_path_object(self):
        """Should accept Path objects."""
        result = relative_path(Path("/project/src/file.py"), Path("/project"))
        assert result == "src/file.py"

    def test_returns_original_on_failure(self):
        """Should return original path if not under root."""
        result = relative_path("/other/path/file.md", Path("/project"))
        assert result == "/other/path/file.md"

    def test_handles_string_path(self):
        """Should accept string paths."""
        result = relative_path("/project/docs/index.md", Path("/project"))
        assert result == "docs/index.md"


# =============================================================================
# Tests: get_section_pages
# =============================================================================


class TestGetSectionPages:
    """Tests for get_section_pages utility."""

    def test_returns_pages_attribute(self):
        """Should return section.pages when available."""
        section = MagicMock()
        section.pages = ["page1", "page2"]
        result = get_section_pages(section)
        assert result == ["page1", "page2"]

    def test_falls_back_to_children(self):
        """Should fall back to children attribute."""
        section = MagicMock(spec=["children"])
        section.children = ["child1", "child2"]
        result = get_section_pages(section)
        assert result == ["child1", "child2"]

    def test_returns_empty_list_if_neither(self):
        """Should return empty list if neither attribute exists."""
        section = MagicMock(spec=[])
        result = get_section_pages(section)
        assert result == []


# =============================================================================
# Tests: get_health_config
# =============================================================================


class TestGetHealthConfig:
    """Tests for get_health_config utility."""

    def test_returns_config_value(self, mock_site):
        """Should return value from health_check config."""
        result = get_health_config(mock_site, "orphan_threshold")
        assert result == 10

    def test_returns_default_if_missing(self, mock_site):
        """Should return default if key not found."""
        result = get_health_config(mock_site, "nonexistent", default=5)
        assert result == 5

    def test_returns_default_if_no_health_config(self):
        """Should return default if health_check section missing."""
        site = MagicMock()
        site.config = {}
        result = get_health_config(site, "threshold", default=20)
        assert result == 20

    def test_handles_non_dict_health_config(self):
        """Should handle object-style config access."""
        site = MagicMock()
        health_config = MagicMock()
        health_config.orphan_threshold = 15
        site.config = {"health_check": health_config}
        # For non-dict, falls back to getattr
        result = get_health_config(site, "orphan_threshold", default=5)
        assert result == 15

    def test_default_is_none(self, mock_site):
        """Should use None as default if not specified."""
        result = get_health_config(mock_site, "nonexistent")
        assert result is None
