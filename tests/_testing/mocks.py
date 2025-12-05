"""
Shared mock objects for Bengal testing.

This module provides canonical mock implementations of core Bengal objects
for use in unit tests. Using these mocks instead of ad-hoc class definitions
ensures consistency across the test suite and reduces duplication.

Usage:
    from tests._testing.mocks import MockPage, MockSection, create_mock_xref_index

    def test_something():
        page = MockPage(title="Test", url="/test/")
        section = MockSection(name="docs", title="Documentation")
        xref_index = create_mock_xref_index([page])

Patterns:
    - MockPage: Lightweight page mock for directive/rendering tests
    - MockSection: Lightweight section mock for navigation tests
    - create_mock_xref_index: Build xref_index from mock pages
    - MockSite: Lightweight site mock for validator tests
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock


@dataclass
class MockPage:
    """
    Mock page object for testing.

    Provides a lightweight page implementation with common attributes
    used in directive, rendering, and template tests.

    Attributes:
        title: Page title (required)
        url: Page URL path (default: "/")
        source_path: Path to source file (default: Path("test.md"))
        metadata: Page metadata dict (default: empty)
        tags: List of tags (default: empty)
        date: Publication date (default: None)
        description: Page description (default: "")
        icon: Page icon identifier (default: "")
        slug: URL slug (derived from source_path stem if not provided)
        _section: Parent section reference (default: None)

    Example:
        >>> page = MockPage(title="Getting Started", url="/docs/quickstart/")
        >>> page.title
        'Getting Started'
        >>> page.metadata
        {}

        >>> page = MockPage(
        ...     title="API Reference",
        ...     url="/api/",
        ...     metadata={"description": "Complete API docs"},
        ...     tags=["api", "reference"]
        ... )
    """

    title: str = ""
    url: str = "/"
    source_path: Path = field(default_factory=lambda: Path("test.md"))
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    date: datetime | None = None
    description: str = ""
    icon: str = ""
    slug: str = ""
    _section: Any = None
    output_path: Path = field(default_factory=lambda: Path("output.html"))
    relative_url: str = ""
    translations: dict[str, str] | None = None
    name: str = ""

    def __post_init__(self) -> None:
        """Initialize derived fields."""
        if not self.slug:
            self.slug = self.source_path.stem
        if not self.relative_url:
            self.relative_url = self.url
        # Sync metadata with explicit fields
        if self.description and "description" not in self.metadata:
            self.metadata["description"] = self.description
        if self.icon and "icon" not in self.metadata:
            self.metadata["icon"] = self.icon


@dataclass
class MockSection:
    """
    Mock section object for testing.

    Provides a lightweight section implementation for navigation
    and hierarchy tests.

    Attributes:
        name: Section name (directory name)
        title: Section display title
        path: Path to section directory
        metadata: Section metadata dict
        subsections: List of child sections
        pages: List of pages in section
        index_page: Section index page (auto-created if None)

    Example:
        >>> section = MockSection(name="docs", title="Documentation")
        >>> section.index_page.url
        '/docs/'

        >>> section = MockSection(
        ...     name="guides",
        ...     title="User Guides",
        ...     pages=[MockPage(title="Quickstart", url="/guides/quickstart/")]
        ... )
    """

    name: str
    title: str
    path: Path = field(default_factory=lambda: Path("section"))
    metadata: dict[str, Any] = field(default_factory=dict)
    subsections: list[MockSection] = field(default_factory=list)
    pages: list[MockPage] = field(default_factory=list)
    index_page: Any = None

    def __post_init__(self) -> None:
        """Initialize index page if not provided."""
        if self.index_page is None:
            self.index_page = Mock()
            self.index_page.url = f"/{self.name}/"
            self.index_page.title = self.title
            self.index_page.metadata = self.metadata


@dataclass
class MockSite:
    """
    Mock site object for testing.

    Provides a lightweight site implementation for validator
    and health check tests.

    Attributes:
        pages: List of pages in site
        sections: List of top-level sections
        config: Site configuration dict
        root_path: Site root directory
        output_dir: Build output directory

    Example:
        >>> site = MockSite(pages=[MockPage(title="Home", url="/")])
        >>> len(site.pages)
        1
    """

    pages: list[MockPage] = field(default_factory=list)
    sections: list[MockSection] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    root_path: Path = field(default_factory=lambda: Path("."))
    output_dir: Path = field(default_factory=lambda: Path("public"))


def create_mock_xref_index(pages: list[MockPage]) -> dict[str, Any]:
    """
    Build xref_index from mock pages.

    Creates the cross-reference index structure used by the markdown
    parser for resolving [[wiki-style]] links.

    Args:
        pages: List of MockPage objects to index

    Returns:
        Dictionary with by_id, by_path, by_slug, and by_heading keys

    Example:
        >>> pages = [
        ...     MockPage(title="Home", url="/", source_path=Path("index.md")),
        ...     MockPage(title="About", url="/about/", source_path=Path("about.md")),
        ... ]
        >>> index = create_mock_xref_index(pages)
        >>> index["by_slug"]["about"][0].title
        'About'
    """
    by_path: dict[str, MockPage] = {}
    by_slug: dict[str, list[MockPage]] = {}
    by_id: dict[str, MockPage] = {}

    for page in pages:
        # Index by path (without extension)
        path_key = str(page.source_path.with_suffix(""))
        by_path[path_key] = page

        # Index by slug (can have duplicates)
        slug = page.slug or page.source_path.stem
        if slug not in by_slug:
            by_slug[slug] = []
        by_slug[slug].append(page)

        # Index by id (if present in metadata)
        if "id" in page.metadata:
            by_id[page.metadata["id"]] = page

    return {
        "by_id": by_id,
        "by_path": by_path,
        "by_slug": by_slug,
        "by_heading": {},  # Not typically needed for mock tests
    }


def create_mock_page_hierarchy(
    structure: dict[str, Any],
    base_path: str = "",
) -> tuple[list[MockPage], list[MockSection]]:
    """
    Create a page/section hierarchy from a structure definition.

    Useful for creating complex test hierarchies without manual setup.

    Args:
        structure: Dict defining hierarchy (keys are names, values are nested dicts or None)
        base_path: Base URL path (default: "")

    Returns:
        Tuple of (pages, sections)

    Example:
        >>> structure = {
        ...     "docs": {
        ...         "_index": None,  # Section index
        ...         "quickstart": None,  # Page
        ...         "guides": {
        ...             "_index": None,
        ...             "tutorial": None,
        ...         }
        ...     }
        ... }
        >>> pages, sections = create_mock_page_hierarchy(structure)
    """
    pages: list[MockPage] = []
    sections: list[MockSection] = []

    for name, children in structure.items():
        url = f"{base_path}/{name}/" if name != "_index" else f"{base_path}/"

        if children is None:
            # Leaf page
            page = MockPage(
                title=name.replace("-", " ").title(),
                url=url,
                source_path=Path(f"{base_path.strip('/')}/{name}.md"),
            )
            pages.append(page)
        else:
            # Section with children
            child_pages, child_sections = create_mock_page_hierarchy(children, url.rstrip("/"))

            section = MockSection(
                name=name,
                title=name.replace("-", " ").title(),
                path=Path(f"{base_path.strip('/')}/{name}"),
                pages=[p for p in child_pages if "/" not in str(p.source_path).replace(f"{base_path.strip('/')}/{name}/", "")],
                subsections=child_sections,
            )
            sections.append(section)
            pages.extend(child_pages)

    return pages, sections

