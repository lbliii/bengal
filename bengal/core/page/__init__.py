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
    navigation.py: PageNavigationMixin (URL, breadcrumbs)
    computed.py: PageComputedMixin (derived properties)
    content.py: PageContentMixin (AST, TOC, excerpts)
    relationships.py: PageRelationshipsMixin (prev/next, related)
    operations.py: PageOperationsMixin (read, save)
    proxy.py: PageProxy for lazy loading
    utils.py: Field separation utilities

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
    2. Parsing: toc, parsed_ast populated
    3. Rendering: rendered_html, output_path populated

Related Packages:
    bengal.core.page.page_core: Cacheable page metadata
    bengal.rendering.renderer: Page rendering pipeline
    bengal.orchestration.content: Content discovery and page creation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.section import Section
    from bengal.core.site import Site

from .computed import PageComputedMixin
from .content import PageContentMixin
from .frontmatter import Frontmatter
from .metadata import PageMetadataMixin
from .navigation import PageNavigationMixin
from .operations import PageOperationsMixin
from .page_core import PageCore
from .proxy import PageProxy
from .relationships import PageRelationshipsMixin


@dataclass
class Page(
    PageMetadataMixin,
    PageNavigationMixin,
    PageComputedMixin,
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
       ❌ Not available: toc, parsed_ast, toc_items, rendered_html

    2. Parsing (pipeline.py)
       ✅ Available: All Stage 1 + toc, parsed_ast
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
        parsed_ast: Abstract Syntax Tree from parsed content
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
    _MAX_WARNING_KEYS: ClassVar[int] = 100

    # Required field (no default)
    source_path: Path

    # PageCore: Cacheable metadata (single source of truth for Page/PageMetadata/PageProxy)
    # Auto-created in __post_init__ from Page fields
    core: PageCore | None = field(default=None, init=False)

    # Optional fields (with defaults)
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    # NOTE: Despite the name, parsed_ast currently stores rendered HTML (legacy).
    # The ASTNode types in bengal.rendering.ast_types are for future AST-based
    # processing. See plan/ready/plan-type-system-hardening.md for migration path.
    parsed_ast: Any | None = None
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

    # Private cache for lazy toc_items property
    _toc_items_cache: list[dict[str, Any]] | None = field(default=None, repr=False, init=False)

    # Private cache for lazy frontmatter property
    _frontmatter: Frontmatter | None = field(default=None, init=False, repr=False)

    # Private caches for AST-based content (Phase 3 of RFC)
    # See: plan/active/rfc-content-ast-architecture.md
    _ast_cache: list[dict[str, Any]] | None = field(default=None, repr=False, init=False)
    _html_cache: str | None = field(default=None, repr=False, init=False)
    _plain_text_cache: str | None = field(default=None, repr=False, init=False)

    # Virtual page support (for API docs, generated content)
    _virtual: bool = field(default=False, repr=False)

    # Pre-rendered HTML for virtual pages (bypasses markdown parsing)
    _prerendered_html: str | None = field(default=None, repr=False)

    # Template override for virtual pages (uses custom template)
    _template_name: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize computed fields and PageCore."""
        if self.metadata:
            self.tags = self.metadata.get("tags", [])
            # Priority: explicit 'version' frontmatter -> auto-detected '_version' metadata
            self.version = self.metadata.get("version") or self.metadata.get("_version")
            self.aliases = self.metadata.get("aliases", [])

        # Auto-create PageCore from Page fields
        self._init_core_from_fields()

    def _init_core_from_fields(self) -> None:
        """
        Initialize PageCore from Page fields.

        Note: Initially creates PageCore with absolute paths, but normalize_core_paths()
        should be called before caching to convert to relative paths.
        """
        # Separate standard fields from custom props (Component Model)
        from bengal.core.page.utils import separate_standard_and_custom_fields

        standard_fields, custom_props = separate_standard_and_custom_fields(self.metadata)

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
        )

    def normalize_core_paths(self) -> None:
        """
        Normalize PageCore paths to be relative (for cache consistency).

        This should be called before caching to ensure all paths are relative
        to the site root, preventing absolute path leakage into cache.

        Note: Directly mutates self.core.source_path since dataclasses are mutable.
        """
        if not self._site or not self.core:
            return

        # Convert absolute source_path to relative
        source_path_str = self.core.source_path
        if Path(source_path_str).is_absolute():
            try:
                rel_path = Path(source_path_str).relative_to(self._site.root_path)
                # Directly update the field - no need to recreate entire PageCore
                self.core.source_path = str(rel_path)
            except (ValueError, AttributeError):
                pass  # Keep absolute if not under root

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
            content=content,
            metadata=page_metadata,
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

    def __eq__(self, other: Any) -> bool:
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
        from bengal.utils.paths import format_path_for_display

        base_path = None
        if self._site is not None and hasattr(self._site, "root_path"):
            base_path = self._site.root_path

        return format_path_for_display(path, base_path)

    @property
    def _section(self) -> Any | None:
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

        # Perform O(1) lookup via appropriate registry
        if self._section_path is not None:
            # Regular section: path-based lookup
            section = self._site.get_section_by_path(self._section_path)
        else:
            # Virtual section: URL-based lookup
            section = self._site.get_section_by_url(self._section_url)

        if section is None:
            # Counter-gated warning to prevent log spam (class-level counter)
            warn_key = str(self._section_path or self._section_url)
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

        return section

    @_section.setter
    def _section(self, value: Any) -> None:
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


__all__ = ["Frontmatter", "Page", "PageProxy"]
