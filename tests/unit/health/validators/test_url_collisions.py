"""
Tests for URL collision validator.

Tests health/validators/url_collisions.py:
- URLCollisionValidator: Detects when multiple pages output to the same URL

This test file would have caught Bug #3: _check_section_page_conflicts never being called.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.url_collisions import URLCollisionValidator


@pytest.fixture
def validator():
    """Create URLCollisionValidator instance."""
    return URLCollisionValidator()


@pytest.fixture
def mock_site():
    """Create mock site with pages."""
    site = MagicMock()

    # Create mock pages with unique URLs
    page1 = MagicMock()
    page1._path = "/page1/"
    page1.source_path = "content/page1.md"
    page1.title = "Page 1"

    page2 = MagicMock()
    page2._path = "/page2/"
    page2.source_path = "content/page2.md"
    page2.title = "Page 2"

    site.pages = [page1, page2]
    site.sections = []
    site.url_registry = None

    return site


class TestURLCollisionValidatorBasics:
    """Tests for URLCollisionValidator basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "URL Collisions"

    def test_has_description(self, validator):
        """Validator has a description."""
        desc = validator.description.lower()
        assert "url" in desc or "same" in desc or "multiple" in desc

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestURLCollisionValidatorNoCollisions:
    """Tests when no collisions exist."""

    def test_no_results_when_no_collisions(self, validator, mock_site):
        """Returns no errors when URLs are unique."""
        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) == 0

    def test_empty_site_passes(self, validator):
        """Empty site (no pages) passes validation."""
        site = MagicMock()
        site.pages = []
        site.sections = []

        results = validator.validate(site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) == 0


class TestURLCollisionValidatorDetectsCollisions:
    """Tests for collision detection."""

    def test_detects_duplicate_urls(self, validator, mock_site):
        """Detects when two pages have the same URL."""
        # Make both pages have the same URL
        mock_site.pages[0]._path = "/same-url/"
        mock_site.pages[1]._path = "/same-url/"

        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1
        assert any("collision" in r.message.lower() for r in error_results)

    def test_collision_has_code_H020(self, validator, mock_site):
        """Collision error has code H020."""
        mock_site.pages[0]._path = "/same-url/"
        mock_site.pages[1]._path = "/same-url/"

        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert any(r.code == "H020" for r in error_results)

    def test_collision_details_show_sources(self, validator, mock_site):
        """Collision error details show source files."""
        mock_site.pages[0]._path = "/same-url/"
        mock_site.pages[0].source_path = "content/first.md"
        mock_site.pages[1]._path = "/same-url/"
        mock_site.pages[1].source_path = "content/second.md"

        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1

        # Details should mention source files
        details = error_results[0].details or []
        details_str = "\n".join(details)
        assert "first.md" in details_str or "second.md" in details_str

    def test_detects_multiple_collisions(self, validator, mock_site):
        """Detects multiple collisions."""
        # Create 4 pages with 2 collision groups
        page3 = MagicMock()
        page3._path = "/collision1/"
        page3.source_path = "content/page3.md"

        page4 = MagicMock()
        page4._path = "/collision2/"
        page4.source_path = "content/page4.md"

        mock_site.pages[0]._path = "/collision1/"
        mock_site.pages[1]._path = "/collision2/"
        mock_site.pages.extend([page3, page4])

        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1
        # Should report 2 collisions
        assert "2" in error_results[0].message


class TestURLCollisionValidatorSectionConflicts:
    """Tests for section/page URL conflict detection."""

    def test_detects_section_page_conflict(self, validator, mock_site):
        """Detects when a page URL conflicts with a section URL."""
        # Create a section with URL /docs/
        section = MagicMock()
        section._path = "/docs/"
        section.name = "docs"
        mock_site.sections = [section]

        # Create a page at the same URL (not an index page)
        conflict_page = MagicMock()
        conflict_page._path = "/docs/"
        conflict_page.source_path = "content/docs.md"  # Not _index.md
        conflict_page.title = "Docs Page"

        mock_site.pages.append(conflict_page)

        results = validator.validate(mock_site)

        # Should warn about section/page conflict
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        conflict_warnings = [r for r in warning_results if r.code == "H021"]
        assert len(conflict_warnings) >= 1

    def test_index_pages_dont_conflict_with_sections(self, validator, mock_site):
        """Index pages at section URLs are expected and don't conflict."""
        # Create a section with URL /docs/
        section = MagicMock()
        section._path = "/docs/"
        section.name = "docs"
        mock_site.sections = [section]

        # Create an index page at the same URL
        index_page = MagicMock()
        index_page._path = "/docs/"
        index_page.source_path = "content/docs/_index.md"
        index_page.title = "Docs Index"

        mock_site.pages.append(index_page)

        results = validator.validate(mock_site)

        # Should NOT warn about index pages
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        conflict_warnings = [r for r in warning_results if r.code == "H021"]
        assert len(conflict_warnings) == 0

    def test_section_index_pages_dont_conflict(self, validator, mock_site):
        """Section index pages (section-index.md) don't conflict."""
        section = MagicMock()
        section._path = "/cli/"
        section.name = "cli"
        mock_site.sections = [section]

        # Virtual section index page
        index_page = MagicMock()
        index_page._path = "/cli/"
        index_page.source_path = "__virtual__/cli/section-index.md"
        index_page.title = "CLI Section"

        mock_site.pages.append(index_page)

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        conflict_warnings = [r for r in warning_results if r.code == "H021"]
        assert len(conflict_warnings) == 0


class TestURLCollisionValidatorURLRegistry:
    """Tests for URL registry integration."""

    def test_shows_ownership_info_from_registry(self, validator, mock_site):
        """Shows ownership info when URL registry is available."""
        mock_site.pages[0]._path = "/same-url/"
        mock_site.pages[1]._path = "/same-url/"

        # Set up URL registry with claim info
        claim = MagicMock()
        claim.owner = "autodoc"
        claim.priority = 100

        registry = MagicMock()
        registry.get_claim.return_value = claim
        mock_site.url_registry = registry

        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1

        # Details should include ownership info
        details = error_results[0].details or []
        details_str = "\n".join(details)
        assert "autodoc" in details_str or "priority" in details_str


class TestURLCollisionValidatorRecommendations:
    """Tests for actionable recommendations."""

    def test_collision_has_recommendation(self, validator, mock_site):
        """Collision error has actionable recommendation."""
        mock_site.pages[0]._path = "/same-url/"
        mock_site.pages[1]._path = "/same-url/"

        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1
        assert error_results[0].recommendation is not None
        # Should mention common causes
        assert (
            "slug" in error_results[0].recommendation.lower()
            or "rename" in error_results[0].recommendation.lower()
        )
