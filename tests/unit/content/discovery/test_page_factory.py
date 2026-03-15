"""
Unit tests for PageInitializer (page_factory module).

Tests: ensure_initialized validation, output_path requirement,
section reference, URL generation validation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.content.discovery.page_factory import PageInitializer
from bengal.core.page import Page


def _make_site(output_dir: Path) -> MagicMock:
    """Create mock Site with output_dir."""
    site = MagicMock()
    site.output_dir = output_dir
    site.get_section_by_path = MagicMock(return_value=None)
    return site


class TestPageInitializerEnsureInitialized:
    """Test ensure_initialized behavior."""

    def test_sets_site_if_missing(self, tmp_path: Path) -> None:
        """ensure_initialized sets _site if missing."""
        site = _make_site(tmp_path / "output")
        page = Page(
            source_path=tmp_path / "page.md",
            _raw_content="",
            _raw_metadata={"title": "Test"},
        )
        page.output_path = tmp_path / "output" / "page" / "index.html"
        initializer = PageInitializer(site)
        initializer.ensure_initialized(page)
        assert page._site is site

    def test_raises_when_output_path_missing(self, tmp_path: Path) -> None:
        """ensure_initialized raises when output_path is not set."""
        from bengal.errors import BengalContentError

        site = _make_site(tmp_path / "output")
        page = Page(
            source_path=tmp_path / "page.md",
            _raw_content="",
            _raw_metadata={"title": "Test"},
        )
        page.output_path = None  # type: ignore[assignment]
        initializer = PageInitializer(site)
        with pytest.raises(BengalContentError) as exc_info:
            initializer.ensure_initialized(page)
        assert "output_path" in str(exc_info.value).lower()

    def test_raises_when_output_path_relative(self, tmp_path: Path) -> None:
        """ensure_initialized raises when output_path is relative."""
        from bengal.errors import BengalContentError

        site = _make_site(tmp_path / "output")
        page = Page(
            source_path=tmp_path / "page.md",
            _raw_content="",
            _raw_metadata={"title": "Test"},
        )
        page.output_path = Path("page/index.html")
        initializer = PageInitializer(site)
        with pytest.raises(BengalContentError) as exc_info:
            initializer.ensure_initialized(page)
        assert (
            "relative" in str(exc_info.value).lower() or "absolute" in str(exc_info.value).lower()
        )


class TestPageInitializerEnsureInitializedForSection:
    """Test ensure_initialized_for_section."""

    def test_sets_section_reference(self, tmp_path: Path) -> None:
        """ensure_initialized_for_section sets _section_path and lookup returns section."""
        from bengal.core.section import Section

        section = Section(name="blog", path=tmp_path / "blog")
        site = _make_site(tmp_path / "output")
        site.get_section_by_path = lambda path: section if path == section.path else None
        page = Page(
            source_path=tmp_path / "blog" / "post.md",
            _raw_content="",
            _raw_metadata={"title": "Post"},
        )
        page.output_path = tmp_path / "output" / "blog" / "post" / "index.html"
        initializer = PageInitializer(site)
        initializer.ensure_initialized_for_section(page, section)
        assert page._section_path == section.path
        assert page._section is section
