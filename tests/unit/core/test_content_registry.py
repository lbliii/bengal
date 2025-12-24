"""
Unit tests for ContentRegistry.

Tests the ContentRegistry class which provides O(1) content lookups
by path and URL with freeze/unfreeze lifecycle management.

See: plan/drafted/rfc-site-responsibility-separation.md
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.core.registry import ContentRegistry


class TestContentRegistryBasics:
    """Test basic registry operations."""

    def test_empty_registry(self) -> None:
        """Empty registry has zero counts."""
        registry = ContentRegistry()
        assert registry.page_count == 0
        assert registry.section_count == 0
        assert not registry.is_frozen

    def test_repr_shows_counts(self) -> None:
        """Repr shows page and section counts."""
        registry = ContentRegistry()
        assert "pages=0" in repr(registry)
        assert "sections=0" in repr(registry)
        assert "(frozen)" not in repr(registry)

    def test_repr_shows_frozen(self) -> None:
        """Repr indicates frozen state."""
        registry = ContentRegistry()
        registry.freeze()
        assert "(frozen)" in repr(registry)


class TestPageRegistration:
    """Test page registration and lookup."""

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.source_path = Path("/site/content/blog/my-post.md")
        page._path = "/blog/my-post/"
        return page

    def test_register_page_by_path(self, mock_page: MagicMock) -> None:
        """Pages are registered by source path."""
        registry = ContentRegistry()
        registry.register_page(mock_page)

        assert registry.page_count == 1
        # Without root_path set, lookup uses exact path
        assert registry.get_page(mock_page.source_path) == mock_page

    def test_register_page_by_url(self, mock_page: MagicMock) -> None:
        """Pages are registered by output URL."""
        registry = ContentRegistry()
        registry.register_page(mock_page)

        assert registry.get_page_by_url("/blog/my-post/") == mock_page

    def test_get_page_not_found(self) -> None:
        """Returns None for unknown page path."""
        registry = ContentRegistry()
        assert registry.get_page(Path("/nonexistent.md")) is None

    def test_get_page_by_url_not_found(self) -> None:
        """Returns None for unknown page URL."""
        registry = ContentRegistry()
        assert registry.get_page_by_url("/nonexistent/") is None

    def test_register_page_without_path(self) -> None:
        """Pages without _path are still registered by source_path."""
        page = MagicMock()
        page.source_path = Path("/site/content/about.md")
        page._path = None  # No URL yet

        registry = ContentRegistry()
        registry.register_page(page)

        assert registry.page_count == 1
        assert registry.get_page(page.source_path) == page
        assert registry.get_page_by_url(None) is None  # type: ignore[arg-type]


class TestSectionRegistration:
    """Test section registration and lookup."""

    @pytest.fixture
    def mock_section(self) -> MagicMock:
        """Create a mock section for testing."""
        section = MagicMock()
        section.path = Path("/site/content/blog")
        section.name = "blog"
        section._path = "/blog/"
        section.subsections = []
        return section

    @pytest.fixture
    def mock_virtual_section(self) -> MagicMock:
        """Create a mock virtual section (path=None) for testing."""
        section = MagicMock()
        section.path = None
        section.name = "api"
        section._path = "/api/"
        section.subsections = []
        return section

    def test_register_section_by_path(self, mock_section: MagicMock) -> None:
        """Sections are registered by directory path."""
        registry = ContentRegistry()
        registry.register_section(mock_section)

        assert registry.section_count == 1

    def test_register_virtual_section(self, mock_virtual_section: MagicMock) -> None:
        """Virtual sections (path=None) are registered by URL."""
        registry = ContentRegistry()
        registry.register_section(mock_virtual_section)

        assert registry.section_count == 1
        assert registry.get_section_by_url("/api/") == mock_virtual_section

    def test_get_section_not_found(self) -> None:
        """Returns None for unknown section path."""
        registry = ContentRegistry()
        assert registry.get_section(Path("/nonexistent")) is None

    def test_get_section_by_url_not_found(self) -> None:
        """Returns None for unknown section URL."""
        registry = ContentRegistry()
        assert registry.get_section_by_url("/nonexistent/") is None

    def test_register_sections_recursive(
        self, mock_section: MagicMock, mock_virtual_section: MagicMock
    ) -> None:
        """Recursive registration includes subsections."""
        mock_section.subsections = [mock_virtual_section]

        registry = ContentRegistry()
        registry.register_sections_recursive(mock_section)

        assert registry.section_count == 2
        assert registry.get_section_by_url("/api/") == mock_virtual_section


class TestFreezeLifecycle:
    """Test freeze/unfreeze lifecycle."""

    def test_freeze_prevents_registration(self) -> None:
        """Frozen registry raises on mutation."""
        registry = ContentRegistry()
        registry.freeze()

        page = MagicMock()
        page.source_path = Path("/test.md")
        page._path = "/test/"

        with pytest.raises(RuntimeError, match="Cannot modify frozen registry"):
            registry.register_page(page)

    def test_freeze_prevents_section_registration(self) -> None:
        """Frozen registry raises on section registration."""
        registry = ContentRegistry()
        registry.freeze()

        section = MagicMock()
        section.path = Path("/test")
        section.subsections = []

        with pytest.raises(RuntimeError, match="Cannot modify frozen registry"):
            registry.register_section(section)

    def test_unfreeze_allows_registration(self) -> None:
        """Unfreezing allows mutations again."""
        registry = ContentRegistry()
        registry.freeze()
        registry.unfreeze()

        page = MagicMock()
        page.source_path = Path("/test.md")
        page._path = "/test/"

        # Should not raise
        registry.register_page(page)
        assert registry.page_count == 1

    def test_is_frozen_property(self) -> None:
        """is_frozen property reflects state."""
        registry = ContentRegistry()
        assert not registry.is_frozen

        registry.freeze()
        assert registry.is_frozen

        registry.unfreeze()
        assert not registry.is_frozen


class TestClear:
    """Test clear functionality."""

    def test_clear_removes_all_entries(self) -> None:
        """Clear removes all registered content."""
        registry = ContentRegistry()

        # Add some content
        page = MagicMock()
        page.source_path = Path("/page.md")
        page._path = "/page/"
        registry.register_page(page)

        section = MagicMock()
        section.path = Path("/section")
        section.subsections = []
        registry.register_section(section)

        assert registry.page_count == 1
        assert registry.section_count == 1

        registry.clear()

        assert registry.page_count == 0
        assert registry.section_count == 0

    def test_clear_unfreezes(self) -> None:
        """Clear also unfreezes the registry."""
        registry = ContentRegistry()
        registry.freeze()
        assert registry.is_frozen

        registry.clear()
        assert not registry.is_frozen

    def test_clear_resets_url_ownership(self) -> None:
        """Clear creates fresh URL registry."""
        registry = ContentRegistry()
        original_url_registry = registry.url_ownership

        registry.clear()

        assert registry.url_ownership is not original_url_registry


class TestPathNormalization:
    """Test path normalization for cross-platform consistency."""

    def test_set_root_path(self) -> None:
        """Root path can be set for normalization."""
        registry = ContentRegistry()
        registry.set_root_path(Path("/site"))

        assert registry._root_path is not None

    def test_normalization_with_root_path(self, tmp_path: Path) -> None:
        """Paths are normalized relative to root."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        registry = ContentRegistry()
        registry.set_root_path(tmp_path)

        page = MagicMock()
        page.source_path = content_dir / "blog" / "post.md"
        page._path = "/blog/post/"

        registry.register_page(page)

        # Should be able to look up by normalized path
        assert registry.page_count == 1


class TestURLOwnership:
    """Test URL ownership integration."""

    def test_url_ownership_initialized(self) -> None:
        """URL ownership registry is initialized."""
        registry = ContentRegistry()
        assert registry.url_ownership is not None

    def test_url_ownership_claim(self) -> None:
        """URL claims work through ownership."""
        registry = ContentRegistry()
        registry.url_ownership.claim(
            "/about/", owner="content", source="content/about.md", priority=100
        )

        claim = registry.url_ownership.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"

    def test_url_ownership_cleared_on_clear(self) -> None:
        """URL claims are cleared on registry clear."""
        registry = ContentRegistry()
        registry.url_ownership.claim(
            "/about/", owner="content", source="content/about.md", priority=100
        )

        registry.clear()

        claim = registry.url_ownership.get_claim("/about/")
        assert claim is None
