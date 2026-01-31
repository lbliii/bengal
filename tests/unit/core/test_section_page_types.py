"""
Tests for Section handling of Page and PageProxy types.

These tests verify that Section.add_page correctly handles:
- Regular Page objects
- PageProxy objects
- Mixed collections of Page and PageProxy
- PageProxy lazy loading behavior when accessed via Section
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bengal.core.page import Page, PageProxy
from bengal.core.page.page_core import PageCore
from bengal.core.section import Section


def make_page_core(source_path: str | Path, title: str, *, weight: int | None = None) -> PageCore:
    """Helper to create a PageCore for testing."""
    return PageCore(
        source_path=str(source_path),
        title=title,
        weight=weight,
    )


def make_page(source_path: Path, title: str = "Test", content: str = "") -> Page:
    """Helper to create a Page for testing."""
    return Page(
        source_path=source_path,
        _raw_content=content,
        metadata={"title": title},
    )


def make_proxy(
    source_path: Path,
    title: str,
    *,
    weight: int | None = None,
    loader: Any = None,
) -> PageProxy:
    """Helper to create a PageProxy for testing."""
    core = make_page_core(source_path, title, weight=weight)
    if loader is None:

        def loader(path: Path = source_path) -> Page:
            return make_page(path, title)

    return PageProxy(
        source_path=source_path,
        metadata=core,
        loader=loader,
    )


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Create a test content directory."""
    content = tmp_path / "content"
    content.mkdir()
    return content


@pytest.fixture
def docs_section(content_dir: Path) -> Section:
    """Create a test section."""
    docs = content_dir / "docs"
    docs.mkdir()
    return Section(name="docs", path=docs)


@pytest.fixture
def sample_page(content_dir: Path) -> Page:
    """Create a sample page."""
    file_path = content_dir / "docs" / "guide.md"
    file_path.write_text("---\ntitle: Guide\n---\n# Guide")
    return make_page(file_path, "Guide", "# Guide")


@pytest.fixture
def sample_proxy(content_dir: Path) -> PageProxy:
    """Create a sample PageProxy."""
    file_path = content_dir / "docs" / "proxy.md"
    file_path.write_text("---\ntitle: Proxy Page\nweight: 1\n---\n# Proxy")

    return make_proxy(file_path, "Proxy Page", weight=1)


class TestSectionAddPage:
    """Test Section.add_page method with different types."""

    def test_add_regular_page(self, docs_section: Section, sample_page: Page) -> None:
        """Section should accept regular Page objects."""
        docs_section.add_page(sample_page)

        assert len(docs_section.pages) == 1
        assert docs_section.pages[0] is sample_page

    def test_add_page_proxy(self, docs_section: Section, sample_proxy: PageProxy) -> None:
        """Section should accept PageProxy objects."""
        docs_section.add_page(sample_proxy)

        assert len(docs_section.pages) == 1
        assert docs_section.pages[0] is sample_proxy

    def test_add_mixed_types(
        self, docs_section: Section, sample_page: Page, sample_proxy: PageProxy
    ) -> None:
        """Section should handle mixed Page and PageProxy."""
        docs_section.add_page(sample_page)
        docs_section.add_page(sample_proxy)

        assert len(docs_section.pages) == 2
        assert isinstance(docs_section.pages[0], Page)
        assert isinstance(docs_section.pages[1], PageProxy)


class TestSectionQueriesWithProxy:
    """Test section query methods work with PageProxy."""

    def test_pages_list_includes_proxies(
        self, docs_section: Section, sample_page: Page, sample_proxy: PageProxy
    ) -> None:
        """pages list should include both types after add_page."""
        docs_section.add_page(sample_page)
        docs_section.add_page(sample_proxy)

        all_pages = docs_section.pages

        assert len(all_pages) == 2

    def test_find_page_by_title(self, docs_section: Section, content_dir: Path) -> None:
        """Finding pages by attribute should work with proxies."""
        page1 = make_proxy(content_dir / "p1.md", "First")
        page2 = make_proxy(content_dir / "p2.md", "Second")

        docs_section.add_page(page1)
        docs_section.add_page(page2)

        # Find by title
        found = [p for p in docs_section.pages if p.title == "First"]

        assert len(found) == 1
        assert found[0].title == "First"


