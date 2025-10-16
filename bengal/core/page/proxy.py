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

logger = get_logger(__name__)


class PageProxy:
    """
    Lazy-loaded page placeholder.

    Holds page metadata from cache and defers loading full content until
    accessed. Transparent to callers - implements Page-like interface.

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
        metadata: Any,
        loader: callable,
    ):
        """
        Initialize PageProxy with metadata and loader.

        Args:
            source_path: Path to source content file
            metadata: PageMetadata from cache (has title, date, tags, etc.)
            loader: Callable that loads full Page(source_path) -> Page
        """
        self.source_path = source_path
        self._metadata = metadata
        self._loader = loader
        self._lazy_loaded = False
        self._full_page: Page | None = None

        # Populate metadata fields from cache for immediate access
        self.title = metadata.title if hasattr(metadata, "title") else ""
        self.date = self._parse_date(metadata.date) if metadata.date else None
        self.tags = metadata.tags if metadata.tags else []
        self.section = metadata.section
        self.slug = metadata.slug
        self.weight = metadata.weight
        self.lang = metadata.lang

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse ISO date string to datetime."""
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
        """Get full metadata dict (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.metadata if self._full_page else {}

    @property
    def rendered_html(self) -> str:
        """Get rendered HTML (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.rendered_html if self._full_page else ""

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

    @property
    def toc_items(self) -> list[dict[str, Any]]:
        """Get TOC items (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.toc_items if self._full_page else []

    @property
    def output_path(self) -> Path | None:
        """Get output path (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.output_path if self._full_page else None

    @property
    def parsed_ast(self) -> Any:
        """Get parsed AST (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.parsed_ast if self._full_page else None

    @property
    def related_posts(self) -> list:
        """Get related posts (lazy-loaded)."""
        self._ensure_loaded()
        return self._full_page.related_posts if self._full_page else []

    @property
    def translation_key(self) -> str | None:
        """Get translation key."""
        self._ensure_loaded()
        return self._full_page.translation_key if self._full_page else None

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

    # ============================================================================
    # Methods - Delegate to full page
    # ============================================================================

    def extract_links(self) -> None:
        """Extract links from content."""
        self._ensure_loaded()
        if self._full_page:
            self._full_page.extract_links()

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
