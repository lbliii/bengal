"""
Shared mock objects for Bengal testing.

This module provides canonical mock implementations of core Bengal objects
for use in unit tests. Using these mocks instead of ad-hoc class definitions
ensures consistency across the test suite and reduces duplication.

Usage:
from tests._testing.mocks import MockPage, MockSection, create_mock_xref_index

def test_something():
    page = MockPage(title="Test", href="/test/")
    section = MockSection(name="docs", title="Documentation")
    xref_index = create_mock_xref_index([page])

# For analysis/graph tests:
from tests._testing.mocks import MockAnalysisPage
    page = MockAnalysisPage(source_path=Path("test.md"), tags=["python"])

Patterns:
- MockPage: Lightweight page mock for directive/rendering tests
- MockSection: Lightweight section mock for navigation tests
- create_mock_xref_index: Build xref_index from mock pages
- MockSite: Lightweight site mock for validator tests
- MockAnalysisPage: Page mock for analysis tests (no `categories` attr)

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
        href: Page URL with baseurl (default: "/")
        _path: Page internal path (default: same as href)
        url: Backward-compatible alias for href (deprecated, use href)
        source_path: Path to source file (default: Path("test.md"))
        metadata: Page metadata dict (default: empty)
        tags: List of tags (default: empty)
        date: Publication date (default: None)
        description: Page description (default: "")
        icon: Page icon identifier (default: "")
        slug: URL slug (derived from source_path stem if not provided)
        _section: Parent section reference (default: None)
    
    Example:
            >>> page = MockPage(title="Getting Started", href="/docs/quickstart/")
            >>> page.title
            'Getting Started'
            >>> page.metadata
        {}
    
            >>> page = MockPage(
            ...     title="API Reference",
            ...     href="/api/",
            ...     metadata={"description": "Complete API docs"},
            ...     tags=["api", "reference"]
            ... )
        
    """

    title: str = ""
    href: str = "/"
    _path: str = ""
    source_path: Path = field(default_factory=lambda: Path("test.md"))
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    date: datetime | None = None
    description: str = ""
    icon: str = ""
    slug: str = ""
    _section: Any = None
    output_path: Path = field(default_factory=lambda: Path("output.html"))
    translations: dict[str, str] | None = None
    name: str = ""

    def __post_init__(self) -> None:
        """Initialize derived fields."""
        if not self.slug:
            self.slug = self.source_path.stem
        if not self._path:
            self._path = self.href
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
            >>> section.index_page.href
            '/docs/'
    
            >>> section = MockSection(
            ...     name="guides",
            ...     title="User Guides",
            ...     pages=[MockPage(title="Quickstart", href="/guides/quickstart/")]
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
            self.index_page.href = f"/{self.name}/"
            self.index_page._path = f"/{self.name}/"
            self.index_page.title = self.title
            self.index_page.metadata = self.metadata


@dataclass
class MockSite:
    """
    Mock site object for testing.
    
    Provides a lightweight site implementation for validator
    and health check tests.
    
    WARNING: This is a mock - do not use for actual file I/O operations.
    The default paths use /dev/null parent to prevent accidental file creation.
    For tests that need real file I/O, pass explicit tmp_path-based paths.
    
    Attributes:
        pages: List of pages in site
        sections: List of top-level sections
        config: Site configuration dict
        root_path: Site root directory (defaults to /dev/null/mock-site)
        output_dir: Build output directory (defaults to /dev/null/mock-output)
    
    Example:
            >>> site = MockSite(pages=[MockPage(title="Home", href="/")])
            >>> len(site.pages)
        1
    
        # For tests needing real paths:
            >>> site = MockSite(
            ...     pages=[page],
            ...     root_path=tmp_path,
            ...     output_dir=tmp_path / "public"
            ... )
        
    """

    pages: list[MockPage] = field(default_factory=list)
    sections: list[MockSection] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    # Use non-existent paths to prevent accidental file I/O at project root
    root_path: Path = field(default_factory=lambda: Path("/dev/null/mock-site"))
    output_dir: Path = field(default_factory=lambda: Path("/dev/null/mock-output"))

    @property
    def baseurl(self) -> str:
        """Return baseurl from config, supporting nested [site].baseurl or flat baseurl."""
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("baseurl"):
            return site_section.get("baseurl", "")
        return self.config.get("baseurl", "")


@dataclass(eq=False)
class MockAnalysisPage:
    """
    Mock page for analysis/graph tests (link suggestions, PageRank, etc.).
    
    This dataclass deliberately does NOT have a `categories` attribute to match
    the Page interface used by LinkSuggestionEngine._build_category_map(), which
    checks `hasattr(page, "category")` first, then falls back to `categories`.
    
    Use this instead of raw Mock() with `del page.categories` patterns.
    
    HASHABILITY:
    ============
    MockAnalysisPage is hashable based on source_path (matching the real Page
    class behavior), allowing use in sets and as dict keys for analysis graphs.
    
    Attributes:
        source_path: Path to source file (required for identity)
        title: Page title (used in LinkSuggestion repr)
        tags: List of tags for topic similarity scoring
        category: Single category (optional, used for category similarity)
        metadata: Page metadata dict (for _generated flag, etc.)
    
    Example:
            >>> page = MockAnalysisPage(
            ...     source_path=Path("docs/guide.md"),
            ...     title="User Guide",
            ...     tags=["python", "tutorial"],
            ...     category="guides"
            ... )
            >>> hasattr(page, "categories")
        False
            >>> hash(page)  # Hashable!
            ...
        
    """

    source_path: Path
    title: str = ""
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash based on source_path (same as Page)."""
        return hash(self.source_path)

    def __eq__(self, other: object) -> bool:
        """Pages are equal if they have the same source path."""
        if not isinstance(other, MockAnalysisPage):
            return NotImplemented
        return self.source_path == other.source_path


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
                href=url,
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
                pages=[
                    p
                    for p in child_pages
                    if "/" not in str(p.source_path).replace(f"{base_path.strip('/')}/{name}/", "")
                ],
                subsections=child_sections,
            )
            sections.append(section)
            pages.extend(child_pages)

    return pages, sections
