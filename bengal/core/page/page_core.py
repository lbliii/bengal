"""
PageCore - Cacheable page metadata shared between Page, PageMetadata, and PageProxy.

This module defines PageCore, the single source of truth for all cacheable page
metadata. Any field added to PageCore automatically becomes available in:

- Page: via page.core.field or @property delegate (e.g., page.title)
- PageMetadata: IS PageCore (type alias in cache/page_discovery_cache.py)
- PageProxy: via proxy.field property (no lazy load needed for core fields)

This design prevents cache bugs by making it impossible to have mismatched field
definitions between Page, PageMetadata, and PageProxy. The compiler enforces that
all three representations stay in sync.

Architecture:
    PageCore = Cacheable fields only (title, date, tags, etc.)
    Page = PageCore + non-cacheable fields (content, rendered_html, toc, etc.)
    PageMetadata = PageCore (type alias for caching)
    PageProxy = Wraps PageCore (lazy loads only non-core fields)

What Goes in PageCore?
    ✅ DO include if:
    - Field comes from frontmatter (title, date, tags, slug, etc.)
    - Field is computed without full content parsing (url path components)
    - Field needs to be accessible in templates without lazy loading
    - Field is cascaded from section _index.md (type, layout, etc.)
    - Field is used for navigation (section reference as path)

    ❌ DO NOT include if:
    - Field requires full content parsing (toc, excerpt, meta_description)
    - Field is a build artifact (output_path, links, rendered_html)
    - Field changes every build (timestamp, render_time)
    - Field is computed from other non-cacheable fields

Example Usage:
    # Creating a PageCore
    from datetime import datetime

    core = PageCore(
        source_path="content/posts/my-post.md",  # String path for JSON compatibility
        title="My Post",
        date=datetime(2025, 10, 26),
        tags=["python", "web"],
        slug="my-post",
        type="doc",
    )

    # Using in Page (composition)
    from bengal.core.page import Page

    page = Page(
        core=core,
        content="# Hello World",
        rendered_html="<h1>Hello World</h1>",
    )

    # Accessing fields via property delegates
    assert page.title == "My Post"  # Property delegate
    assert page.core.title == "My Post"  # Direct access

    # Caching (PageMetadata = PageCore)
    from dataclasses import asdict
    import json

    metadata = page.core  # Already PageCore!
    json_str = json.dumps(asdict(metadata), default=str)

    # Loading from cache
    from bengal.core.page.proxy import PageProxy

    loaded_core = PageCore(**json.loads(json_str))
    proxy = PageProxy(core=loaded_core, loader=load_page_fn)

    # Accessing cached fields (no lazy load)
    assert proxy.title == "My Post"  # Direct from core

Adding New Fields:
    When adding a new cacheable field:

    1. Add to PageCore (this file):
        @dataclass
        class PageCore:
            # ... existing fields ...
            author: str | None = None  # NEW

    2. Add @property delegate to Page (bengal/core/page/__init__.py):
        @property
        def author(self) -> str | None:
            return self.core.author

    3. Add @property delegate to PageProxy (bengal/core/page/proxy.py):
        @property
        def author(self) -> str | None:
            return self._core.author

    That's it! Field is now available in Page, PageMetadata, and PageProxy.
    The compiler will catch any missing implementations.

See Also:
    - architecture/object-model.md - PageProxy & Cache Contract section
    - plan/active/rfc-cache-proxy-contract.md - Design rationale
    - CONTRIBUTING.md - Guidelines for adding fields
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PageCore:
    """
    Cacheable page metadata shared between Page, PageMetadata, and PageProxy.

    This is the single source of truth for all cacheable page data. All fields
    here can be serialized to JSON and stored in .bengal/page_metadata.json for
    incremental builds.

    Attributes:
        source_path: Path to source markdown file (relative to content dir).
            Used as cache key and for file change detection.

        title: Page title from frontmatter or filename.
            Required field, defaults to "Untitled" if not provided.

        date: Publication date from frontmatter.
            Used for sorting, archives, and RSS feeds. None if not specified.

        tags: List of tag strings from frontmatter.
            Used for taxonomy pages and filtering. Empty list if not specified.

        slug: URL slug for this page.
            Overrides default slug derived from filename. None means use default.

        weight: Sort weight within section.
            Lower numbers appear first. None means use default sorting.

        lang: Language code for i18n (e.g., "en", "es", "fr").
            None means use site default language.

        type: Page type from frontmatter or cascaded from section.
            Determines which layout/template to use (e.g., "doc", "post", "page").
            Cascaded from section _index.md if not specified in page frontmatter.

        section: Section path (e.g., "content/docs" or "docs").
            Stored as path string, not Section object, for stability across rebuilds.
            None for root-level pages.

        file_hash: SHA256 hash of source file content.
            Used for cache validation to detect file changes.
            None during initial creation, populated during caching.

    Design Notes:
        - All fields are JSON-serializable (no object references)
        - Paths stored as strings (resolved to objects via registry on access)
        - Optional fields default to None (not all pages have all metadata)
        - No circular references (enables straightforward serialization)
        - No computed fields that require full content (those go in Page)

    Cache Lifecycle:
        1. Page created with PageCore during discovery
        2. PageCore serialized to JSON and saved to cache
        3. On incremental rebuild, PageCore loaded from cache
        4. PageProxy wraps PageCore for lazy loading
        5. Templates access fields via proxy properties (no load)
        6. Full page loaded only if non-core field accessed

    Performance:
        - PageCore is ~500 bytes per page (10 fields × ~50 bytes each)
        - 10,000 pages = ~5MB for all cores (acceptable)
        - Serialization/deserialization via asdict() is ~10µs per page
        - Memory overhead negligible vs full Page objects
    """

    # Required fields
    source_path: str  # Path to source file (cache key, stored as string for JSON)
    title: str  # Page title (frontmatter or filename)

    # Frontmatter fields (optional)
    date: datetime | None = None  # Publication date
    tags: list[str] = field(default_factory=list)  # Taxonomy tags
    slug: str | None = None  # URL slug override
    weight: int | None = None  # Sort weight in section
    lang: str | None = None  # Language code (i18n)

    # Cascaded fields (from section _index.md)
    type: str | None = None  # Page type (determines layout)

    # References (path-based, not object references)
    section: str | None = None  # Section path (stable across rebuilds)

    # Validation
    file_hash: str | None = None  # SHA256 of source file for cache validation

    def __post_init__(self):
        """
        Validate and normalize fields after initialization.

        This runs automatically after dataclass initialization.
        """
        # Ensure title is not empty
        if not self.title:
            self.title = "Untitled"

        # Ensure tags is a list (not None)
        if self.tags is None:
            self.tags = []
