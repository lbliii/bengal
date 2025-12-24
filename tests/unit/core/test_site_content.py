"""
Unit tests for SiteContent.

Tests the SiteContent mutable container for site content
(pages, sections, assets) with freeze/unfreeze lifecycle.

See: plan/drafted/rfc-site-responsibility-separation.md
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.core.site_content import SiteContent


class TestSiteContentBasics:
    """Test basic SiteContent operations."""

    def test_empty_content(self) -> None:
        """Empty content has zero counts."""
        content = SiteContent()

        assert content.page_count == 0
        assert content.section_count == 0
        assert content.asset_count == 0

    def test_repr_shows_counts(self) -> None:
        """Repr shows page, section, and asset counts."""
        content = SiteContent()

        repr_str = repr(content)

        assert "pages=0" in repr_str
        assert "sections=0" in repr_str
        assert "assets=0" in repr_str

    def test_repr_shows_frozen(self) -> None:
        """Repr indicates frozen state."""
        content = SiteContent()
        content.freeze()

        assert "(frozen)" in repr(content)


class TestContentPopulation:
    """Test content population."""

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        """Create a mock page."""
        page = MagicMock()
        page.metadata = {}
        page.in_listings = True
        return page

    @pytest.fixture
    def mock_section(self) -> MagicMock:
        """Create a mock section."""
        return MagicMock()

    @pytest.fixture
    def mock_asset(self) -> MagicMock:
        """Create a mock asset."""
        return MagicMock()

    def test_add_pages(self, mock_page: MagicMock) -> None:
        """Pages can be added."""
        content = SiteContent()
        content.pages.append(mock_page)

        assert content.page_count == 1

    def test_add_sections(self, mock_section: MagicMock) -> None:
        """Sections can be added."""
        content = SiteContent()
        content.sections.append(mock_section)

        assert content.section_count == 1

    def test_add_assets(self, mock_asset: MagicMock) -> None:
        """Assets can be added."""
        content = SiteContent()
        content.assets.append(mock_asset)

        assert content.asset_count == 1


class TestFreezeLifecycle:
    """Test freeze/unfreeze lifecycle."""

    def test_starts_unfrozen(self) -> None:
        """Content starts unfrozen."""
        content = SiteContent()
        assert not content.is_frozen

    def test_freeze(self) -> None:
        """Content can be frozen."""
        content = SiteContent()
        content.freeze()

        assert content.is_frozen

    def test_unfreeze(self) -> None:
        """Content can be unfrozen."""
        content = SiteContent()
        content.freeze()
        content.unfreeze()

        assert not content.is_frozen


class TestClear:
    """Test clear functionality."""

    def test_clear_removes_all(self) -> None:
        """Clear removes all content."""
        content = SiteContent()

        # Add content
        content.pages.append(MagicMock())
        content.sections.append(MagicMock())
        content.assets.append(MagicMock())
        content.taxonomies["tags"] = {"python": {}}
        content.menu["main"] = [MagicMock()]

        content.clear()

        assert content.page_count == 0
        assert content.section_count == 0
        assert content.asset_count == 0
        assert len(content.taxonomies) == 0
        assert len(content.menu) == 0

    def test_clear_unfreezes(self) -> None:
        """Clear unfreezes content."""
        content = SiteContent()
        content.freeze()

        content.clear()

        assert not content.is_frozen

    def test_clear_invalidates_caches(self) -> None:
        """Clear invalidates derived caches."""
        content = SiteContent()

        # Populate a cache
        page = MagicMock()
        page.metadata = {}
        page.in_listings = True
        content.pages.append(page)
        _ = content.regular_pages  # Populate cache

        content.clear()

        # Cache should be invalidated
        assert content._regular_pages_cache is None


class TestDerivedPageLists:
    """Test cached derived page lists."""

    @pytest.fixture
    def regular_page(self) -> MagicMock:
        """Create a regular (non-generated) page."""
        page = MagicMock()
        page.metadata = {}
        page.in_listings = True
        return page

    @pytest.fixture
    def generated_page(self) -> MagicMock:
        """Create a generated page."""
        page = MagicMock()
        page.metadata = {"_generated": True}
        page.in_listings = True
        return page

    @pytest.fixture
    def hidden_page(self) -> MagicMock:
        """Create a hidden page."""
        page = MagicMock()
        page.metadata = {}
        page.in_listings = False
        return page

    def test_regular_pages(self, regular_page: MagicMock, generated_page: MagicMock) -> None:
        """regular_pages excludes generated pages."""
        content = SiteContent()
        content.pages = [regular_page, generated_page]

        result = content.regular_pages

        assert len(result) == 1
        assert regular_page in result
        assert generated_page not in result

    def test_generated_pages(self, regular_page: MagicMock, generated_page: MagicMock) -> None:
        """generated_pages returns only generated pages."""
        content = SiteContent()
        content.pages = [regular_page, generated_page]

        result = content.generated_pages

        assert len(result) == 1
        assert generated_page in result
        assert regular_page not in result

    def test_listable_pages(
        self, regular_page: MagicMock, generated_page: MagicMock, hidden_page: MagicMock
    ) -> None:
        """listable_pages returns pages with in_listings=True."""
        content = SiteContent()
        content.pages = [regular_page, generated_page, hidden_page]

        result = content.listable_pages

        assert len(result) == 2
        assert regular_page in result
        assert generated_page in result
        assert hidden_page not in result

    def test_regular_pages_cached(self, regular_page: MagicMock) -> None:
        """regular_pages is cached."""
        content = SiteContent()
        content.pages = [regular_page]

        result1 = content.regular_pages
        result2 = content.regular_pages

        assert result1 is result2

    def test_invalidate_caches(self, regular_page: MagicMock) -> None:
        """invalidate_caches clears cached lists."""
        content = SiteContent()
        content.pages = [regular_page]
        _ = content.regular_pages  # Populate cache

        content.invalidate_caches()

        assert content._regular_pages_cache is None
        assert content._generated_pages_cache is None
        assert content._listable_pages_cache is None


class TestMenuStructures:
    """Test menu-related structures."""

    def test_menu_empty(self) -> None:
        """Menu starts empty."""
        content = SiteContent()
        assert len(content.menu) == 0

    def test_menu_builders_empty(self) -> None:
        """Menu builders starts empty."""
        content = SiteContent()
        assert len(content.menu_builders) == 0

    def test_menu_localized_empty(self) -> None:
        """Localized menus starts empty."""
        content = SiteContent()
        assert len(content.menu_localized) == 0

    def test_menu_cleared(self) -> None:
        """Menus are cleared on clear()."""
        content = SiteContent()
        content.menu["main"] = [MagicMock()]
        content.menu_builders["main"] = MagicMock()
        content.menu_localized["en"] = {"main": [MagicMock()]}
        content.menu_builders_localized["en"] = {"main": MagicMock()}

        content.clear()

        assert len(content.menu) == 0
        assert len(content.menu_builders) == 0
        assert len(content.menu_localized) == 0
        assert len(content.menu_builders_localized) == 0


class TestTaxonomies:
    """Test taxonomy structures."""

    def test_taxonomies_empty(self) -> None:
        """Taxonomies starts empty."""
        content = SiteContent()
        assert len(content.taxonomies) == 0

    def test_taxonomies_cleared(self) -> None:
        """Taxonomies are cleared on clear()."""
        content = SiteContent()
        content.taxonomies["tags"] = {"python": {"pages": []}}

        content.clear()

        assert len(content.taxonomies) == 0


class TestData:
    """Test data structure."""

    def test_data_empty(self) -> None:
        """Data starts empty."""
        content = SiteContent()
        assert len(content.data) == 0

    def test_data_preserved_on_clear(self) -> None:
        """Data is NOT cleared on clear() (reloaded separately)."""
        content = SiteContent()
        content.data["key"] = "value"

        content.clear()

        # Data should still be present (typically reloaded from disk)
        assert content.data.get("key") == "value"
