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
operations.py: PageOperationsMixin (render, validate_links, extract_links)

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from bengal.core.author import Author
    from bengal.core.section import Section
    from bengal.core.series import Series
    from bengal.core.site import Site
    from bengal.parsing.ast.types import ASTNode
    from bengal.utils.pagination import Paginator

from .bundle import BundleType, PageBundleMixin, PageResource, PageResources
from .computed import PageComputedMixin
from .content import PageContentMixin
from .frontmatter import Frontmatter
from .metadata import PageMetadataMixin
from .navigation import PageNavigationMixin
from .operations import PageOperationsMixin
from .page_core import PageCore
from .page_identity import PageIdentity
from .page_section import PageSectionMixin
from .proxy import PageProxy
from .relationships import PageRelationshipsMixin
from .types import TOCItem
from .utils import normalize_tags


@dataclass
class Page(
    PageMetadataMixin,
    PageSectionMixin,
    PageRelationshipsMixin,
    PageNavigationMixin,
    PageBundleMixin,
    PageComputedMixin,
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
    _toc_items_cache: list[TOCItem] | None = field(default=None, repr=False, init=False)

    # AST-extracted excerpt (set by pipeline when Patitas parses; bypasses compute_excerpt)
    _excerpt: str | None = field(default=None, repr=False, init=False)
    # AST-extracted meta description (set by pipeline; bypasses compute_meta_description)
    _meta_description: str | None = field(default=None, repr=False, init=False)

    # Private cache for lazy frontmatter property
    _frontmatter: Frontmatter | None = field(default=None, init=False, repr=False)

    # Cache for CascadeView (invalidated when site/section changes)
    _metadata_view_cache: Any = field(default=None, init=False, repr=False)
    _metadata_view_cache_key: tuple[int, str] | None = field(default=None, init=False, repr=False)
    # Cached section path string (avoids pathlib.relative_to on every .metadata access)
    _cached_section_path_str: str | None = field(default=None, init=False, repr=False)

    # Private caches for AST-based content (Phase 3 of RFC)
    # See: plan/active/rfc-content-ast-architecture.md
    # Patitas: dict (Document with "children"); legacy: list[ASTNode]
    _ast_cache: list[ASTNode] | dict[str, Any] | None = field(default=None, repr=False, init=False)
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

    # Frozen identity struct for hot-path O(1) access in build/render loops
    _identity: PageIdentity | None = field(default=None, repr=False, init=False)

    # Complexity cache for parallel render ordering (set by orchestration)
    _complexity_score: int | None = field(default=None, repr=False, init=False)
    # Cascade invalidation flag (set by provenance filter when provenance changes)
    _cascade_invalidated: bool = field(default=False, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize computed fields and PageCore."""
        if self._raw_metadata:
            self.tags = normalize_tags(self._raw_metadata.get("tags"))
            # Priority: explicit 'version' frontmatter -> auto-detected '_version' metadata
            self.version = self._raw_metadata.get("version") or self._raw_metadata.get("_version")
            self.aliases = self._raw_metadata.get("aliases", [])

        # Auto-create PageCore from Page fields
        self._init_core_from_fields()

    @property
    def identity(self) -> PageIdentity:
        """Frozen hot-path struct for O(1) access in build/render loops.

        Cost: O(1) — returns cached frozen dataclass.

        Raises RuntimeError if accessed before finalize_identity() is called
        (i.e., before content phases complete).
        """
        if self._identity is None:
            raise RuntimeError(
                f"PageIdentity not yet finalized for {self.source_path}. "
                "Call page.finalize_identity() after content phases complete."
            )
        return self._identity

    def finalize_identity(self) -> None:
        """Snapshot the page's hot-path fields into a frozen PageIdentity struct.

        Called by build orchestration at the end of content phases, after all
        section assignments, output paths, and tag normalization are complete.
        The resulting PageIdentity is immutable and safe for concurrent read
        access during rendering.
        """
        section_str = self._cached_section_path_str
        if section_str is None and self._section_path:
            try:
                if self._site:
                    content_dir = self._site.root_path / "content"
                    section_str = str(self._section_path.relative_to(content_dir))
                else:
                    section_str = str(self._section_path)
            except ValueError, AttributeError:
                section_str = str(self._section_path)
            self._cached_section_path_str = section_str

        tag_slugs = frozenset(self.tags) if self.tags else frozenset()

        self._identity = PageIdentity(
            page_id=id(self),
            source_path=str(self.source_path),
            section_path_str=section_str or "",
            slug=self.slug,
            kind=self.kind,
            is_generated=bool(self._raw_metadata.get("_generated")),
            is_index=self.source_path.stem in ("_index", "index"),
            tag_slugs=tag_slugs,
            href=self.href,
        )

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


__all__ = [
    "BundleType",
    "Frontmatter",
    "Page",
    "PageIdentity",
    "PageProxy",
    "PageResource",
    "PageResources",
]