class TestPageProxyLazyLoading:
    """Test PageProxy lazy loading behavior in Section context."""

    def test_proxy_title_without_loading(
        self, docs_section: Section, sample_proxy: PageProxy
    ) -> None:
        """Accessing proxy.title should not trigger full load."""
        # Track if loader was called
        loader_called = [False]
        original_loader = sample_proxy._loader

        def tracking_loader(path: Path) -> Page:
            loader_called[0] = True
            return original_loader(path)

        sample_proxy._loader = tracking_loader
        docs_section.add_page(sample_proxy)

        # Access title
        _ = docs_section.pages[0].title

        # Should not have loaded
        assert not loader_called[0]

    def test_proxy_content_triggers_loading(
        self, docs_section: Section, sample_proxy: PageProxy
    ) -> None:
        """Accessing proxy.content should trigger full load."""
        docs_section.add_page(sample_proxy)

        # Access content (requires full load)
        proxy = docs_section.pages[0]
        if isinstance(proxy, PageProxy):
            # Force load
            proxy._ensure_loaded()
            full_page = proxy._full_page
            assert isinstance(full_page, Page)

    def test_proxy_load_once(self, docs_section: Section, content_dir: Path) -> None:
        """Loader should only be called once on repeated access."""
        call_count = [0]

        def counting_loader(path: Path) -> Page:
            call_count[0] += 1
            return make_page(path, "Test", "content")

        proxy = make_proxy(
            content_dir / "test.md",
            "Test",
            loader=counting_loader,
        )
        docs_section.add_page(proxy)

        # Multiple _ensure_loaded calls
        proxy._ensure_loaded()
        proxy._ensure_loaded()
        proxy._ensure_loaded()

        # Should only call loader once
        assert call_count[0] == 1


class TestSectionIterationWithProxies:
    """Test Section iteration methods with mixed types."""

    def test_iterate_pages(
        self, docs_section: Section, sample_page: Page, sample_proxy: PageProxy
    ) -> None:
        """Iterating section.pages should yield both types."""
        docs_section.add_page(sample_page)
        docs_section.add_page(sample_proxy)

        types = [type(p) for p in docs_section.pages]

        assert Page in types
        assert PageProxy in types

    def test_pages_len_includes_proxies(
        self, docs_section: Section, sample_page: Page, sample_proxy: PageProxy
    ) -> None:
        """len(pages) should count both Page and PageProxy."""
        docs_section.add_page(sample_page)
        docs_section.add_page(sample_proxy)

        assert len(docs_section.pages) == 2


class TestSectionPageFiltering:
    """Test filtering operations work with both types."""

    def test_filter_by_attribute(self, docs_section: Section, content_dir: Path) -> None:
        """Filtering pages by attribute should work for proxies."""
        page1 = make_proxy(content_dir / "p1.md", "Python Guide", weight=1)
        page2 = make_proxy(content_dir / "p2.md", "Java Guide", weight=2)

        docs_section.add_page(page1)
        docs_section.add_page(page2)

        # Filter by title containing "Python"
        python_pages = [p for p in docs_section.pages if "Python" in p.title]

        assert len(python_pages) == 1
        assert python_pages[0].title == "Python Guide"


class TestTypeAnnotationCompatibility:
    """Test that type annotations are consistent."""

    def test_pages_list_type_allows_both(
        self, docs_section: Section, sample_page: Page, sample_proxy: PageProxy
    ) -> None:
        """pages list should accept both Page and PageProxy via add_page."""
        docs_section.add_page(sample_page)
        docs_section.add_page(sample_proxy)

        assert len(docs_section.pages) == 2

    def test_section_builder_compatibility(self, content_dir: Path) -> None:
        """SectionBuilder should work with PageProxy."""
        from bengal.content.discovery.section_builder import SectionBuilder

        builder = SectionBuilder(content_dir)

        proxy = make_proxy(content_dir / "test.md", "Test")

        # Should not raise
        builder.pages.append(proxy)

        assert len(builder.pages) == 1
