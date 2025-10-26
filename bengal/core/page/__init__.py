"""
Page Object - Represents a single content page.

This module provides the main Page class, which combines multiple mixins
to provide a complete page interface while maintaining separation of concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from .computed import PageComputedMixin
from .metadata import PageMetadataMixin
from .navigation import PageNavigationMixin
from .operations import PageOperationsMixin
from .proxy import PageProxy
from .relationships import PageRelationshipsMixin


@dataclass
class Page(
    PageMetadataMixin,
    PageNavigationMixin,
    PageComputedMixin,
    PageRelationshipsMixin,
    PageOperationsMixin,
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
        source_path: Path to the source content file
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
    """

    # Class-level warning counter (shared across all Page instances)
    # This prevents unbounded memory growth in long-running dev servers where
    # pages are recreated frequently. Warnings are suppressed globally after
    # the first 3 occurrences per unique warning key.
    # The dict is bounded to max 100 entries (oldest removed when limit reached).
    _global_missing_section_warnings: ClassVar[dict[str, int]] = {}
    _MAX_WARNING_KEYS: ClassVar[int] = 100

    source_path: Path
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

    # References for navigation (set during site building)
    _site: Any | None = field(default=None, repr=False)
    # Path-based section reference (stable across rebuilds)
    _section_path: Path | None = field(default=None, repr=False)

    # Private cache for lazy toc_items property
    _toc_items_cache: list[dict[str, Any]] | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize computed fields."""
        if self.metadata:
            self.tags = self.metadata.get("tags", [])
            self.version = self.metadata.get("version")

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
