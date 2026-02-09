"""
Page representation for content pages in Bengal SSG.

Provides the main Page class combining multiple mixins for metadata,
navigation, content processing, and rendering. Pages represent markdown
content files and are the primary content unit in Bengal.

Public API:
Page: Content page with metadata, content, and rendering capabilities
PageProxy: Lazy-loading proxy for incremental builds (wraps PageCore)

Package Structure:
page_core.py: PageCore dataclass (cacheable metadata)
metadata.py: PageMetadataMixin (frontmatter access)
navigation.py: Free functions for navigation and hierarchy
computed.py: Free functions for computed properties (word count, reading time, etc.)
content.py: PageContentMixin (AST, TOC, excerpts)
bundle.py: Free functions for bundle detection and resource access
relationships.py: PageRelationshipsMixin (prev/next, related)
proxy.py: PageProxy for lazy loading
utils.py: Field separation utilities
(PageOperationsMixin moved to bengal.rendering.page_operations)

Key Concepts:
Mixin Architecture: Page combines focused mixins for separation of
    concerns. Each mixin handles a specific aspect (metadata, nav, etc.).

Hashability: Pages are hashable by source_path, enabling set operations
    and use as dict keys. Two pages with same path are equal.

Virtual Pages: Pages without disk files (e.g., autodoc). Created via
    Page.create_virtual() for dynamically-generated content.

PageCore: Cacheable subset of page metadata. Shared between Page,
    PageProxy, and cache layer. Enables incremental builds.

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
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from bengal.core.cascade import CascadeSnapshot, CascadeView
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.protocols import SiteLike

if TYPE_CHECKING:
    from bengal.core.author import Author
    from bengal.core.section import Section
    from bengal.core.series import Series
    from bengal.core.site import Site
    from bengal.utils.pagination import Paginator

# Import PageOperationsMixin from rendering layer where it logically belongs.
# This is an intentional cross-layer import - the mixin contains rendering logic
# that is mixed into the Page class for API convenience.
from bengal.rendering.page_operations import PageOperationsMixin

from .bundle import BundleType, PageResource, PageResources
from .content import PageContentMixin
from .frontmatter import Frontmatter
from .metadata import PageMetadataMixin
from .page_core import PageCore
from .proxy import PageProxy
from .relationships import PageRelationshipsMixin


@dataclass
class Page(
    PageMetadataMixin,
    PageRelationshipsMixin,
    PageOperationsMixin,
    PageContentMixin,
):
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
    - Have _virtual=True and a synthetic source_path
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
        _virtual: True if this is a virtual page (not backed by a disk file)

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

    # PageCore: Cacheable metadata (single source of truth for Page/PageMetadata/PageProxy)
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
    _site: Site | None = field(default=None, repr=False)
    # Path-based section reference (stable across rebuilds)
    _section_path: Path | None = field(default=None, repr=False)
    # URL-based section reference for virtual sections (path=None)
    # See: plan/active/rfc-page-section-reference-contract.md
    _section_url: str | None = field(default=None, repr=False)

    # Cached resolved Section object for fast repeated access during template rendering.
    # NOTE: Cache is per-site-object + epoch + reference tuple and must be invalidated when those change.
    _section_obj_cache: Section | object | None = field(default=None, repr=False, init=False)
    _section_obj_cache_key: tuple[int, int, Path | None, str | None] | None = field(
        default=None, repr=False, init=False
    )

    # Sentinel representing a cached "not found" section.
    _SECTION_NOT_FOUND: ClassVar[object] = object()

    # Private cache for lazy toc_items property
    _toc_items_cache: list[dict[str, Any]] | None = field(default=None, repr=False, init=False)

    # Private cache for lazy frontmatter property
    _frontmatter: Frontmatter | None = field(default=None, init=False, repr=False)

    # Cache for CascadeView (invalidated when site/section changes)
    _metadata_view_cache: CascadeView | None = field(default=None, init=False, repr=False)
    _metadata_view_cache_key: tuple[int, str] | None = field(default=None, init=False, repr=False)

    # Patitas Document AST — the structural source of truth for this page's content.
    # Populated during parsing by the Patitas wrapper. Enables incremental diffing,
    # fragment updates, multi-output derivation (HTML, TOC, plain text), and
    # AST-driven provenance hashing.
    # Type is Any because Patitas is an external dependency (cannot import into core).
    _ast_cache: Any = field(default=None, repr=False, init=False)
    _html_cache: str | None = field(default=None, repr=False, init=False)
    _plain_text_cache: str | None = field(default=None, repr=False, init=False)

    # Virtual page support (for API docs, generated content)
    _virtual: bool = field(default=False, repr=False)

    # Internal metadata for section index pages (replaces metadata["_key"] pattern)
    # These are build-time bookkeeping, not user-facing frontmatter
    _posts: list[Page] | None = field(default=None, repr=False, init=False)
    _subsections: list[Any] | None = field(default=None, repr=False, init=False)  # list[Section]
    _paginator: Paginator[Page] | None = field(default=None, repr=False, init=False)
    _page_num: int | None = field(default=None, repr=False, init=False)
    _autodoc_fallback_template: bool = field(default=False, repr=False, init=False)
    _autodoc_fallback_reason: str | None = field(default=None, repr=False, init=False)

    # Pre-rendered HTML for virtual pages (bypasses markdown parsing)
    _prerendered_html: str | None = field(default=None, repr=False)

    # Template override for virtual pages (uses custom template)
    _template_name: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize computed fields and PageCore."""
        if self._raw_metadata:
            self.tags = self._raw_metadata.get("tags", [])
            # Priority: explicit 'version' frontmatter -> auto-detected '_version' metadata
            self.version = self._raw_metadata.get("version") or self._raw_metadata.get("_version")
            self.aliases = self._raw_metadata.get("aliases", [])

        # Auto-create PageCore from Page fields
        self._init_core_from_fields()

    @property
    def metadata(self) -> Mapping[str, Any]:
        """
        Return combined frontmatter + cascade metadata as CascadeView.

        This property provides dict-like access to page metadata. Values come from:
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
            except (ValueError, AttributeError):
                section_path = str(self._section_path)

        # Check cache validity (site id + section path)
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

    def _init_core_from_fields(self) -> None:
        """
        Initialize PageCore from Page fields.

        Note: Initially creates PageCore with absolute paths, but normalize_core_paths()
        should be called before caching to convert to relative paths.
        """
        # Separate standard fields from custom props (Component Model)
        from bengal.core.page.utils import separate_standard_and_custom_fields

        standard_fields, custom_props = separate_standard_and_custom_fields(self._raw_metadata)

        # Component Model: variant (normalized from layout/hero_style)
        variant = standard_fields.get("variant")
        # Normalize legacy fields to variant
        if not variant:
            variant = standard_fields.get("layout") or custom_props.get("hero_style")

        self.core = PageCore(
            source_path=str(self.source_path),  # May be absolute initially
            title=standard_fields.get("title", ""),
            date=standard_fields.get("date"),
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
            # when _index.md files are loaded from cache as PageProxy
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
            except (ValueError, AttributeError):
                pass  # Keep absolute if not under root

        # Update section from _section_path (may have been set after core creation)
        # Convert to relative path for cache consistency
        if self._section_path is not None:
            try:
                content_dir = self._site.root_path / "content"
                rel_section = str(self._section_path.relative_to(content_dir))
                updates["section"] = rel_section
            except (ValueError, AttributeError):
                # Fallback: use string representation
                updates["section"] = str(self._section_path)

        # Apply all updates at once
        if updates:
            self.core = replace(self.core, **updates)

    @property
    def is_virtual(self) -> bool:
        """
        Check if this is a virtual page (not backed by a disk file).

        Virtual pages are used for:
        - API documentation generated from Python source code
        - Dynamically-generated content from external sources
        - Content that doesn't have a corresponding content/ file

        Returns:
            True if this page is virtual (not backed by a disk file)
        """
        return self._virtual

    @property
    def template_name(self) -> str | None:
        """
        Get custom template name for this page.

        Virtual pages may specify a custom template for rendering.
        Returns None to use the default template selection logic.
        """
        return self._template_name

    @property
    def prerendered_html(self) -> str | None:
        """
        Get pre-rendered HTML for virtual pages.

        Virtual pages with pre-rendered HTML bypass markdown parsing
        and use this HTML directly in the template.
        """
        return self._prerendered_html

    @property
    def frontmatter(self) -> Frontmatter:
        """
        Typed access to frontmatter fields.

        Lazily created from metadata dict on first access.

        Example:
            >>> page.frontmatter.title  # Typed: str
            'My Post'
            >>> page.frontmatter["title"]  # Dict syntax for templates
            'My Post'
        """
        if self._frontmatter is None:
            self._frontmatter = Frontmatter.from_dict(self.metadata)
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
        page._virtual = True
        page._prerendered_html = rendered_html
        page._template_name = template_name

        return page

    @property
    def relative_path(self) -> str:
        """
        Get relative path string (alias for source_path as string).

        Used by templates and filtering where a string path is expected.
        This provides convenience.
        """
        return str(self.source_path)

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
    def _section(self) -> Section | None:
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
            return None if cached is self._SECTION_NOT_FOUND else cached

        # Perform O(1) lookup via appropriate registry (but may be non-trivial due to normalization)
        if self._section_path is not None:
            # Regular section: path-based lookup
            section = self._site.get_section_by_path(self._section_path)
        else:
            # Virtual section: URL-based lookup
            section = self._site.get_section_by_url(self._section_url)

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
        self._section_obj_cache_key = cache_key
        self._section_obj_cache = section if section is not None else self._SECTION_NOT_FOUND
        return section

    @_section.setter
    def _section(self, value: Section | None) -> None:
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

        Returns the path to the section this page belongs to, or None if
        the page doesn't belong to a section.

        Returns:
            Section path as string (e.g., "docs/guides") or None
        """
        return str(self._section_path) if self._section_path else None

    # ------------------------------------------------------------------
    # Navigation properties (delegate to free functions in navigation.py)
    # ------------------------------------------------------------------

    @property
    def next(self) -> Page | None:
        """Next page in site collection."""
        from bengal.core.page.navigation import get_next_page

        return get_next_page(self, self._site)

    @property
    def prev(self) -> Page | None:
        """Previous page in site collection."""
        from bengal.core.page.navigation import get_prev_page

        return get_prev_page(self, self._site)

    @property
    def next_in_section(self) -> Page | None:
        """Next page in current section."""
        from bengal.core.page.navigation import get_next_in_section

        return get_next_in_section(self, self._section)

    @property
    def prev_in_section(self) -> Page | None:
        """Previous page in current section."""
        from bengal.core.page.navigation import get_prev_in_section

        return get_prev_in_section(self, self._section)

    @property
    def parent(self) -> Section | None:
        """Parent section of this page."""
        return self._section

    @property
    def ancestors(self) -> list[Section]:
        """Ancestor sections from immediate parent to root."""
        from bengal.core.page.navigation import get_ancestors

        return get_ancestors(self._section)

    # ------------------------------------------------------------------
    # Bundle properties (delegate to free functions in bundle.py)
    # ------------------------------------------------------------------

    @cached_property
    def bundle_type(self) -> BundleType:
        """Bundle type classification (LEAF, BRANCH, or NONE)."""
        from bengal.core.page.bundle import get_bundle_type

        return get_bundle_type(self.source_path)

    @property
    def is_bundle(self) -> bool:
        """True if this page is a leaf bundle with resources."""
        return self.bundle_type == BundleType.LEAF

    @property
    def is_branch_bundle(self) -> bool:
        """True if this page is a branch bundle (section index)."""
        return self.bundle_type == BundleType.BRANCH

    @cached_property
    def resources(self) -> PageResources:
        """Get resources co-located with this page bundle."""
        from bengal.core.page.bundle import get_resources

        return get_resources(self.source_path, getattr(self, "url", "/"))

    # ------------------------------------------------------------------
    # Computed properties (delegate to free functions in computed.py)
    # ------------------------------------------------------------------

    @property
    def _source(self) -> str:
        """Raw markdown source content."""
        return self._raw_content

    @cached_property
    def word_count(self) -> int:
        """Word count from source markdown."""
        from bengal.core.page.computed import compute_word_count

        return compute_word_count(self._raw_content)

    @cached_property
    def meta_description(self) -> str:
        """SEO-friendly meta description (max 160 chars)."""
        from bengal.core.page.computed import compute_meta_description

        return compute_meta_description(self.metadata, self._raw_content)

    @cached_property
    def reading_time(self) -> int:
        """Estimated reading time in minutes (minimum 1)."""
        from bengal.core.page.computed import compute_reading_time

        return compute_reading_time(self.word_count)

    @cached_property
    def excerpt(self) -> str:
        """Content excerpt for listings (max 200 chars)."""
        from bengal.core.page.computed import compute_excerpt

        return compute_excerpt(self._raw_content)

    @cached_property
    def age_days(self) -> int:
        """Days since publication."""
        from bengal.core.page.computed import compute_age_days

        return compute_age_days(self.date)

    @cached_property
    def age_months(self) -> int:
        """Months since publication."""
        from bengal.core.page.computed import compute_age_months

        return compute_age_months(self.date)

    @cached_property
    def author(self) -> Author | None:
        """Primary author as Author object."""
        from bengal.core.page.computed import get_primary_author

        return get_primary_author(self.metadata)

    @cached_property
    def authors(self) -> list[Author]:
        """All authors as list of Author objects."""
        from bengal.core.page.computed import get_all_authors

        return get_all_authors(self.metadata)

    @cached_property
    def series(self) -> Series | None:
        """Series info as Series object."""
        from bengal.core.page.computed import get_series_info

        return get_series_info(self.metadata)

    @cached_property
    def prev_in_series(self) -> Page | None:
        """Previous page in series."""
        from bengal.core.page.computed import get_series_neighbor

        return get_series_neighbor(self.metadata, self._site, -1)

    @cached_property
    def next_in_series(self) -> Page | None:
        """Next page in series."""
        from bengal.core.page.computed import get_series_neighbor

        return get_series_neighbor(self.metadata, self._site, 1)


__all__ = [
    "BundleType",
    "Frontmatter",
    "Page",
    "PageProxy",
    "PageResource",
    "PageResources",
]
