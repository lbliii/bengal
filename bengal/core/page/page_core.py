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

```python
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
```

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
from typing import Any

from bengal.cache.cacheable import Cacheable


@dataclass
class PageCore(Cacheable):
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

    Why Strings Instead of Path Objects?
        1. JSON Serialization: Path objects cannot be directly JSON-serialized.
           Using strings allows cache files to be saved/loaded without custom handlers.

        2. Cache Portability: String paths work across systems without Path object
           compatibility concerns (Windows vs Unix path separators handled by Path
           when converting back).

        3. Type Consistency: PageMetadata IS PageCore (type alias). Cache expects
           strings, so PageCore must use strings for type compatibility.

        4. Performance: String comparison for cache lookups is marginally faster
           than Path comparison (matters for incremental builds with 1000+ pages).

        Convert at boundaries:
        - Input: Path → str when creating PageCore (Page.__post_init__)
        - Output: str → Path when using paths (PageProxy, lookups)

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
    nav_title: str | None = None  # Short title for navigation (falls back to title)

    # Cascaded fields (from section _index.md)
    type: str | None = None  # Page type (routing/strategy)
    variant: str | None = None  # Visual variant (CSS/layouts)

    # Core Props (Promoted for performance)
    description: str | None = None  # SEO description (promoted from metadata)
    props: dict[str, Any] = field(default_factory=dict)  # Additional metadata/props

    # References (path-based, not object references)
    section: str | None = None  # Section path (stable across rebuilds)

    # Validation
    file_hash: str | None = None  # SHA256 of source file for cache validation

    # Redirect aliases - alternative URLs that redirect to this page
    aliases: list[str] = field(default_factory=list)

    # Versioning (from discovery or frontmatter)
    version: str | None = None  # Version ID (e.g., 'v3', 'v2')

    def __post_init__(self) -> None:
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

    def to_cache_dict(self) -> dict[str, Any]:
        """
        Serialize PageCore to cache-friendly dictionary.

        Implements the Cacheable protocol for type-safe caching.

        Returns:
            Dictionary with all PageCore fields, suitable for JSON serialization.
            datetime fields are serialized as ISO-8601 strings.
        """
        return {
            "source_path": self.source_path,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "tags": self.tags,
            "slug": self.slug,
            "weight": self.weight,
            "lang": self.lang,
            "nav_title": self.nav_title,
            "type": self.type,
            "variant": self.variant,
            "description": self.description,
            "props": self.props,
            "section": self.section,
            "file_hash": self.file_hash,
            "aliases": self.aliases,
            "version": self.version,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> PageCore:
        """
        Deserialize PageCore from cache dictionary.

        Implements the Cacheable protocol for type-safe caching.

        Args:
            data: Dictionary from cache (JSON-deserialized)

        Returns:
            Reconstructed PageCore instance
        """
        return cls(
            source_path=data["source_path"],
            title=data["title"],
            date=datetime.fromisoformat(data["date"]) if data.get("date") else None,
            tags=data.get("tags", []),
            slug=data.get("slug"),
            weight=data.get("weight"),
            lang=data.get("lang"),
            nav_title=data.get("nav_title"),
            type=data.get("type"),
            variant=data.get("variant"),
            description=data.get("description"),
            props=data.get("props", {}),
            section=data.get("section"),
            file_hash=data.get("file_hash"),
            aliases=data.get("aliases", []),
            version=data.get("version"),
        )
