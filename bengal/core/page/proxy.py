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

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.cascade import CascadeSnapshot, CascadeView
from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.utils.pagination import Paginator

from .page_core import PageCore

# =============================================================================
# Lazy Property Delegation Helpers
# =============================================================================
# These reduce boilerplate for properties that delegate to _full_page after
# ensuring it's loaded.
# =============================================================================


def _lazy_property(attr_name: str, default: Any = None, doc: str | None = None) -> property:
    """Create a lazy property that delegates to _full_page.

    Args:
        attr_name: Attribute name on the full Page object
        default: Default value if _full_page is None
        doc: Optional docstring for the property

    """

    def getter(self: PageProxy) -> Any:
        self._ensure_loaded()
        return getattr(self._full_page, attr_name, default) if self._full_page else default

    getter.__doc__ = doc or f"Get {attr_name} (lazy-loaded from full page)."
    return property(getter)


def _lazy_property_with_setter(
    attr_name: str, default: Any = None, getter_doc: str | None = None
) -> property:
    """Create a lazy property with getter and setter that delegates to _full_page.

    Args:
        attr_name: Attribute name on the full Page object
        default: Default value if _full_page is None
        getter_doc: Optional docstring for the getter

    """

    def getter(self: PageProxy) -> Any:
        self._ensure_loaded()
        return getattr(self._full_page, attr_name, default) if self._full_page else default

    def setter(self: PageProxy, value: Any) -> None:
        self._ensure_loaded()
        if self._full_page:
            setattr(self._full_page, attr_name, value)

    getter.__doc__ = getter_doc or f"Get {attr_name} (lazy-loaded from full page)."
    setter.__doc__ = f"Set {attr_name}."
    return property(getter, setter)


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

    4. **Update** (build/rendering.py Phase 15):
       - Freshly rendered Page objects REPLACE their PageProxy counterparts
       - site.pages becomes: mix of fresh Page (rebuilt) + PageProxy (cached)

    5. **Postprocessing** (postprocess.py):
       - Iterates over site.pages (now updated with fresh Pages)
       - ⚠️ CRITICAL: PageProxy must implement ALL properties/methods used:
         * output_path (for finding where to write .txt/.json)
         * href, _path, permalink (for generating index.json)
         * title, date, tags (for content in output files)

    TRANSPARENCY CONTRACT:
    ----------------------
    PageProxy must be transparent to:
    - **Templates**: Implements .href, ._path, .title, etc.
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

    # Site reference - set externally during content discovery
    _site: Site | None

    def __init__(
        self,
        source_path: Path,
        metadata: PageCore,  # Now explicitly PageCore (or PageMetadata alias)
        loader: Callable[[Path], Page],
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
        self._related_posts_cache: list[Page] | None = None
        self._site = None  # Site reference - set externally

        # Section index page caches (set during section finalization, avoid forcing load)
        self._posts_cache: list[Page] | None = None
        self._subsections_cache: list[Any] | None = None
        self._paginator_cache: Paginator[Page] | None = None
        self._page_num_cache: int | None = None

        # Path-based section reference (stable across rebuilds)
        # Initialized from core.section if available
        self._section_path: Path | None = Path(self.core.section) if self.core.section else None

        # Output path will be set during rendering or computed on demand
        # Stored in _pending_output_path to avoid forcing lazy load
        self._pending_output_path: Path | None = None

        # Cache for CascadeView (invalidated when site/section changes)
        self._metadata_view_cache: CascadeView | None = None
        self._metadata_view_cache_key: tuple[int, str] | None = None

        # Raw frontmatter from PageCore (for fallback and CascadeView construction)
        self._raw_metadata: dict[str, Any] = self._build_raw_metadata_from_core()

    # ============================================================================
    # PageCore Property Delegates - Expose cached metadata without lazy load
    # ============================================================================

    @property
    def title(self) -> str:
        """Get page title from cached metadata."""
        return self.core.title

    @property
    def nav_title(self) -> str:
        """
        Get navigation title from cached metadata.

        Falls back to title if nav_title not set.
        """
        return self.core.nav_title or self.core.title

    @property
    def weight(self) -> float:
        """
        Get page weight for sorting (always returns sortable value).

        Returns weight from cached core if set, otherwise infinity (sorts last).
        This property ensures pages are always sortable without None errors.
        """
        if self.core.weight is not None:
            try:
                return float(self.core.weight)
            except (ValueError, TypeError):
                pass
        return float("inf")

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
    def lang(self) -> str | None:
        """Get language code from cached metadata."""
        return self.core.lang

    @property
    def type(self) -> str | None:
        """
        Get page type from metadata (frontmatter or cascade, already merged).

        With eager cascade merge, cascade values are merged into metadata
        on first access. This eliminates the duality between
        page.metadata.get("type") and page.type.
        """
        return self.metadata.get("type")

    @property
    def variant(self) -> str | None:
        """
        Get visual variant from metadata (frontmatter or cascade, already merged).

        With eager cascade merge, cascade values (including 'variant' and 'layout')
        are merged into metadata on first access.
        """
        props = self.metadata
        return props.get("variant") or props.get("layout") or props.get("hero_style")

    @property
    def props(self) -> dict[str, Any]:
        """
        Get custom props from cached metadata.

        This provides access to the 'props' dictionary (formerly metadata)
        without loading the full page.
        """
        return self.core.props

    @property
    def section(self) -> str | None:
        """Get section path from cached metadata."""
        return self.core.section

    @property
    def relative_path(self) -> str:
        """Get relative path string (alias for source_path as string)."""
        return str(self.source_path)

    @property
    def version(self) -> str | None:
        """Get version ID from cached metadata."""
        return self.core.version

    @property
    def aliases(self) -> list[str]:
        """Get redirect aliases from cached metadata."""
        return self.core.aliases or []

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

            emit_diagnostic(self, "debug", "page_proxy_loaded", source_path=str(self.source_path))
        except Exception as e:
            emit_diagnostic(
                self,
                "error",
                "page_proxy_load_failed",
                source_path=str(self.source_path),
                error=str(e),
            )
            raise

    # ============================================================================
    # Lazy Properties - Load full page on first access
    # ============================================================================
    # Properties using _lazy_property helper for reduced boilerplate

    content = _lazy_property("content", default="", doc="Rendered HTML content (lazy-loaded).")
    _source = _lazy_property("_source", default="", doc="Raw markdown source (lazy-loaded).")

    @property
    def metadata(self) -> Mapping[str, Any]:
        """
        Return combined frontmatter + cascade metadata as CascadeView.

        This property provides dict-like access to page metadata. Values come from:
        1. Page frontmatter (from PageCore, always takes precedence)
        2. Cascade from parent sections (inherited values)

        The CascadeView is immutable and resolves values on access, ensuring
        cascade values are always current even during incremental builds.

        Returns:
            CascadeView combining frontmatter and cascade, or raw metadata dict
            if cascade is not yet available (during early construction).
        """
        # If fully loaded, use full page metadata (delegates to its CascadeView)
        if self._lazy_loaded and self._full_page:
            return self._full_page.metadata

        # During early construction or without site, return raw metadata
        if self._site is None:
            return self._raw_metadata

        # Get cascade snapshot from site
        cascade = getattr(self._site, "cascade", None)
        if cascade is None or not isinstance(cascade, CascadeSnapshot):
            return self._raw_metadata

        # Get section path for cascade lookup
        section_path = ""
        if self._section_path:
            try:
                content_dir = self._site.root_path / "content"
                section_path = str(self._section_path.relative_to(content_dir))
            except (ValueError, AttributeError):
                section_path = str(self._section_path)

        # Check cache validity (cascade id + section path)
        cache_key = (id(cascade), section_path)
        if self._metadata_view_cache is not None and self._metadata_view_cache_key == cache_key:
            return self._metadata_view_cache

        # Create and cache new CascadeView
        view = CascadeView.for_page(
            frontmatter=self._raw_metadata,
            section_path=section_path,
            snapshot=cascade,
        )
        self._metadata_view_cache = view
        self._metadata_view_cache_key = cache_key
        return view

    def _build_raw_metadata_from_core(self) -> dict[str, Any]:
        """
        Build raw frontmatter dict from cached PageCore fields.

        This creates the frontmatter dict used by CascadeView. These are
        the page's own values that take precedence over cascade.

        Also includes the 'cascade' block for _index.md files - this is critical
        for incremental builds where the cascade snapshot needs to read cascade
        data from cached PageProxy index pages.
        """
        # Always include weight with sortable default (None → infinity for sort-last)
        raw_metadata: dict[str, Any] = {
            "weight": self.core.weight if self.core.weight is not None else float("inf"),
        }

        # Add non-cascade fields from core
        if self.core.tags:
            raw_metadata["tags"] = self.core.tags
        if self.core.date:
            raw_metadata["date"] = self.core.date
        if self.core.slug:
            raw_metadata["slug"] = self.core.slug
        if self.core.lang:
            raw_metadata["lang"] = self.core.lang

        # Add frontmatter values for cascade-eligible keys
        # These take precedence over cascade (frontmatter wins)
        if self.core.type:
            raw_metadata["type"] = self.core.type
        if self.core.variant:
            raw_metadata["variant"] = self.core.variant

        # Add custom props
        if self.core.props:
            raw_metadata.update(self.core.props)

        # Include cascade block for _index.md files
        # This is essential for incremental builds: when the cascade snapshot is
        # being built, it reads section.index_page.metadata.get("cascade", {}).
        # For PageProxy index pages, this falls back to _raw_metadata, so we must
        # include the cascade data here.
        if self.core.cascade:
            raw_metadata["cascade"] = self.core.cascade

        return raw_metadata

    rendered_html = _lazy_property_with_setter(
        "rendered_html", default="", getter_doc="Rendered HTML (lazy-loaded)."
    )
    links = _lazy_property_with_setter(
        "links", default=[], getter_doc="Extracted links (lazy-loaded)."
    )
    toc = _lazy_property_with_setter(
        "toc", default=None, getter_doc="Table of contents (lazy-loaded)."
    )
    toc_items = _lazy_property("toc_items", default=[], doc="TOC items (lazy-loaded).")

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

    html_content = _lazy_property_with_setter(
        "html_content", default=None, getter_doc="HTML content (lazy-loaded)."
    )
    plain_text = _lazy_property(
        "plain_text",
        default="",
        doc="Plain text content (lazy-loaded). Used for search indexing and LLM context.",
    )

    @property
    def is_virtual(self) -> bool:
        """
        Check if this is a virtual page (not backed by a disk file).

        PageProxy objects are always backed by cached disk files, so they
        are never virtual. Virtual pages (like autodoc-generated pages)
        are not cached as proxies.

        Returns:
            Always False for PageProxy
        """
        return False

    def normalize_core_paths(self) -> None:
        """
        Normalize PageCore paths to be relative (for cache consistency).

        For PageProxy, this is a no-op since the paths are already normalized
        (they were loaded from the cache which stores relative paths).
        """
        # PageProxy paths are already relative from cache - no normalization needed

    @property
    def related_posts(self) -> list[Page]:
        """Get related posts (lazy-loaded)."""
        # If set on proxy without loading, return cached value
        if self._related_posts_cache is not None:
            return self._related_posts_cache
        # Otherwise load full page and return its value
        self._ensure_loaded()
        return self._full_page.related_posts if self._full_page else []

    @related_posts.setter
    def related_posts(self, value: list[Page]) -> None:
        """Set related posts.

        In incremental mode, allow setting on proxy without forcing a full load.
        """
        if not self._lazy_loaded and self._full_page is None:
            self._related_posts_cache = value
            return
        self._ensure_loaded()
        if self._full_page:
            self._full_page.related_posts = value

    # ============================================================================
    # Section Index Page Properties - Used by section finalization
    # ============================================================================
    # These properties store section context (_posts, _subsections, _paginator)
    # for index pages. They allow setting on proxy without forcing a full load,
    # which is critical for incremental builds where index pages may be PageProxy.

    @property
    def _posts(self) -> list[Page] | None:
        """Get posts list for section index pages."""
        if self._posts_cache is not None:
            return self._posts_cache
        if self._lazy_loaded and self._full_page:
            return self._full_page._posts
        return None

    @_posts.setter
    def _posts(self, value: list[Page] | None) -> None:
        """Set posts list for section index pages."""
        if not self._lazy_loaded and self._full_page is None:
            self._posts_cache = value
            return
        self._ensure_loaded()
        if self._full_page:
            self._full_page._posts = value

    @property
    def _subsections(self) -> list[Any] | None:
        """Get subsections list for section index pages."""
        if self._subsections_cache is not None:
            return self._subsections_cache
        if self._lazy_loaded and self._full_page:
            return self._full_page._subsections
        return None

    @_subsections.setter
    def _subsections(self, value: list[Any] | None) -> None:
        """Set subsections list for section index pages."""
        if not self._lazy_loaded and self._full_page is None:
            self._subsections_cache = value
            return
        self._ensure_loaded()
        if self._full_page:
            self._full_page._subsections = value

    @property
    def _paginator(self) -> Paginator[Page] | None:
        """Get paginator for section index pages."""
        if self._paginator_cache is not None:
            return self._paginator_cache
        if self._lazy_loaded and self._full_page:
            return self._full_page._paginator
        return None

    @_paginator.setter
    def _paginator(self, value: Paginator[Page] | None) -> None:
        """Set paginator for section index pages."""
        if not self._lazy_loaded and self._full_page is None:
            self._paginator_cache = value
            return
        self._ensure_loaded()
        if self._full_page:
            self._full_page._paginator = value

    @property
    def _page_num(self) -> int | None:
        """Get page number for paginated section index pages."""
        if self._page_num_cache is not None:
            return self._page_num_cache
        if self._lazy_loaded and self._full_page:
            return self._full_page._page_num
        return None

    @_page_num.setter
    def _page_num(self, value: int | None) -> None:
        """Set page number for paginated section index pages."""
        if not self._lazy_loaded and self._full_page is None:
            self._page_num_cache = value
            return
        self._ensure_loaded()
        if self._full_page:
            self._full_page._page_num = value

    translation_key = _lazy_property("translation_key", default=None, doc="Translation key.")
    href = _lazy_property("href", default="/", doc="URL path with baseurl (lazy-loaded).")
    _path = _lazy_property("_path", default="/", doc="Site-relative path without baseurl.")
    absolute_href = _lazy_property(
        "absolute_href", default="/", doc="Fully-qualified URL for meta tags and sitemaps."
    )

    # ============================================================================
    # Computed Properties - delegate to full page (cached_properties)
    # ============================================================================

    meta_description = _lazy_property(
        "meta_description", default="", doc="Meta description (lazy-loaded)."
    )
    excerpt = _lazy_property("excerpt", default="", doc="Content excerpt (lazy-loaded).")
    keywords = _lazy_property("keywords", default=[], doc="Keywords (lazy-loaded).")

    @property
    def reading_time(self) -> str:
        """Get reading time estimate (lazy-loaded from full page)."""
        self._ensure_loaded()
        if self._full_page:
            rt = self._full_page.reading_time
            return str(rt) if isinstance(rt, int) else rt
        return ""

    # ============================================================================
    # Navigation Properties - Section relationships
    # ============================================================================

    @property
    def parent(self) -> Section | None:
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

    is_home = _lazy_property("is_home", default=False, doc="Check if this page is the home page.")
    is_section = _lazy_property(
        "is_section", default=False, doc="Check if this page is a section page."
    )
    is_page = _lazy_property(
        "is_page", default=True, doc="Check if this is a regular page (not a section)."
    )
    kind = _lazy_property("kind", default="page", doc="Kind of page: 'home', 'section', or 'page'.")
    draft = _lazy_property("draft", default=False, doc="Check if page is marked as draft.")

    @property
    def description(self) -> str:
        """
        Get page description.

        Favors core.description (fast, cached) but falls back to full page
        load if not available, for backward compatibility.
        """
        if self.core.description:
            return self.core.description
        self._ensure_loaded()
        return self._full_page.description if self._full_page else ""

    # ============================================================================
    # Visibility Properties - Page visibility controls
    # ============================================================================

    hidden = _lazy_property("hidden", default=False, doc="Check if page is hidden (unlisted).")
    in_listings = _lazy_property(
        "in_listings", default=True, doc="Check if page should appear in listings/queries."
    )
    in_sitemap = _lazy_property(
        "in_sitemap", default=True, doc="Check if page should appear in sitemap."
    )
    in_search = _lazy_property(
        "in_search", default=True, doc="Check if page should appear in search index."
    )
    in_rss = _lazy_property("in_rss", default=True, doc="Check if page should appear in RSS feeds.")
    robots_meta = _lazy_property(
        "robots_meta", default="index, follow", doc="Robots meta content for this page."
    )
    should_render = _lazy_property(
        "should_render", default=True, doc="Check if page should be rendered."
    )

    @property
    def visibility(self) -> dict[str, Any]:
        """Get visibility settings with defaults."""
        self._ensure_loaded()
        if self._full_page:
            return self._full_page.visibility
        # Fallback to permissive defaults
        return {
            "menu": True,
            "listings": True,
            "sitemap": True,
            "robots": "index, follow",
            "render": "always",
            "search": True,
            "rss": True,
        }

    def should_render_in_environment(self, is_production: bool = False) -> bool:
        """Check if page should be rendered in the given environment."""
        self._ensure_loaded()
        if self._full_page:
            return self._full_page.should_render_in_environment(is_production)
        return True

    # ============================================================================
    # Navigation Properties - Most work with cached metadata only
    # ============================================================================

    next = _lazy_property("next", default=None, doc="Next page in site collection.")
    prev = _lazy_property("prev", default=None, doc="Previous page in site collection.")
    next_in_section = _lazy_property(
        "next_in_section", default=None, doc="Next page in same section."
    )
    prev_in_section = _lazy_property(
        "prev_in_section", default=None, doc="Previous page in same section."
    )

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
    def _section(self) -> Section | None:
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
    def _section(self, value: Section | None) -> None:
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

    @property
    def section_path(self) -> str | None:
        """
        Get the section path as a string.

        Returns the path to the section this page belongs to, or None if
        the page doesn't belong to a section.

        Returns:
            Section path as string (e.g., "docs/guides") or None
        """
        return str(self._section_path) if self._section_path else None

    def __hash__(self) -> int:
        """Hash based on source_path (same as Page)."""
        return hash(self.source_path)

    def __eq__(self, other: object) -> bool:
        """Equality based on source_path."""
        if isinstance(other, PageProxy):
            return self.source_path == other.source_path
        if hasattr(other, "source_path"):
            return bool(self.source_path == other.source_path)
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
    def from_page(cls, page: Page, metadata: PageCore) -> PageProxy:
        """Create proxy from full page (for testing)."""

        # This is mainly for testing - normally you'd create from metadata
        # and load from disk, but we can create from an existing page too
        def loader(source_path: Path) -> Page:
            return page

        return cls(page.source_path, metadata, loader)
