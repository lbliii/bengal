"""
PageProxy - Lazy-loaded page placeholder for incremental builds.

A PageProxy holds minimal page metadata (title, date, tags, etc.) loaded from
the PageDiscoveryCache and defers loading full page content until needed.

This enables incremental builds to skip disk I/O and parsing for unchanged
pages while maintaining transparent access (code doesn't know it's lazy).

Architecture:
- Metadata loaded immediately from cache (fast)
- Full content loaded on first access to .content or other lazy properties
- Transparent to callers - behaves like a normal Page object
- Falls back to eager load if cascades or complex operations detected
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page

from .page_core import PageCore

logger = get_logger(__name__)


class PageProxy:
    """
    Lazy-loaded page placeholder.

    Holds page metadata from cache and defers loading full content until
    accessed. Transparent to callers - implements Page-like interface.

    LIFECYCLE IN INCREMENTAL BUILDS:
    ---------------------------------
    1. **Discovery** (content_discovery.py):
       - Created from cached metadata for unchanged pages
       - Has: title, date, tags, slug, _section, _site, output_path
       - Does NOT have: content, rendered_html (lazy-loaded on demand)

    2. **Filtering** (incremental.py):
       - PageProxy objects pass through find_work_early() unchanged
       - Only modified pages become full Page objects for rendering

    3. **Rendering** (render.py):
       - Modified pages rendered as full Page objects
       - PageProxy objects skipped (already have cached output)

    4. **Update** (build.py Phase 8.4):
       - Freshly rendered Page objects REPLACE their PageProxy counterparts
       - site.pages becomes: mix of fresh Page (rebuilt) + PageProxy (cached)

    5. **Postprocessing** (postprocess.py):
       - Iterates over site.pages (now updated with fresh Pages)
       - ⚠️ CRITICAL: PageProxy must implement ALL properties/methods used:
         * output_path (for finding where to write .txt/.json)
         * url, permalink (for generating index.json)
         * title, date, tags (for content in output files)

    TRANSPARENCY CONTRACT:
    ----------------------
    PageProxy must be transparent to:
    - **Templates**: Implements .url, .permalink, .title, etc.
    - **Postprocessing**: Implements .output_path, metadata access
    - **Navigation**: Implements .prev, .next (via lazy load)

    ⚠️ When adding new Page properties used by templates/postprocessing,
    MUST also add to PageProxy or handle in _ensure_loaded().

    Usage:
        # Create from cached metadata
        page = PageProxy(
            source_path=Path("content/post.md"),
            metadata=cached_metadata,
            loader=load_page_from_disk,  # Callable that loads full page
        )

        # Access metadata (instant, from cache)
        print(page.title)  # "My Post"
        print(page.tags)   # ["python", "web"]

        # Access full content (triggers lazy load)
        print(page.content)  # Loads from disk and parses

        # After first access, it's fully loaded
        assert page._lazy_loaded  # True
    """

    def __init__(
        self,
        source_path: Path,
        metadata: PageCore,  # Now explicitly PageCore (or PageMetadata alias)
        loader: callable,
    ):
        """
        Initialize PageProxy with PageCore metadata and loader.

        Args:
            source_path: Path to source content file
            metadata: PageCore with cached page metadata (title, date, tags, etc.)
            loader: Callable that loads full Page(source_path) -> Page
        """
        self.source_path = source_path
        self.core = metadata  # Wrap PageCore directly (single source of truth!)
        self._loader = loader
        self._lazy_loaded = False
        self._full_page: Page | None = None
        self._related_posts_cache: list | None = None

        # Path-based section reference (stable across rebuilds)
        # Initialized from core.section if available
        self._section_path: Path | None = Path(self.core.section) if self.core.section else None

        # Output path will be set during rendering or computed on demand
        # Stored in _pending_output_path to avoid forcing lazy load
        self._pending_output_path: Path | None = None

    # ============================================================================
    # PageCore Property Delegates - Expose cached metadata without lazy load
    # ============================================================================

    @property
    def title(self) -> str:
        """Get page title from cached metadata."""
        return self.core.title

    @property
    def date(self) -> datetime | None:
        """Get page date from cached metadata (parsed from ISO string)."""
        if not self.core.date:
            return None
        # Parse ISO date string to datetime if it's a string
        if isinstance(self.core.date, str):
            try:
                return datetime.fromisoformat(self.core.date)
            except (ValueError, TypeError):
                return None
        # If it's already a datetime object, return it
        return self.core.date

    @property
    def tags(self) -> list[str]:
        """Get page tags from cached metadata."""
        return self.core.tags or []

    @property
    def slug(self) -> str | None:
        """Get URL slug from cached metadata."""
        return self.core.slug

    @property
    def weight(self) -> int | None:
        """Get sort weight from cached metadata."""
        return self.core.weight

    @property
    def lang(self) -> str | None:
        """Get language code from cached metadata."""
        return self.core.lang

    @property
    def type(self) -> str | None:
        """Get page type from cached metadata (cascaded)."""
        return self.core.type

    @property
    def section(self) -> str | None:
        """Get section path from cached metadata."""
        return self.core.section

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse ISO date string to datetime (deprecated, use date property)."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None

    def _ensure_loaded(self) -> None:
        """Load full page content if not already loaded."""
        if self._lazy_loaded:
            return

        try:
            self._full_page = self._loader(self.source_path)
            self._lazy_loaded = True

            # Transfer site and section references to loaded page
            if self._full_page:
                if hasattr(self, "_site"):
                    self._full_page._site = self._site
                # Transfer section path (not object) for stable references
                if self._section_path is not None:
                    self._full_page._section_path = self._section_path

            # Apply any pending attributes that were set before loading
            if hasattr(self, "_pending_output_path") and self._full_page:
                self._full_page.output_path = self._pending_output_path

            logger.debug("page_proxy_loaded", source_path=str(self.source_path))
        except Exception as e:
            logger.error(
                "page_proxy_load_failed",
                source_path=str(self.source_path),
                error=str(e),
            )
            raise

    # ============================================================================
    # Lazy Properties - Load full page on first access
    # ============================================================================

    @property
    def content(self) -> str:
        """Get page content (lazy-loaded from disk)."""
        self._ensure_loaded()
        return self._full_page.content if self._full_page else ""

    @property
    def metadata(self) -> dict[str, Any]:
        """
        Get metadata dict from cache (no lazy load).

        Returns cached metadata including cascaded fields like 'type'.
        This allows templates to check page.metadata.get("type") without
        triggering a full page load.
        """
        # If fully loaded, use full page metadata (more complete)
        if self._lazy_loaded and self._full_page:
            return self._full_page.metadata

        # Build metadata dict from cached PageCore fields
        cached_metadata = {}
        if self.core.type:
            cached_metadata["type"] = self.core.type
        if self.core.weight is not None:
            cached_metadata["weight"] = self.core.weight
        if self.core.tags:
            cached_metadata["tags"] = self.core.tags
        if self.core.date:
            cached_metadata["date"] = self.core.date
        if self.core.slug:
            cached_metadata["slug"] = self.core.slug
        if self.core.lang:
            cached_metadata["lang"] = self.core.lang

        return cached_metadata

    @property
    def rendered_html(self) -> str:
        """Get rendered HTML (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.rendered_html if self._full_page else ""

    @rendered_html.setter
    def rendered_html(self, value: str) -> None:
        """Set rendered HTML."""
        self._ensure_loaded()
        if self._full_page:
            self._full_page.rendered_html = value

    @property
    def links(self) -> list[str]:
        """Get extracted links (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.links if self._full_page else []

    @property
    def version(self) -> str | None:
        """Get version (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.version if self._full_page else None

    @property
    def toc(self) -> str | None:
        """Get table of contents (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.toc if self._full_page else None

    @toc.setter
    def toc(self, value: str | None) -> None:
        """Set table of contents."""
        self._ensure_loaded()
        if self._full_page:
            self._full_page.toc = value

    @property
    def toc_items(self) -> list[dict[str, Any]]:
        """Get TOC items (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.toc_items if self._full_page else []

    @property
    def output_path(self) -> Path | None:
        """Get output path (lazy-loaded)."""
        # Check if output_path was set before loading
        if hasattr(self, "_pending_output_path"):
            return self._pending_output_path

        self._ensure_loaded()
        return self._full_page.output_path if self._full_page else None

    @output_path.setter
    def output_path(self, value: Path | None) -> None:
        """Set output path."""
        # For proxies that haven't been loaded yet, we can set output_path
        # directly without loading the full page
        if not self._lazy_loaded and self._full_page is None:
            # Store in pending until loaded
            self._pending_output_path = value
        else:
            # If loaded, set on full page
            self._ensure_loaded()
            if self._full_page:
                self._full_page.output_path = value
                # Also update pending to keep them in sync
                self._pending_output_path = value

    @property
    def parsed_ast(self) -> Any:
        """Get parsed AST (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.parsed_ast if self._full_page else None

    @parsed_ast.setter
    def parsed_ast(self, value: Any) -> None:
        """Set parsed AST."""
        self._ensure_loaded()
        if self._full_page:
            self._full_page.parsed_ast = value

    @property
    def related_posts(self) -> list:
        """Get related posts (lazy-loaded)."""
        # If set on proxy without loading, return cached value
        if self._related_posts_cache is not None:
            return self._related_posts_cache
        # Otherwise load full page and return its value
        self._ensure_loaded()
        return self._full_page.related_posts if self._full_page else []

    @related_posts.setter
    def related_posts(self, value: list) -> None:
        """Set related posts.

        In incremental mode, allow setting on proxy without forcing a full load.
        """
        if not self._lazy_loaded and self._full_page is None:
            self._related_posts_cache = value
            return
        self._ensure_loaded()
        if self._full_page:
            self._full_page.related_posts = value

    @property
    def translation_key(self) -> str | None:
        """Get translation key."""
        self._ensure_loaded()
        return self._full_page.translation_key if self._full_page else None

    @property
    def url(self) -> str:
        """Get the URL path for the page (lazy-loaded, cached after first access)."""
        self._ensure_loaded()
        return self._full_page.url if self._full_page else "/"

    @property
    def permalink(self) -> str:
        """Get the permalink (URL with baseurl) for the page (lazy-loaded, cached after first access)."""
        self._ensure_loaded()
        return self._full_page.permalink if self._full_page else "/"

    # ============================================================================
    # Computed Properties - delegate to full page (cached_properties)
    # ============================================================================

    @property
    def meta_description(self) -> str:
        """Get meta description (lazy-loaded from full page)."""
        self._ensure_loaded()
        return self._full_page.meta_description if self._full_page else ""

    @property
    def reading_time(self) -> str:
        """Get reading time estimate (lazy-loaded from full page)."""
        self._ensure_loaded()
        return self._full_page.reading_time if self._full_page else ""

    @property
    def excerpt(self) -> str:
        """Get content excerpt (lazy-loaded from full page)."""
        self._ensure_loaded()
        return self._full_page.excerpt if self._full_page else ""

    @property
    def keywords(self) -> list[str]:
        """Get keywords (lazy-loaded from full page)."""
        self._ensure_loaded()
        return self._full_page.keywords if self._full_page else []

    # ============================================================================
    # Navigation Properties - Section relationships
    # ============================================================================

    @property
    def parent(self) -> Any:
        """
        Get the parent section of this page.

        Returns parent section without forcing full page load (uses _section).
        """
        return self._section

    @property
    def ancestors(self) -> list[Any]:
        """
        Get all ancestor sections of this page.

        Returns list of ancestor sections from immediate parent to root
        without forcing full page load (uses _section property).
        """
        result = []
        current = self._section

        while current:
            result.append(current)
            current = getattr(current, "parent", None)

        return result

    # ============================================================================
    # Type/Kind Properties - Metadata-based type checking
    # ============================================================================

    @property
    def is_home(self) -> bool:
        """Check if this page is the home page."""
        self._ensure_loaded()
        return self._full_page.is_home if self._full_page else False

    @property
    def is_section(self) -> bool:
        """Check if this page is a section page."""
        self._ensure_loaded()
        return self._full_page.is_section if self._full_page else False

    @property
    def is_page(self) -> bool:
        """Check if this is a regular page (not a section)."""
        self._ensure_loaded()
        return self._full_page.is_page if self._full_page else True

    @property
    def kind(self) -> str:
        """Get the kind of page: 'home', 'section', or 'page'."""
        self._ensure_loaded()
        return self._full_page.kind if self._full_page else "page"

    @property
    def description(self) -> str:
        """Get page description from metadata."""
        self._ensure_loaded()
        return self._full_page.description if self._full_page else ""

    @property
    def draft(self) -> bool:
        """Check if page is marked as draft."""
        self._ensure_loaded()
        return self._full_page.draft if self._full_page else False

    # ============================================================================
    # Navigation Properties - Most work with cached metadata only
    # ============================================================================

    @property
    def next(self) -> Page | None:
        """Get next page in site collection."""
        self._ensure_loaded()
        return self._full_page.next if self._full_page else None

    @property
    def prev(self) -> Page | None:
        """Get previous page in site collection."""
        self._ensure_loaded()
        return self._full_page.prev if self._full_page else None

    @property
    def next_in_section(self) -> Page | None:
        """Get next page in same section."""
        self._ensure_loaded()
        return self._full_page.next_in_section if self._full_page else None

    @property
    def prev_in_section(self) -> Page | None:
        """Get previous page in same section."""
        self._ensure_loaded()
        return self._full_page.prev_in_section if self._full_page else None

    # ============================================================================
    # Methods - Delegate to full page
    # ============================================================================

    def extract_links(self) -> None:
        """Extract links from content."""
        self._ensure_loaded()
        if self._full_page:
            self._full_page.extract_links()

    # ============================================================================
    # Section Property - Path-based lookup
    # ============================================================================

    @property
    def _section(self) -> Any | None:
        """
        Get the section this page belongs to (lazy lookup via path).

        If the page is loaded, delegates to the full page's _section property.
        Otherwise, performs path-based lookup via site registry without forcing load.

        Returns:
            Section object if found, None otherwise
        """
        # If page is loaded, delegate to full page
        if self._lazy_loaded and self._full_page:
            return self._full_page._section

        # Otherwise, perform lookup via path without forcing load
        if self._section_path is None:
            return None

        if not hasattr(self, "_site") or self._site is None:
            return None

        # Perform O(1) lookup via site registry
        return self._site.get_section_by_path(self._section_path)

    @_section.setter
    def _section(self, value: Any) -> None:
        """
        Set the section this page belongs to (stores path, not object).

        Args:
            value: Section object or None
        """
        if value is None:
            self._section_path = None
        else:
            # Extract and store path from Section object
            self._section_path = value.path

    def __hash__(self) -> int:
        """Hash based on source_path (same as Page)."""
        return hash(self.source_path)

    def __eq__(self, other: Any) -> bool:
        """Equality based on source_path."""
        if isinstance(other, PageProxy):
            return self.source_path == other.source_path
        if hasattr(other, "source_path"):
            return self.source_path == other.source_path
        return False

    def __repr__(self) -> str:
        """String representation."""
        loaded_str = "loaded" if self._lazy_loaded else "proxy"
        return f"PageProxy(title='{self.title}', source='{self.source_path.name}', {loaded_str})"

    def __str__(self) -> str:
        """String conversion."""
        return self.__repr__()

    # ============================================================================
    # Debugging & Inspection
    # ============================================================================

    def get_load_status(self) -> dict[str, Any]:
        """Get debugging info about proxy state."""
        return {
            "source_path": str(self.source_path),
            "is_loaded": self._lazy_loaded,
            "title": self.title,
            "has_full_page": self._full_page is not None,
        }

    @classmethod
    def from_page(cls, page: Page, metadata: Any) -> PageProxy:
        """Create proxy from full page (for testing)."""

        # This is mainly for testing - normally you'd create from metadata
        # and load from disk, but we can create from an existing page too
        def loader(source_path):
            return page

        return cls(page.source_path, metadata, loader)
