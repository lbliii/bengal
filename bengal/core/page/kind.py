"""
PageKind - Canonical page classification for dispatch and context injection.

Provides a single source of truth for "what kind of page is this" used by
the renderer, content type system, and build phases. Replaces scattered
string comparisons (page.type == "tag") with type-safe enum dispatch.

RFC: rfc-generated-page-context-protocol
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.protocols import PageLike


class PageKind(StrEnum):
    """
    Canonical page classification for dispatch and context injection.

    Used by:
    - Renderer: _add_generated_page_context dispatch
    - phase_update_pages_list: tag/tag-index inclusion
    - Content type strategies: template selection
    """

    # Content pages (from disk)
    PAGE = "page"
    HOME = "home"
    SECTION_INDEX = "section-index"

    # Generated pages (orchestrator-created)
    TAG = "tag"
    TAG_INDEX = "tag-index"
    ARCHIVE = "archive"
    BLOG = "blog"
    CHANGELOG = "changelog"
    TUTORIAL = "tutorial"
    AUTODOC_PYTHON = "autodoc-python"
    AUTODOC_CLI = "autodoc-cli"

    @classmethod
    def from_page(cls, page: PageLike) -> PageKind:
        """
        Resolve PageKind from page metadata (single source of truth).

        For generated pages, uses metadata.type. For content pages,
        uses structural classification (home, section-index, page).
        """
        # Generated pages: use metadata type
        if getattr(page, "is_generated", False):
            page_type = getattr(page, "type", None) or (
                page.metadata.get("type") if hasattr(page, "metadata") else None
            )
            if page_type:
                return cls._from_generated_type(str(page_type)) or cls.PAGE
            return cls.PAGE

        # Structural classification for content pages
        if getattr(page, "is_home", False):
            return cls.HOME
        if getattr(page, "source_path", None) and str(getattr(page.source_path, "stem", "")) in (
            "_index",
            "index",
        ):
            return cls.SECTION_INDEX
        return cls.PAGE

    @classmethod
    def _from_generated_type(cls, page_type: str) -> PageKind | None:
        """Map metadata type string to PageKind."""
        mapping = {
            "tag": cls.TAG,
            "tag-index": cls.TAG_INDEX,
            "archive": cls.ARCHIVE,
            "blog": cls.BLOG,
            "changelog": cls.CHANGELOG,
            "tutorial": cls.TUTORIAL,
            "autodoc/python": cls.AUTODOC_PYTHON,
            "autodoc-python": cls.AUTODOC_PYTHON,
            "autodoc-cli": cls.AUTODOC_CLI,
        }
        return mapping.get(page_type)

    def is_generated_kind(self) -> bool:
        """True if this kind is for orchestrator-generated pages."""
        return self in (
            PageKind.TAG,
            PageKind.TAG_INDEX,
            PageKind.ARCHIVE,
            PageKind.BLOG,
            PageKind.CHANGELOG,
            PageKind.TUTORIAL,
            PageKind.AUTODOC_PYTHON,
            PageKind.AUTODOC_CLI,
        )
