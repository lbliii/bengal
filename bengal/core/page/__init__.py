"""
Page representation for content pages in Bengal SSG.

This module provides the main Page class, which combines multiple mixins
to provide a complete page interface while maintaining separation of concerns.
Pages represent markdown content files and provide metadata, navigation,
content processing, and template rendering capabilities.

Key Concepts:
    - Mixin architecture: Separated concerns via mixins (metadata, content, navigation)
    - Hashability: Pages hashable by source_path for set operations
    - AST-based content: Content represented as AST for efficient processing
    - Cacheable metadata: PageCore provides cacheable page metadata

Related Modules:
    - bengal.core.page.page_core: Cacheable page metadata
    - bengal.core.page.proxy: Lazy-loaded page placeholder
    - bengal.rendering.renderer: Page rendering logic
    - bengal.orchestration.content: Content discovery and page creation

See Also:
    - bengal/core/page/__init__.py:Page class for page representation
    - plan/active/rfc-content-ast-architecture.md: AST architecture RFC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from .computed import PageComputedMixin
from .content import PageContentMixin
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
    # Auto-created in __post_init__ from Page fields for backward compatibility
    core: PageCore = field(default=None, init=False)

    # Optional fields (with defaults)
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
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
    _site: Any | None = field(default=None, repr=False)
    # Path-based section reference (stable across rebuilds)
    _section_path: Path | None = field(default=None, repr=False)

    # Private cache for lazy toc_items property
    _toc_items_cache: list[dict[str, Any]] | None = field(default=None, repr=False, init=False)

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
            self.version = self.metadata.get("version")
            self.aliases = self.metadata.get("aliases", [])

        # Auto-create PageCore from Page fields
        # This provides backward compatibility until all instantiation updated
        self._init_core_from_fields()

    def _init_core_from_fields(self) -> None:
        """
        Initialize PageCore from Page fields (backward compatibility helper).

        This allows existing code that creates Page objects without passing
        core to continue working. Once all instantiation is updated, this
        can be removed and core made required.

        Note: Initially creates PageCore with absolute paths, but normalize_core_paths()
        should be called before caching to convert to relative paths.
        """
        # Logic to extract variant from legacy fields if needed
        # Component Model: variant (normalized from layout/hero_style)
        variant = self.metadata.get("variant") or self.metadata.get("layout") or self.metadata.get("hero_style")
        
        self.core = PageCore(
            source_path=str(self.source_path),  # May be absolute initially
            title=self.metadata.get("title", ""),
            date=self.metadata.get("date"),
            tags=self.tags or [],
            slug=self.metadata.get("slug"),
            weight=self.metadata.get("weight"),
            lang=self.lang,
            # Component Model Fields
            type=self.metadata.get("type"),
            variant=variant,
            description=self.metadata.get("description"),
            props=self.metadata,  # Pass all metadata as props bucket
            # Links
            section=str(self._section_path) if self._section_path else None,
            file_hash=None,  # Will be populated during caching
            aliases=self.aliases or [],
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
                metadata={"type": "api-reference"},
                rendered_html="<div class='api-card'>...</div>",
                template_name="api-reference/module",
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
        This provides backward compatibility and convenience.
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

    @property
    def _section(self) -> Any | None:
        """
        Get the section this page belongs to (lazy lookup via path).

        This property performs a path-based lookup in the site's section registry,
        enabling stable section references across rebuilds when Section objects
        are recreated.

        Returns:
            Section object if found, None if page has no section or section not found

        Implementation Note:
            Uses counter-gated warnings to prevent log spam when sections are
            missing (warns first 3 times, shows summary, then silent).
        """
        if self._section_path is None:
            return None

        if self._site is None:
            # Warn globally about missing site reference (class-level counter)
            warn_key = "missing_site"
            if self._global_missing_section_warnings.get(warn_key, 0) < 3:
                from bengal.utils.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    "page_section_lookup_no_site",
                    page=str(self.source_path),
                    section_path=str(self._section_path),
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

        # Perform O(1) lookup via site registry
        section = self._site.get_section_by_path(self._section_path)

        if section is None:
            # Counter-gated warning to prevent log spam (class-level counter)
            warn_key = str(self._section_path)
            count = self._global_missing_section_warnings.get(warn_key, 0)

            if count < 3:
                from bengal.utils.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    "page_section_not_found",
                    page=str(self.source_path),
                    section_path=str(self._section_path),
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
                from bengal.utils.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    "page_section_not_found_summary",
                    page=str(self.source_path),
                    section_path=str(self._section_path),
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
        Set the section this page belongs to (stores path, not object).

        This setter extracts the path from the Section object and stores it
        in _section_path, enabling stable references when Section objects
        are recreated during incremental rebuilds.

        Args:
            value: Section object or None
        """
        if value is None:
            self._section_path = None
        else:
            # Extract path from Section object
            self._section_path = value.path


__all__ = ["Page", "PageProxy"]
