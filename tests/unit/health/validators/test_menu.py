"""Tests for menu validator.

Tests health/validators/menu.py:
- MenuValidator: navigation menu validation in health check system
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.menu import MenuValidator


@pytest.fixture
def validator():
    """Create MenuValidator instance."""
    return MenuValidator()


@pytest.fixture
def mock_site():
    """Create mock site with menus and pages."""
    site = MagicMock()

    # Create mock pages
    page1 = MagicMock()
    page1.url = "/about/"
    page2 = MagicMock()
    page2.url = "/contact/"
    site.pages = [page1, page2]

    # Create mock menu items
    menu_item1 = MagicMock()
    menu_item1.name = "About"
    menu_item1.url = "/about/"
    menu_item1.children = []

    menu_item2 = MagicMock()
    menu_item2.name = "Contact"
    menu_item2.url = "/contact/"
    menu_item2.children = []

    site.menu = {"main": [menu_item1, menu_item2]}
    site.menu_builders = {"main": MagicMock()}

    return site


class TestMenuValidatorBasics:
    """Tests for MenuValidator basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Navigation Menus"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates menu structure and links"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestMenuValidatorNoMenus:
    """Tests when no menus are defined."""

    def test_info_when_no_menus(self, validator):
        """Returns info when no menus defined."""
        site = MagicMock()
        site.menu = {}
        results = validator.validate(site)
        assert len(results) == 1
        assert results[0].status == CheckStatus.INFO
        assert "no" in results[0].message.lower() and "menu" in results[0].message.lower()

    def test_info_has_recommendation(self, validator):
        """Info message has recommendation."""
        site = MagicMock()
        site.menu = {}
        results = validator.validate(site)
        assert results[0].recommendation is not None


class TestMenuValidatorEmptyMenu:
    """Tests for empty menu detection."""

    def test_warning_when_menu_empty(self, validator, mock_site):
        """Returns warning when menu has no items."""
        mock_site.menu = {"main": []}
        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("empty" in r.message.lower() for r in warning_results)


class TestMenuValidatorItemCount:
    """Tests for menu item counting."""

    def test_success_shows_item_count(self, validator, mock_site):
        """Success message shows item count."""
        results = validator.validate(mock_site)
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert len(success_results) >= 1
        # Should mention the item count
        assert any("2" in r.message for r in success_results)

    def test_counts_nested_items(self, validator, mock_site):
        """Counts nested menu items correctly."""
        # Add nested children
        child1 = MagicMock()
        child1.name = "Child 1"
        child1.url = "/about/child1/"
        child1.children = []

        child2 = MagicMock()
        child2.name = "Child 2"
        child2.url = "/about/child2/"
        child2.children = []

        mock_site.menu["main"][0].children = [child1, child2]

        results = validator.validate(mock_site)
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        # Should count parent + children (2 + 2 = 4)
        assert any("4" in r.message for r in success_results)


class TestMenuValidatorBrokenLinks:
    """Tests for broken menu link detection."""

    def test_warning_for_broken_internal_url(self, validator, mock_site):
        """Returns warning for menu item with broken internal URL."""
        # Create menu item pointing to non-existent page
        broken_item = MagicMock()
        broken_item.name = "Broken"
        broken_item.url = "/nonexistent/"
        broken_item.children = []

        mock_site.menu = {"main": [broken_item]}
        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("broken" in r.message.lower() for r in warning_results)

    def test_skips_external_urls(self, validator, mock_site):
        """Does not flag external URLs as broken."""
        external_item = MagicMock()
        external_item.name = "External"
        external_item.url = "https://example.com"
        external_item.children = []

        mock_site.menu = {"main": [external_item]}
        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        # Should not warn about external URLs
        broken_warnings = [r for r in warning_results if "broken" in r.message.lower()]
        assert len(broken_warnings) == 0

    def test_skips_protocol_relative_urls(self, validator, mock_site):
        """Does not flag protocol-relative URLs as broken."""
        proto_item = MagicMock()
        proto_item.name = "Protocol Relative"
        proto_item.url = "//example.com/page"
        proto_item.children = []

        mock_site.menu = {"main": [proto_item]}
        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        broken_warnings = [r for r in warning_results if "broken" in r.message.lower()]
        assert len(broken_warnings) == 0


class TestMenuValidatorMultipleMenus:
    """Tests for multiple menu validation."""

    def test_validates_all_menus(self, validator, mock_site):
        """Validates all defined menus."""
        # Add second menu
        footer_item = MagicMock()
        footer_item.name = "Footer Link"
        footer_item.url = "/contact/"
        footer_item.children = []

        mock_site.menu["footer"] = [footer_item]
        mock_site.menu_builders["footer"] = MagicMock()

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        # Should have success for both menus
        assert len(success_results) >= 2


class TestMenuValidatorPrivateMethods:
    """Tests for private helper methods."""

    def test_count_menu_items_flat(self, validator):
        """_count_menu_items counts flat list correctly."""
        items = [MagicMock(), MagicMock(), MagicMock()]
        for item in items:
            item.children = []
        count = validator._count_menu_items(items)
        assert count == 3

    def test_count_menu_items_nested(self, validator):
        """_count_menu_items counts nested items correctly."""
        child1 = MagicMock()
        child1.children = []
        child2 = MagicMock()
        child2.children = []

        parent = MagicMock()
        parent.children = [child1, child2]

        count = validator._count_menu_items([parent])
        assert count == 3  # 1 parent + 2 children

    def test_check_menu_urls_finds_broken(self, validator, mock_site):
        """_check_menu_urls finds broken URLs."""
        broken_item = MagicMock()
        broken_item.name = "Broken"
        broken_item.url = "/nonexistent/"
        broken_item.children = []

        broken = validator._check_menu_urls(mock_site, [broken_item])
        assert len(broken) == 1
        assert "Broken" in broken[0]

    def test_check_menu_urls_skips_external(self, validator, mock_site):
        """_check_menu_urls skips external URLs."""
        external_item = MagicMock()
        external_item.name = "External"
        external_item.url = "https://example.com"
        external_item.children = []

        broken = validator._check_menu_urls(mock_site, [external_item])
        assert len(broken) == 0


class TestMenuValidatorMenuBuilder:
    """Tests for menu builder integration."""

    def test_uses_menu_builder_when_available(self, validator, mock_site):
        """Uses menu builder when available for validation."""
        # The validator checks for menu builder presence
        results = validator.validate(mock_site)

        # Should get success with item count
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert len(success_results) >= 1

    def test_basic_validation_without_builder(self, validator, mock_site):
        """Falls back to basic validation without builder."""
        mock_site.menu_builders = {}  # No builders

        results = validator.validate(mock_site)

        # Should still get success with item count
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert len(success_results) >= 1

