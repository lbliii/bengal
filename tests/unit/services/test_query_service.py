"""
Unit tests for QueryService.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 4: Service Extraction)
"""

from pathlib import Path
from types import MappingProxyType

import pytest

from bengal.services.query import (
    QueryService,
    get_page,
    get_page_by_path,
    get_pages_by_tag,
    get_section,
)
from bengal.snapshots.types import PageSnapshot, SectionSnapshot, SiteSnapshot


def make_section_snapshot(
    path: Path,
    url: str,
    title: str = "Test Section",
) -> SectionSnapshot:
    """Create a test SectionSnapshot."""
    return SectionSnapshot(
        name=path.name if path else "test",
        title=title,
        nav_title=title,
        href=url,
        path=path,
        pages=(),
        sorted_pages=(),
        regular_pages=(),
        subsections=(),
        sorted_subsections=(),
        parent=None,
        depth=0,
    )


def make_page_snapshot(
    source_path: Path,
    href: str,
    title: str = "Test Page",
    tags: tuple[str, ...] = (),
    section: SectionSnapshot | None = None,
) -> PageSnapshot:
    """Create a test PageSnapshot."""
    return PageSnapshot(
        title=title,
        href=href,
        source_path=source_path,
        output_path=Path(f"public{href}index.html"),
        template_name="single.html",
        content="Test content",
        parsed_html="<p>Test content</p>",
        toc="",
        toc_items=(),
        excerpt="Test excerpt",
        metadata=MappingProxyType({}),
        tags=tags,
        categories=(),
        reading_time=1,
        word_count=100,
        content_hash="abc123",
        section=section,
        next_page=None,
        prev_page=None,
        attention_score=1.0,
        estimated_render_ms=10.0,
    )


def make_site_snapshot(
    pages: list[PageSnapshot],
    sections: list[SectionSnapshot],
) -> SiteSnapshot:
    """Create a test SiteSnapshot."""
    # Create a minimal root section if needed
    root_section = sections[0] if sections else make_section_snapshot(
        Path("/test/site/content"),
        "/",
        "Root",
    )
    
    return SiteSnapshot(
        pages=tuple(pages),
        regular_pages=tuple(pages),
        sections=tuple(sections),
        root_section=root_section,
        config=MappingProxyType({}),
        params=MappingProxyType({}),
        data=MappingProxyType({}),
        menus=MappingProxyType({}),
        taxonomies=MappingProxyType({}),
        topological_order=(),
        template_groups=MappingProxyType({}),
        attention_order=(),
        scout_hints=(),
        snapshot_time=0.0,
        page_count=len(pages),
        section_count=len(sections),
    )


class TestQueryService:
    """Tests for QueryService class."""

    def test_create_from_snapshot(self) -> None:
        """QueryService can be created from SiteSnapshot."""
        section = make_section_snapshot(Path("/test/docs"), "/docs/")
        page = make_page_snapshot(
            Path("/test/content/docs/intro.md"),
            "/docs/intro/",
            section=section,
        )
        snapshot = make_site_snapshot([page], [section])
        
        service = QueryService.from_snapshot(snapshot)
        assert service is not None

    def test_get_page_by_href(self) -> None:
        """QueryService.get_page returns page by href."""
        page = make_page_snapshot(Path("/test/content/page.md"), "/page/")
        snapshot = make_site_snapshot([page], [])
        
        service = QueryService.from_snapshot(snapshot)
        result = service.get_page("/page/")
        assert result == page

    def test_get_page_not_found(self) -> None:
        """QueryService.get_page returns None for unknown href."""
        snapshot = make_site_snapshot([], [])
        service = QueryService.from_snapshot(snapshot)
        
        result = service.get_page("/unknown/")
        assert result is None

    def test_get_page_by_path(self) -> None:
        """QueryService.get_page_by_path returns page by source path."""
        source_path = Path("/test/content/page.md")
        page = make_page_snapshot(source_path, "/page/")
        snapshot = make_site_snapshot([page], [])
        
        service = QueryService.from_snapshot(snapshot)
        result = service.get_page_by_path(source_path)
        assert result == page

    def test_get_section_by_url(self) -> None:
        """QueryService.get_section returns section by URL."""
        section = make_section_snapshot(Path("/test/docs"), "/docs/")
        snapshot = make_site_snapshot([], [section])
        
        service = QueryService.from_snapshot(snapshot)
        result = service.get_section("/docs/")
        assert result == section

    def test_get_pages_by_tag(self) -> None:
        """QueryService.get_pages_by_tag returns all pages with tag."""
        page1 = make_page_snapshot(
            Path("/test/content/p1.md"),
            "/p1/",
            tags=("python", "web"),
        )
        page2 = make_page_snapshot(
            Path("/test/content/p2.md"),
            "/p2/",
            tags=("python",),
        )
        page3 = make_page_snapshot(
            Path("/test/content/p3.md"),
            "/p3/",
            tags=("rust",),
        )
        snapshot = make_site_snapshot([page1, page2, page3], [])
        
        service = QueryService.from_snapshot(snapshot)
        result = service.get_pages_by_tag("python")
        
        assert len(result) == 2
        assert page1 in result
        assert page2 in result
        assert page3 not in result

    def test_get_pages_by_section(self) -> None:
        """QueryService.get_pages_by_section returns section pages."""
        section = make_section_snapshot(Path("/test/docs"), "/docs/")
        other_section = make_section_snapshot(Path("/test/blog"), "/blog/")
        
        page1 = make_page_snapshot(
            Path("/test/content/docs/p1.md"),
            "/docs/p1/",
            section=section,
        )
        page2 = make_page_snapshot(
            Path("/test/content/docs/p2.md"),
            "/docs/p2/",
            section=section,
        )
        page3 = make_page_snapshot(
            Path("/test/content/blog/p3.md"),
            "/blog/p3/",
            section=other_section,
        )
        
        snapshot = make_site_snapshot([page1, page2, page3], [section, other_section])
        service = QueryService.from_snapshot(snapshot)
        
        result = service.get_pages_by_section("/docs/")
        assert len(result) == 2
        assert page1 in result
        assert page2 in result


class TestQueryPureFunctions:
    """Tests for pure query functions."""

    def test_get_section(self) -> None:
        """get_section returns section by URL."""
        section = make_section_snapshot(Path("/test/docs"), "/docs/")
        snapshot = make_site_snapshot([], [section])
        
        result = get_section(snapshot, "/docs/")
        assert result == section

    def test_get_page(self) -> None:
        """get_page returns page by href."""
        page = make_page_snapshot(Path("/test/content/page.md"), "/page/")
        snapshot = make_site_snapshot([page], [])
        
        result = get_page(snapshot, "/page/")
        assert result == page

    def test_get_page_by_path(self) -> None:
        """get_page_by_path returns page by source path."""
        source_path = Path("/test/content/page.md")
        page = make_page_snapshot(source_path, "/page/")
        snapshot = make_site_snapshot([page], [])
        
        result = get_page_by_path(snapshot, source_path)
        assert result == page

    def test_get_pages_by_tag(self) -> None:
        """get_pages_by_tag returns pages with tag."""
        page1 = make_page_snapshot(
            Path("/test/content/p1.md"),
            "/p1/",
            tags=("python",),
        )
        page2 = make_page_snapshot(
            Path("/test/content/p2.md"),
            "/p2/",
            tags=("rust",),
        )
        snapshot = make_site_snapshot([page1, page2], [])
        
        result = get_pages_by_tag(snapshot, "python")
        assert len(result) == 1
        assert page1 in result
