"""
Unit tests for autodoc index page creation.

Tests the create_index_pages() function which generates section-index
virtual pages for autodoc sections. Specifically covers the URL registry
interaction that was causing 404s when cached URL claims blocked
recreation of section-index pages.

Regression: Section-index pages for /api/, /cli/, /api/bengal/ were
not created during incremental builds because the URL registry was
pre-populated with stale claims from the previous build's cache.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.autodoc.orchestration.index_pages import create_index_pages
from bengal.core.section import Section
from bengal.core.url_ownership import URLRegistry


@pytest.fixture
def mock_site() -> MagicMock:
    """Create a mock site with URL registry."""
    site = MagicMock()
    site.root_path = Path("/test/site")
    site.output_dir = Path("/test/site/public")
    site.config = {
        "site": {"title": "Test Site", "baseurl": "/"},
    }
    site.baseurl = "/"
    site.url_registry = URLRegistry()
    return site


def _make_sections(paths: list[str]) -> dict[str, Section]:
    """Helper to create virtual sections for given paths."""
    sections: dict[str, Section] = {}
    for path in paths:
        name = path.split("/")[-1] if "/" in path else path
        section = Section.create_virtual(
            name=name,
            relative_url=f"/{path}/",
            title=f"Section {name}",
            metadata={"type": "autodoc-python"},
        )
        sections[path] = section
    return sections


class TestCreateIndexPages:
    """Tests for create_index_pages()."""

    def test_creates_index_for_sections_without_one(self, mock_site: MagicMock) -> None:
        """Section without index_page should get a section-index page created."""
        sections = _make_sections(["api/bengal"])
        assert sections["api/bengal"].index_page is None

        pages = create_index_pages(sections, mock_site)

        assert len(pages) == 1
        assert "section-index" in str(pages[0].source_path)
        assert sections["api/bengal"].index_page is not None

    def test_skips_section_with_existing_index(self, mock_site: MagicMock) -> None:
        """Section that already has index_page should be skipped."""
        sections = _make_sections(["api/bengal"])
        existing_page = MagicMock()
        sections["api/bengal"].index_page = existing_page

        pages = create_index_pages(sections, mock_site)

        assert len(pages) == 0
        # index_page should remain unchanged
        assert sections["api/bengal"].index_page is existing_page

    def test_skips_when_url_claimed_by_different_producer(self, mock_site: MagicMock) -> None:
        """Section-index should NOT be created when URL is claimed by a different source."""
        sections = _make_sections(["cli/assets"])

        # Simulate an autodoc page (e.g., command-group) claiming this URL
        mock_site.url_registry.claim(
            url="/cli/assets/",
            owner="autodoc:cli",
            source="cli/assets.md",
            priority=80,
        )

        pages = create_index_pages(sections, mock_site)

        assert len(pages) == 0

    def test_creates_index_when_url_claimed_by_own_previous_run(self, mock_site: MagicMock) -> None:
        """Section-index SHOULD be created even when URL was claimed by a previous
        section-index page (stale cache claim from incremental build).

        Regression test: incremental builds load URL claims from the build cache.
        Claims from create_index_pages itself (priority 90, source __virtual__/*/section-index.md)
        should not block recreation.
        """
        sections = _make_sections(["api", "cli", "api/bengal"])

        # Simulate stale URL claims loaded from build cache
        for section_path in ["api", "cli", "api/bengal"]:
            mock_site.url_registry.claim(
                url=f"/{section_path}/",
                owner=f"autodoc:{section_path.split('/')[-1]}",
                source=f"__virtual__/{section_path}/section-index.md",
                priority=90,
            )

        pages = create_index_pages(sections, mock_site)

        # All 3 section-index pages should be created despite stale claims
        assert len(pages) == 3
        created_paths = {str(p.source_path) for p in pages}
        assert any("api/section-index" in p for p in created_paths)
        assert any("cli/section-index" in p for p in created_paths)
        assert any("api/bengal/section-index" in p for p in created_paths)

    def test_creates_multiple_index_pages(self, mock_site: MagicMock) -> None:
        """Should create index pages for all sections needing them."""
        sections = _make_sections(["api", "api/bengal", "api/bengal/core", "cli"])

        pages = create_index_pages(sections, mock_site)

        assert len(pages) == 4
        for section_path, section in sections.items():
            assert section.index_page is not None, f"{section_path} should have index_page"

    def test_index_page_output_path_is_html(self, mock_site: MagicMock) -> None:
        """Created index pages should have .html output paths."""
        sections = _make_sections(["api/bengal"])

        pages = create_index_pages(sections, mock_site)

        assert len(pages) == 1
        assert str(pages[0].output_path).endswith("index.html")

    def test_index_page_has_autodoc_metadata(self, mock_site: MagicMock) -> None:
        """Created index pages should have is_autodoc and is_section_index metadata."""
        sections = _make_sections(["api/bengal"])

        pages = create_index_pages(sections, mock_site)

        assert len(pages) == 1
        page = pages[0]
        assert page.metadata.get("is_autodoc") is True
        assert page.metadata.get("is_section_index") is True

    def test_index_page_claims_url_at_priority_90(self, mock_site: MagicMock) -> None:
        """Created index pages should claim their URL at priority 90."""
        sections = _make_sections(["cli"])

        pages = create_index_pages(sections, mock_site)

        assert len(pages) == 1
        claim = mock_site.url_registry.get_claim("/cli/")
        assert claim is not None
        assert claim.priority == 90
        assert "section-index" in claim.source

    def test_mixed_scenario_with_cache_and_other_claims(self, mock_site: MagicMock) -> None:
        """Integration: mix of stale cache claims, other-producer claims, and fresh sections."""
        sections = _make_sections(["api", "api/bengal", "cli", "cli/assets"])

        # api: stale cache claim (should be recreated)
        mock_site.url_registry.claim(
            url="/api/",
            owner="autodoc:api",
            source="__virtual__/api/section-index.md",
            priority=90,
        )

        # cli/assets: claimed by a command-group page (should be skipped)
        mock_site.url_registry.claim(
            url="/cli/assets/",
            owner="autodoc:cli",
            source="cli/assets.md",
            priority=80,
        )

        pages = create_index_pages(sections, mock_site)

        # api: recreated (stale self-claim)
        # api/bengal: fresh (no prior claim)
        # cli: fresh (no prior claim)
        # cli/assets: skipped (claimed by command-group page)
        assert len(pages) == 3
        created_sources = {str(p.source_path) for p in pages}
        assert any("api/section-index" in s for s in created_sources)
        assert any("api/bengal/section-index" in s for s in created_sources)
        assert any("cli/section-index" in s for s in created_sources)
        # cli/assets should NOT have been created
        assert not any("cli/assets/section-index" in s for s in created_sources)
