"""
Page representation for content pages in Bengal SSG.

Provides the main Page class combining metadata, navigation, and passive
content access. Pages represent markdown
content files and are the primary content unit in Bengal.

Public API:
Page: Content page with metadata, content, and rendering capabilities

Package Structure:
page_core.py: PageCore dataclass (cacheable metadata)
metadata_helpers.py: Pure helper functions behind metadata compatibility properties
navigation.py: Free functions for navigation and hierarchy
computed.py: Free functions for computed properties (word count, reading time, etc.)
rendering/page_content.py: Rendering-side helpers behind content compatibility properties
bundle.py: Free functions for bundle detection and resource access
utils.py: Field separation utilities
rendering/page_operations.py: Rendering-side helpers behind Page compatibility shims

Key Concepts:
Compatibility Shims: Page keeps a few thin methods/properties for existing
    template or third-party access while rendering-side helpers own the actual
    work.

Hashability: Pages are hashable by source_path, enabling set operations
    and use as dict keys. Two pages with same path are equal.

Virtual Pages: Pages without disk files (e.g., autodoc). Created via
    Page.create_virtual() for dynamically-generated content.

PageCore: Cacheable subset of page metadata. Shared between Page
    and cache layer. Enables incremental builds.

Build Lifecycle:
1. Discovery: source_path, content, metadata available
2. Parsing: toc, html_content populated
3. Rendering: rendered_html, output_path populated

Related Packages:
bengal.core.page.page_core: Cacheable page metadata
bengal.rendering.renderer: Page rendering pipeline
bengal.orchestration.content: Content discovery and page creation

"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bengal.core.cascade import CascadeSnapshot, CascadeView
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.page.metadata_helpers import (
    coerce_weight,
    fallback_url,
    get_internal_metadata,
    get_user_metadata,
    infer_nav_title,
    infer_slug,
    infer_title,
    normalize_edition,
    normalize_keywords,
    normalize_visibility,
    should_render_visibility,
)
from bengal.core.utils.url import apply_baseurl, get_baseurl, get_site_origin
from bengal.protocols import SiteLike

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from bengal.core.author import Author
    from bengal.core.records import SourcePage
    from bengal.core.series import Series
    from bengal.core.site.context import SiteContext
    from bengal.parsing.ast.types import ASTNode
    from bengal.protocols.core import PageLike, SectionLike
    from bengal.utils.pagination import Paginator

from .bundle import BundleType, PageResource, PageResources
from .frontmatter import Frontmatter
from .page_core import PageCore
from .utils import normalize_tags


@dataclass
class Page:
    """
    Represents a single content page.

    HASHABILITY:
    ============
    Pages are hashable based on their source_path, allowing them to be stored
    in sets and used as dictionary keys. This enables:
    - Fast membership tests (O(1) instead of O(n))
    - Automatic deduplication with sets
    - Set operations for page analysis
    - Direct use as dictionary keys

    Two pages with the same source_path are considered equal, even if their
    content differs. The hash is stable throughout the page lifecycle because
    source_path is immutable. Mutable fields (content, rendered_html, etc.)
    do not affect the hash or equality.

    VIRTUAL PAGES:
    ==============
    Virtual pages represent dynamically-generated content (e.g., API docs)
    that doesn't have a corresponding file on disk. Virtual pages:
    - Have virtual=True and a synthetic source_path
    - Are created via Page.create_virtual() factory
    - Don't read from disk (content provided directly)
    - Integrate with site's page collection and navigation

    BUILD LIFECYCLE:
    ================
    Pages progress through distinct build phases. Properties have different
    availability depending on the current phase:

    1. Discovery (content_discovery.py)
       ✅ Available: source_path, content, metadata, title, slug, date
       ❌ Not available: toc, html_content, toc_items, rendered_html

    2. Parsing (pipeline.py)
       ✅ Available: All Stage 1 + toc, html_content
       ✅ toc_items can be accessed (will extract from toc)

    3. Rendering (pipeline.py)
       ✅ Available: All previous + rendered_html, output_path
       ✅ All properties fully populated

    Note: Some properties like toc_items can be accessed early (returning [])
    but won't cache empty results, allowing proper extraction after parsing.

    Attributes:
        source_path: Path to the source content file (synthetic for virtual pages)
        content: Raw content (Markdown, etc.)
        metadata: Frontmatter metadata (title, date, tags, etc.)
        html_content: Rendered HTML content (parsed from Markdown by Patitas)
        rendered_html: Rendered HTML output
        output_path: Path where the rendered page will be written
        links: List of links found in the page
        tags: Tags associated with the page
        version: Version information for versioned content
        toc: Table of contents HTML (auto-generated from headings)
        toc_items: Structured TOC data for custom rendering
        related_posts: Related pages (pre-computed during build based on tag overlap)
        virtual: True if this is a virtual page (not backed by a disk file)

    """

    # Class-level warning counter (shared across all Page instances)
    # This prevents unbounded memory growth in long-running dev servers where
    # pages are recreated frequently. Warnings are suppressed globally after
    # the first 3 occurrences per unique warning key.
    # The dict is bounded to max 100 entries (oldest removed when limit reached).
    _global_missing_section_warnings: ClassVar[dict[str, int]] = {}
    _warnings_lock: ClassVar[threading.Lock] = threading.Lock()
    _MAX_WARNING_KEYS: ClassVar[int] = 100

    # Required field (no default)
    source_path: Path

    # PageCore: Cacheable metadata (single source of truth for Page/PageMetadata)
    # Auto-created in __post_init__ from Page fields
    core: PageCore | None = field(default=None, init=False)

    # Optional fields (with defaults)
    # Raw markdown source content (use _source property for access)
    _raw_content: str = ""
    # Raw frontmatter from YAML parsing (user's metadata)
    # Access via .metadata property which combines with cascade
    _raw_metadata: dict[str, Any] = field(default_factory=dict)
    # HTML content rendered from Markdown by Patitas parser.
    html_content: str | None = None
    rendered_html: str = ""
    render_time_ms: float = 0.0  # Per-page render time, set during rendering
    output_path: Path | None = None
    links: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: str | None = None
    toc: str | None = None
    related_posts: list[Page] = field(default_factory=list)  # Pre-computed during build

    # Internationalization (i18n)
    # Language code for this page (e.g., 'en', 'fr'). When i18n is disabled, remains None.
    lang: str | None = None
    # Stable key used to link translations across locales (e.g., 'docs/getting-started').
    translation_key: str | None = None

    # Redirect aliases - alternative URLs that redirect to this page
    # Aliases are stored in PageCore for caching, but we also keep them here for easy access
    # and for frontmatter parsing before core is initialized
    aliases: list[str] = field(default_factory=list)

    # References for navigation (set during site building)
    _site: SiteContext | None = field(default=None, repr=False)
    # Path-based section reference (stable across rebuilds)
    _section_path: Path | None = field(default=None, repr=False)
    # URL-based section reference for virtual sections (path=None)
    # See: plan/active/rfc-page-section-reference-contract.md
    _section_url: str | None = field(default=None, repr=False)

    # Cached resolved Section object for fast repeated access during template rendering.
    # NOTE: Cache is per-site-object + epoch + reference tuple and must be invalidated when those change.
    _section_obj_cache: SectionLike | object | None = field(default=None, repr=False, init=False)
    _section_obj_cache_key: tuple[int, int, Path | None, str | None] | None = field(
        default=None, repr=False, init=False
    )

    # Sentinel representing a cached "not found" section.
    _SECTION_NOT_FOUND: ClassVar[object] = object()

    # Private cache for lazy toc_items property
    _toc_items_cache: list[dict[str, Any]] | None = field(default=None, repr=False, init=False)

    # AST-extracted excerpt (set by pipeline when Patitas parses; bypasses compute_excerpt)
    _excerpt: str | None = field(default=None, repr=False, init=False)
    # AST-extracted meta description (set by pipeline; bypasses compute_meta_description)
    _meta_description: str | None = field(default=None, repr=False, init=False)

    # Private cache for lazy frontmatter property
    _frontmatter: Frontmatter | None = field(default=None, init=False, repr=False)
    # Lock for thread-safe lazy initialization of _frontmatter
    _init_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    # Cache for CascadeView (invalidated when site/section changes)
    _metadata_view_cache: CascadeView | None = field(default=None, init=False, repr=False)
    _metadata_view_cache_key: tuple[int, str] | None = field(default=None, init=False, repr=False)

    # Private caches for AST-based content (Phase 3 of RFC)
    # See: plan/active/rfc-content-ast-architecture.md
    # Patitas: dict (Document with "children"); legacy: list[ASTNode]
    _ast_cache: list[ASTNode] | dict[str, Any] | None = field(default=None, repr=False, init=False)
    _html_cache: str | None = field(default=None, repr=False, init=False)
    _plain_text_cache: str | None = field(default=None, repr=False, init=False)

    # Virtual page support (for API docs, generated content)
    virtual: bool = field(default=False, repr=False)

    # Internal metadata for section index pages (replaces metadata["_key"] pattern)
    # These are build-time bookkeeping, not user-facing frontmatter
    _posts: list[Page] | None = field(default=None, repr=False, init=False)
    _subsections: list[Any] | None = field(default=None, repr=False, init=False)  # list[Section]
    _paginator: Paginator[Page] | None = field(default=None, repr=False, init=False)
    _page_num: int | None = field(default=None, repr=False, init=False)
    _autodoc_fallback_template: bool = field(default=False, repr=False, init=False)
    _autodoc_fallback_reason: str | None = field(default=None, repr=False, init=False)

    # Pre-rendered HTML for virtual pages (bypasses markdown parsing)
    prerendered_html: str | None = field(default=None, repr=False)

    # Template override for virtual pages (uses custom template)
    template_name: str | None = field(default=None, repr=False)

    # Complexity cache for parallel render ordering (set by orchestration)
    _complexity_score: int | None = field(default=None, repr=False, init=False)
    # Cascade invalidation flag (set by provenance filter when provenance changes)
    _cascade_invalidated: bool = field(default=False, repr=False, init=False)

    # Sprint 5: True when page was reconstructed from cache without disk I/O.
    # Used for metrics/logging and to skip wasteful re-initialization in __post_init__.
    _from_cache: bool = field(default=False, repr=False)

    # Sprint 4 dual-write bridge: immutable SourcePage record from discovery.
    # Set by ContentDiscovery._create_page(); None for cached/proxy pages.
    # Removed in Sprint 6 when Page is deleted.
    _source_page: SourcePage | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize computed fields and PageCore."""
        if self._raw_metadata:
            self.tags = normalize_tags(self._raw_metadata.get("tags"))
            # Priority: explicit 'version' frontmatter -> auto-detected '_version' metadata
            self.version = self._raw_metadata.get("version") or self._raw_metadata.get("_version")
            self.aliases = self._raw_metadata.get("aliases", [])

        # Skip PageCore creation for cache-reconstructed pages — the caller
        # assigns the cached core directly, avoiding a wasteful throwaway object.
        if not self._from_cache:
            self._init_core_from_fields()

    @property
    def metadata(self) -> Mapping[str, Any]:
        """
        Return combined frontmatter + cascade metadata as CascadeView.

        When to use:
            Prefer this over ``self._raw_metadata`` whenever you want the
            *effective* value seen by templates — raw metadata misses
            cascaded values from parent sections. Prefer
            ``self.frontmatter`` instead when you want **typed** access to
            known fields (``page.frontmatter.title: str``) rather than
            dict-style lookup. The View is immutable — write via
            ``self._raw_metadata`` directly only during early construction.

        Values come from:
        1. Page frontmatter (always takes precedence)
        2. Cascade from parent sections (inherited values)

        The CascadeView is immutable and resolves values on access, ensuring
        cascade values are always current even during incremental builds.

        Returns:
            CascadeView combining frontmatter and cascade, or raw metadata dict
            if cascade is not yet available (during early construction).
        """
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
            except ValueError, AttributeError:
                section_path = str(self._section_path)

        # Check cache validity (site id + section path)
        cache_key = (id(cascade), section_path)
        if self._metadata_view_cache is not None and self._metadata_view_cache_key == cache_key:
            return self._metadata_view_cache

        with self._init_lock:
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

    @property
    def title(self) -> str:
        """Page title from metadata or source path."""
        return infer_title(self.metadata, self.source_path)

    @property
    def nav_title(self) -> str:
        """Navigation title, falling back to the regular page title."""
        return infer_nav_title(
            core_nav_title=self.core.nav_title if self.core is not None else None,
            metadata=self.metadata,
            fallback_title=self.title,
        )

    @property
    def weight(self) -> float:
        """Sortable page weight, defaulting to infinity."""
        return coerce_weight(self.core.weight if self.core is not None else None, self.metadata)

    @property
    def date(self) -> datetime | None:
        """Parsed page date from metadata."""
        from bengal.utils.primitives.dates import parse_date

        return parse_date(self.metadata.get("date"))

    @property
    def slug(self) -> str:
        """URL slug for the page."""
        return infer_slug(self.metadata, self.source_path)

    @property
    def href(self) -> str:
        """
        URL for template href attributes. Includes baseurl.

        Use this in templates for all links:
            <a href="{{ page.href }}">
            <link href="{{ page.href }}">

        Returns:
            URL path with baseurl prepended (if configured)

        Note: Uses manual caching that only stores when _path is properly
        computed (not from fallback).
        """
        manual_value = self.__dict__.get("href")
        if manual_value is not None:
            return manual_value

        cached = self.__dict__.get("_href_cache")
        if cached is not None:
            return cached

        with self._init_lock:
            cached = self.__dict__.get("_href_cache")
            if cached is not None:
                return cached

            rel = self._path or "/"

            try:
                site = getattr(self, "_site", None)
                baseurl = get_baseurl(site) if site else ""
            except Exception as e:
                emit_diagnostic(self, "debug", "page_baseurl_lookup_failed", error=str(e))
                baseurl = ""

            result = apply_baseurl(rel, baseurl)

            if "_path_cache" in self.__dict__:
                self.__dict__["_href_cache"] = result

        return result

    @property
    def _path(self) -> str:
        """
        Internal site-relative path. NO baseurl.

        Use for internal operations only:
        - Cache keys
        - Active trail detection
        - URL comparisons
        - Link validation

        NEVER use in templates - use .href instead.
        """
        manual_value = self.__dict__.get("_path")
        if manual_value is not None:
            return manual_value

        cached = self.__dict__.get("_path_cache")
        if cached is not None:
            return cached

        if not self.output_path:
            return self._fallback_url()

        if not self._site:
            return self._fallback_url()

        with self._init_lock:
            cached = self.__dict__.get("_path_cache")
            if cached is not None:
                return cached

            try:
                rel_path = self.output_path.relative_to(self._site.output_dir)
            except ValueError:
                emit_diagnostic(
                    self,
                    "debug",
                    "page_output_path_fallback",
                    output_path=str(self.output_path),
                    output_dir=str(self._site.output_dir),
                    page_source=str(getattr(self, "source_path", "unknown")),
                )
                return self._fallback_url()

            url_parts = list(rel_path.parts)
            if url_parts and url_parts[-1] == "index.html":
                url_parts = url_parts[:-1]
            elif url_parts and url_parts[-1].endswith(".html"):
                url_parts[-1] = url_parts[-1][:-5]

            if not url_parts:
                url = "/"
            else:
                url = "/" + "/".join(url_parts)
                if not url.endswith("/"):
                    url += "/"

            self.__dict__["_path_cache"] = url
        return url

    @property
    def absolute_href(self) -> str:
        """Fully-qualified URL for meta tags and sitemaps when configured."""
        origin = get_site_origin(self._site) if self._site else ""
        if not origin:
            return self.href
        return f"{origin}{self._path}"

    def _fallback_url(self) -> str:
        """Generate fallback URL when output_path or site is not available."""
        return fallback_url(self.slug)

    @property
    def toc_items(self) -> list[dict[str, Any]]:
        """Structured TOC data for template compatibility."""
        from bengal.rendering.page_content import get_toc_items

        return get_toc_items(self)

    @property
    def is_home(self) -> bool:
        """True if this page is the home page."""
        return self._path == "/" or self.slug in ("index", "_index", "home")

    @property
    def is_section(self) -> bool:
        """True if this page is a Section instance."""
        from bengal.core.section import Section

        return isinstance(self, Section)

    @property
    def is_page(self) -> bool:
        """True if this is a regular page, not a section."""
        return not self.is_section

    @property
    def kind(self) -> str:
        """Page kind: ``home``, ``section``, or ``page``."""
        if self.is_home:
            return "home"
        if self.is_section:
            return "section"
        return "page"

    @property
    def type(self) -> str | None:
        """Page type from metadata."""
        return self.metadata.get("type")

    @property
    def description(self) -> str:
        """Page description from core metadata or frontmatter."""
        if self.core is not None and self.core.description:
            return self.core.description
        return str(self.metadata.get("description", ""))

    @property
    def variant(self) -> str | None:
        """Visual variant from metadata, with legacy layout fallbacks."""
        return (
            self.metadata.get("variant")
            or self.metadata.get("layout")
            or self.metadata.get("hero_style")
        )

    @property
    def props(self) -> dict[str, Any]:
        """Page props alias for metadata."""
        return cast("dict[str, Any]", self.metadata)

    @property
    def params(self) -> dict[str, Any]:
        """Page params alias for metadata."""
        return cast("dict[str, Any]", self.metadata)

    @property
    def draft(self) -> bool:
        """True if page is marked as draft."""
        return bool(self.metadata.get("draft", False))

    @property
    def keywords(self) -> list[str]:
        """Sanitized page keywords from metadata."""
        return normalize_keywords(self.metadata.get("keywords", []))

    @property
    def hidden(self) -> bool:
        """True if page is hidden from listings/navigation."""
        return bool(self.metadata.get("hidden", False))

    def _get_content_signal_defaults(self) -> dict[str, Any]:
        """Get site-level content signal defaults from config."""
        site = getattr(self, "_site", None)
        if site is None:
            return {}
        config = getattr(site, "config", None)
        if config is None:
            return {}
        try:
            cs = config.get("content_signals", {})
            return cs if isinstance(cs, dict) else {}
        except Exception:
            return {}

    @property
    def visibility(self) -> dict[str, Any]:
        """Visibility settings merged with Bengal defaults."""
        return normalize_visibility(self.metadata, self._get_content_signal_defaults())

    @property
    def in_listings(self) -> bool:
        """True if page should appear in listings/queries."""
        return self.visibility["listings"] and not self.draft

    @property
    def in_sitemap(self) -> bool:
        """True if page should appear in sitemap.xml."""
        return self.visibility["sitemap"] and not self.draft

    @property
    def in_search(self) -> bool:
        """True if page should appear in the search index."""
        return self.visibility["search"] and not self.draft

    @property
    def in_rss(self) -> bool:
        """True if page should appear in RSS feeds."""
        return self.visibility["rss"] and not self.draft

    @property
    def in_ai_train(self) -> bool:
        """True if page permits AI training use."""
        return self.visibility["ai_train"] and not self.draft

    @property
    def in_ai_input(self) -> bool:
        """True if page permits AI input/RAG use."""
        return self.visibility["ai_input"] and not self.draft

    @property
    def robots_meta(self) -> str:
        """Robots meta directive for this page."""
        return str(self.visibility["robots"])

    @property
    def should_render(self) -> bool:
        """True if visibility.render is not ``never``."""
        return bool(self.visibility["render"] != "never")

    def should_render_in_environment(self, is_production: bool = False) -> bool:
        """True if page should render in the given environment."""
        return should_render_visibility(self.visibility, is_production)

    @property
    def edition(self) -> list[str]:
        """Edition/variant list from frontmatter for multi-variant builds."""
        return normalize_edition(self.metadata.get("edition"))

    def in_variant(self, variant: str | None) -> bool:
        """True if page should be included for the given build variant."""
        if variant is None or not str(variant).strip():
            return True
        editions = self.edition
        if not editions:
            return True
        return variant in editions

    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        """Get user frontmatter, excluding internal underscore keys."""
        return get_user_metadata(self.metadata, key, default)

    def get_internal_metadata(self, key: str, default: Any = None) -> Any:
        """Get internal underscore-prefixed metadata."""
        return get_internal_metadata(self.metadata, key, default)

    @property
    def is_generated(self) -> bool:
        """True if page was dynamically generated."""
        return bool(self.metadata.get("_generated"))

    @property
    def assigned_template(self) -> str | None:
        """Template explicitly assigned to this page."""
        return self.metadata.get("template")

    @property
    def content_type_name(self) -> str | None:
        """Content type assigned to this page."""
        return self.metadata.get("content_type")

    def _init_core_from_fields(self) -> None:
        """
        Initialize PageCore from Page fields.

        Note: Initially creates PageCore with absolute paths, but normalize_core_paths()
        should be called before caching to convert to relative paths.
        """
        # Separate standard fields from custom props (Component Model)
        from bengal.core.page.utils import separate_standard_and_custom_fields
        from bengal.utils.primitives.dates import parse_date

        standard_fields, custom_props = separate_standard_and_custom_fields(self._raw_metadata)

        # Component Model: variant (normalized from layout/hero_style)
        variant = standard_fields.get("variant")
        # Normalize legacy fields to variant
        if not variant:
            variant = standard_fields.get("layout") or custom_props.get("hero_style")

        self.core = PageCore(
            source_path=str(self.source_path),  # May be absolute initially
            title=standard_fields.get("title", ""),
            date=parse_date(standard_fields.get("date")),
            tags=self.tags or [],
            slug=self.slug,  # Use computed slug (includes filename fallback)
            weight=standard_fields.get("weight"),
            lang=self.lang,
            nav_title=standard_fields.get("nav_title"),  # Short title for navigation
            # Component Model Fields
            type=standard_fields.get("type"),
            variant=variant,
            description=standard_fields.get("description"),
            props=custom_props,  # Only custom fields go into props
            # Links
            section=str(self._section_path) if self._section_path else None,
            file_hash=None,  # Will be populated during caching
            aliases=standard_fields.get("aliases") or self.aliases or [],
            # Cascade data (from _index.md frontmatter)
            # Critical for incremental builds: without this, cascade data is lost
            # when _index.md files are loaded from cache
            cascade=self._raw_metadata.get("cascade", {}),
        )

    def normalize_core_paths(self) -> None:
        """
        Normalize PageCore paths to be relative (for cache consistency).

        This should be called before caching to ensure all paths are relative
        to the site root, preventing absolute path leakage into cache.

        Also updates core.section from _section_path since the page may have
        been assigned to a section after core was initially created.

        Uses dataclasses.replace() since PageCore is frozen (immutable).
        """
        from dataclasses import replace

        if not self._site or not self.core:
            return

        updates: dict[str, str] = {}

        # Convert absolute source_path to relative
        source_path_str = self.core.source_path
        if Path(source_path_str).is_absolute():
            try:
                rel_path = Path(source_path_str).relative_to(self._site.root_path)
                updates["source_path"] = str(rel_path)
            except ValueError, AttributeError:
                pass  # Keep absolute if not under root

        # Update section from _section_path (may have been set after core creation)
        # Convert to relative path for cache consistency
        if self._section_path is not None:
            try:
                content_dir = self._site.root_path / "content"
                rel_section = str(self._section_path.relative_to(content_dir))
                updates["section"] = rel_section
            except ValueError, AttributeError:
                # Fallback: use string representation
                updates["section"] = str(self._section_path)

        # Apply all updates at once
        if updates:
            self.core = replace(self.core, **updates)

    @property
    def frontmatter(self) -> Frontmatter:
        """
        Typed access to frontmatter fields.

        When to use:
            Use this when calling code knows the expected types — the
            ``Frontmatter`` wrapper gives IDE/type-checker support and safer
            coercion than ``self.metadata[...]``. Prefer ``self.metadata``
            for dict-style iteration or unknown-key access (templates,
            frontmatter dumps). Both include cascade; the difference is
            typed-object vs dict-like access.

        Lazily created from metadata dict on first access.

        Example:
            >>> page.frontmatter.title  # Typed: str
            'My Post'
            >>> page.frontmatter["title"]  # Dict syntax for templates
            'My Post'
        """
        if self._frontmatter is None:
            with self._init_lock:
                if self._frontmatter is None:
                    self._frontmatter = Frontmatter.from_dict(dict(self.metadata))
        return self._frontmatter

    @classmethod
    def create_virtual(
        cls,
        source_id: str,
        title: str,
        content: str = "",
        metadata: dict[str, Any] | None = None,
        rendered_html: str | None = None,
        template_name: str | None = None,
        output_path: Path | None = None,
        section_path: Path | None = None,
    ) -> Page:
        """
        Create a virtual page for dynamically-generated content.

        When to use:
            Use this for pages that have no corresponding markdown file —
            typically autodoc (Python/OpenAPI), generated listing indexes,
            or content imported from external sources at build time. Prefer
            the regular ``Page(...)`` constructor whenever a real source
            file exists; virtual pages bypass disk mtime tracking and must
            register their output path explicitly. Pass ``rendered_html=``
            to skip markdown parsing when you already have HTML.

        Virtual pages are not backed by a disk file but integrate with
        the site's page collection, navigation, and rendering pipeline.

        Args:
            source_id: Unique identifier for this page (used as source_path)
            title: Page title
            content: Raw content (markdown) - optional if rendered_html provided
            metadata: Page metadata/frontmatter
            rendered_html: Pre-rendered HTML (bypasses markdown parsing)
            template_name: Custom template name (optional)
            output_path: Explicit output path (optional)
            section_path: Section this page belongs to (optional)

        Returns:
            A new virtual Page instance

        Example:
            page = Page.create_virtual(
                source_id="api/bengal/core/page.md",
                title="Page Module",
                metadata={"type": "autodoc/python"},
                rendered_html="<div class='api-card'>...</div>",
                template_name="autodoc/python/module",
            )
        """
        page_metadata = metadata or {}
        page_metadata["title"] = title

        page = cls(
            source_path=Path(source_id),
            _raw_content=content,
            _raw_metadata=page_metadata,
            rendered_html=rendered_html or "",
            output_path=output_path,
            _section_path=section_path,
        )

        # Set virtual page fields (not in __init__ to preserve dataclass)
        page.virtual = True
        page.prerendered_html = rendered_html
        page.template_name = template_name

        return page

    def __hash__(self) -> int:
        """
        Hash based on source_path for stable identity.

        The hash is computed from the page's source_path, which is immutable
        throughout the page lifecycle. This allows pages to be stored in sets
        and used as dictionary keys.

        Returns:
            Integer hash of the source path
        """
        return hash(self.source_path)

    def __eq__(self, other: object) -> bool:
        """
        Pages are equal if they have the same source path.

        Equality is based on source_path only, not on content or other
        mutable fields. This means two Page objects representing the same
        source file are considered equal, even if their processed content
        differs.

        Args:
            other: Object to compare with

        Returns:
            True if other is a Page with the same source_path
        """
        if not isinstance(other, Page):
            return NotImplemented
        return self.source_path == other.source_path

    def eq(self, other: object) -> bool:
        """
        Template-facing page equality helper.

        This mirrors ``__eq__`` but returns ``False`` instead of
        ``NotImplemented`` for non-Page values, preserving the older template
        helper behavior.
        """
        if not isinstance(other, Page):
            return False
        return self.source_path == other.source_path

    def in_section(self, section: Any) -> bool:
        """Return True when this page belongs to the given section."""
        return bool(self._section == section)

    def is_ancestor(self, other: Page) -> bool:
        """Return True when this page acts as a section ancestor of another page."""
        if not self.is_section:
            return False

        from bengal.protocols.capabilities import has_walk

        return other._section in self.walk() if has_walk(self) else False

    def is_descendant(self, other: object) -> bool:
        """Return True when this page is a descendant of another page."""
        if hasattr(other, "is_ancestor") and isinstance(other, Page):
            return other.is_ancestor(self)
        return False

    def __repr__(self) -> str:
        return f"Page(title='{self.title}', source='{self.source_path}')"

    def _format_path_for_log(self, path: Path | str | None) -> str | None:
        """
        Format a path as relative to site root for logging.

        Makes paths relative to the site root directory to avoid showing
        user-specific absolute paths in logs and warnings.

        Args:
            path: Path to format (can be Path, str, or None)

        Returns:
            Relative path string, or None if path was None
        """
        from bengal.utils.primitives.text import format_path_for_display

        base_path = None
        if self._site is not None and isinstance(self._site, SiteLike):
            base_path = self._site.root_path

        return format_path_for_display(path, base_path)

    @property
    def _section(self) -> SectionLike | None:
        """
        Get the section this page belongs to (lazy lookup via path or URL).

        This property performs a path-based or URL-based lookup in the site's
        section registry, enabling stable section references across rebuilds
        when Section objects are recreated.

        Virtual sections (path=None) use URL-based lookups via _section_url.
        Regular sections use path-based lookups via _section_path.

        Returns:
            Section object if found, None if page has no section or section not found

        Implementation Note:
            Uses counter-gated warnings to prevent log spam when sections are
            missing (warns first 3 times, shows summary, then silent).

        See Also:
            plan/active/rfc-page-section-reference-contract.md
        """
        # No section reference at all
        if self._section_path is None and self._section_url is None:
            return None

        if self._site is None:
            # Warn globally about missing site reference (class-level counter)
            warn_key = "missing_site"
            with self._warnings_lock:
                if self._global_missing_section_warnings.get(warn_key, 0) < 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_lookup_no_site",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                    )
                    # Bound the warning dict to prevent unbounded growth
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        # Remove oldest entry (first key in dict)
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = (
                        self._global_missing_section_warnings.get(warn_key, 0) + 1
                    )
            return None

        # Cache key ties the resolved section to the active site object + reference fields + registry epoch.
        # This keeps lookups O(1) after the first resolution within a build.
        # The epoch ensures cache invalidation when sections are re-registered.
        epoch = self._site.registry.epoch if hasattr(self._site, "registry") else 0
        cache_key = (id(self._site), epoch, self._section_path, self._section_url)
        if self._section_obj_cache_key == cache_key:
            cached = self._section_obj_cache
            return None if cached is self._SECTION_NOT_FOUND else cast("SectionLike | None", cached)

        with self._init_lock:
            if self._section_obj_cache_key == cache_key:
                cached = self._section_obj_cache
                return (
                    None
                    if cached is self._SECTION_NOT_FOUND
                    else cast("SectionLike | None", cached)
                )

            # Perform O(1) lookup via appropriate registry
            if self._section_path is not None:
                section = self._site.get_section_by_path(self._section_path)
            else:
                section = self._site.get_section_by_url(self._section_url or "")

        if section is None:
            # Counter-gated warning to prevent log spam (class-level counter)
            warn_key = str(self._section_path or self._section_url)
            with self._warnings_lock:
                count = self._global_missing_section_warnings.get(warn_key, 0)

                if count < 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_not_found",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                        count=count + 1,
                    )
                    # Bound the warning dict to prevent unbounded growth
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        # Remove oldest entry (first key in dict)
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = count + 1
                elif count == 3:
                    # Show summary after 3rd warning, then go silent
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_not_found_summary",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                        total_warnings=count + 1,
                        note="Further warnings for this section will be suppressed",
                    )
                    # Bound the warning dict to prevent unbounded growth
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        # Remove oldest entry (first key in dict)
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = count + 1

        # Cache both hits and misses (misses use a sentinel).
        with self._init_lock:
            self._section_obj_cache_key = cache_key
            self._section_obj_cache = section if section is not None else self._SECTION_NOT_FOUND
        return section

    @_section.setter
    def _section(self, value: SectionLike | None) -> None:
        """
        Set the section this page belongs to (stores path or URL, not object).

        This setter extracts the path (or URL for virtual sections) from the
        Section object and stores it, enabling stable references when Section
        objects are recreated during incremental rebuilds.

        For virtual sections (path=None), stores relative_url in _section_url.
        For regular sections, stores path in _section_path.

        Args:
            value: Section object or None

        See Also:
            plan/active/rfc-page-section-reference-contract.md
        """
        if value is None:
            self._section_path = None
            self._section_url = None
        elif value.path is not None:
            # Regular section: use path for lookup
            self._section_path = value.path
            self._section_url = None
        else:
            # Virtual section: use _path for lookup
            self._section_path = None
            self._section_url = getattr(value, "_path", None) or f"/{value.name}/"

        # Invalidate resolved section cache (reference changed).
        self._section_obj_cache_key = None
        self._section_obj_cache = None

    @property
    def section_path(self) -> str | None:
        """
        Get the section path as a string.

        When to use:
            Use when you need a serializable path string (cache keys, JSON
            output, log lines). Prefer ``self.parent`` (``Section`` object)
            for navigation and ``self._section_path`` (``Path``) for
            filesystem operations — this property strings both together
            and should not be round-tripped back into those forms.

        Returns:
            Section path as string (e.g., "docs/guides") or None
        """
        return str(self._section_path) if self._section_path else None

    # ------------------------------------------------------------------
    # Navigation properties (delegate to free functions in navigation.py)
    # ------------------------------------------------------------------

    @property
    def next(self) -> PageLike | None:
        """
        Next page in the full site collection (chronological by date).

        When to use:
            Use this for site-wide "next post" navigation (blog archive
            feeds). Prefer ``next_in_section`` when the reader should stay
            within the current directory (docs chapters, tutorial steps).
        """
        from bengal.core.page.navigation import get_next_page

        return get_next_page(self, self._site)

    @property
    def prev(self) -> PageLike | None:
        """
        Previous page in the full site collection (chronological by date).

        When to use:
            Site-wide companion to ``next``. Prefer ``prev_in_section`` for
            within-directory navigation.
        """
        from bengal.core.page.navigation import get_prev_page

        return get_prev_page(self, self._site)

    @property
    def next_in_section(self) -> PageLike | None:
        """
        Next page among siblings in this page's section.

        When to use:
            Use this for chapter-style navigation where the reader should
            stay inside the current section (``docs/guides/``, ``tutorial/``).
            Prefer ``next`` for site-wide chronological navigation, and
            ``next_in_series`` when a page declares ``series:`` frontmatter.
        """
        from bengal.core.page.navigation import get_next_in_section

        return get_next_in_section(self, self._section)

    @property
    def prev_in_section(self) -> PageLike | None:
        """
        Previous page among siblings in this page's section.

        When to use:
            Section-scoped companion to ``next_in_section``. See ``next`` and
            ``prev_in_series`` for the other two navigation modes.
        """
        from bengal.core.page.navigation import get_prev_in_section

        return get_prev_in_section(self, self._section)

    @property
    def parent(self) -> SectionLike | None:
        """Parent section of this page."""
        return self._section

    @property
    def ancestors(self) -> list[SectionLike]:
        """Ancestor sections from immediate parent to root."""
        from bengal.core.page.navigation import get_ancestors

        return get_ancestors(self._section)

    # ------------------------------------------------------------------
    # Bundle properties (delegate to free functions in bundle.py)
    # ------------------------------------------------------------------

    @cached_property
    def bundle_type(self) -> BundleType:
        """
        Bundle type classification (LEAF, BRANCH, or NONE).

        When to use:
            Use this for switch-style logic where you need to distinguish all
            three cases (``LEAF`` = page bundle with co-located resources,
            ``BRANCH`` = section index like ``_index.md``, ``NONE`` = plain
            page). For simple boolean checks, prefer the ``is_bundle`` /
            ``is_branch_bundle`` shortcuts.
        """
        from bengal.core.page.bundle import get_bundle_type

        return get_bundle_type(self.source_path)

    @property
    def is_bundle(self) -> bool:
        """
        True if this page is a leaf bundle (markdown + co-located resources).

        When to use:
            Use this to gate resource-copying logic (images, downloads)
            that applies only to leaf bundles. Mutually exclusive with
            ``is_branch_bundle``. For full three-way classification, use
            ``bundle_type``.
        """
        return self.bundle_type == BundleType.LEAF

    @property
    def is_branch_bundle(self) -> bool:
        """
        True if this page is a branch bundle (section index: ``_index.md``).

        When to use:
            Use this to detect pages that represent a whole section rather
            than a single piece of content — typically to render section
            landing layouts or to merge branch frontmatter into cascade.
            Mutually exclusive with ``is_bundle``.
        """
        return self.bundle_type == BundleType.BRANCH

    @cached_property
    def resources(self) -> PageResources:
        """
        Resources co-located with this page bundle (images, downloads).

        When to use:
            Use when rendering a leaf bundle that needs to surface its
            co-located files — image galleries, download links, featured
            media. Returns an empty container for non-bundle pages, so
            templates can iterate unconditionally. Gate heavier resource
            logic on ``self.is_bundle`` to avoid unnecessary lookups.
        """
        from bengal.core.page.bundle import get_resources

        return get_resources(self.source_path, getattr(self, "url", "/"))

    # ------------------------------------------------------------------
    # Computed properties (delegate to free functions in computed.py)
    # ------------------------------------------------------------------

    @property
    def _source(self) -> str:
        """Raw markdown source content."""
        return self._raw_content

    @property
    def content(self) -> str:
        """
        Rendered HTML content for template display.

        Compatibility property for ``{{ page.content | safe }}``. Raw markdown
        remains available as ``page._source`` for internal use.
        """
        from bengal.rendering.page_content import get_content

        return get_content(self)

    @property
    def ast(self) -> list[ASTNode] | dict[str, Any] | None:
        """Parser AST cache when available."""
        from bengal.rendering.page_content import get_ast

        return get_ast(self)

    @property
    def html(self) -> str:
        """Rendered HTML content."""
        from bengal.rendering.page_content import get_html

        return get_html(self)

    @property
    def plain_text(self) -> str:
        """Plain text extracted from AST, HTML, or raw source."""
        from bengal.rendering.page_content import get_plain_text

        return get_plain_text(self)

    def _render_ast_to_html(self) -> str:
        """Compatibility shim for older private Page content callers."""
        from bengal.rendering.page_content import render_ast_to_html

        return render_ast_to_html(self)

    def _extract_text_from_ast(self) -> str:
        """Compatibility shim for older private Page content callers."""
        from bengal.rendering.page_content import extract_text_from_ast_cache

        return extract_text_from_ast_cache(self._ast_cache)

    def _extract_links_from_ast(self) -> list[str]:
        """Compatibility shim for older private Page content callers."""
        from bengal.rendering.page_content import extract_links_from_ast_cache

        return extract_links_from_ast_cache(self._ast_cache)

    def _strip_html_to_text(self, html: str) -> str:
        """Compatibility shim for older private Page content callers."""
        from bengal.rendering.page_content import strip_html_to_text

        return strip_html_to_text(html)

    def extract_links(self, plugin_links: list[str] | None = None) -> list[str]:
        """
        Extract links from page content via the rendering-side service.

        Compatibility shim for older call sites that invoke
        ``page.extract_links()`` directly. Build code should prefer
        ``bengal.rendering.page_operations.extract_links(page, ...)``.
        """
        from bengal.rendering.page_operations import extract_links

        return extract_links(self, plugin_links=plugin_links)

    def HasShortcode(self, name: str) -> bool:
        """
        Return True if page content uses the given shortcode.

        When to use:
            Use in templates to branch on optional content — e.g. render a
            hero layout only when the page includes a ``{{% hero %}}``
            shortcode, or skip an expensive block when its driving
            shortcode is absent. Preferable to string-matching the raw
            source because shortcode parsing handles comments and nesting.
        """
        from bengal.rendering.page_operations import has_shortcode

        return has_shortcode(self, name)

    @cached_property
    def word_count(self) -> int:
        """Word count from source markdown."""
        from bengal.core.page.computed import compute_word_count

        return compute_word_count(self._raw_content)

    @cached_property
    def meta_description(self) -> str:
        """SEO-friendly meta description (max 160 chars)."""
        from bengal.rendering.page_content import get_meta_description

        return get_meta_description(self, self.metadata)

    @cached_property
    def reading_time(self) -> int:
        """Estimated reading time in minutes (minimum 1)."""
        from bengal.core.page.computed import compute_reading_time

        return compute_reading_time(self.word_count)

    @cached_property
    def excerpt(self) -> str:
        """Content excerpt for listings (max 250 chars)."""
        from bengal.rendering.page_content import get_excerpt

        return get_excerpt(self)

    @cached_property
    def age_days(self) -> int:
        """
        Days since publication.

        When to use:
            Use for short-range freshness checks ("new this week", "posted
            less than N days ago"). For coarse ranges use ``age_months`` —
            it uses calendar arithmetic and is not equivalent to
            ``age_days // 30``.
        """
        from bengal.core.page.computed import compute_age_days

        return compute_age_days(self.date)

    @cached_property
    def age_months(self) -> int:
        """
        Months since publication (calendar-aware, not ``age_days // 30``).

        When to use:
            Use for coarse freshness labels ("updated 3 months ago"). Uses
            calendar month arithmetic, so a post from Jan 31 is reported as
            1 month old on Feb 28, not ~29 days. Prefer ``age_days`` for
            short-range checks.
        """
        from bengal.core.page.computed import compute_age_months

        return compute_age_months(self.date)

    @cached_property
    def author(self) -> Author | None:
        """
        Primary author as an ``Author`` object (first entry, or ``None``).

        When to use:
            Use this for byline display where a single name is shown. For
            multi-author pages, iterate ``authors`` instead — ``author``
            returns only the first one and hides collaborators.
        """
        from bengal.core.page.computed import get_primary_author

        return get_primary_author(self.metadata)

    @cached_property
    def authors(self) -> list[Author]:
        """
        All authors as a list of ``Author`` objects (may be empty).

        When to use:
            Use this for pages with multiple contributors, author cards,
            or co-author metadata. Prefer ``author`` when the template only
            shows a single byline — ``authors`` always returns a list even
            for single-author pages.
        """
        from bengal.core.page.computed import get_all_authors

        return get_all_authors(self.metadata)

    @cached_property
    def series(self) -> Series | None:
        """
        Series metadata object if this page declares ``series:`` frontmatter.

        When to use:
            Use as the truthiness gate before rendering series navigation —
            calling ``next_in_series`` / ``prev_in_series`` when
            ``page.series`` is ``None`` returns ``None`` silently, which
            hides template logic errors. Also exposes series-level metadata
            (total count, series title) not available on the navigation
            properties.
        """
        from bengal.core.page.computed import get_series_info

        return get_series_info(self.metadata)

    @cached_property
    def prev_in_series(self) -> PageLike | None:
        """
        Previous page in the explicit series this page belongs to.

        When to use:
            Use this for tutorial/article-series navigation where pages opt
            in via ``series:`` frontmatter. Returns ``None`` when the page
            has no series. Distinct from ``prev_in_section`` (directory
            siblings) and ``prev`` (site-wide chronological).
        """
        from bengal.core.page.computed import get_series_neighbor

        return get_series_neighbor(self.metadata, self._site, -1)

    @cached_property
    def next_in_series(self) -> PageLike | None:
        """
        Next page in the explicit series this page belongs to.

        When to use:
            Series companion to ``prev_in_series``. See ``next`` and
            ``next_in_section`` for the other two navigation modes.
        """
        from bengal.core.page.computed import get_series_neighbor

        return get_series_neighbor(self.metadata, self._site, 1)


__all__ = [
    "BundleType",
    "Frontmatter",
    "Page",
    "PageResource",
    "PageResources",
]
