"""
Extended tests for menu validator.

Additional tests that would have caught the unused menu builder bug.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.menu import MenuValidator


@pytest.fixture
def validator():
    """Create MenuValidator instance."""
    return MenuValidator()


@pytest.fixture
def mock_site_with_builder():
    """Create mock site with menu builder that has validation results."""
    site = MagicMock()

    # Create mock pages
    page1 = MagicMock()
    page1._path = None
    page1.href = "/about/"

    site.pages = [page1]

    # Create mock menu items
    menu_item = MagicMock()
    menu_item.name = "About"
    menu_item._path = None
    menu_item.href = "/about/"
    menu_item.children = []

    site.menu = {"main": [menu_item]}

    # Create menu builder with issues
    builder = MagicMock()
    builder.issues = ["Issue 1: Missing icon", "Issue 2: Invalid weight"]
    site.menu_builders = {"main": builder}

    return site


class TestMenuValidatorConsistency:
    """Tests for consistent behavior with/without menu builder."""

    def test_same_item_count_with_builder(self, validator, mock_site_with_builder):
        """Item count is correct when builder is available."""
        results = validator.validate(mock_site_with_builder)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        # Should report 1 item
        assert any("1" in r.message for r in success_results)

    def test_same_item_count_without_builder(self, validator, mock_site_with_builder):
        """Item count is correct when builder is NOT available."""
        mock_site_with_builder.menu_builders = {}

        results = validator.validate(mock_site_with_builder)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        # Should still report 1 item
        assert any("1" in r.message for r in success_results)

    def test_broken_links_checked_with_builder(self, validator, mock_site_with_builder):
        """Broken links are checked when builder is available."""
        # Add a broken link
        broken_item = MagicMock()
        broken_item.name = "Broken"
        broken_item._path = None
        broken_item.href = "/nonexistent/"
        broken_item.children = []
        mock_site_with_builder.menu["main"].append(broken_item)

        results = validator.validate(mock_site_with_builder)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("broken" in r.message.lower() for r in warning_results)

    def test_broken_links_checked_without_builder(self, validator, mock_site_with_builder):
        """Broken links are checked when builder is NOT available."""
        mock_site_with_builder.menu_builders = {}

        # Add a broken link
        broken_item = MagicMock()
        broken_item.name = "Broken"
        broken_item._path = None
        broken_item.href = "/nonexistent/"
        broken_item.children = []
        mock_site_with_builder.menu["main"].append(broken_item)

        results = validator.validate(mock_site_with_builder)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("broken" in r.message.lower() for r in warning_results)


class TestMenuValidatorNestedItems:
    """Tests for nested menu item handling."""

    def test_counts_deeply_nested_items(self, validator):
        """Counts items in deep nesting correctly."""
        site = MagicMock()

        # Create 3-level nesting: grandparent > parent > child
        child = MagicMock()
        child.name = "Child"
        child._path = None
        child.href = "/child/"
        child.children = []

        parent = MagicMock()
        parent.name = "Parent"
        parent._path = None
        parent.href = "/parent/"
        parent.children = [child]

        grandparent = MagicMock()
        grandparent.name = "Grandparent"
        grandparent._path = None
        grandparent.href = "/grandparent/"
        grandparent.children = [parent]

        site.menu = {"main": [grandparent]}
        site.menu_builders = {}
        site.pages = []

        results = validator.validate(site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        # Should count 3 items total (grandparent + parent + child)
        assert any("3" in r.message for r in success_results)

    def test_checks_broken_links_in_nested_items(self, validator):
        """Checks broken links in nested items."""
        site = MagicMock()

        # Create a class for menu items with proper attributes
        class MenuItem:
            def __init__(self, name, href, children=None):
                self.name = name
                self.href = href
                self.children = children or []

            # Explicitly define _path as not existing
            # The validator uses getattr(item, "_path", None)
            # Without defining _path, MagicMock would auto-create it,
            # but with a real class, getattr returns None default

        # Create nested broken link
        broken_child = MenuItem(
            name="Broken Child",
            href="/nonexistent/",
            children=[],
        )

        parent = MenuItem(
            name="Parent",
            href="https://example.com",  # External, not broken
            children=[broken_child],
        )

        site.menu = {"main": [parent]}
        site.menu_builders = {}
        site.pages = []

        results = validator.validate(site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        # Should find the broken child link
        # Note: the message says "potentially broken links"
        assert any("broken" in r.message.lower() for r in warning_results), (
            f"Expected broken link warning, got: {[r.message for r in results]}"
        )


class TestMenuValidatorMultipleMenus:
    """Tests for multiple menu handling."""

    def test_validates_each_menu_independently(self, validator):
        """Each menu is validated independently."""
        site = MagicMock()

        # Main menu with valid items
        valid_item = MagicMock()
        valid_item.name = "Valid"
        valid_item._path = None
        valid_item.href = "/valid/"
        valid_item.children = []

        # Footer menu with broken items
        broken_item = MagicMock()
        broken_item.name = "Broken"
        broken_item._path = None
        broken_item.href = "/broken/"
        broken_item.children = []

        # Only /valid/ exists
        page = MagicMock()
        page._path = None
        page.href = "/valid/"

        site.menu = {
            "main": [valid_item],
            "footer": [broken_item],
        }
        site.menu_builders = {}
        site.pages = [page]

        results = validator.validate(site)

        # Should have success for main, warning for footer
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]

        assert len(success_results) >= 2  # Item counts for both menus
        assert len(warning_results) >= 1  # Broken link in footer

    def test_reports_correct_menu_names(self, validator):
        """Reports mention the correct menu name."""
        site = MagicMock()

        item = MagicMock()
        item.name = "Item"
        item._path = None
        item.href = "/item/"
        item.children = []

        site.menu = {
            "primary_nav": [item],
            "sidebar": [item],
        }
        site.menu_builders = {}
        site.pages = []

        results = validator.validate(site)

        messages = " ".join(r.message for r in results)
        assert "primary_nav" in messages
        assert "sidebar" in messages


class TestMenuValidatorURLMatching:
    """Tests for URL matching logic."""

    def test_matches_by_path_attribute(self, validator):
        """Matches menu items by _path attribute."""
        site = MagicMock()

        # Menu item uses _path
        item = MagicMock()
        item.name = "Docs"
        item._path = "/docs/"
        item.href = None
        item.children = []

        # Page uses _path
        page = MagicMock()
        page._path = "/docs/"
        page.href = None

        site.menu = {"main": [item]}
        site.menu_builders = {}
        site.pages = [page]

        results = validator.validate(site)

        # Should NOT report broken link (matched by _path)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        broken_warnings = [r for r in warning_results if "broken" in r.message.lower()]
        assert len(broken_warnings) == 0

    def test_matches_by_href_attribute(self, validator):
        """Matches menu items by href attribute."""
        site = MagicMock()

        # Menu item uses href
        item = MagicMock()
        item.name = "Docs"
        item._path = None
        item.href = "/docs/"
        item.children = []

        # Page uses href
        page = MagicMock()
        page._path = None
        page.href = "/docs/"

        site.menu = {"main": [item]}
        site.menu_builders = {}
        site.pages = [page]

        results = validator.validate(site)

        # Should NOT report broken link (matched by href)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        broken_warnings = [r for r in warning_results if "broken" in r.message.lower()]
        assert len(broken_warnings) == 0
